# 피지수 야간 자동 학습 — 작업 스케줄러 등록
# 매일 02:00 실행. 관리자 권한 PowerShell에서 실행하거나 -RunLevel Highest로 자동 상승.
#
# 사용법:
#   PowerShell -ExecutionPolicy Bypass -File "D:\Git\AG-Forge\scripts\register_nightly_learn.ps1"

$PythonExe  = "C:\Users\USER\AppData\Local\Programs\Python\Python310\python.exe"
$ScriptPath = "D:\Git\AG-Forge\scripts\run_nightly_learn.py"
$WorkDir    = "D:\Git\AG-Forge"
$TaskName   = "PhysisNightlyLearn"

# Python 실행 파일 존재 확인
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python 실행 파일을 찾을 수 없습니다: $PythonExe"
    Write-Host "설치된 Python 경로를 확인하고 \$PythonExe 변수를 수정하세요."
    exit 1
}

# 스크립트 존재 확인
if (-not (Test-Path $ScriptPath)) {
    Write-Error "학습 스크립트를 찾을 수 없습니다: $ScriptPath"
    exit 1
}

$action   = New-ScheduledTaskAction `
                -Execute $PythonExe `
                -Argument $ScriptPath `
                -WorkingDirectory $WorkDir

$trigger  = New-ScheduledTaskTrigger -Daily -At "02:00"

$settings = New-ScheduledTaskSettingsSet `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
                -StartWhenAvailable `
                -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "피지수 야간 학습 스케줄 등록 완료: 매일 02:00"
Write-Host "  태스크명  : $TaskName"
Write-Host "  Python    : $PythonExe"
Write-Host "  스크립트  : $ScriptPath"
Write-Host "  로그 파일 : $WorkDir\learn_log.jsonl"
Write-Host ""
Write-Host "즉시 테스트: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "등록 확인  : Get-ScheduledTask -TaskName '$TaskName' | Format-List"
