#!/usr/bin/env tclkit
#
# Bitrock unpacking script
#
# Fork of a script made by mickael9 <mickael9 at gmail dot com>
# https://gist.github.com/mickael9/0b902da7c13207d1b86e
#
# Added an option to only extract Metakit files, inspired by dfir-it's fork
# https://gist.github.com/dfir-it/06f3baa4556bba6822998103db43bc74

#source /usr/bin/sdx.kit

if {$argc < 2} {
    puts "Usage: $argv0 installerFile outputDirectory [--metakit-only]"
    exit 1
}

set installerFile [lindex $argv 0]
set destDir  [lindex $argv 1]

set installerMount /installer
set dataMount /installerData

puts "Mounting the installer as a Metakit database..."
vfs::mk4::Mount $installerFile $installerMount -readonly

if {[lindex $argv 2] == "--metakit-only"} {
    puts "Copying files from the Metakit database to the output directory..."
    file copy -force $installerMount $destDir
    puts "Done"
    exit
}

lappend auto_path $installerMount/libraries/
package require vfs::cookfs
catch {package require Tcllzmadec}

# progress from http://wiki.tcl.tk/16939 (sligtly modified)
# thanks to the author
proc progress {cur tot} {
    # set to total width of progress bar
    set total 76
    
    if {$cur == $tot} {
        # cleanup
        set str "\r[string repeat " " [expr $total + 4]]\r"
    } else {
        set half [expr {$total/2}]
        set percent [expr {100.*$cur/$tot}]
        set val (\ [format "%6.2f%%" $percent]\ )
        set str "\r|[string repeat = [
                    expr {round($percent*$total/100)}]][
                            string repeat { } [expr {$total-round($percent*$total/100)}]]|"
        set str "[string range $str 0 $half]$val[string range $str [expr {$half+[string length $val]-1}] end]"
    }
    puts -nonewline stderr $str
}

# Read cookfs options
set optionsFile [open $installerMount/cookfsinfo.txt]
set options [read $optionsFile]
close $optionsFile

# Read the manifest
set manifestFile [open $installerMount/manifest.txt]
set manifest [read $manifestFile]
close $manifestFile

# Mount the files to $dataMount
puts "Mounting the installer files as a Cookfs archive..."
vfs::cookfs::Mount {*}$options $installerFile $dataMount

puts "Creating directories..."
foreach {fileName props} $manifest {
    set type [lindex $props 0]

    if {$type == "directory"} {
        set mode [lindex $props 1]
        file mkdir $destDir/$fileName
        #file attributes $destDir/$fileName -permissions $mode
    }
}

puts "Unpacking files, please wait..."

set entryCount [expr [llength $manifest] / 2]
set entryIndex 0

foreach {fileName props} $manifest {
    set type [lindex $props 0]

    if {$type == "file"} {
        set mode [lindex $props 1]
        set sizes [lindex $props 4]
        set nparts [llength $sizes]
        set index 1

        file mkdir [file dirname $destDir/$fileName]
        file copy -force $dataMount/$fileName $destDir/$fileName

        if {$nparts > 0} {
            set fp [open $destDir/$fileName a]
            fconfigure $fp -translation binary

            while {$index < $nparts} {
                set chunkName $dataMount/${fileName}___bitrockBigFile$index
                set fp2 [open $chunkName r]
                fconfigure $fp2 -translation binary
                puts -nonewline $fp [read $fp2]
                close $fp2
                incr index
            }
            close $fp
        }

        #file attributes $destDir/$fileName -permissions $mode
    }

    incr entryIndex
    progress $entryIndex $entryCount
}

puts "Creating links..."

foreach {fileName props} $manifest {
    set type [lindex $props 0]

    if {$type == "link"} {
        set linkTarget [lindex $props 1]
        file delete $destDir/$fileName
        file link -symbolic $destDir/$fileName $linkTarget
    }
}
puts "Done"
