$watchDir = "C:\Users\satvi\Desktop\Mnemo\src\mnemo"
$daemonDir = "C:\Users\satvi\Desktop\Mnemo"

Write-Host "==================================="
Write-Host "  Mnemo Dev Mode"
Write-Host "==================================="
Write-Host "Watching: src\mnemo\"
Write-Host "Edit a file and save to auto-restart."
Write-Host "Close this window to stop."
Write-Host ""

function Start-Daemon {
    $script:daemon = Start-Process -WindowStyle Normal -FilePath "$daemonDir\.venv\Scripts\python.exe" `
        -ArgumentList "-X utf8 -m mnemo.daemon" `
        -WorkingDirectory $daemonDir -PassThru
    Write-Host "  [Daemon started — PID $($daemon.Id)]"
}

function Stop-Daemon {
    if ($script:daemon -and !$script:daemon.HasExited) {
        $script:daemon.Kill()
        $script:daemon.WaitForExit(3000) | Out-Null
        Write-Host "  [Daemon stopped]"
    }
}

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchDir
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$signalFile = "$env:TEMP\mnemo_dev_signal.txt"

Register-ObjectEvent $watcher "Changed" -Action {
    [System.IO.File]::WriteAllText("$env:TEMP\mnemo_dev_signal.txt", (Get-Date).Ticks.ToString())
} > $null
Register-ObjectEvent $watcher "Created" -Action {
    [System.IO.File]::WriteAllText("$env:TEMP\mnemo_dev_signal.txt", (Get-Date).Ticks.ToString())
} > $null
Register-ObjectEvent $watcher "Deleted" -Action {
    [System.IO.File]::WriteAllText("$env:TEMP\mnemo_dev_signal.txt", (Get-Date).Ticks.ToString())
} > $null
Register-ObjectEvent $watcher "Renamed" -Action {
    [System.IO.File]::WriteAllText("$env:TEMP\mnemo_dev_signal.txt", (Get-Date).Ticks.ToString())
} > $null

$lastSignal = 0
Start-Daemon

while ($true) {
    Start-Sleep -Milliseconds 1500
    if (Test-Path $signalFile) {
        $content = [System.IO.File]::ReadAllText($signalFile).Trim()
        if ($content -and $content -ne $lastSignal) {
            $lastSignal = $content
            Write-Host ""
            Write-Host "$(Get-Date -Format 'HH:mm:ss') Change detected — restarting..."
            Stop-Daemon
            Start-Sleep 1
            Start-Daemon
        }
    }
}
