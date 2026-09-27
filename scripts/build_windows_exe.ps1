# Build HelldiversStratagemWheel.exe on Windows.
# Same payload as scripts/build_windows_exe.sh: pynsist stages official
# Windows CPython and wheels, then NSIS packs the portable launcher.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$PyVersion = "3.12.10"
$Cache = Join-Path $Root "build\cache"
$Wheels = Join-Path $Root "build\wheels"
$Staged = Join-Path $Root "build\nsis"
$Payload = Join-Path $Root "build\windows\payload"
$Out = Join-Path $Root "build\windows\HelldiversStratagemWheel.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
    )
    & $File @Args
    if ($LASTEXITCODE -ne 0) {
        throw "$File exited with $LASTEXITCODE"
    }
}

function Find-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Fallbacks
    )
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    foreach ($path in $Fallbacks) {
        if (Test-Path $path) {
            return $path
        }
    }
    throw "Missing $Name. Install it and run this script again."
}

$SevenZip = Find-Tool "7z" @(
    "$env:ProgramFiles\7-Zip\7z.exe",
    "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
)
$MakeNsis = Find-Tool "makensis" @(
    "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
    "$env:ProgramFiles\NSIS\makensis.exe"
)

$appVersion = $null
$inApp = $false
foreach ($line in Get-Content (Join-Path $Root "packaging\installer.cfg")) {
    if ($line -match '^\[(.+)\]\s*$') {
        $inApp = $Matches[1] -eq "Application"
        continue
    }
    if ($inApp -and $line -match '^version=(.+)$') {
        $appVersion = $Matches[1].Trim()
        break
    }
}
if (-not $appVersion) {
    throw "packaging/installer.cfg is missing the Application version."
}

New-Item -ItemType Directory -Force -Path $Cache, $Wheels, (Join-Path $Root "build\windows"), (Join-Path $Root "packaging") | Out-Null

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Invoke-Checked "python" "-m" "venv" (Join-Path $Root ".venv")
}
Invoke-Checked $venvPy "-m" "pip" "install" "pynsist" "pillow"

$iconPy = @'
from PIL import Image, ImageDraw
from pathlib import Path
icon = Image.new("RGB", (64, 64), "#111111")
draw = ImageDraw.Draw(icon)
draw.rectangle((3, 3, 60, 60), outline="#FFE900", width=4)
draw.polygon([(32, 14), (50, 32), (32, 50), (14, 32)], outline="#FFE900")
draw.polygon([(32, 22), (42, 32), (32, 42), (22, 32)], fill="#FFE900")
path = Path("build/app.ico")
path.parent.mkdir(parents=True, exist_ok=True)
icon.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
'@
$iconPy | Invoke-Checked $venvPy "-"

$tcltkMsi = Join-Path $Cache "tcltk-$PyVersion.msi"
if (-not (Test-Path $tcltkMsi) -or (Get-Item $tcltkMsi).Length -eq 0) {
    Invoke-Checked "curl.exe" "-fL" "--retry" "3" "-o" $tcltkMsi "https://www.python.org/ftp/python/$PyVersion/amd64/tcltk.msi"
}

$tessExe = Join-Path $Cache "tesseract-ocr-w64-setup-5.4.0.20240606.exe"
if (-not (Test-Path $tessExe) -or (Get-Item $tessExe).Length -eq 0) {
    Invoke-Checked "curl.exe" "-fL" "--retry" "3" "-o" $tessExe "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
}

if (Test-Path $Wheels) {
    Remove-Item -Recurse -Force $Wheels
}
New-Item -ItemType Directory -Force -Path $Wheels | Out-Null
Invoke-Checked $venvPy "-m" "pip" "download" "--dest" $Wheels "--no-deps" "--only-binary=:all:" "--platform" "win_amd64" "--python-version" "3.12" "--implementation" "cp" "pynput" "six" "mss" "pytesseract" "packaging" "rapidfuzz" "Pillow"
# Name fallback: Windows.Media.Ocr, then RapidOCR (ONNX). Pull their dependencies.
Invoke-Checked $venvPy "-m" "pip" "download" "--dest" $Wheels "--only-binary=:all:" "--platform" "win_amd64" "--python-version" "3.12" "rapidocr" "onnxruntime" "winrt-runtime" "winrt-Windows.Foundation" "winrt-Windows.Globalization" "winrt-Windows.Graphics.Imaging" "winrt-Windows.Media.Ocr" "winrt-Windows.Storage.Streams"

$env:PYTHONPATH = $Root
Invoke-Checked $venvPy "-m" "pynsist" (Join-Path $Root "packaging\installer.cfg") "--no-makensis"

if (Test-Path $Payload) {
    Remove-Item -Recurse -Force $Payload
}
New-Item -ItemType Directory -Force -Path $Payload | Out-Null
Copy-Item -Recurse (Join-Path $Staged "Python") (Join-Path $Payload "Python")
Copy-Item -Recurse (Join-Path $Staged "pkgs") (Join-Path $Payload "pkgs")
Copy-Item (Join-Path $Staged "Stratagem_Terminal.launch.pyw") (Join-Path $Payload "Stratagem_Terminal.launch.pyw")
Get-ChildItem -Path $Payload -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

$launcher = Get-Content (Join-Path $Payload "Stratagem_Terminal.launch.pyw") -Raw
if ($launcher -match '--demo') {
    throw "Launcher must start live mode, without --demo."
}

$tcltk = Join-Path $Cache "tcltk-$PyVersion"
if (Test-Path $tcltk) {
    Remove-Item -Recurse -Force $tcltk
}
New-Item -ItemType Directory -Force -Path $tcltk | Out-Null
$install = Start-Process -FilePath "msiexec.exe" -ArgumentList @(
    "/a", $tcltkMsi, "/qn", "TARGETDIR=$tcltk"
) -Wait -PassThru
if ($install.ExitCode -ne 0 -and $install.ExitCode -ne 3010) {
    throw "msiexec /a tcltk.msi exited with $($install.ExitCode)"
}

$tkinterPyd = Get-ChildItem -Path $tcltk -Recurse -Filter "_tkinter.pyd" -File | Select-Object -First 1
$tclInit = Get-ChildItem -Path $tcltk -Recurse -Filter "init.tcl" -File | Where-Object { $_.Directory.Name -eq "tcl8.6" } | Select-Object -First 1
$tkPkg = Get-ChildItem -Path $tcltk -Recurse -Directory -Filter "tkinter" | Where-Object { Test-Path (Join-Path $_.FullName "__init__.py") } | Select-Object -First 1
if (-not $tkinterPyd -or -not $tclInit -or -not $tkPkg) {
    throw "tcltk.msi extract is missing _tkinter.pyd, tcl8.6/init.tcl, or Lib/tkinter."
}

$pyDir = Join-Path $Payload "Python"
New-Item -ItemType Directory -Force -Path (Join-Path $pyDir "DLLs"), (Join-Path $pyDir "Lib"), (Join-Path $pyDir "tcl") | Out-Null
Copy-Item $tkinterPyd.FullName (Join-Path $pyDir "_tkinter.pyd") -Force
Copy-Item $tkinterPyd.FullName (Join-Path $pyDir "DLLs\_tkinter.pyd") -Force
foreach ($dllName in @("tcl86t.dll", "tk86t.dll", "zlib1.dll")) {
    $dll = Get-ChildItem -Path $tkinterPyd.DirectoryName -Filter $dllName -File | Select-Object -First 1
    if (-not $dll) {
        $dll = Get-ChildItem -Path $tcltk -Recurse -Filter $dllName -File | Select-Object -First 1
    }
    if (-not $dll) {
        throw "tcltk extract is missing $dllName"
    }
    Copy-Item $dll.FullName (Join-Path $pyDir $dllName) -Force
    Copy-Item $dll.FullName (Join-Path $pyDir "DLLs\$dllName") -Force
}
$tclRoot = $tclInit.Directory.Parent
foreach ($dirName in @("tcl8.6", "tk8.6", "dde1.4", "reg1.3")) {
    $src = Join-Path $tclRoot.FullName $dirName
    if (Test-Path $src) {
        Copy-Item -Recurse $src (Join-Path $pyDir "tcl\$dirName")
    }
}
$demos = Join-Path $pyDir "tcl\tk8.6\demos"
if (Test-Path $demos) {
    Remove-Item -Recurse -Force $demos
}
$destTk = Join-Path $pyDir "Lib\tkinter"
if (Test-Path $destTk) {
    Remove-Item -Recurse -Force $destTk
}
Copy-Item -Recurse $tkPkg.FullName $destTk

$pth = Get-ChildItem -Path $pyDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pth) {
    throw "Embeddable Python pth file is missing."
}
$pthText = Get-Content $pth.FullName -Raw
if ($pthText -notmatch '(?m)^DLLs\s*$') {
    Add-Content -Path $pth.FullName -Value "`r`nDLLs`r`nLib" -Encoding ascii
}
if ($pthText -notmatch 'import site') {
    throw "Embeddable Python pth is missing 'import site'."
}

$tessRaw = Join-Path $Cache "tesseract-extract"
if (Test-Path $tessRaw) {
    Remove-Item -Recurse -Force $tessRaw
}
New-Item -ItemType Directory -Force -Path $tessRaw | Out-Null
Invoke-Checked $SevenZip "x" "-y" "-o$tessRaw" $tessExe "tesseract.exe" "*.dll" "tessdata/eng.traineddata" "tessdata/eng.user-words" "tessdata/eng.user-patterns"

$tessDest = Join-Path $Payload "tesseract"
if (Test-Path $tessDest) {
    Remove-Item -Recurse -Force $tessDest
}
New-Item -ItemType Directory -Force -Path (Join-Path $tessDest "tessdata") | Out-Null
$tessBin = Get-ChildItem -Path $tessRaw -Recurse -Filter "tesseract.exe" -File | Select-Object -First 1
if (-not $tessBin) {
    throw "UB Mannheim installer did not contain tesseract.exe"
}
Copy-Item $tessBin.FullName (Join-Path $tessDest "tesseract.exe")
Get-ChildItem -Path $tessBin.DirectoryName -Filter "*.dll" -File | Copy-Item -Destination $tessDest
$trained = Get-ChildItem -Path $tessRaw -Recurse -Filter "eng.traineddata" -File | Select-Object -First 1
if (-not $trained) {
    throw "UB Mannheim installer did not contain eng.traineddata"
}
Copy-Item $trained.FullName (Join-Path $tessDest "tessdata\eng.traineddata")
foreach ($extra in @("eng.user-words", "eng.user-patterns")) {
    $found = Get-ChildItem -Path $tessRaw -Recurse -Filter $extra -File | Select-Object -First 1
    if ($found) {
        Copy-Item $found.FullName (Join-Path $tessDest "tessdata\$extra")
    }
}
foreach ($runtimeDll in @("vcruntime140.dll", "vcruntime140_1.dll")) {
    $fromPy = Join-Path $pyDir $runtimeDll
    $dest = Join-Path $tessDest $runtimeDll
    if ((Test-Path $fromPy) -and -not (Test-Path $dest)) {
        Copy-Item $fromPy $dest
    }
}

$trainedPath = Join-Path $tessDest "tessdata\eng.traineddata"
$trainedBytes = (Get-Item $trainedPath).Length
if ($trainedBytes -lt 1000000) {
    throw "eng.traineddata is only $trainedBytes bytes."
}
Write-Host "staged payload tesseract/tessdata/eng.traineddata ($trainedBytes bytes)"
foreach ($required in @(
    (Join-Path $tessDest "tesseract.exe"),
    $trainedPath,
    (Join-Path $pyDir "pythonw.exe"),
    (Join-Path $pyDir "Lib\tkinter\__init__.py"),
    (Join-Path $pyDir "tcl\tcl8.6\init.tcl"),
    (Join-Path $Payload "pkgs\stratagems\__main__.py")
)) {
    if (-not (Test-Path $required)) {
        throw "Missing staged file $required"
    }
}

$checkPy = @'
import struct
import sys
from pathlib import Path

payload = Path(sys.argv[1])
SYSTEM = {
    "kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "comctl32.dll", "comdlg32.dll", "imm32.dll",
    "ws2_32.dll", "netapi32.dll", "userenv.dll", "ntdll.dll", "shlwapi.dll",
    "setupapi.dll", "winmm.dll", "winspool.drv", "crypt32.dll", "bcrypt.dll",
    "secur32.dll", "iphlpapi.dll", "rpcrt4.dll", "msvcrt.dll", "version.dll",
    "uxtheme.dll", "dwmapi.dll", "mpr.dll", "netutils.dll", "wldap32.dll",
    "normaliz.dll", "psapi.dll", "imagehlp.dll", "dbghelp.dll", "cabinet.dll",
    "powrprof.dll", "propsys.dll", "dnsapi.dll", "nsi.dll", "sspicli.dll",
    "kernelbase.dll", "ucrtbase.dll", "msvcp140.dll", "msvcp140_1.dll",
    "concrt140.dll", "vcomp140.dll", "sechost.dll", "combase.dll",
    "msimg32.dll", "usp10.dll", "dwrite.dll", "gdiplus.dll", "oleacc.dll",
    "winhttp.dll", "wintrust.dll", "d3d11.dll", "dxgi.dll", "opengl32.dll",
    "glu32.dll", "wsock32.dll", "mswsock.dll", "cryptbase.dll", "msi.dll",
}

def imports(path: Path) -> list[str]:
    data = path.read_bytes()
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    coff = e_lfanew + 4
    _machine, nsec, _t, _s, _p, optsize, _c = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    dd_off = opt + (112 if magic == 0x20B else 96)
    import_rva, _import_size = struct.unpack_from("<II", data, dd_off + 8)
    if import_rva == 0:
        return []
    sections = []
    sec_off = opt + optsize
    for index in range(nsec):
        off = sec_off + index * 40
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((va, max(vsize, rsize), raw))

    def rva_to_off(rva: int) -> int:
        for va, span, raw in sections:
            if va <= rva < va + span:
                return raw + (rva - va)
        raise KeyError(rva)

    off = rva_to_off(import_rva)
    names = []
    while True:
        _ilt, _time, _fwd, name_rva, _iat = struct.unpack_from("<IIIII", data, off)
        if name_rva == 0:
            break
        start = rva_to_off(name_rva)
        end = data.index(b"\0", start)
        names.append(data[start:end].decode("ascii", "replace"))
        off += 20
    return names

def check(folder: Path, also_present: set[str] | None = None) -> None:
    present = {path.name.casefold() for path in folder.iterdir() if path.is_file()}
    if also_present:
        present |= also_present
    missing = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in {".dll", ".exe", ".pyd"}:
            continue
        for name in imports(path):
            key = name.casefold()
            if key.startswith("api-ms-win-"):
                continue
            if key in SYSTEM or key in present:
                continue
            missing.append(f"{path.name} -> {name}")
    if missing:
        print("\n".join(missing), file=sys.stderr)
        raise SystemExit(f"Missing DLLs under {folder}")

check(payload / "tesseract")
python_dir = payload / "Python"
check(python_dir)
dll_dir = python_dir / "DLLs"
if dll_dir.is_dir():
    parent_files = {path.name.casefold() for path in python_dir.iterdir() if path.is_file()}
    check(dll_dir, parent_files)
print("PE import closure ok")
'@
$checkPy | Invoke-Checked $venvPy "-" $Payload

if (Test-Path $Out) {
    Remove-Item -Force $Out
}
$icon = Join-Path $Root "build\app.ico"
Invoke-Checked $MakeNsis "-NOCD" "-DPAYLOAD=$Payload" "-DOUTFILE=$Out" "-DICON=$icon" "-DAPP_VERSION=$appVersion" (Join-Path $Root "packaging\portable.nsi")

$listing = & $SevenZip "l" $Out
if ($listing -notcontains "tesseract/tessdata/eng.traineddata" -and ($listing -join "`n") -notmatch "tesseract/tessdata/eng.traineddata") {
    throw "Installer is missing tesseract/tessdata/eng.traineddata"
}
Get-Item $Out | Format-List FullName, Length
