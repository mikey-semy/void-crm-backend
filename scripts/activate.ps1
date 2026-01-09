# Переходим в корневую директорию
Set-Location $PSScriptRoot/..

# Запускаем setup.ps1
./scripts/setup.ps1

# Запускаем воркер в фоне
Write-Host "🔄 Запускаю воркер в фоне..." -ForegroundColor Cyan
$workerJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    uv run worker
}
Write-Host "✅ Воркер запущен (Job ID: $($workerJob.Id))" -ForegroundColor Green

# Регистрируем остановку воркера при выходе
Register-EngineEvent PowerShell.Exiting -Action {
    Write-Host "🛑 Останавливаю воркер..." -ForegroundColor Cyan
    Stop-Job $workerJob -ErrorAction SilentlyContinue
    Remove-Job $workerJob -ErrorAction SilentlyContinue
}

# Запускаем dev режим из корня
Write-Host "🚀 Запускаю dev режим..." -ForegroundColor Cyan
try {
    uv run dev
} finally {
    # Останавливаем воркер при завершении
    Write-Host "🛑 Останавливаю воркер..." -ForegroundColor Cyan
    Stop-Job $workerJob -ErrorAction SilentlyContinue
    Remove-Job $workerJob -ErrorAction SilentlyContinue
    Write-Host "✅ Воркер остановлен" -ForegroundColor Green
}
