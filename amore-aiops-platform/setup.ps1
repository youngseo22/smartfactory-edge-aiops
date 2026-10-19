# Windows PowerShell: 가상환경 생성 + 의존성 설치 (.\setup.ps1 [-Gcp])
param([switch]$Gcp)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== AIOps Platform 환경 설정 시작 ===" -ForegroundColor Cyan

# 1. Python 감지
$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
} else {
    Write-Error "Python을 찾을 수 없습니다. Python 3.11 이상이 설치되어 있고 PATH에 등록되어 있는지 확인하세요."
    exit 1
}

# 2. 가상환경 생성 및 점검
$venvPy = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "▶ 가상환경 생성 중: backend\.venv" -ForegroundColor Yellow
    if (Test-Path "backend\.venv") {
        Remove-Item -Recurse -Force "backend\.venv"
    }
    & $pyCmd -m venv backend\.venv
}

if (-not (Test-Path $venvPy)) {
    Write-Error "가상환경 Python 인터프리터를 생성하지 못했습니다 ($venvPy)."
    exit 1
}

# 3. .env 파일 준비
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "▶ .env.example -> .env 복사 생성" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 4. 백엔드 의존성 설치
$req = if ($Gcp) { "requirements-gcp.txt" } else { "requirements.txt" }
Write-Host "▶ 백엔드 의존성 설치 중 ($req)..." -ForegroundColor Yellow
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r "backend\$req"

# 5. 프론트엔드 의존성 설치
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "▶ 프론트엔드 의존성 설치 중 (npm install)..." -ForegroundColor Yellow
    Push-Location frontend
    try {
        npm install
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "npm 명령어를 찾을 수 없습니다. Node.js를 설치한 뒤 frontend 디렉토리에서 npm install을 실행하세요."
}

Write-Host "`n✔ 설정 완료!" -ForegroundColor Green
Write-Host "  - 백엔드 실행: .\run_backend.ps1" -ForegroundColor Cyan
Write-Host "  - 프론트엔드 실행: .\run_frontend.ps1" -ForegroundColor Cyan
Write-Host "  (보안 정책 오류 발생 시: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 실행 후 재시도)" -ForegroundColor DarkGray
