# 피지수 엑셀 감시 자동 시작 — 작업 스케줄러 등록
# 로그인 시 자동 시작.
#
# 사용법 (관리자 PowerShell):
#   PowerShell -ExecutionPolicy Bypass -File "D:\Git\AG-Forge\scripts\register_excel_watcher.ps1"

$PythonExe  = "C:\Users\USER\AppData\Local\Programs\Python\Python310\python.exe"
$ScriptPath = "D:\Git\AG-Forge\scripts\excel_watcher.py"
$WorkDir    = "D:\Git\AG-Forge"
$TaskName   = "PhysisExcelWatcher"

# Python 실행 파일 존재 확인
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python 실행 파일을 찾을 수 없습니다: $PythonExe"
    Write-Host "설치된 Python 경로를 확인하고 `$PythonExe 변수를 수정하세요."
    exit 1
}

# 스크립트 존재 확인
if (-not (Test-Path $ScriptPath)) {
    Write-Error "감시 스크립트를 찾을 수 없습니다: $ScriptPath"
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkDir

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "엑셀 감시 등록 완료: 로그인 시 자동 시작"
Write-Host "  태스크명  : $TaskName"
Write-Host "  Python    : $PythonExe"
Write-Host "  스크립트  : $ScriptPath"
Write-Host "  감시 폴더 : $WorkDir\watch\"
Write-Host ""
Write-Host "즉시 시작 : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "등록 확인 : Get-ScheduledTask -TaskName '$TaskName' | Format-List"
Write-Host "제거      : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
