$ErrorActionPreference = "Stop"
Set-Location "C:\Users\peddy\plane"
$env:CI = "true"
& pnpm dev
