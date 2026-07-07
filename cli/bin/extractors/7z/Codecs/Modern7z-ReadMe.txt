Modern7z

https://www.tc4shell.com/en/7zip/modern7z/
Copyright (C) 2018-24 Dec Software.

Modern7z is a plugin for the popular 7-Zip archiver. It adds support for the
following leading-edge compression methods:

    Zstandard v1.5.6
    Brotli v1.1.0
    LZ4 v1.10.0
    LZ5 v1.5
    Lizard v1.0
    Fast LZMA2 v1.0.1

Each of these compression methods can only pack a single file. Multiple files
are usually pre-packed into a container like TAR, and then it is compressed with
the method. You can also use any of these compression methods as a codec when
packing files into a .7z file.

Modern7z also allows you to unpack files from Zip archives packed with ZSTD 
method.

INSTALLATION

To install Modern7z, first create a folder named "Codecs" in the 7-Zip
installation folder. Then copy the files from the "32" or "64" folder, depending
on the 7-Zip edition that you are using (32-bit or 64-bit), to the "Codecs"
folder. After that, each time you launch 7-Zip, it will automatically find the
Modern7z plugin and use it to support the new compression methods.

USAGE

To pack a file using an methods supported by Modern7z, select the standard "Add
to archive..." 7-Zip command. When the "Add to Archive" dialog box appears,
select the archive format you want to use in the "Archive format" field.

Each of the methods supported by Modern7z has a very wide compression level
range:

Compression method  Compression level range
Zstandard           1-22
Brotli              0-11
LZ4                 0-12
LZ5                 0-15
Lizard              10-19 - FastLZ4 will be used
                    20-29 - LIZv1 will be used
                    30-39 - FastLZ4 + Huffman will be used
                    40-49 - LIZv1 + Huffman will be used
Fast LZMA2          1-9

As the 7-Zip user interface only allows you to select the values 0, 1, 3, 5, 7,
or 9, you have to specify the exact compression level via the "Parameters"
field. For example, the string "x=20" means that the compression level is 20.

The 7-Zip user interface doesn't allow you to directly select the number of CPU
threads to be used when packing the files, but you can specify it via the
"Parameters" field. For example, the string "mt=4" tells plugin to use 4 CPU
threads for compression. If you omit the "mt" parameter, plugin will use as many
threads as there are CPU cores in the system.

Random access mode is supported for compressed files. This mode allows you to
navigate the contents of a TAR container inside a compressed file without
completely unpacking the container. This mode is supported only if the size of
an independent block doesn't exceed 64 MB. (For more details on independent
blocks, see the Fine tuning section.)

USAGE AS A CODEC

As the 7-Zip user interface doesn't allow you to directly select an additional
compression method to be used when packing files into a .7z file, you have to
specify it via the "Parameters" field. Use a string in the format "0=NAME"
(where NAME is the internal name of the compression method).

Compression method  Internal name
Zstandard           ZSTD
Brotli              BROTLI
LZ4                 LZ4
LZ5                 LZ5
Lizard              LIZARD
Fast LZMA2          FLZMA2

For example, the string "0=ZSTD" tells 7-Zip to use Zstandard to compress the
files.

You also need to specify the exact compression level via the “Parameters” field
(see above).

FINE TUNING

The compression algorithms allow you to set additional parameters that have an
impact on different compression aspects. If you want to specify any additional
parameters, enter them in the "Parameters" field in the format "key=value" (just
like you do for Compression level).

You can specify the size as follows: "key=Nx" (where N is a number, and x is a
unit of measurement). You can use the following units: b (byte), k (kilobyte), m
(megabyte), and g (gigabyte).

Block size

When you compress files using the Brotli algorithm as a codec, or the Zstandard,
LZ4, LZ5, or Lizard algorithm as a codec or to create a single file, the input
stream is divided into blocks of equal size, and each block is compressed
separately. This approach allows you to compress data faster by compressing each
block in a separate thread. However, it reduces the overall compression level.

By default, the block size is set according to the selected compression level:

Compression level                                           Block size
Zstandard  Brotli  LZ4  LZ5    Lizard
0-2        0-1     0-1  0-1    10-11, 20-21, 30-31, 40-41  1 MB
3-5        2-3     2-3  2-3    12, 22, 32, 42              2 MB
6-10       4-5     4-5  4-5    13, 23, 33, 43              4 MB
11-15      6       6-7  6-7    14, 24, 34, 44              8 MB
16-17      7       8    8-9    15, 25, 35, 45              16 MB
18-19      8       9    10-11  16, 26, 36, 46              32 MB
20         9       10   12-13  17, 27, 37, 47              64 MB
21         10      11   14     18, 28, 38, 48              128 MB
22         11      12   15     19, 29, 39, 49              256 MB

You can set the block size using the "c" key. For example, the string "c=512m"
sets the block size to 512 MB. The string "c=0b" has a special meaning. It
instructs the archiver not to split the input stream into blocks and disables
multi-threaded compression. (Note: This string doesn't affect the Brotli
algorithm.) This approach allows you to achieve the maximum compression level,
but it is also the slowest one.

ZSTD, LZ4, LZ5, and Lizard

The ZSTD, LZ4, LZ5, and Lizard algorithms allow you to set the dictionary size 
using the "d" key. By default, the dictionary size is set automatically based 
on the size of data being packed, but you can select it manually.

Allowed values:

Algorithm  Dictionary size
ZSTD       64k, 128k, 256k, 512k, 1m, 2m, 4m, 8m, 16m, 32m, 64m, 128m, 256m, 512m, 1g
LZ4        64k, 256k, 1m, 4m
LZ5        64k, 256k, 1m, 4m, 16m, 64m, 256m
Lizard     128k, 256k, 1m, 4m, 16m, 64m, 256m

Brotli

When using the Brotli method, you can configure the following additional
parameters:

Algorithm; use the "a" key
Allowed values:
 0: In this mode, the compressor doesn't know anything in advance about the
 properties of the input.
 1: Compression mode for UTF-8 formatted text input.
 2: Compression mode used in WOFF 2.0.
Example: a=0

Sliding LZ77 window size; use the "d" key
Allowed value range: 1k - 1g
The encoder may reduce this value, for example, if the input is much smaller
than the window size.
Example: d=256m

Input block size; use the "mem" key
Allowed value range: 1k - 16m
The encoder may reduce this value, for example, if the input is much smaller
than the input block size.
A bigger input block size allows you to achieve a higher compression level but
consumes more memory.
Example: mem=256m

A flag that affects the usage of the "literal context modeling" format feature;
use the "lc" key
Allowed values: 0, 1
This flag is a "decoding speed vs compression ratio" trade-off.
Example: lc=1

The number of postfix bits (NPOSTFIX); use the "pb" key
Allowed values: 0, 1, 2, 3
The encoder may change this value.
Example: pb=0

The number of direct distance codes; use the "fb" key
Allowed value range: 0 - 15 << NPOSTFIX in steps of 1 << NPOSTFIX
The encoder may change this value.

Fast LZMA2

When using the Fast LZMA2 method, you can configure the following additional
parameters:    

Algorithm; use the "a" key
Allowed values:  (fast), 2 (optimize), 3 (hybrid mode)
Example: a=3

Dictionary size; use the "d" key
Allowed value range: 1m - 128m for the 32-bit plugin version; 1m - 1g for the
64-bit plugin version.
Example: d=64m

The number of fast bytes; use the "fb" key
Allowed value range: 5-273
Example: fb=160

Match finder cycles; use the "mc" key
Allowed value range: 0-1000000000
Example: mc=1000

The number of literal context bits; use the "lc" key
Allowed value range: 0-4
Example: lc=3

The number of literal pos bits; use the "lp" key
Allowed value range: 0-4
Example: lp=0

The number of pos bits; use the "pb" key
Allowed value range: 0-4
Example: pb=2

For more details about the meaning of the keys, read the 7-Zip help (see the
section about the LZMA and LZMA2 compression algorithms).
