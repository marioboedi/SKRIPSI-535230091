$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $appPython)) {
    $pythonCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        'C:\Python311\python.exe',
        'C:\Python312\python.exe'
    )
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $pythonCandidates += $pythonCommand.Source }
    $bootstrapPython = $null
    foreach ($candidate in $pythonCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            $version = & $candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
            if ($version -in @('3.11', '3.12')) { $bootstrapPython = $candidate; break }
        }
    }
    if (-not $bootstrapPython) {
        throw 'Install Python 3.11 or 3.12, then run this launcher again. See README.md.'
    }
    Write-Host 'Preparing the project environment...'
    & $bootstrapPython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project environment.' }
}

& $appPython -c 'import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ["streamlit", "spectralbridges", "sklearn", "altair", "pydeck", "matplotlib", "seaborn", "shapely"]) else 1)'
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing the app dependencies. Internet is needed on the first run...'
    & $appPython -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. See README.md.' }
}

Write-Host 'Jakarta Siaga is starting at http://localhost:8501'
Write-Host 'Keep this window open. Press Ctrl+C here to stop the app.'
& $appPython -m streamlit run app.py --server.headless=false
exit $LASTEXITCODE
