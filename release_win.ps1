# release_win.ps1 - VoiceType4TW Clean Release Packager
$ReleaseFolder = "VoiceType4TW_Win_Stable_V92"
$ZipFile = "VoiceType4TW_Win_Stable_V92.zip"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   VoiceType4TW Clean Release Packager (Windows)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Cleanup existing release folders
if (Test-Path $ReleaseFolder) {
    Write-Host "[INFO] Cleaning up old release folder..."
    Remove-Item -Recurse -Force $ReleaseFolder
}
if (Test-Path $ZipFile) {
    Remove-Item -Force $ZipFile
}

# 2. Create new release structure
Write-Host "[INFO] Creating release folder: $ReleaseFolder..."
New-Item -ItemType Directory -Path $ReleaseFolder | Out-Null

# 3. Whitelist of folders to copy
$Folders = @(
    "actions", "assets", "audio", "hotkey", "llm", "output", "memory",
    "platform_layer", "soul", "stats", "stt", "ui", "utils", "vocab", "tools"
)

foreach ($folder in $Folders) {
    if (Test-Path $folder) {
        Write-Host "[INFO] Copying folder: $folder..."
        # Using Robocopy for better reliability and exclusion handling
        robocopy $folder "$ReleaseFolder\$folder" /E /XD __pycache__ /XF *.log *.pyc *.bak /NFL /NDL /NJH /NJS /nc /ns /np
    }
}

# 4. Whitelist of files to copy
$Files = @(
    "main.py", "paths.py", "config.py", "requirements-win.txt", 
    "setup_win.bat", "run_voicetype.bat", "README.md", "VERSION_TAG.txt",
    "create_shortcut.ps1", "安裝下載教學.MD"
)

foreach ($file in $Files) {
    if (Test-Path $file) {
        Write-Host "[INFO] Copying file: $file..."
        Copy-Item -Path $file -Destination "$ReleaseFolder\$file"
    }
}

# 5. ZIP the folder
Write-Host "[INFO] Compressing release into $ZipFile..."
Compress-Archive -Path $ReleaseFolder -DestinationPath $ZipFile -Force

Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Release Packaged Successfully!" -ForegroundColor Green
Write-Host "   Archive: $ZipFile" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
