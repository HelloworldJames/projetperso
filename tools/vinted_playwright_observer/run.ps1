param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [int]$Scrolls = 5
)

$observerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectTools = Split-Path -Parent $observerRoot
$observerPython = Join-Path $projectTools "leboncoin_playwright_observer\.venv\Scripts\python.exe"
$observerScript = Join-Path $observerRoot "observer.py"

if (-not (Test-Path -LiteralPath $observerPython)) {
    throw "L'environnement Playwright partage n'existe pas. Installez d'abord l'outil Leboncoin."
}

& $observerPython $observerScript --url $Url --scrolls $Scrolls
exit $LASTEXITCODE
