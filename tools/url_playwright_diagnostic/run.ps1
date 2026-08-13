param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [ValidateRange(0, 120)]
    [double]$WaitSeconds = 12
)

$diagnosticRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectTools = Split-Path -Parent $diagnosticRoot
$pythonPath = Join-Path $projectTools "leboncoin_playwright_observer\.venv\Scripts\python.exe"
$diagnosticScript = Join-Path $diagnosticRoot "diagnose_urls.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "L'environnement Playwright partage n'existe pas."
}

$arguments = @(
    $diagnosticScript,
    "--url", $Url,
    "--wait-seconds", $WaitSeconds
)

& $pythonPath @arguments
exit $LASTEXITCODE
