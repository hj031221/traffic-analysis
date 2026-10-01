$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python run_all.py
    if ($LASTEXITCODE -ne 0) { throw "분석 실행 실패: 종료 코드 $LASTEXITCODE" }
} finally {
    Pop-Location
}
