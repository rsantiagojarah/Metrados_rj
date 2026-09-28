param(
    [string]$AutoCadDirectory = 'C:\Program Files\Autodesk\AutoCAD 2021',
    [string]$TargetDirectory = ''
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceDirectory = Resolve-Path (Join-Path $projectDirectory '..\..')
if ([string]::IsNullOrWhiteSpace($TargetDirectory)) {
    $TargetDirectory = Join-Path $workspaceDirectory 'target\autocad'
}
$bundleDirectory = Join-Path $TargetDirectory 'Metrados.AutoCAD2021.bundle'
$contentDirectory = Join-Path $bundleDirectory 'Contents\Windows'
$compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$frameworkDirectory = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319'
$acMgd = Join-Path $AutoCadDirectory 'AcMgd.dll'
$acDbMgd = Join-Path $AutoCadDirectory 'AcDbMgd.dll'
$acCoreMgd = Join-Path $AutoCadDirectory 'AcCoreMgd.dll'

foreach ($required in @($compiler, $acMgd, $acDbMgd, $acCoreMgd)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "No se encontró el archivo requerido: $required"
    }
}

New-Item -ItemType Directory -Path $contentDirectory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectDirectory 'PackageContents.xml') -Destination $bundleDirectory -Force

$common = @(
    '/nologo', '/optimize+', '/platform:x64', '/langversion:5',
    "/reference:$(Join-Path $frameworkDirectory 'System.dll')",
    "/reference:$(Join-Path $frameworkDirectory 'System.Core.dll')",
    "/reference:$(Join-Path $frameworkDirectory 'System.Runtime.Serialization.dll')"
)
$bridgeSource = Join-Path $projectDirectory 'src\BridgeClient.cs'
$pluginSource = Join-Path $projectDirectory 'src\Plugin.cs'
$areaSource = Join-Path $projectDirectory 'src\AreaCommand.cs'
$lengthSource = Join-Path $projectDirectory 'src\LengthCommand.cs'
$steelSource = Join-Path $projectDirectory 'src\SteelCommand.cs'
$probeSource = Join-Path $projectDirectory 'src\Probe.cs'
$pluginOutput = Join-Path $contentDirectory 'Metrados.AutoCAD2021.dll'
$probeOutput = Join-Path $TargetDirectory 'Metrados.AutoCAD2021.Probe.exe'

& $compiler @common '/target:library' "/out:$pluginOutput" "/reference:$acMgd" "/reference:$acDbMgd" "/reference:$acCoreMgd" $bridgeSource $pluginSource $areaSource $lengthSource $steelSource
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo compilar el complemento de AutoCAD 2021.'
}

& $compiler @common '/target:exe' "/out:$probeOutput" $bridgeSource $probeSource
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo compilar la sonda de conexión.'
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $pluginOutput).Hash
Write-Output "Complemento: $pluginOutput"
Write-Output "Sonda: $probeOutput"
Write-Output "SHA256: $hash"
