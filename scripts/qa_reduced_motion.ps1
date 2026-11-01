param(
    [string]$Url = "http://127.0.0.1:8083/landing",
    [int]$DebugPort = 9333
)

$ErrorActionPreference = "Stop"

$edgeCandidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)
$edgePath = $edgeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $edgePath) {
    throw "Microsoft Edge is required for the reduced-motion runtime check."
}

$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$profileDir = Join-Path $tempRoot ("ai-inbox-motion-" + [guid]::NewGuid().ToString("N"))
$arguments = @(
    "--headless=new",
    "--disable-gpu",
    "--disable-extensions",
    "--no-first-run",
    "--remote-allow-origins=*",
    "--remote-debugging-port=$DebugPort",
    "--user-data-dir=$profileDir",
    "--force-prefers-reduced-motion=reduce",
    $Url
)

$edgeProcess = Start-Process -FilePath $edgePath -ArgumentList $arguments -WindowStyle Hidden -PassThru

try {
    $targets = $null
    for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
        try {
            $targets = Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/list" -TimeoutSec 1
            if ($targets) { break }
        } catch {
            Start-Sleep -Milliseconds 150
        }
    }

    $target = $targets | Where-Object { $_.type -eq "page" -and $_.url -eq $Url } | Select-Object -First 1
    if (-not $target) {
        throw "The Landing page did not appear in the Edge debugging target list."
    }

    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    try {
        [void]$socket.ConnectAsync([Uri]$target.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
        $expression = @"
(async () => {
  if (document.readyState !== 'complete') {
    await new Promise((resolve) => addEventListener('load', resolve, { once: true }));
  }
  await document.fonts.ready;
  return JSON.stringify({
    reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
    scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
    heroAnimation: getComputedStyle(document.querySelector('.hero-copy')).animationName,
    railTransition: getComputedStyle(document.querySelector('.orbit-stickers')).transitionDuration,
    mascotAnimation: getComputedStyle(document.querySelector('.orbit-button img')).animationName
  });
})()
"@
        $request = @{
            id = 1
            method = "Runtime.evaluate"
            params = @{
                expression = $expression
                awaitPromise = $true
                returnByValue = $true
            }
        } | ConvertTo-Json -Depth 6 -Compress
        $requestBytes = [Text.Encoding]::UTF8.GetBytes($request)
        $requestSegment = [ArraySegment[byte]]::new($requestBytes)
        [void]$socket.SendAsync($requestSegment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()

        $buffer = New-Object byte[] 8192
        $responseBuilder = [Text.StringBuilder]::new()
        do {
            $segment = [ArraySegment[byte]]::new($buffer)
            $receive = $socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
            [void]$responseBuilder.Append([Text.Encoding]::UTF8.GetString($buffer, 0, $receive.Count))
        } until ($receive.EndOfMessage)

        $response = $responseBuilder.ToString() | ConvertFrom-Json
        $result = $response.result.result.value | ConvertFrom-Json
        $result | ConvertTo-Json -Compress

        $failures = @()
        if (-not $result.reduced) { $failures += "prefers-reduced-motion did not resolve to reduce" }
        if ($result.scrollBehavior -ne "auto") { $failures += "smooth scrolling remains enabled" }
        if ($result.heroAnimation -ne "none") { $failures += "hero entrance animation remains enabled" }
        if ($result.railTransition -ne "0s") { $failures += "channel rail transition remains enabled" }
        if ($result.mascotAnimation -ne "none") { $failures += "mascot animation remains enabled" }
        if ($failures.Count) {
            throw ($failures -join "; ")
        }
    } finally {
        if ($socket) {
            $socket.Dispose()
        }
    }
} finally {
    if ($edgeProcess -and -not $edgeProcess.HasExited) {
        Stop-Process -Id $edgeProcess.Id -Force
        $edgeProcess.WaitForExit()
    }
    if (Test-Path -LiteralPath $profileDir) {
        $resolvedProfile = [IO.Path]::GetFullPath($profileDir)
        if ($resolvedProfile.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedProfile -Recurse -Force
        }
    }
}
