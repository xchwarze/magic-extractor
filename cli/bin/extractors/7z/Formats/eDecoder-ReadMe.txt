eDecoder

https://www.tc4shell.com/en/7zip/edecoder/
Copyright (C) 2017-2023 Dec Software.

eDecoder is a plugin for the popular archiver 7-Zip. It enables 7-Zip to handle
many different types of mailboxes (files that contain email messages) like
archives. It also enables 7-Zip to handle email message files like archives.
Thanks to eDecoder, you can easily extract an email message or only an email
attachment from a mail base without using the email client that created that
mail base. Moreover, eDecoder enables 7-Zip to open so-called web archive files
(MIME HTML files, which usually have the extension MHT or MHTML), as well as to
open or create UUE and XXE encoded files.

The eDecoder plugin also contains eSplitter. It's a special codec that helps
7-Zip pack text files containing binary data encoded using base64 and some other
binary-to-text encoding schemes (for example, web pages saved in the MHTML
format, email messages in the EML format, mail bases in the MBOX and TBB
formats, illustrated e-books in the FB2 format, and many more) into 7z files
more efficiently.

List of formats that can be opened in 7-Zip with eDecoder

    MSG - used by Microsoft Office Outlook
    TNEF - used by Microsoft Office Outlook (winmail.dat or ATT0001.dat files)
    DBX - used by Outlook Express 5 and 6
    MBX - used by Outlook Express 4
    MBOX - used by the following applications:
        Mozilla Thunderbird
        SeaMonkey
        Netscape
        Apple Mail
        Opera
        Opera Mail
        Eudora
        Mulberry
        Pine
        PocoMail
        and by many other email clients
    TBB - used by The Bat!
    PMM - used by Pegasus Mail
    EMLX - used by Apple Mail
    EML, NWS, MHT, MHTML, B64
    UUE, XXE
    YEnc
    BIN - MacBinary files
    HQX - BinHex files
    WARC - Web ARChive files

INSTALLATION

To install the plugin into the 7-Zip installation folder, you need to create the
"Formats" subfolder. After that, copy eDecoder.64.dll or eDecoder.32.dll
(depending on your 7-Zip edition) to that subfolder. If you do that, each time
you launch 7-Zip, it will automatically find eDecoder and use it when opening
files of the supported formats.

USING THE ESPLITTER CODEC

THE COMPRESSION PRINCIPLE

eSplitter searches for encoded binary data in a text and splits the file into
two parts. Text data is put in the first part, and decoded binary data is put in
the second part. There is a vast difference between text data and binary data,
so it makes sense to use two independent compression methods.

The eSplitter codec knows the specific internal structure of certain file
formats (EML, MHTML, MBOX, TBB, and WARC). Thanks to that fact, these formats
can be packed using the most suitable methods.

DATA PACKING

7-Zip doesn't allow you to directly select the eSplitter codec as a compression
method when packing files into a 7z file, so you need to enter the packing
parameters into the Parameters field. We recommend using a parameters string
like this:

0=eSplitter 1=XXX 2=YYY 3=LZMA:x9:d1m:lc8:lp0:pb0 b0s0:1 b0s1:2 b0s2:3

Here XXX is packing parameters for text data, and YYY is packing parameters for
decoded binary data. XXX and YYY can be the same. Here are some examples:

0=eSplitter 1=LZMA2:x9:d128m:mt2 2=LZMA2:x9:d128m:mt1 3=LZMA:x9:d1m:lc8:lp0:pb0 b0s0:1 b0s1:2 b0s2:3
0=eSplitter 1=PPMD:x9:mem1g:o32 2=LZMA2:x9:d128m:mt1 3=LZMA:x9:d1m:lc8:lp0:pb0 b0s0:1 b0s1:2 b0s2:3

Having entered the packing parameters into the Parameters field, click the OK
button, and 7-Zip will start packing the files you selected.

The more encoded binary data a text file contains, the better will be the
overall compression ratio, the less time it will take to pack the text file, and
the less time it will take to unpack the 7z file afterward. We have tested
eSplitter on the MESSAGES.TBB file that you can see in the screenshot above on
our test computer and obtained the following results:

Compression parameters:   0=LZMA2:x9:d128m:mt2
File packing time:        1:45:07
Packed file testing time: 7:01

Compression parameters:   0=eSplitter 1=LZMA2:x9:d128m:mt1 2=LZMA2:x9:d128m:mt1 3=LZMA:x9:d1m:lc8:lp0:pb0 b0s0:1 b0s1:2 b0s2:3
File packing time:        0:56:30
Packed file testing time: 1:30

Of course, when packing different files, the improvements in compression ratio
and packing speed can be very different.

You can also use the eSplitter codec in automatic mode to pack the files most
suitable for eSplitter when using the Smart7z plugin to create a 7z file.
