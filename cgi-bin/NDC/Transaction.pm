package NDC::Transaction;
##
## Transaction.pm - Utilities for handling completed transactions/orders
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: Transaction.pm,v 1.2 2004/03/22 05:04:44 cameron Exp $

use lib '.';
use strict;
use NDC::Conf;
use CGI::Carp qw(fatalsToBrowser);

delete @ENV{qw(PATH IFS CDPATH ENV BASH_ENV)};

sub new { return bless {},__PACKAGE__ }

######################################################################
## vars ##############################################################
######################################################################

my $NOTICE_ADDR = 'cameron@adminmail.bitstreet.net';
my $SENDMAIL    = '/usr/sbin/sendmail';

######################################################################
## subs ##############################################################
######################################################################

######################################################################
sub email_ordernotice {
  my ($self, $idref) = @_;

  my $C = NDC::Conf->new();
  my $sth = $C->db_query('SELECT data,orderid FROM cards WHERE sid=?', [ $$idref ]);
  my ($cyphertext,$orderid) = $sth->fetchrow_array();
  $sth->finish();

  open(MAIL, "|$SENDMAIL -t") or croak "Failed to create new mail: $!\n";
  print MAIL <<_MESSAGE_;
From: NDCSales.com <webmaster\@ndcsales.com>
To: $NOTICE_ADDR
Subject: Online Order [$orderid]

$cyphertext
_MESSAGE_
  close(MAIL);
  return 0;
}


1;
# vim: set ts=2 et :
