@echo off
REM Trim the DIE portable to the console engine magic-extractor uses.
REM Keeps: diec.exe, its VC runtime, Qt Core/Script DLLs, db\ and info\.
REM Drops: die.exe (GUI) and the GUI-only Qt modules / folders.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal
set "U=%~2"
if not exist "%U%" exit /b 0
pushd "%U%"

del /q die.exe 2>nul

REM keep only the Qt Core + Script DLLs; drop the GUI Qt modules
for %%F in (Qt*.dll) do if /i not "%%~nxF"=="Qt5Core.dll" if /i not "%%~nxF"=="Qt6Core.dll" if /i not "%%~nxF"=="Qt5Script.dll" if /i not "%%~nxF"=="Qt6Script.dll" del /q "%%F" 2>nul

REM keep only the signature db and info folders
for /d %%D in (*) do (
  if /i not "%%~nxD"=="db" if /i not "%%~nxD"=="info" rd /s /q "%%D" 2>nul
)

popd
exit /b 0
