param(
  [string]$Python = "python",
  [string]$Name = "Autoparser",
  [string]$OutputDir = ".\dist"
)

Write-Host "===> Creating venv and installing dependencies"
$venv = ".\.venv"
& $Python -m venv $venv
& "$venv\Scripts\pip.exe" install -r requirements.txt
& "$venv\Scripts\pip.exe" install pyinstaller

# Install browsers to local folder (bundled)
Write-Host "===> Installing Playwright Chromium to local ms-playwright folder"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\ms-playwright"
& "$venv\Scripts\python.exe" -m playwright install chromium

Write-Host "===> Building single EXE with PyInstaller"
$cmd = "$venv\Scripts\pyinstaller.exe --noconsole --name $Name ops/win/start_app.py " +
       "--add-data ""apps/api/admin;apps/api/admin"" " +
       "--add-data ""prompts;prompts"" " +
       "--add-data ""packages/schemas;packages/schemas"""
Invoke-Expression $cmd

# Copy bundled browsers into dist folder
Write-Host "===> Copying bundled browsers"
$bundleSrc = ".\ms-playwright"
$bundleDst = ".\dist\$Name\ms-playwright"
if (Test-Path $bundleSrc) {
  New-Item -ItemType Directory -Force -Path $bundleDst | Out-Null
  Copy-Item -Path "$bundleSrc\*" -Destination $bundleDst -Recurse -Force
} else {
  Write-Host "WARNING: ms-playwright was not found; installer will require first-run download."
}

# Optional: build installer with Inno Setup if ISCC is available
$iss = "ops\win\autoparser.iss"
if (Test-Path $iss) {
  if (Get-Command "iscc.exe" -ErrorAction SilentlyContinue) {
    Write-Host "===> Building installer with Inno Setup"
    & iscc.exe $iss /DMyAppName="$Name"
  } else {
    Write-Host "Inno Setup (iscc.exe) not found. To produce a .exe installer, install Inno Setup and re-run."
  }
}

Write-Host "===> Build complete. Portable EXE: dist\$Name\$Name.exe"
