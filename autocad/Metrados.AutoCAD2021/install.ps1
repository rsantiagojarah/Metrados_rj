param(
    [string]$AutoCadDirectory = 'C:\Program Files\Autodesk\AutoCAD 2021'
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $projectDirectory 'build.ps1') -AutoCadDirectory $AutoCadDirectory

$workspaceDirectory = Resolve-Path (Join-Path $projectDirectory '..\..')
$source = Join-Path $workspaceDirectory 'target\autocad\Metrados.AutoCAD2021.bundle'
$pluginsDirectory = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Autodesk\ApplicationPlugins'
$destination = Join-Path $pluginsDirectory 'Metrados.AutoCAD2021.bundle'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $destination -Recurse -Force
Write-Output "Instalado para el usuario actual en: $destination"
Write-Output 'Reinicia AutoCAD 2021. Si AutoCAD solicita confirmar el complemento, verifica el nombre y acepta una sola vez.'
