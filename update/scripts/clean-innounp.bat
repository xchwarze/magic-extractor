@echo off
REM Keep innounp.exe (+ its .htm doc); drop the license/source leftovers from
REM the release .rar.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal
set "U=%~2"
if not exist "%U%" exit /b 0
pushd "%U%"

del /q *.txt 2>nul

popd
exit /b 0
