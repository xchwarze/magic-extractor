@echo off
REM Standalone unshield updater.
REM
REM The scoop `main` unshield package is a BCJ2-filtered .7z that the updater's
REM py7zr backend can't decode, and the updater has no hook between download and
REM unpack to re-fix it. So this script does it out-of-band: download the scoop
REM .7z and extract it with the bundled full 7z (which handles BCJ2) straight
REM into cli\bin\extractors\unshield. Run it whenever unshield needs refreshing.
REM
REM Bump VER when scoop's unshield changes:
REM   https://github.com/ScoopInstaller/Main/blob/master/bucket/unshield.json
setlocal
set "VER=1.6.2"
set "URL=https://raw.githubusercontent.com/ScoopInstaller/Binary/master/unshield/unshield-%VER%-x64.7z"
set "SEVENZIP=%~dp0..\..\cli\bin\extractors\7z\7z.exe"
set "DEST=%~dp0..\..\cli\bin\extractors\unshield"
set "TMP=%~dp0_unshield_tmp"

if not exist "%SEVENZIP%" ( echo update-unshield: bundled 7z.exe not found at "%SEVENZIP%" & exit /b 1 )

rd /s /q "%TMP%" 2>nul
mkdir "%TMP%"

echo Downloading unshield %VER% ...
curl -fL -o "%TMP%\unshield.7z" "%URL%"
if errorlevel 1 ( echo update-unshield: download failed & rd /s /q "%TMP%" 2>nul & exit /b 1 )

"%SEVENZIP%" x "%TMP%\unshield.7z" -o"%TMP%\x" -y >nul
if errorlevel 1 ( echo update-unshield: extract failed & rd /s /q "%TMP%" 2>nul & exit /b 1 )

REM copy the binaries into the bundle; unshield-deobfuscate.exe and docs already
REM present are left untouched if the package doesn't ship them
for /r "%TMP%\x" %%F in (unshield.exe unshield-deobfuscate.exe zlib1.dll) do copy /y "%%F" "%DEST%\" >nul 2>nul

rd /s /q "%TMP%" 2>nul
echo unshield %VER% installed into "%DEST%"
echo Now set  local_version = %VER%  under [unshield] in tools.ini so the updater stops flagging it.
exit /b 0
