#!/usr/bin/perl -wT
##
## orders_admin.cgi - Order administration script
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: orders_admin.cgi,v 1.1 2002/10/04 04:38:35 cameron Exp $

use lib '..';
use strict;
use NDC::Conf;
use NDC::Transaction;
use CGI;
use CGI::Carp('fatalsToBrowser');
use HTML::Entities;
use HTML::Template;
use FreezeThaw qw(thaw);

## multi-screen modes
my %Modes = (
  'default'         => \&do_default,
  'pending'         => \&do_pending,
  'pending_view'    => \&do_pending_view,
  'pending_resend'  => \&do_pending_resend,
  'pending_ack'     => \&do_pending_ack,
  'history'         => \&do_history,
  'history_view'    => \&do_history_view,
);

my $Q = CGI->new();
my $C = NDC::Conf->new();
my %F = $Q->Vars();

my $ERRSTR = '';

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
sub do_pending {
  &show_pending();
}

######################################################################
sub do_pending_view {
  &show_pending($ERRSTR) unless &vrfy_pending_order_sid(\$F{'id'});
  &show_pending_view();
}

######################################################################
sub do_pending_resend {
  &show_pending($ERRSTR) unless &vrfy_pending_order_sid(\$F{'sid'});

  my $cardid = &get_cardid_from_order_sid(\$F{'sid'});
  my $T = NDC::Transaction->new();
  $T->email_ordernotice(\$cardid);

  &show_pending_resend();
}

######################################################################
sub do_pending_ack {
  &show_pending($ERRSTR) unless &vrfy_pending_order_sid(\$F{'sid'});

  my $cardid = &get_cardid_from_order_sid(\$F{'sid'});
  $C->db_query('DELETE FROM cards WHERE sid=?', [ $cardid ]);
  $C->db_query('UPDATE transactions SET cardid=0 WHERE cardid=?', [ $cardid ]);
  &show_pending_ack();
}

######################################################################
sub do_history {
  &show_history();
}

######################################################################
sub do_history_view {
  &show_history($ERRSTR) unless &vrfy_order_sid(\$F{'id'});
  &show_history_view();
}

######################################################################
sub show_default {
  my $tmpl = $C->tmpl('admin_orders');
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_pending {
  my $tmpl = $C->tmpl('admin_orders_pending');
  $tmpl->param( orders => &mk_pending_tmpl_obj() );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_pending_view {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%b %e, %Y / %H:%i:%s") AS saletime,'.
                         'sid,orderid,amount,ccnum,prodlist,'.
                         'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country,'.
                         'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country,'.
                         'ship_phone,ship_class FROM transactions WHERE sid=?',
                          [ $F{'id'} ] );
  my $ref = $sth->fetchrow_hashref();
  $sth->finish();

  $ref->{prodlist} = &mk_view_tmpl_obj( $ref->{prodlist} );
  $ref->{amount} = &mk_currency( \sprintf("%.2f", $ref->{amount}) );

  my $tmpl = $C->tmpl('admin_orders_pending_view');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_pending_resend {
  my $tmpl = $C->tmpl('admin_orders_pending_resend');
  $tmpl->param( orderid => &get_orderid_from_sid(\$F{'sid'}) );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_pending_ack {
  my $tmpl = $C->tmpl('admin_orders_pending_ack');
  $tmpl->param( orderid => &get_orderid_from_sid(\$F{'sid'}) );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_history {
  my $tmpl = $C->tmpl('admin_orders_history');
  $tmpl->param( orders => &mk_history_tmpl_obj() );
  print $Q->header();
print $ERRSTR if ($ERRSTR);
  print $tmpl->output();
  exit;
}

######################################################################
sub show_history_view {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%b %e, %Y / %H:%i:%s") AS saletime,'.
                         'orderid,amount,ccnum,prodlist,'.
                         'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country,'.
                         'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country,'.
                         'ship_phone,ship_class FROM transactions WHERE sid=?',
                          [ $F{'id'} ] );
  my $ref = $sth->fetchrow_hashref();
  $sth->finish();

  $ref->{prodlist} = &mk_view_tmpl_obj( $ref->{prodlist} );
  $ref->{amount} = &mk_currency( \sprintf("%.2f", $ref->{amount}) );

  my $tmpl = $C->tmpl('admin_orders_history_view');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub mk_pending_tmpl_obj {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%b %e, %Y") AS saletime,'.
                         'sid,orderid,bill_name,amount FROM transactions '.
                         'WHERE cardid!=0');

  my @tmp;
  while (my $i = $sth->fetchrow_hashref()) {
    my %row = (
      sid       => $i->{sid},
      orderid   => $i->{orderid},
      date      => $i->{saletime},
      customer  => &encode_entities( $i->{bill_name} ),
      amount    => &mk_currency( \sprintf("%.2f", $i->{amount}) ),
    );
    push @tmp, \%row;
  }
  return \@tmp;
}

######################################################################
sub mk_view_tmpl_obj {
  my $prodlist = shift;

  ($prodlist) = &thaw($prodlist);
  my @tmp;
  foreach my $i (keys %$prodlist ) {
    next unless $prodlist->{$i}->{qty};
    my %row = (
      item_num  => $prodlist->{$i}->{obj}->{item_num},
      title     => &encode_entities( $prodlist->{$i}->{obj}->{title} ),
      manuf     => &encode_entities( $prodlist->{$i}->{obj}->{manuf} ),
      qty       => &encode_entities( $prodlist->{$i}->{qty} ),
      price     => &mk_currency( \sprintf("%.2f", $prodlist->{$i}->{obj}->{price}) ),
      total     => &mk_currency( \sprintf("%.2f", ($prodlist->{$i}->{qty})
                    ? $prodlist->{$i}->{qty} * $prodlist->{$i}->{obj}->{price}
                    : 0.0 ) ),

    );
    push @tmp, \%row;
  }
  return \@tmp;
}

######################################################################
sub mk_history_tmpl_obj {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%b %e, %Y") AS saletime,'.
                         'sid,orderid,bill_name,amount FROM transactions '.
                         'WHERE cardid=0');

  my @tmp;
  while (my $i = $sth->fetchrow_hashref()) {
    my %row = (
      sid       => $i->{sid},
      orderid   => $i->{orderid},
      date      => $i->{saletime},
      customer  => &encode_entities( $i->{bill_name} ),
      amount    => &mk_currency( \sprintf("%.2f", $i->{amount}) ),
    );
    push @tmp, \%row;
  }
  return \@tmp;
}

######################################################################
sub mk_currency {
  my $ref = shift;
  $$ref =~ s/(^[-+]?\d+?(?=(?>(?:\d{3})+)(?!\d))|\G\d{3}(?=\d))/$1,/g;
  return $$ref;
}

######################################################################
sub get_cardid_from_order_sid {
  my $ref = shift;
  my $sth = $C->db_query('SELECT cardid FROM transactions WHERE sid=?', [ $$ref ]);
  return ($sth->fetchrow_array())[0];
}

######################################################################
sub get_orderid_from_sid {
  my $ref = shift;
  my $sth = $C->db_query('SELECT orderid FROM transactions WHERE sid=?', [ $$ref ]);
  return ($sth->fetchrow_array())[0];
}

######################################################################
sub vrfy_pending_order_sid {
  my $ref = shift || \'';
  my $sth;

  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($$ref && $$ref =~ /^(\d+)$/);
  $$ref = $1;

  $sth = $C->db_query('SELECT COUNT(*) FROM transactions WHERE sid=? AND cardid!=0', [$$ref]);
  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($sth->fetchrow_array());
  $sth->finish();

  return 1;
}

######################################################################
sub vrfy_order_sid {
  my $ref = shift || \'';
  my $sth;

  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($$ref && $$ref =~ /^(\d+)$/);
  $$ref = $1;

  $sth = $C->db_query('SELECT COUNT(*) FROM transactions WHERE sid=? AND cardid=0', [$$ref]);
  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($sth->fetchrow_array());
  $sth->finish();

  return 1;
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
