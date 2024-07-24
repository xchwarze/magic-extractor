; Define the source directory as one level up from the directory containing this script
!define SourcePath ".."

; Basic installer information
Name "TestApp"
OutFile "test-file.exe"
InstallDir "$PROGRAMFILES\TestApp"

; Pages
Page directory
Page instfiles

; Sections
Section "Install"
    ; Set the output directory for installation
    SetOutPath $INSTDIR

    ; Include the file from the source path defined above
    File "${SourcePath}\test-file.txt"
SectionEnd

; Optional, create a shortcut in the Start Menu
Section "Create Shortcuts"
    CreateDirectory "$SMPROGRAMS\TestApp"
    CreateShortCut "$SMPROGRAMS\TestApp\TestApp.lnk" "$INSTDIR\test-file.txt"
SectionEnd
