$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backendRoot = Join-Path $projectRoot "apps\backend"
$mobileRoot = Join-Path $projectRoot "apps\mobile"
$runtimeRoot = Join-Path $projectRoot ".runtime"

if (-not (Test-Path $pythonPath) -or -not (Test-Path (Join-Path $mobileRoot "node_modules"))) {
    throw "Dependencies are missing. Run 'npm run setup' first."
}

function Test-LocalTcpPort {
    param([int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $connection.Wait(300)) {
            return $false
        }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

foreach ($port in @(8000, 8081)) {
    if (Test-LocalTcpPort -Port $port) {
        throw "Port $port is already in use. Stop the existing local server with Ctrl+C, then run 'npm run dev' again."
    }
}

$defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
    Where-Object { $_.NextHop -ne "0.0.0.0" } |
    Sort-Object RouteMetric, InterfaceMetric |
    Select-Object -First 1

$lanIp = if ($defaultRoute) {
    Get-NetIPAddress -InterfaceIndex $defaultRoute.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "169.254.*" } |
        Select-Object -ExpandProperty IPAddress -First 1
} else {
    $null
}

if (-not $lanIp) {
    throw "No active LAN IPv4 address was found. Connect this PC and phone to the same network."
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
$backendOut = Join-Path $runtimeRoot "backend.out.log"
$backendErr = Join-Path $runtimeRoot "backend.error.log"
$workerOut = Join-Path $runtimeRoot "celery-worker.out.log"
$workerErr = Join-Path $runtimeRoot "celery-worker.error.log"
$beatOut = Join-Path $runtimeRoot "celery-beat.out.log"
$beatErr = Join-Path $runtimeRoot "celery-beat.error.log"

$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost,$lanIp"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:8081,http://127.0.0.1:8081,http://${lanIp}:8081"
$env:HAIRDOC_DEV_BACKEND_ORIGIN = "http://127.0.0.1:8000"
$env:EXPO_PUBLIC_REALTIME_API_URL = "http://${lanIp}:8000/api/v1"

& $pythonPath (Join-Path $backendRoot "manage.py") migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed. If DATABASE_URL uses the included PostgreSQL service, start Docker Desktop and run 'docker compose up -d', then retry."
}

$backend = Start-Process -FilePath $pythonPath `
    -ArgumentList @("manage.py", "runserver", "0.0.0.0:8000", "--noreload") `
    -WorkingDirectory $backendRoot `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -WindowStyle Hidden `
    -PassThru
$worker = $null
$beat = $null

try {
    $ready = $false
    $lastProbeError = "No response received."
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $backend.Refresh()
        if ($backend.HasExited) {
            break
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health/" -TimeoutSec 2
            if ($health.status -eq "ok") {
                $ready = $true
                break
            }
            $lastProbeError = "Health endpoint returned an unexpected response."
        } catch {
            $lastProbeError = $_.Exception.Message
            Start-Sleep -Milliseconds 250
        }
    }

    if (-not $ready) {
        $details = if (Test-Path $backendErr) { Get-Content -Raw $backendErr } else { "No backend log was created." }
        throw "Django did not become ready. Last health check: $lastProbeError`n$details"
    }

    try {
        $lanHealth = Invoke-RestMethod -Uri "http://${lanIp}:8000/api/v1/health/" -TimeoutSec 3
        if ($lanHealth.status -ne "ok") {
            throw "Unexpected health response."
        }
    } catch {
        throw "Django works on localhost but not on the LAN address ${lanIp}. Check the active network adapter and Windows Firewall. $($_.Exception.Message)"
    }

    $worker = Start-Process -FilePath $pythonPath `
        -ArgumentList @("-m", "celery", "-A", "config", "worker", "--pool=solo", "--loglevel=INFO") `
        -WorkingDirectory $backendRoot `
        -RedirectStandardOutput $workerOut `
        -RedirectStandardError $workerErr `
        -WindowStyle Hidden `
        -PassThru
    $beat = Start-Process -FilePath $pythonPath `
        -ArgumentList @("-m", "celery", "-A", "config", "beat", "--loglevel=INFO") `
        -WorkingDirectory $backendRoot `
        -RedirectStandardOutput $beatOut `
        -RedirectStandardError $beatErr `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Milliseconds 750
    $worker.Refresh()
    $beat.Refresh()
    if ($worker.HasExited -or $beat.HasExited) {
        $workerDetails = if (Test-Path $workerErr) { Get-Content -Raw $workerErr } else { "No worker log was created." }
        $beatDetails = if (Test-Path $beatErr) { Get-Content -Raw $beatErr } else { "No beat log was created." }
        throw "The notification worker or reminder scheduler did not start.`nWorker: $workerDetails`nScheduler: $beatDetails"
    }

    Write-Host "Backend: http://${lanIp}:8000/api/v1/health/" -ForegroundColor Green
    Write-Host "Notification worker and appointment reminder scheduler are running." -ForegroundColor Green
    Write-Host "Expo Go is starting through a tunnel. Scan the QR code Expo prints below." -ForegroundColor Cyan
    Write-Host "Keep this terminal open; stopping it also stops the backend." -ForegroundColor Cyan

    $tunnelAttempts = 3
    for ($attempt = 1; $attempt -le $tunnelAttempts; $attempt++) {
        if ($attempt -gt 1) {
            Write-Host "Retrying Expo tunnel ($attempt/$tunnelAttempts)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 4
            npm run start --prefix $mobileRoot -- --go --tunnel
        } else {
            npm run start --prefix $mobileRoot -- --go --tunnel --clear
        }

        $expoExitCode = $LASTEXITCODE
        if ($expoExitCode -eq 0 -or $expoExitCode -in @(130, -1073741510)) {
            break
        }

        if ($attempt -eq $tunnelAttempts) {
            throw "Expo's ngrok tunnel failed after $tunnelAttempts attempts. Check https://status.ngrok.com, temporarily disable any VPN/proxy, and allow Node.js/ngrok through antivirus or firewall before retrying 'npm run dev'."
        }
    }
} finally {
    if ($beat -and -not $beat.HasExited) {
        Stop-Process -Id $beat.Id -Force -ErrorAction SilentlyContinue
    }
    if ($worker -and -not $worker.HasExited) {
        Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
