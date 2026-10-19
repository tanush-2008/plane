$ErrorActionPreference = "Stop"
Set-Location "C:\Users\peddy\plane\apps\api"
Get-Content .env | Where-Object { $_ -match '=' -and -not $_.TrimStart().StartsWith('#') } | ForEach-Object {
    $idx = $_.IndexOf('=')
    $name = $_.Substring(0, $idx).Trim()
    $value = $_.Substring($idx + 1).Trim().Trim('"')
    $expanded = [regex]::Replace($value, '\$\{([A-Za-z_][A-Za-z0-9_]*)\}', {
        param($m)
        $refName = $m.Groups[1].Value
        $refVal = [System.Environment]::GetEnvironmentVariable($refName, 'Process')
        if ($null -eq $refVal) { "" } else { $refVal }
    })
    [System.Environment]::SetEnvironmentVariable($name, $expanded)
}
$env:DJANGO_SETTINGS_MODULE = "plane.settings.local"
& ".\venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
