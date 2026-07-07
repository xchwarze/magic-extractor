@echo off
REM Keep the lessmsi CLI (lessmsi.exe + its DLLs + .config); drop the GUI and
REM the per-language satellite folders magic-extractor does not use.
REM Args passed by the updater: %1=tool_name  %2=unpack_folder  %3=version
setlocal
set "U=%~2"
if not exist "%U%" exit /b 0
pushd "%U%"

del /q lessmsi-gui.exe 2>nul
del /q lessmsi-gui.exe.config 2>nul
del /q AddWindowsExplorerShortcut.exe 2>nul

REM language satellite dirs (cs, da, de, es, ...) are not used by the CLI
for /d %%D in (*) do rd /s /q "%%D" 2>nul

popd
exit /b 0
