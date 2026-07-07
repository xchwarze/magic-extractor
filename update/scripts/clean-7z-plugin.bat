@echo off
REM post_unpack cleanup for tc4shell 7-Zip plugins (Formats\ and Codecs\).
REM Args passed by universal-tool-updater: %1=tool_name  %2=unpack_folder  %3=version
REM
REM magic-extractor's bundled 7z.exe is 32-bit. tc4shell ships plugins two ways:
REM   * flat  -> Plugin.32.dll + Plugin.64.dll side by side (Asar, Iso7z, ...)
REM   * split -> 32\ and 64\ subfolders, each a full set (Modern7z per its ReadMe:
REM             "copy the files from the 32 or 64 folder ... to the Codecs folder")
REM In both cases we want ONLY the 32-bit files, laid out FLAT so 7-Zip finds them.
setlocal
set "U=%~2"
if not exist "%U%" exit /b 0

REM split layout: promote the contents of 32\ to the root, discard 64\
if exist "%U%\32" (
  robocopy "%U%\32" "%U%" /E /MOVE >nul
  rd /s /q "%U%\64" 2>nul
  rd /s /q "%U%\32" 2>nul
)

REM flat layout: drop the 64-bit DLL (and any stray installer)
del /s /q "%U%\*.64.dll" 2>nul
del /s /q "%U%\*.exe"    2>nul

REM every plugin archive ships a generic "ReadMe.txt"; rename it to the plugin
REM name so the readmes coexist in the shared folder instead of overwriting each
REM other (%1 = section/tool name, e.g. Modern7z -> Modern7z-ReadMe.txt)
if exist "%U%\ReadMe.txt" ren "%U%\ReadMe.txt" "%~1-ReadMe.txt"

exit /b 0
