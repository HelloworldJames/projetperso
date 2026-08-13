param(
    [switch]$Register,
    [switch]$Launch
)

$ErrorActionPreference = "Stop"

$sourceRoot = $PSScriptRoot
$buildRoot = Join-Path -Path $sourceRoot -ChildPath "build"
$assetsRoot = Join-Path -Path $buildRoot -ChildPath "Assets"

$compiler = (
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
)

$systemRuntime = (
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.Runtime.dll"
)

$windowsFoundation = (
    "C:\Windows\System32\WinMetadata\Windows.Foundation.winmd"
)

$windowsApplicationModel = (
    "C:\Windows\System32\WinMetadata\Windows.ApplicationModel.winmd"
)

$windowsUi = (
    "C:\Windows\System32\WinMetadata\Windows.UI.winmd"
)

$requiredFiles = @(
    $compiler,
    $systemRuntime,
    $windowsFoundation,
    $windowsApplicationModel,
    $windowsUi
)

foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile)) {
        throw "Composant Windows requis introuvable : $requiredFile"
    }
}

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
New-Item -ItemType Directory -Path $assetsRoot -Force | Out-Null

Add-Type -AssemblyName System.Drawing

function New-DiagnosticLogo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [int]$Size
    )

    $bitmap = New-Object System.Drawing.Bitmap($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    try {
        $graphics.Clear(
            [System.Drawing.Color]::FromArgb(24, 36, 51)
        )

        $penWidth = [Math]::Max(2, [int]($Size / 18))
        $pen = New-Object System.Drawing.Pen(
            [System.Drawing.Color]::FromArgb(88, 181, 255),
            $penWidth
        )

        try {
            $margin = [int]($Size / 5)
            $diameter = $Size - (2 * $margin)
            $graphics.DrawEllipse(
                $pen,
                $margin,
                $margin,
                $diameter,
                $diameter
            )
        }
        finally {
            $pen.Dispose()
        }

        $bitmap.Save(
            $Path,
            [System.Drawing.Imaging.ImageFormat]::Png
        )
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

New-DiagnosticLogo (
    Join-Path $assetsRoot "StoreLogo.png"
) 50

New-DiagnosticLogo (
    Join-Path $assetsRoot "Square150x150Logo.png"
) 150

New-DiagnosticLogo (
    Join-Path $assetsRoot "Square44x44Logo.png"
) 44

$sourceFile = Join-Path $sourceRoot "DiagnosticNotificationsWindows.cs"
$outputFile = Join-Path $buildRoot "DiagnosticNotificationsWindows.exe"
$manifestSource = Join-Path $sourceRoot "AppxManifest.xml"
$manifestOutput = Join-Path $buildRoot "AppxManifest.xml"

$compilerArguments = @(
    "/nologo",
    "/target:exe",
    "/platform:x64",
    "/optimize+",
    "/out:$outputFile",
    "/reference:$systemRuntime",
    "/reference:$windowsFoundation",
    "/reference:$windowsApplicationModel",
    "/reference:$windowsUi",
    $sourceFile
)

& $compiler $compilerArguments

if ($LASTEXITCODE -ne 0) {
    throw "La compilation C# a échoué avec le code $LASTEXITCODE."
}

Copy-Item -LiteralPath $manifestSource -Destination $manifestOutput -Force

Write-Output "Compilation réussie : $outputFile"

if ($Register) {
    $appModelUnlock = Get-ItemProperty -LiteralPath "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" -ErrorAction SilentlyContinue
    $developerMode = $null

    if ($null -ne $appModelUnlock) {
        $developerModeProperty = (
            $appModelUnlock.PSObject.Properties[
                "AllowDevelopmentWithoutDevLicense"
            ]
        )

        if ($null -ne $developerModeProperty) {
            $developerMode = $developerModeProperty.Value
        }
    }

    if ($developerMode -ne 1) {
        throw (
            "Active d'abord le Mode développeur dans Paramètres Windows " +
            "> Système > Pour les développeurs, puis relance avec -Register."
        )
    }

    Add-AppxPackage -Register $manifestOutput -ForceApplicationShutdown
    Write-Output "Application Windows inscrite pour l'utilisateur courant."
}

if ($Launch) {
    $package = Get-AppxPackage -Name "PCHunter.NotificationDiagnostic"

    if ($null -eq $package) {
        throw "Application non inscrite. Relance avec -Register -Launch."
    }

    $appUserModelId = "$($package.PackageFamilyName)!App"

    Start-Process -FilePath "explorer.exe" -ArgumentList "shell:AppsFolder\$appUserModelId"

    Write-Output "Diagnostic lancé : $appUserModelId"
}
