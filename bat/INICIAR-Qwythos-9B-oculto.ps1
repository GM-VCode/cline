# INICIAR-Qwythos-9B-oculto.ps1
# Inicia o servidor em janela oculta usando main.py
# ★ A configuração fica no arquivo .env (mesma pasta deste script)

# $dir = raiz do projeto (pasta pai de bat\, onde esta este script)
$dir = Split-Path -Parent $PSScriptRoot

# Usa o Python do venv se existir; senao, usa o py -3 do sistema
$pyExe = 'py.exe'
$pyArgs = @('-3')
if (Test-Path (Join-Path $dir '.venv\Scripts\python.exe')) {
  $pyExe = Join-Path $dir '.venv\Scripts\python.exe'
  $pyArgs = @()
}

Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Sobe o main.py em janela oculta.
# A saida dele vai para server_runner.log na mesma pasta.
Start-Process -FilePath $pyExe `
  -ArgumentList ($pyArgs + @((Join-Path $dir 'main.py'))) `
  -WorkingDirectory $dir `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $dir 'server_runner.log') `
  -RedirectStandardError (Join-Path $dir 'server_runner.err.log')

Write-Host "Iniciado em janela oculta. Config: .env"
Write-Host "Aguardando servidor subir (ate 120s)..."

# Le HOST e PORT do arquivo .env
$port = '8080'
$hostAddr = '127.0.0.1'
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

if ($ok) {
  Write-Host "PRONTO: http://${hostAddr}:${port}/v1 (Model ID: ver ALIAS no .env)"
} else {
  Write-Host "FALHOU - veja:"
  Write-Host "  $dir\server_runner.err.log"
  Write-Host "  C:\llama.cpp\server.err.log"
  if (Test-Path (Join-Path $dir 'server_runner.err.log')) {
    Get-Content (Join-Path $dir 'server_runner.err.log') -Tail 15
  }
}
Read-Host 'Pressione ENTER para fechar'
