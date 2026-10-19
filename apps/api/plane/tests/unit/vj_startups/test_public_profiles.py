# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import datetime
from types import SimpleNamespace

import pytest

from plane.vj_startups.services import profile_activity as activity
from plane.vj_startups.services import profile_handle as handles
from plane.vj_startups.views.profiles import clean_profile_update, public_photo

D = datetime.date


@pytest.mark.unit
class TestHandles:
    def test_valid_handle_is_lower_cased_and_trimmed(self):
        assert handles.validate_handle("  Tanush-P ") == "tanush-p"

    @pytest.mark.parametrize(
        "bad", ["", "ab", "a" * 31, "-abc", "abc-", "a--b", "has space", "under_score", "dot.name"]
    )
    def test_malformed_handles_are_rejected(self, bad):
        with pytest.raises(handles.HandleError):
            handles.validate_handle(bad)

    @pytest.mark.parametrize("word", ["admin", "API", "settings", "vjos"])
    def test_reserved_words_are_rejected(self, word):
        with pytest.raises(handles.HandleError):
            handles.validate_handle(word)

    def test_suggestion_comes_from_the_name(self):
        assert handles.suggest_handle("Asha", "Rao", "a@x.in", lambda h, e: False) == "asha-rao"

    def test_suggestion_falls_back_to_the_email_then_numbers_a_clash(self):
        taken = {"asha-rao", "asha-rao2"}
        assert handles.suggest_handle("Asha", "Rao", "a@x.in", lambda h, e: h in taken) == "asha-rao3"
        assert handles.suggest_handle("", "", "kiran.k@x.in", lambda h, e: False) == "kirank"

    def test_suggestion_still_works_for_a_nameless_account(self):
        assert handles.suggest_handle("", "", "", lambda h, e: False) == "user"
        assert handles.suggest_handle("", "", "", lambda h, e: h == "user") == "user2"

    def test_suggestion_stays_within_the_length_limit(self):
        handle = handles.suggest_handle("A" * 50, "", "", lambda h, e: h == "a" * 30)
        assert len(handle) <= handles.HANDLE_MAX_LENGTH and handle.startswith("a")


@pytest.mark.unit
class TestIntensityLevels:
    def test_no_activity_is_level_zero(self):
        assert activity.level_for(0, 10) == 0
        assert activity.level_for(5, 0) == 0

    def test_levels_scale_to_the_busiest_day(self):
        assert [activity.level_for(n, 8) for n in (1, 2, 3, 4, 5, 6, 7, 8)] == [1, 1, 2, 2, 3, 3, 4, 4]

    def test_one_contribution_is_visible_even_on_a_very_busy_calendar(self):
        assert activity.level_for(1, 400) == 1


@pytest.mark.unit
class TestStreaks:
    def test_no_activity(self):
        assert activity.streaks([], D(2026, 10, 19)) == (0, 0)

    def test_current_streak_counts_back_from_today(self):
        days = [D(2026, 10, 17), D(2026, 10, 18), D(2026, 10, 19)]
        assert activity.streaks(days, D(2026, 10, 19)) == (3, 3)

    def test_an_empty_today_does_not_reset_the_streak(self):
        days = [D(2026, 10, 17), D(2026, 10, 18)]
        assert activity.streaks(days, D(2026, 10, 19)) == (2, 2)

    def test_a_gap_breaks_the_streak_but_keeps_the_longest(self):
        days = [D(2026, 10, 1), D(2026, 10, 2), D(2026, 10, 3), D(2026, 10, 18)]
        assert activity.streaks(days, D(2026, 10, 19)) == (1, 3)

    def test_stale_activity_has_no_current_streak(self):
        assert activity.streaks([D(2026, 9, 1)], D(2026, 10, 19)) == (0, 1)


@pytest.mark.unit
class TestCalendar:
    START, END = D(2025, 10, 20), D(2026, 10, 19)

    def test_days_are_sparse_summed_and_levelled(self):
        per_kind = {
            "completed": {D(2026, 10, 18): 3, D(2026, 10, 19): 1},
            "comments": {D(2026, 10, 18): 1},
            "pages": {D(2026, 10, 1): 2},
        }
        cal = activity.build_calendar(per_kind, self.START, self.END)

        assert cal["total"] == 7
        assert cal["active_days"] == 3
        assert cal["max_daily"] == 4
        assert cal["breakdown"] == {"completed": 4, "created": 0, "comments": 1, "pages": 2}
        busiest = next(d for d in cal["days"] if d["date"] == "2026-10-18")
        assert (busiest["count"], busiest["level"], busiest["completed"], busiest["comments"]) == (4, 4, 3, 1)
        assert [d["date"] for d in cal["days"]] == ["2026-10-01", "2026-10-18", "2026-10-19"]
        assert cal["current_streak"] == 2

    def test_activity_outside_the_window_is_ignored(self):
        cal = activity.build_calendar({"created": {D(2024, 1, 1): 9, D(2027, 1, 1): 9}}, self.START, self.END)
        assert cal["total"] == 0 and cal["days"] == []

    def test_empty_calendar_is_well_formed(self):
        cal = activity.build_calendar({}, self.START, self.END)
        assert cal["range"] == {"from": "2025-10-20", "to": "2026-10-19"}
        assert (cal["current_streak"], cal["longest_streak"], cal["max_daily"]) == (0, 0, 0)

    def test_window_ends_today_in_the_club_timezone(self):
        # 20:00 UTC on the 18th is already 01:30 on the 19th in India.
        now = datetime.datetime(2026, 10, 18, 20, 0, tzinfo=datetime.timezone.utc)
        start, end, _ = activity.window(365, "Asia/Kolkata", now)
        assert end == D(2026, 10, 19)
        assert (end - start).days == 364


@pytest.mark.unit
class TestProfileEdit:
    def test_valid_edit_is_cleaned(self):
        cleaned, errors = clean_profile_update(
            {
                "handle": "Asha-Rao",
                "profile_visibility": "PUBLIC",
                "bio": "  builds things ",
                "skills": ["Python", " python ", "React", ""],
                "github_url": "https://github.com/asha",
                "linkedin_url": "https://www.linkedin.com/in/asha",
                "portfolio_url": "https://asha.dev",
            }
        )
        assert errors == {}
        assert cleaned == {
            "handle": "asha-rao",
            "profile_visibility": "public",
            "bio": "builds things",
            "skills": ["Python", "React"],
            "github_url": "https://github.com/asha",
            "linkedin_url": "https://www.linkedin.com/in/asha",
            "portfolio_url": "https://asha.dev",
        }

    def test_fields_a_member_must_not_control_are_ignored(self):
        cleaned, errors = clean_profile_update(
            {"role": "Admin", "reputation_score": 999, "wing": "x", "public_role": "ADMIN", "is_club_member": True}
        )
        assert cleaned == {} and errors == {}

    def test_bad_values_are_reported_per_field(self):
        _, errors = clean_profile_update(
            {
                "handle": "a",
                "profile_visibility": "everyone",
                "bio": "x" * 1001,
                "skills": "python",
                "github_url": "https://evil.example/asha",
                "linkedin_url": "javascript:alert(1)",
                "portfolio_url": 12,
            }
        )
        assert set(errors) == {
            "handle",
            "profile_visibility",
            "bio",
            "skills",
            "github_url",
            "linkedin_url",
            "portfolio_url",
        }

    def test_lookalike_hosts_do_not_pass_the_github_check(self):
        _, errors = clean_profile_update({"github_url": "https://notgithub.com/asha"})
        assert "github_url" in errors
        _, errors = clean_profile_update({"github_url": "https://gist.github.com/asha"})
        assert errors == {}

    def test_a_link_can_be_cleared(self):
        cleaned, errors = clean_profile_update({"github_url": ""})
        assert cleaned == {"github_url": ""} and errors == {}

    def test_too_many_skills_are_rejected(self):
        _, errors = clean_profile_update({"skills": [f"s{i}" for i in range(21)]})
        assert "skills" in errors


@pytest.mark.unit
class TestPublicPhoto:
    def _profile(self, photo, avatar):
        return SimpleNamespace(photo_url=photo, user=SimpleNamespace(avatar=avatar))

    def test_sheet_photo_wins_then_web_avatar_and_never_an_internal_path(self):
        assert public_photo(self._profile("https://x/s.jpg", "https://x/a.jpg")) == "https://x/s.jpg"
        assert public_photo(self._profile(None, "https://x/a.jpg")) == "https://x/a.jpg"
        assert public_photo(self._profile(None, "/uploads/a.png")) == ""
