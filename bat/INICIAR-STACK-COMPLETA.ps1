# INICIAR-STACK-COMPLETA.ps1
# Sobe a stack inteira: modelo (main.py) + proxy (:8081) e valida as duas portas.
# A configuracao fica no .env da raiz (PORT do modelo, etc).

$dir = Split-Path -Parent $PSScriptRoot
$pyExe = 'py.exe'
$pyArgs = @('-3')
if (Test-Path (Join-Path $dir '.venv\Scripts\python.exe')) {
  $pyExe = Join-Path $dir '.venv\Scripts\python.exe'
  $pyArgs = @()
}

# 1) Limpeza: derruba residuos de execucoes anteriores (evita porta ocupada)
Write-Host "== 1/4 Derrubando residuos (modelo/proxy antigos)..."
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  if ($_.CommandLine -match 'main\.py|tools\\proxy\.py|tools/proxy\.py') {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep -Seconds 2

# 2) Sob o modelo em janela oculta
Write-Host "== 2/4 Subindo o modelo (main.py)..."
Start-Process -FilePath $pyExe `
  -ArgumentList ($pyArgs + @((Join-Path $dir 'main.py'))) `
  -WorkingDirectory $dir `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $dir 'logs\proxy_and_server\stack_server.log') `
  -RedirectStandardError (Join-Path $dir 'logs\proxy_and_server\stack_server.err.log')

# Le HOST/PORT do .env
$port = '8080'; $hostAddr = '127.0.0.1'
$envFile = Join-Path $dir '.env'
if (Test-Path $envFile) {
  $m = Select-String -Path $envFile -Pattern '^\s*PORT\s*=\s*(\d+)'
  if ($m) { $port = $m.Matches[0].Groups[1].Value }
  $m = Select-String -Path $envFile -Pattern '^\s*HOST\s*=\s*(.+)$'
  if ($m) { $hostAddr = $m.Matches[0].Groups[1].Value.Trim() }
}
$healthUrl = "http://${hostAddr}:${port}/health"

$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 2
  try { $h = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3; if ($h.status -eq 'ok') { $ok = $true; break } } catch {}
}
if (-not $ok) {
  Write-Host "FALHOU: modelo nao subiu em $healthUrl"
  if (Test-Path (Join-Path $dir 'logs\proxy_and_server\stack_server.err.log')) { Get-Content (Join-Path $dir 'logs\proxy_and_server\stack_server.err.log') -Tail 15 }
  Read-Host 'Pressione ENTER para fechar'; exit 1
}
Write-Host "   MODELO PRONTO: http://${hostAddr}:${port}/v1"

# 3) Sob o proxy :8081 (ponte para o Cline)
Write-Host "== 3/4 Subindo o proxy (:8081)..."
Start-Process -FilePath $pyExe `
  -ArgumentList ($pyArgs + @((Join-Path $dir 'tools\proxy.py'))) `
  -WorkingDirectory $dir `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $dir 'logs\proxy_and_server\stack_proxy.log') `
  -RedirectStandardError (Join-Path $dir 'logs\proxy_and_server\stack_proxy.err.log')

$proxyOk = $false
for ($i = 0; $i -lt 15; $i++) {
  Start-Sleep -Seconds 2
  try { $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/health' -TimeoutSec 3; if ($h.status -eq 'ok') { $proxyOk = $true; break } } catch {}
}

# 4) Status final
Write-Host "== 4/4 Status"
if ($proxyOk) {
  Write-Host "STACK PRONTA: modelo ${hostAddr}:${port} + proxy :8081 -> aponte o Cline para http://127.0.0.1:8081/v1"
} else {
  Write-Host "AVISO: modelo OK, mas proxy nao respondeu em :8081 (veja logs\proxy_and_server\stack_proxy.err.log)"
}
Read-Host 'Pressione ENTER para fechar'
