# Levanta todo para la demo de ¿Le creo?
#   .\scripts\demo.ps1            → Postgres + app para compartir + Streamlit + túnel HTTPS
#   .\scripts\demo.ps1 -SinTunel  → igual, pero solo en este computador
#   .\scripts\demo.ps1 -Detener   → apaga lo que levantó este script
param(
    [switch]$SinTunel,
    [switch]$Detener,
    # Por defecto busca cloudflared junto al proyecto (..\herramientas\cloudflared) o en el PATH.
    [string]$Cloudflared = (Join-Path $PSScriptRoot "..\..\herramientas\cloudflared\cloudflared.exe")
)

$raiz = Split-Path $PSScriptRoot -Parent
$python = Join-Path $raiz ".venv\Scripts\python.exe"
$streamlit = Join-Path $raiz ".venv\Scripts\streamlit.exe"
$registro = Join-Path $env:TEMP "lecreo-compartir.log"
$registroTunel = Join-Path $env:TEMP "lecreo-tunel.log"

function Paso($texto) { Write-Host "`n▶ $texto" -ForegroundColor Cyan }
function Bien($texto) { Write-Host "  ✓ $texto" -ForegroundColor Green }
function Mal($texto)  { Write-Host "  ✗ $texto" -ForegroundColor Red }

function Detener-Todo {
    Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq "python.exe" -and $_.CommandLine -match "compartir\.py") -or
        ($_.Name -match "streamlit|python" -and $_.CommandLine -match "app_streamlit\.py") -or
        ($_.Name -eq "cloudflared.exe")
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

if ($Detener) {
    Detener-Todo
    Bien "Apagados la app para compartir, Streamlit y el túnel (Postgres sigue en Docker)."
    exit 0
}

Paso "Docker"
$docker = docker info --format "{{.ServerVersion}}" 2>$null
if (-not $docker) {
    $exe = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"
    if (-not (Test-Path $exe)) { $exe = "C:\Program Files\Docker\Docker\Docker Desktop.exe" }
    if (Test-Path $exe) { Start-Process $exe; Write-Host "  Abriendo Docker Desktop (puede tardar un par de minutos)..." }
    $fin = (Get-Date).AddMinutes(4)
    do { Start-Sleep -Seconds 5; $docker = docker info --format "{{.ServerVersion}}" 2>$null } until ($docker -or (Get-Date) -gt $fin)
}
if (-not $docker) { Mal "Docker no arrancó. Ábrelo a mano, espera 'Engine running' y vuelve a correr este script."; exit 1 }
Bien "Docker $docker"

Paso "Postgres"
Push-Location $raiz
docker compose up -d 2>$null | Out-Null
Pop-Location
$fin = (Get-Date).AddSeconds(40)
do { Start-Sleep -Seconds 2; $pg = docker exec lecreo-db pg_isready -U lecreo -d lecreo 2>$null } until ($pg -match "accepting" -or (Get-Date) -gt $fin)
if ($pg -notmatch "accepting") { Mal "Postgres no responde."; exit 1 }
Bien "Postgres listo (puerto 5433)"

Paso "Configuración del modelo"
Push-Location $raiz
$modelo = & $python -c "from app import config; print(config.PROVEEDOR + ' / ' + config.modelo())" 2>$null
Pop-Location
if (-not $modelo) { Mal "Falta el modelo o la llave en .env."; exit 1 }
Bien $modelo

Paso "Apagando copias anteriores"
Detener-Todo
Start-Sleep -Seconds 1
Bien "Sin servidores duplicados"

Paso "App para compartir (puerto 8600) y Streamlit (puerto 8501)"
Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList "-u", "ui\compartir.py" -WorkingDirectory $raiz -RedirectStandardOutput $registro | Out-Null
Start-Process -WindowStyle Hidden -FilePath $streamlit -ArgumentList "run", "ui\app_streamlit.py", "--server.headless", "true", "--server.port", "8501" -WorkingDirectory $raiz -RedirectStandardOutput (Join-Path $env:TEMP "lecreo-streamlit.log") -RedirectStandardError (Join-Path $env:TEMP "lecreo-streamlit.err") | Out-Null
$fin = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Seconds 2
    $a = try { (Invoke-WebRequest -UseBasicParsing http://localhost:8600 -TimeoutSec 3).StatusCode } catch { 0 }
    $b = try { (Invoke-WebRequest -UseBasicParsing http://localhost:8501 -TimeoutSec 3).StatusCode } catch { 0 }
} until (($a -eq 200 -and $b -eq 200) -or (Get-Date) -gt $fin)
if ($a -eq 200) { Bien "Compartir: http://localhost:8600" } else { Mal "La app para compartir no respondió" }
if ($b -eq 200) { Bien "Streamlit: http://localhost:8501" } else { Mal "Streamlit no respondió" }

$url = $null
if (-not $SinTunel) {
    Paso "Túnel HTTPS para el celular"
    if (-not (Test-Path $Cloudflared)) { $c = Get-Command cloudflared -ErrorAction SilentlyContinue; if ($c) { $Cloudflared = $c.Source } }
    if (-not (Test-Path $Cloudflared)) {
        Mal "No encontré cloudflared.exe. Sin túnel solo funciona en este computador."
    } else {
        Remove-Item $registroTunel -ErrorAction SilentlyContinue
        Start-Process -WindowStyle Hidden -FilePath $Cloudflared -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://localhost:8600", "--logfile", $registroTunel -RedirectStandardOutput (Join-Path $env:TEMP "lecreo-tunel.out") -RedirectStandardError (Join-Path $env:TEMP "lecreo-tunel.err") | Out-Null
        $fin = (Get-Date).AddSeconds(45)
        do { Start-Sleep -Seconds 2; if (Test-Path $registroTunel) { $url = (Select-String -Path $registroTunel -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1).Matches.Value } } until ($url -or (Get-Date) -gt $fin)
        if ($url) {
            # Un túnel nuevo puede tardar uno o dos minutos en propagarse.
            $fin = (Get-Date).AddSeconds(120); $ok = $false
            do { try { $ok = (Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 8).StatusCode -eq 200 } catch { Start-Sleep -Seconds 3 } } until ($ok -or (Get-Date) -gt $fin)
            if ($ok) { Bien "Túnel activo" } else { Mal "El túnel abrió pero todavía no responde; espera unos segundos" }
        } else { Mal "No apareció la dirección del túnel" }
    }
}

Write-Host "`n════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  ¿Le creo? listo para la demo" -ForegroundColor Magenta
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  En este PC:   http://localhost:8600   (compartir / pegar)"
Write-Host "                http://localhost:8501   (Streamlit con traza)"
if ($url) {
    Write-Host "  Celular:      $url" -ForegroundColor Yellow
    Write-Host "                Chrome → ⋮ → Instalar app (la dirección cambia cada vez:"
    Write-Host "                si ya estaba instalada con otra, desinstálala y vuelve a instalar)"
}
Write-Host "  Registro:     $registro  (nunca guarda el texto de los mensajes)"
Write-Host "  Para apagar:  .\scripts\demo.ps1 -Detener"
