@echo off
REM Keep magika.exe (+ LICENSE/README); drop the checksum and self-update
REM sidecar files shipped in the CLI zip.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal
set "U=%~2"
if not exist "%U%" exit /b 0
pushd "%U%"

del /q *.sha256 2>nul
del /q *update*.exe 2>nul

popd
exit /b 0
