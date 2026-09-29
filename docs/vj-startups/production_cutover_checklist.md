# Production cutover checklist: moving www.vjstartup.com to the new site

Today `www.vjstartup.com` is served by the previous MongoDB-backed site (its API answers at
`/be/...` and its Google login at `authv2.vjstartup.com`). The new site (Postgres, connected to
the Plane admin panel) is deployed by the `main` branch of `vjstartups-main-website` onto the
`gamma` machine, but nothing public points at it yet. This is the ordered list for switching over.
See `deployment_topology.md` for which machine is which.

Each step says who normally does it. Do not skip the order: the early steps make the later ones
safe.

## A. Before touching anything public

1. **A `main` deploy is green.** Actions > Deploy Applications, latest run on `main`. Its step
   "Apply site database changes" must pass (it needs `PLANE_DATABASE_URL`, see topology doc).
2. **The data is imported.** Run the "Data operations" workflow in the Plane repo:
   `team-members`, then `problems-and-ideas` (dry run first, then apply). Check
   Plane admin > VJ Startups > Ecosystem Problems / Ideas show the records.
3. **Take a backup** of the database (every "apply" run does this automatically; the file is
   on the dev-ai host under `~/vj-backups/`). Keep one copy off that machine.
4. **Freeze the old site's data.** Between exporting the problems/ideas and the cutover, anything
   people submit on the old site is not in the new database. Either announce a short freeze or
   re-run `problems-and-ideas` (it is idempotent) right before the switch.

## B. Secrets and variables for the `vj-production` environment

Repository > Settings > Environments > `vj-production` (in `vjstartups-main-website`). The `main`
deploy reads exactly these:

| Name                                                                          | Kind      | Notes                                                                                                                |
| ----------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| `PLANE_DATABASE_URL`                                                          | secret    | `postgresql://USER:PASSWORD@10.100.0.15:5434/plane` (dev-ai's private IP)                                            |
| `PLANE_INTERNAL_TOKEN`                                                        | secret    | Must equal `PUBLIC_SITE_INTERNAL_TOKEN` in Plane's repo secrets                                                      |
| `PLANE_API_URL`                                                               | variable  | Plane's public URL, `https://vjos.vjstartup.com` (that is also the default)                                          |
| `GOOGLE_CLIENT_ID`                                                            | secret    | The Google OAuth client the login uses (server side check)                                                           |
| `ADMIN_EMAILS`                                                                | secret    | Emails auto-promoted to admin on login                                                                               |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`        | secrets   | Image uploads                                                                                                        |
| `PORT`                                                                        | secret    | Optional, defaults to 6220                                                                                           |
| `VITE_API_BASE_URL`                                                           | secret    | The public URL of the API the browser calls, e.g. `https://www.vjstartup.com/be`                                     |
| `VITE_GOOGLE_CLIENT`                                                          | secret    | The Google OAuth client ID the browser login uses                                                                    |
| `VITE_AUTH_URL`                                                               | secret    | Only a fallback: the login page calls `VITE_API_BASE_URL` + `/auth/google` first and uses this only if that is unset |
| `VITE_DEBUG_MODE`, `VITE_GOOGLE_SPREADSHEET_ID`, `VITE_GOOGLE_SHEETS_API_KEY` | secrets   | As used by the frontend                                                                                              |
| `CORS_ORIGINS`, `INSTITUTIONAL_EMAIL_DOMAINS`                                 | variables | Optional; defaults apply when unset                                                                                  |

Notes on these values (from checking the live site and from the site-code session; confirm before
relying on them):

- **Repository-level secrets also apply.** A secret set at the repository level is used by the
  `vj-production` deploy unless the environment sets its own. As of 2026-09-29 the repository
  level was reported to hold `GOOGLE_CLIENT_ID`, `PLANE_INTERNAL_TOKEN`, `PORT`,
  `VITE_GOOGLE_CLIENT` and `VITE_GOOGLE_SPREADSHEET_ID`, and the `vj-production` environment held
  only `PLANE_DATABASE_URL`. Still missing for production: `VITE_API_BASE_URL`, the three
  `CLOUDINARY_*` values and `ADMIN_EMAILS`.
- **Cloudinary.** The existing images (about 180 problem images) are served from the Cloudinary
  cloud named `dfwj0qzvz` (visible in the image URLs). `CLOUDINARY_CLOUD_NAME` must be that cloud
  and the API key and secret must be that account's, otherwise uploads fail and old images stay
  on the old account only. A different, disabled cloud name in someone's local `.env` will not
  work.
- **Google OAuth.** The OAuth client was reported to allow only `https://www.vjstartup.com` as an
  origin: sign-in from `https://vjstartup.com` or a preview URL fails with `redirect_uri_mismatch`
  until those origins are added in Google Cloud Console.
- **Check what `www` really points at.** One lookup on 2026-09-29 returned only
  `103.248.208.120`; the site-code session's lookup also returned `202.65.141.82`. Resolvers can
  disagree, so look up `www.vjstartup.com` at the DNS provider itself and find out what any second
  address is before changing routes.
- **Keep `env_file: ./backend/.env`** in `docker-compose.yml`. The backend image no longer
  contains a `.env` (`backend/.dockerignore` excludes it), so the container gets its settings
  only from compose.

Set secrets from a terminal with `--body` (a hidden paste can silently save an empty value):

```bash
gh secret set NAME --env vj-production --repo Vignana-Jyothi/vjstartups-main-website --body "value"
```

The frontend variables (`VITE_*`) are baked in at build time, so changing one needs a new deploy.
Re-run the latest `main` deploy after changing any of them.

## C. Prove the new site works before pointing anyone at it

The new frontend runs on `gamma` port 3005 and the API on port 6220.

1. Open `http://10.100.0.16:3005` from a machine on the private network (or through an SSH tunnel).
2. Sign in with Google using an email listed in `ADMIN_EMAILS`.
3. Submit a test problem and idea, approve them in Plane admin > Ecosystem Problems / Ideas,
   and check the approval e-mail arrives and the item shows as verified on the site.
4. Check the pages that read the shared data: problems, ideas, leaderboards, member directory.

## D. The switch (Pavani / whoever manages the front proxy on the .120 host)

1. **Route the API.** Requests for `www.vjstartup.com/be/*` must go to `gamma:6220`. (Today they go
   to the previous site's backend.)
2. **Route the site.** Requests for `www.vjstartup.com/*` must go to `gamma:3005`.
3. **Login.** The previous site logged in through `authv2.vjstartup.com`. The new backend has its
   own Google login (`POST /auth/google`, in `auth-api.js`) and the new frontend calls it through
   `VITE_API_BASE_URL`, so once step D1 routes `/be` to gamma:6220 the login goes there and
   `authv2` is no longer used. `VITE_GOOGLE_CLIENT` (browser) and `GOOGLE_CLIENT_ID` (server) must
   be the same OAuth client, and that client in Google Cloud Console must list
   `https://www.vjstartup.com` (and `https://vjstartup.com`) as authorised JavaScript origins.
   Existing sessions from the previous site will not carry over: people sign in again.
4. **The bare domain.** `vjstartup.com` has no DNS record today. Add one (or a redirect to `www`).
   Verification e-mails link to the address set in Plane's `VJ_PUBLIC_SITE_URL` variable (default
   `https://www.vjstartup.com`); change that variable if the bare domain becomes the main one.
5. **Certificates.** `dev-vj.vjstartup.com` currently serves a certificate for the wrong host name;
   check the proxy's certificate for every name it serves.

## E. After the switch

1. Watch the first hour: sign in, submit, approve, check the leaderboard.
2. Keep the previous site running (unrouted) for a week so the switch can be reversed by changing
   the two routes back.
3. Remove the temporary diagnostic endpoints from Plane (`internal/diagnose-*`) if that has not
   been done, and rotate the shared token once the cutover is finished.
4. Change the database password from the default and restrict port 5434 to gamma's address
   (see `deployment_topology.md`).

## Rollback

Point the two routes (D1, D2) back at the previous site. Nothing in the new database is deleted by
that; imports can be re-run later.
