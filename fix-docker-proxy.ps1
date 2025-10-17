# Fix Docker Desktop Proxy Settings
$settingsPath = "$env:APPDATA\Docker\settings.json"

if (Test-Path $settingsPath) {
    Write-Host "Reading Docker settings..."
    $settings = Get-Content $settingsPath | ConvertFrom-Json

    # Disable proxy
    $settings.proxyHttpMode = "system"
    if ($settings.PSObject.Properties.Name -contains "httpProxy") {
        $settings.PSObject.Properties.Remove("httpProxy")
    }
    if ($settings.PSObject.Properties.Name -contains "httpsProxy") {
        $settings.PSObject.Properties.Remove("httpsProxy")
    }

    # Save settings
    $settings | ConvertTo-Json -Depth 100 | Set-Content $settingsPath
    Write-Host "Proxy settings updated. Restarting Docker Desktop..."

    # Restart Docker Desktop
    Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

    Write-Host "Waiting for Docker to start (30 seconds)..."
    Start-Sleep -Seconds 30

    Write-Host "Docker Desktop restarted. Please run deployment again."
} else {
    Write-Host "Docker settings file not found at: $settingsPath"
}
