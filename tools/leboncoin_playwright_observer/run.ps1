param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [double]$DurationMinutes = 60,
    [int]$MinInterval = 240,
    [int]$MaxInterval = 360,
    [int]$Scrolls = 5,
    [switch]$Once
)

$observerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$observerPython = Join-Path $observerRoot ".venv\Scripts\python.exe"
$observerScript = Join-Path $observerRoot "observer.py"

if (-not (Test-Path -LiteralPath $observerPython)) {
    throw "Playwright n'est pas installé. Créez d'abord l'environnement .venv."
}

$observerArguments = @(
    $observerScript,
    "--url", $Url,
    "--duration-minutes", $DurationMinutes,
    "--min-interval", $MinInterval,
    "--max-interval", $MaxInterval,
    "--scrolls", $Scrolls
)

if ($Once) {
    $observerArguments += "--once"
}

& $observerPython @observerArguments
exit $LASTEXITCODE
