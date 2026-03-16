# get_portable_python.ps1 - VoiceType4TW Portable Python Installer
$PythonVersion = "3.12.2"
$Url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$CurrentDir = Get-Location
$RuntimeDir = Join-Path $CurrentDir ".runtime"
$ZipFile = Join-Path $CurrentDir "python_embed.zip"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   VoiceType4TW Portable Python Setup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir | Out-Null
}

if (-not (Test-Path (Join-Path $RuntimeDir "python.exe"))) {
    Write-Host "[INFO] Downloading Python $PythonVersion Embedded..."
    try {
        Invoke-WebRequest -Uri $Url -OutFile $ZipFile
    } catch {
        Write-Error "Failed to download Python."
        exit 1
    }
    
    Write-Host "[INFO] Extracting..."
    try {
        Expand-Archive -Path $ZipFile -DestinationPath $RuntimeDir -Force
        Remove-Item $ZipFile
    } catch {
        Write-Error "Failed to extract Python zip."
        exit 1
    }
}

# 修正 ._pth 檔案
$PthFile = Get-ChildItem -Path $RuntimeDir -Filter "python*._pth" | Select-Object -First 1
if ($PthFile) {
    Write-Host "[INFO] Configuring path..."
    $Content = Get-Content $PthFile.FullName
    $NewContent = @()
    foreach ($line in $Content) {
        if ($line -match "^#import site") {
            $NewContent += "import site"
        } else {
            $NewContent += $line
        }
    }
    # 確保包含 .
    if (-not ($NewContent -contains ".")) {
        $NewContent = @(".") + $NewContent
    }
    $NewContent | Set-Content $PthFile.FullName
}

# 安裝 pip
$PipExe = Join-Path $RuntimeDir "Scripts\pip.exe"
if (-not (Test-Path $PipExe)) {
    Write-Host "[INFO] Installing pip..."
    $GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $GetPipFile = Join-Path $RuntimeDir "get-pip.py"
    Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipFile
    $PyExe = Join-Path $RuntimeDir "python.exe"
    & $PyExe $GetPipFile --no-warn-script-location
    Remove-Item $GetPipFile
}

Write-Host "[SUCCESS] Portable Python ready." -ForegroundColor Green
