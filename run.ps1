# ¿Le creo? — arranque en un solo comando (Windows)
#   powershell -ExecutionPolicy Bypass -File .\run.ps1            → instala lo que falte y levanta todo
#   powershell -ExecutionPolicy Bypass -File .\run.ps1 -SinTunel  → sin túnel para el celular
#   powershell -ExecutionPolicy Bypass -File .\run.ps1 -Detener   → apaga la app (Postgres sigue en Docker)
param([switch]$SinTunel, [switch]$Detener)

$raiz = $PSScriptRoot
Set-Location $raiz
function Paso($t) { Write-Host "`n▶ $t" -ForegroundColor Cyan }
function Bien($t) { Write-Host "  ✓ $t" -ForegroundColor Green }
function Alto($t) { Write-Host "  ✗ $t" -ForegroundColor Red; exit 1 }

if ($Detener) { & (Join-Path $raiz "scripts\demo.ps1") -Detener; exit 0 }

Paso "Python 3.11+"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Alto "No encontré Python. Instala Python 3.11 o superior y vuelve a correr." }
$version = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$version -lt [version]"3.11") { Alto "Tienes Python $version; se necesita 3.11 o superior." }
Bien "Python $version"

Paso "Entorno virtual y dependencias"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & python -m venv .venv; Bien "Creado .venv" }
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { Alto "Falló la instalación de requirements.txt" }
Bien "Dependencias instaladas"

Paso "Credenciales (.env)"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Alto "Creé .env desde .env.example. Llena GOOGLE_API_KEY, MODELO_GOOGLE (y GROQ_* para audio y respaldo) y vuelve a correr."
}
Bien ".env presente"

Paso "Postgres en Docker y semillas"
cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) { Write-Host "  Docker no responde: demo.ps1 intentará abrir Docker Desktop." }
else {
    cmd /c "docker compose up -d >nul 2>&1"
    $fin = (Get-Date).AddSeconds(60)
    do { Start-Sleep 2; cmd /c "docker exec lecreo-db pg_isready -U lecreo >nul 2>&1" } until ($LASTEXITCODE -eq 0 -or (Get-Date) -gt $fin)
    & .\.venv\Scripts\python.exe scripts\cargar_semillas.py
    if ($LASTEXITCODE -ne 0) { Alto "No se pudieron cargar las semillas" }
    Bien "Semillas cargadas (es idempotente: se puede repetir)"
}

& (Join-Path $raiz "scripts\demo.ps1") -SinTunel:$SinTunel
