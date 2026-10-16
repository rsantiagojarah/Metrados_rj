# Comprueba que Install-Uv devuelve solo la ruta de uv.exe.
# Si el mensaje de versión sale por la misma vía, PowerShell lo junta con la ruta
# y el instalador intenta ejecutar ese texto como programa.
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Esta prueba debe ejecutarse con PowerShell 7.'
}

. (Join-Path $PSScriptRoot 'Instalar-Metrados.ps1')

$uv = Install-Uv
if ($uv -is [System.Array]) {
    throw "Install-Uv devolvió $($uv.Count) valores: $($uv -join ' | ')"
}
if ("$uv" -notmatch 'uv\.exe$') {
    throw "Install-Uv no devolvió la ruta de uv.exe: $uv"
}
Write-Output "RETORNO_UV_OK $uv"
