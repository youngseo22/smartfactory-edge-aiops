Set-Location "$PSScriptRoot\backend"
$venvPy = ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "오류: 가상환경 인터프리터를 찾을 수 없습니다 ($venvPy)." -ForegroundColor Red
    Write-Host "먼저 루트 디렉토리에서 .\setup.ps1 를 실행하세요." -ForegroundColor Yellow
    exit 1
}
Write-Host "▶ 백엔드 서버 시작 중 (http://localhost:8000)..." -ForegroundColor Green
& $venvPy -m uvicorn main:app --host 0.0.0.0 --port 8000 @args
