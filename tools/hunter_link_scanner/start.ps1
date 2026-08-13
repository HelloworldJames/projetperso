$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (
    Join-Path $PSScriptRoot "..\.."
)

Set-Location $projectRoot
python -X utf8 -m tools.hunter_link_scanner.server

