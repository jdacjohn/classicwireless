#!/usr/bin/perl -T
##
## order_admin.cgi - Main administration script for order processing
##
## Copyright (C) 2006 2k3 Technologies
##
## $Author: Jarnold $
## $Date: 4/03/06 1:22p $
## $Revision: 1 $

use lib '..';
use strict;
use CGI::Carp('fatalsToBrowser');
use NDC::Conf;

my $C    = NDC::Conf->new;
my $tmpl = $C->tmpl('order/order_admin');
print "Content-type: text/html\n\n";
print $tmpl->output();

