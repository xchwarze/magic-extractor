@echo off
REM Extract 7z.exe + 7z.dll from the downloaded NSIS installer, using the
REM currently-bundled 7z as a bootstrap, and leave only those two files so the
REM updater's `merge` drops them in without disturbing Formats\ / Codecs\.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal
set "U=%~2"
set "SEVENZIP=%~dp0..\..\cli\bin\extractors\7z\7z.exe"
if not exist "%U%" exit /b 0
if not exist "%SEVENZIP%" (
  echo clean-7z: bundled 7z.exe not found at "%SEVENZIP%"
  exit /b 1
)

"%SEVENZIP%" x "%U%\7z*.exe" -o"%U%\_out" 7z.exe 7z.dll -y
if not exist "%U%\_out\7z.exe" (
  echo clean-7z: 7z.exe not found inside the installer
  exit /b 1
)

REM drop the installer (and anything else) at the unpack root, keep the two files
del /q "%U%\*.*" 2>nul
move /y "%U%\_out\7z.exe" "%U%\7z.exe" >nul
move /y "%U%\_out\7z.dll" "%U%\7z.dll" >nul
rd /s /q "%U%\_out" 2>nul

exit /b 0
