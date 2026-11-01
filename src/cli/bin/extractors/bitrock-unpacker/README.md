# bitrock-unpacker
Fork of mickael9's gist: https://gist.github.com/mickael9/0b902da7c13207d1b86e

Usage: `bitrock-unpacker.exe INSTALLER.EXE OUTPUT_DIR [--metakit-only]`

## Download

Windows binaries are available at the releases section.

## Build

Get some tools.

* Install ActiveTcl-8.5 and at `install_path/bin/` there is either **base-tcl8.5-thread-win32-x86_64.exe** or **base-tcl8.5-thread-win32-ix86.exe** -- https://www.activestate.com/products/tcl/downloads/
* **sdx-20110317.kit** -- https://code.google.com/archive/p/tclkit/downloads
* **tclkitsh-8.5.9-win32.upx.exe** or **tclkitsh-8.5.9-win32-x86_64.exe** -- https://code.google.com/archive/p/tclkit/downloads

Your build directory should look something like this. The unpacker script has been renamed to main.tcl.
```
$ tree .
.
├── base-tcl8.5-thread-win32-x86_64.exe
├── bitrock-unpacker.vfs
│   └── main.tcl
├── sdx-20110317.kit
└── tclkitsh-8.5.9-win32.upx.exe
```

When you run this line, an executable without extension is created in the current directory. Append ".exe" to the file and you're done.
```
.\tclkitsh-8.5.9-win32.upx.exe .\sdx-20110317.kit wrap bitrock-unpacker -runtime .\base-tcl8.5-thread-win32-ix86.exe
```
or
```
.\tclkitsh-8.5.9-win32-x86_64.exe .\sdx-20110317.kit wrap bitrock-unpacker -runtime .\base-tcl8.5-thread-win32-x86_64.exe
```

For more instructions, see <https://stackoverflow.com/a/1383674>.

## License and modifications
My modifications to the original are licensed under CC0-1.0 license.

A couple lines had to be commented out for the script to run on Windows. For example, the line `file attributes $destDir/$fileName -permissions $mode` was throwing the following error.
```
bad option "-permissions": must be -archive, -hidden, -longname, -readonly, -shortname, or -system
```
