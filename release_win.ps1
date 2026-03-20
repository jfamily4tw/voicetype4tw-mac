# release_win.ps1 - VoiceType4TW Clean Release Packager
# Usage:
#   .\release_win.ps1           → Full (CUDA + medium model bundled)
#   .\release_win.ps1 -Lite     → Lite (no CUDA, no model — downloads on first run)
param([switch]$Lite)

if ($Lite) {
    $ReleaseFolder = "VoiceType4TW_Win_Lite_V2960"
    $ZipFile       = "VoiceType4TW_Win_Lite_V2960.zip"
    $Edition       = "Lite"
} else {
    $ReleaseFolder = "VoiceType4TW_Win_Stable_V2960"
    $ZipFile       = "VoiceType4TW_Win_Stable_V2960.zip"
    $Edition       = "Full (CUDA + Model)"
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   VoiceType4TW Release Packager — $Edition" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Cleanup
if (Test-Path $ReleaseFolder) {
    Write-Host "[INFO] Cleaning up old release folder..."
    Remove-Item -Recurse -Force $ReleaseFolder
}
if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }

# 2. Create release structure
Write-Host "[INFO] Creating release folder: $ReleaseFolder..."
New-Item -ItemType Directory -Path $ReleaseFolder | Out-Null

# 3. Copy app folders
$Folders = @(
    "actions", "assets", "audio", "hotkey", "llm", "output", "memory",
    "platform_layer", "soul", "stats", "stt", "ui", "utils", "vocab", "tools"
)
foreach ($folder in $Folders) {
    if (Test-Path $folder) {
        Write-Host "[INFO] Copying folder: $folder..."
        robocopy $folder "$ReleaseFolder\$folder" /E /XD __pycache__ /XF *.log *.pyc *.bak /NFL /NDL /NJH /NJS /nc /ns /np
    }
}

# 3.5. Copy .runtime — Lite excludes nvidia (CUDA) packages
Write-Host "[INFO] Copying folder: .runtime..."
if ($Lite) {
    robocopy ".runtime" "$ReleaseFolder\.runtime" /E /XD __pycache__ nvidia /XF *.log *.pyc *.bak /NFL /NDL /NJH /NJS /nc /ns /np
    Write-Host "[INFO] Lite mode: CUDA (nvidia) packages excluded."
} else {
    robocopy ".runtime" "$ReleaseFolder\.runtime" /E /XD __pycache__ /XF *.log *.pyc *.bak /NFL /NDL /NJH /NJS /nc /ns /np
}

# 3.8. Bundle Whisper medium model (Full only)
if (-not $Lite) {
    $ModelSrc  = "$env:APPDATA\VoiceType4TW\whisper_models\models--Systran--faster-whisper-medium"
    $ModelDest = "$ReleaseFolder\bundled_models\models--Systran--faster-whisper-medium"
    if (Test-Path $ModelSrc) {
        Write-Host "[INFO] Bundling Whisper medium model..."
        New-Item -ItemType Directory -Path "$ReleaseFolder\bundled_models" -Force | Out-Null
        robocopy $ModelSrc $ModelDest /E /NFL /NDL /NJH /NJS /nc /ns /np
    } else {
        Write-Host "[WARN] Medium model not found at $ModelSrc — skipping."
    }
}

# 4. Copy root files
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

# 4.5. Normalize .bat to CRLF without BOM
Write-Host "[INFO] Normalizing line endings for .bat files..."
Get-ChildItem -Path $ReleaseFolder -Filter "*.bat" -Recurse | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    $content = $content -replace "`r`n", "`n" -replace "`n", "`r`n"
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($_.FullName, $content, $enc)
}

# 5. ZIP using .NET ZipFile (handles zip-within-zip unlike Compress-Archive)
Write-Host "[INFO] Compressing release into $ZipFile..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Resolve-Path $ReleaseFolder).Path,
    (Join-Path (Get-Location) $ZipFile)
)

Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Release Packaged: $ZipFile" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
