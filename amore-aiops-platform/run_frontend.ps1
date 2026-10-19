Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path "node_modules")) {
    Write-Host "오류: frontend 의존성(node_modules)을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "먼저 루트 디렉토리에서 .\setup.ps1 를 실행하세요." -ForegroundColor Yellow
    exit 1
}
Write-Host "▶ 프론트엔드 개발 서버 시작 중..." -ForegroundColor Green
npm run dev
