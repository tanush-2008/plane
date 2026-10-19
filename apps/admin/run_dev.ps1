$ErrorActionPreference = "Stop"
Set-Location "C:\Users\peddy\plane\apps\admin"
$env:CI = "true"
& ".\node_modules\.bin\react-router.CMD" dev --port 3001
