#!/usr/bin/perl -T
##
## rimg.cgi - Random image script
##
## Copyright (C) Bitstreet Internet
##
## $Id: rimg.cgi,v 1.3 2002/09/10 11:35:03 cameron Exp $

use strict;
use lib '.';
use NDC::Conf;

my $C = new NDC::Conf;

my @files = ();
opendir(IMG,$C->randimg()) or die 'Could not open ' . $C->randimg() . ": $!\n";
while(defined(my $file = readdir(IMG))) {
	push(@files,$file) if ($file =~ /^.+\.(jpg|gif|png)$/);
}
closedir(IMG);

my $rand = int(rand(scalar(@files)));
my $img = $C->randimg_URL() . "/$files[$rand]";

print qq(Content-type: text/html\n\n<img src="$img">);
