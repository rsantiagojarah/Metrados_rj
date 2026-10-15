# Prepara este proyecto e instala el complemento de AutoCAD 2021.
# No es un segundo programa: la plantilla sigue abriéndose desde este repositorio.
param(
    [string]$AutoCadDirectory = 'C:\Program Files\Autodesk\AutoCAD 2021'
)

if ($PSVersionTable.PSVersion.Major -lt 7) {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        & $pwsh.Source -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -AutoCadDirectory $AutoCadDirectory
        exit $LASTEXITCODE
    }
}

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Write-Step {
    param([string]$Message)
    Write-Output ''
    Write-Output "== $Message =="
}

function Update-SessionPath {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $env:Path = "$userPath;$machinePath"
}

function Assert-AutoCadPresent {
    param([string]$Directory)
    $required = @(
        (Join-Path $Directory 'acad.exe'),
        (Join-Path $Directory 'AcMgd.dll'),
        (Join-Path $Directory 'AcDbMgd.dll'),
        (Join-Path $Directory 'AcCoreMgd.dll')
    )
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "No se encontró AutoCAD 2021 en '$Directory'. Falta: $path"
        }
    }
}

function Assert-FreeDisk {
    param([string]$Path)
    $driveName = (Get-Item -LiteralPath $Path).PSDrive.Name
    $freeBytes = (Get-PSDrive -Name $driveName).Free
    $minimum = 800MB
    if ($freeBytes -lt $minimum) {
        $freeMb = [math]::Round($freeBytes / 1MB)
        throw "Hacen falta al menos 800 MB libres en ${driveName}:. Ahora hay $freeMb MB."
    }
}

function Get-BlockingProcesses {
    return @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'acad.exe') -or
        ($_.Name -match '^(python|pythonw)\.exe$' -and
            $_.CommandLine -match '(?i)(^|[\s\\"])metrado(?!\w)')
    })
}

function Assert-ApplicationsClosed {
    $running = Get-BlockingProcesses
    if ($running.Count -eq 0) {
        return
    }
    $names = ($running | ForEach-Object { "$($_.Name) ($($_.ProcessId))" }) -join ', '
    throw "Cierra AutoCAD y Metrados antes de instalar. Siguen abiertos: $names"
}

function Find-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $candidate = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    return $null
}

function Install-Uv {
    $existing = Find-Uv
    if ($existing) {
        Write-Output "uv: $(& $existing --version)"
        return $existing
    }
    Write-Step 'Instalando uv para el usuario actual'
    Invoke-Expression (Invoke-RestMethod 'https://astral.sh/uv/install.ps1')
    Update-SessionPath
    $installed = Find-Uv
    if (-not $installed) {
        throw 'uv se instaló, pero no aparece en esta sesión. Cierra la ventana y vuelve a ejecutar el instalador.'
    }
    return $installed
}

function Test-MsvcCompiler {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere)) {
        return $false
    }
    $found = & $vswhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    return -not [string]::IsNullOrWhiteSpace("$found")
}

function Install-RustToolchain {
    if ((Get-Command rustc -ErrorAction SilentlyContinue) -and (Get-Command cargo -ErrorAction SilentlyContinue)) {
        Write-Output "rustc: $(& rustc --version)"
        return
    }
    if (-not (Test-MsvcCompiler)) {
        throw 'Falta Rust y también las herramientas de C++ de Visual Studio, que Rust necesita en Windows. Instala Build Tools 2022 con el componente de C++ y vuelve a ejecutar este instalador.'
    }
    Write-Step 'Instalando Rust para el usuario actual'
    $installer = Join-Path $env:TEMP 'rustup-init.exe'
    Invoke-WebRequest -Uri 'https://win.rustup.rs/x86_64' -OutFile $installer
    & $installer -y --default-toolchain stable --profile minimal
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo instalar Rust.'
    }
    $env:Path = "$(Join-Path $env:USERPROFILE '.cargo\bin');$env:Path"
    if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
        throw 'Rust se instaló, pero rustc no aparece en esta sesión. Cierra la ventana y vuelve a ejecutar el instalador.'
    }
}

function Sync-Project {
    param([string]$Uv)
    Write-Step 'Instalando Python 3.12 y las dependencias del proyecto'
    & $Uv python install 3.12
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo preparar Python 3.12.'
    }
    & $Uv sync --frozen --python 3.12
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudieron instalar las dependencias del proyecto.'
    }
    & $Uv run --python 3.12 python -c "import metrado._enlace; print('ENLACE_OK')"
    if ($LASTEXITCODE -ne 0) {
        throw 'Las dependencias quedaron instaladas, pero el cálculo no está disponible.'
    }
}

function Assert-HashCommand {
    if (Get-Command Get-FileHash -ErrorAction SilentlyContinue) {
        return
    }
    throw 'PowerShell no puede comprobar el complemento en esta sesión. Instala PowerShell 7 y ejecuta installer\Instalar-Metrados.cmd.'
}

function Install-AutoCadPlugin {
    param([string]$Directory)
    Write-Step 'Compilando e instalando el complemento de AutoCAD 2021'
    $installScript = Join-Path $repo 'autocad\Metrados.AutoCAD2021\install.ps1'
    & $installScript -AutoCadDirectory $Directory
    $built = Join-Path $repo 'target\autocad\Metrados.AutoCAD2021.bundle\Contents\Windows\Metrados.AutoCAD2021.dll'
    $installed = Join-Path $env:APPDATA 'Autodesk\ApplicationPlugins\Metrados.AutoCAD2021.bundle\Contents\Windows\Metrados.AutoCAD2021.dll'
    if (-not (Test-Path -LiteralPath $installed)) {
        throw "No apareció el complemento instalado en: $installed"
    }
    $builtHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $built).Hash
    $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash
    if ($builtHash -ne $installedHash) {
        throw 'La copia instalada del complemento no coincide con la que se compiló.'
    }
    Write-Output "Complemento: $installed"
    Write-Output "SHA256: $installedHash"
}

function New-LaunchShortcut {
    param([string]$ShortcutPath, [string]$Pythonw)
    $folder = Split-Path -Parent $ShortcutPath
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $Pythonw
    $shortcut.Arguments = '-m metrado'
    $shortcut.WorkingDirectory = $repo
    $shortcut.Description = 'Plantilla de metrados'
    $shortcut.Save()
    Write-Output "Acceso directo: $ShortcutPath"
}

function Install-Shortcuts {
    $pythonw = Join-Path $repo '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) {
        throw 'No apareció el lanzador de la plantilla en el entorno del proyecto.'
    }
    $desktop = [Environment]::GetFolderPath('Desktop')
    $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    New-LaunchShortcut (Join-Path $desktop 'Metrados.lnk') $pythonw
    New-LaunchShortcut (Join-Path $startMenu 'Metrados.lnk') $pythonw
}

try {
    Write-Step 'Comprobando AutoCAD 2021'
    Assert-AutoCadPresent -Directory $AutoCadDirectory
    Assert-FreeDisk -Path $repo
    Assert-ApplicationsClosed
    Assert-HashCommand
    $uv = Install-Uv
    Install-RustToolchain
    Sync-Project -Uv $uv
    Install-AutoCadPlugin -Directory $AutoCadDirectory
    Install-Shortcuts
    Write-Step 'Instalación terminada'
    Write-Output 'Abre Metrados con el acceso directo. Después abre AutoCAD 2021, acepta el complemento si lo pide y escribe MTRCONEXION.'
}
catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    exit 1
}
