; Silent portable launcher. Double-click extracts (once per version) and
; opens Stratagem Terminal in live mode. No --demo flag is passed.
Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma
RequestExecutionLevel user
SilentInstall silent
ShowInstDetails nevershow
AutoCloseWindow true
Name "Helldivers Stratagem Wheel"
Caption "Helldivers Stratagem Wheel"
InstallDir "$LOCALAPPDATA\HelldiversStratagemWheel"

!ifndef APP_VERSION
  !define APP_VERSION "1.0.9"
!endif

!ifndef PAYLOAD
  !error "Pass -DPAYLOAD=... pointing at the staged runtime"
!endif

!ifndef OUTFILE
  !error "Pass -DOUTFILE=... for the exe path"
!endif

!ifndef ICON
  !error "Pass -DICON=... for the exe icon"
!endif

OutFile "${OUTFILE}"
Icon "${ICON}"
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "Helldivers Stratagem Wheel"
VIAddVersionKey "FileDescription" "Stratagem Terminal"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "Does not inject into Helldivers 2"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"

!include LogicLib.nsh

Function .onInit
  SetSilent silent
FunctionEnd

Section
  ReadINIStr $1 "$INSTDIR\runtime.ini" Runtime Version
  ${If} $1 != "${APP_VERSION}"
    RMDir /r "$INSTDIR"
    SetOutPath "$INSTDIR\Python"
    File /r "${PAYLOAD}/Python/*"
    SetOutPath "$INSTDIR\pkgs"
    File /r "${PAYLOAD}/pkgs/*"
    ; Last name fallback. tessdata stays its own directory so Tesseract 5.4
    ; loads eng.traineddata from that folder.
    SetOutPath "$INSTDIR\tesseract"
    File "${PAYLOAD}/tesseract/tesseract.exe"
    File "${PAYLOAD}/tesseract/*.dll"
    SetOutPath "$INSTDIR\tesseract\tessdata"
    File "${PAYLOAD}/tesseract/tessdata/eng.traineddata"
    File /nonfatal "${PAYLOAD}/tesseract/tessdata/eng.user-words"
    File /nonfatal "${PAYLOAD}/tesseract/tessdata/eng.user-patterns"
    SetOutPath "$INSTDIR"
    File "${PAYLOAD}/Stratagem_Terminal.launch.pyw"
    WriteINIStr "$INSTDIR\runtime.ini" Runtime Version "${APP_VERSION}"
  ${EndIf}

  SetOutPath "$INSTDIR"
  ExecShell "" "$INSTDIR\Python\pythonw.exe" '"$INSTDIR\Stratagem_Terminal.launch.pyw"' SW_SHOWNORMAL
SectionEnd
