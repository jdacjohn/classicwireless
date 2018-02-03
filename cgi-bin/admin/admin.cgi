#!/usr/bin/perl -wT
##
## admin.cgi - Main administration script
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: admin.cgi,v 1.2 2002/08/26 15:39:45 cameron Exp $

use lib '..';
use strict;
use CGI::Carp('fatalsToBrowser');
use NDC::Conf;

my $C    = NDC::Conf->new;
my $tmpl = $C->tmpl('admin');
print "Content-type: text/html\n\n";
print $tmpl->output();

1;
## vim: set ts=2 et :
