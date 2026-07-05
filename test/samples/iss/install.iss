#define SourcePath ".."

[Setup]
AppName=TestApp
AppVersion=1.0
DefaultDirName={pf}\TestApp
OutputDir=.
OutputBaseFilename=test-file
DefaultGroupName=TestApp

[Files]
Source: "{#SourcePath}\test-file.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TestApp"; Filename: "{app}\test-file.txt"
