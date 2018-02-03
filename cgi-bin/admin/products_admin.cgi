#!/usr/bin/perl
##
## products_admin.cgi - Products administration script
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: products_admin.cgi,v 1.7 2002/10/04 04:38:11 cameron Exp $

use lib '..';
use strict;
use NDC::Conf;
use NDC::Import;
use CGI;
use CGI::Carp('fatalsToBrowser');
use FreezeThaw qw(freeze thaw);
use HTML::Entities;
use HTML::Template;

## multi-screen modes
my %Modes = (
  'default' => \&do_default,
  'check'   => \&do_check,
  'update'  => \&do_update,
);

my $Q = CGI->new();
my $C = NDC::Conf->new();
my $I = NDC::Import->new();
my %F = $Q->Vars();

######################################################################
## main ##############################################################
######################################################################
$|=1;
delete @ENV{qw(PATH IFS CDPATH ENV BASH_ENV)};

if (!defined $F{'mode'}) {
  $Modes{'default'}->();
} elsif ($Modes{"$F{'mode'}"}) {
  $Modes{"$F{'mode'}"}->();
} else {
  &fatal_error('Invalid mode type');
}

exit;

######################################################################
## subs ##############################################################
######################################################################

######################################################################
sub do_default {
  &show_default();
}

######################################################################
sub do_check {
  &show_check( $I->get_check_tmpl_obj(1) );
}

######################################################################
sub do_update {
  my ($ref) = &thaw($F{'state'});
  $I->set_files_found( $ref );
  &show_update( $I->get_files() );
}

######################################################################
sub show_default {
  my $tmpl = $C->tmpl('admin_products');
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_check {
  my $results_ref = shift;
  my $tmpl = $C->tmpl('admin_products_check');
  $tmpl->param(
    results => $results_ref,
    state => &encode_entities( &freeze( $I->get_files() ) ),
  );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_update {
  my $files_ref = shift;

  ## show header
  my $tmpl = $C->tmpl('admin_products_update_header');
  print $Q->header();
  print $tmpl->output();

#$ENV{'PATH'} = '/usr/local/xlHtml-Win32-040';
$ENV{'PATH'} = '/usr/local/bin';
#fatal_error("PATH = " . $ENV{'PATH'});

  ## process each spreadsheet
  foreach my $f (sort keys %$files_ref) {
    next unless ($files_ref->{$f}->{'found'});
    $tmpl = $C->tmpl('admin_products_update_start');
    $tmpl->param(desc => &encode_entities($files_ref->{$f}->{'desc'}) );
    print $tmpl->output();
    $I->process_xls(\$f);
    $tmpl = $C->tmpl('admin_products_update_done');
    print $tmpl->output();
    $I->unlink_xls(\$f);
  }

  ## show footer
  $tmpl = $C->tmpl('admin_products_update_footer');
  print $tmpl->output();
}

######################################################################
sub fatal_error {
  my $errstr = shift || '';
  print $Q->header;
  print "<html><head><title>Fatal Error Occurred</title><head>
<body><h1>Fatal Error Occurred</h1>$errstr</body></html>";
  exit;
}

1;
## vim: set ts=2 et :
