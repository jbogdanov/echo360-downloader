$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv (Join-Path $PSScriptRoot '.venv')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv (Join-Path $PSScriptRoot '.venv')
    } else {
        throw 'Python 3.10 or newer is required. Install Python for Windows with the launcher, then run SETUP.cmd again.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the private Python environment.' }
}
& $venvPython -c 'import sys; sys.exit(sys.version_info < (3,10))'
if ($LASTEXITCODE -ne 0) { throw 'Python is too old.' }
& $venvPython -m pip --disable-pip-version-check install --progress-bar off -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection and run SETUP.cmd again.' }
& $venvPython -c "import imageio_ffmpeg; from PIL import Image; print(imageio_ffmpeg.get_ffmpeg_exe())"
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Host 'Setup complete. Double-click START.cmd.'
