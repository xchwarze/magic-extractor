@echo off
REM Pull just pea.exe out of the PeaZip portable tree (it lives at
REM res\bin\pea\pea.exe) and discard the rest of the package.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal enabledelayedexpansion
set "U=%~2"
if not exist "%U%" exit /b 0

set "FOUND="
for /r "%U%" %%F in (pea.exe) do set "FOUND=%%F"
if not defined FOUND (
  echo clean-peazip: pea.exe not found in package
  exit /b 1
)

copy /y "!FOUND!" "%U%\pea.exe" >nul
for /d %%D in ("%U%\*") do rd /s /q "%%D" 2>nul
for %%F in ("%U%\*") do if /i not "%%~nxF"=="pea.exe" del /q "%%F" 2>nul

exit /b 0
