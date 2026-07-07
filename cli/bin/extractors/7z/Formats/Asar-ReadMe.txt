Asar7z

http://www.tc4shell.com/en/7zip/asar/
Copyright (C) 2017-2023 Dec Software.

Asar7z is a small plugin for the popular 7-Zip archiver. You can use Asar7z with
7-Zip to open, modify, or create .asar archives, which are used for packaging
applications based on the Electron framework.

INSTALLATION

To install the plugin into the 7-Zip installation folder, you need to create the
"Formats" subfolder. After that, copy Asar.64.dll or Asar.32.dll (depending on
your 7-Zip edition) to that subfolder. If you do that, each time you launch
7-Zip, it will automatically find Asar7z and use it when opening .asar files.

USAGE NOTES

When packaging their applications, some Electron app developers may create
encrypted .asar archives. You cannot access the contents of such archives unless
you know the specific encryption method.
