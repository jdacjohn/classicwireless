#!/usr/bin/perl -wT
##
## order.cgi - Online order form for NDC
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: order.cgi,v 1.18 2004/03/22 20:22:48 cameron Exp $


## FIXME
=head
o Email alerts on transaction
o Verify md5sum
=cut
## FIXME


use lib '.';
use strict;
use NDC::Conf;
use NDC::Special;
use NDC::Order ();
use NDC::Transaction ();
use CGI qw(-no_xhtml);
use CGI::Carp qw(fatalsToBrowser);
use HTML::Entities qw(encode_entities);
use FreezeThaw qw(freeze thaw);
use Digest::MD5 qw(md5_hex);
use POSIX qw(strftime);

our $DEBUG = 0;

######################################################################
## vars ##############################################################
######################################################################

my $O = NDC::Order->new();

my @CCTYPE_VALUES = ('American Express', 'DiscoverCard', 'MasterCard', 'Visa');
my @CCEXPM_VALUES = qw(1 2 3 4 5 6 7 8 9 10 11 12);
my @CCEXPY_VALUES;
my @SHIPCLASS_VALUES = qw(business home);
my @SHIPMETHOD_VALUES = ('ground', '2ndday', 'nextday');

{ my $i = (localtime(time))[5]+1900; for ($i .. $i+10) { push @CCEXPY_VALUES, $_; } }

my $CGI_FIELDS = {
  textfield       => ['name', 'size', 'default', 'maxlength', 'override'],
  scrolling_list  => ['name', 'size', 'values','labels','default','multiple'],
  checkbox        => ['name', 'checked','label','default'],
  radio_group     => ['name', 'size', 'values','labels','default'],
};

my $FIELDS = {
  ship_method => {
    type      => 'radio_group',
    size      => 3,
    default   => '',
    values    => [ 'ground', '2ndday', 'nextday' ],
    labels    => {  'ground'  => 'Standard Ground',
                    '2ndday'  => '2nd Day Air',
                    'nextday' => 'Next Day Air', },
  },
  ship_class => {
    type      => 'radio_group',
    size      => 2,
    default   => '',
    values    => [ 'business', 'home' ],
    labels    => { 'business' => 'Business', 'home' => 'Home' },
  },
  email => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 3,
    default   => '',
  },
  ship_name => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 3,
    default   => '',
  },
  ship_addr => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 3,
    default   => '',
  },
  ship_city => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 2,
    default   => '',
  },
  ship_state => {
    type      => 'textfield',
    size      => 2,
    maxlength => 2,
    minlength => 2,
    default   => '',
  },
  ship_zip => {
    type      => 'textfield',
    size      => 9,
    maxlength => 9,
    minlength => 5,
    default   => '',
  },
  ship_country => {
    type      => 'scrolling_list',
    size      => 1,
    default   => 'US',
    values    => $O->country_values(),
    labels    => $O->country_labels(),
  },
  ship_phone => {
    type      => 'textfield',
    size      => 16,
    maxlength => 16,
    minlength => 5,
    default   => '',
  },
  bill_name => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 3,
    default   => '',
  },
  bill_addr => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 3,
    default   => '',
  },
  bill_city => {
    type      => 'textfield',
    size      => 32,
    maxlength => 32,
    minlength => 2,
    default   => '',
  },
  bill_state => {
    type      => 'textfield',
    size      => 2,
    maxlength => 2,
    minlength => 2,
    default   => '',
  },
  bill_zip => {
    type      => 'textfield',
    size      => 10,
    maxlength => 10,
    minlength => 5,
    default   => '',
  },
  bill_country => {
    type      => 'scrolling_list',
    size      => 1,
    default   => 'US',
    values    => $O->country_values(),
    labels    => $O->country_labels(),
  },
  cctype => {
    type      => 'scrolling_list',
    size      => 1,
    default   => '',
    values    => \@CCTYPE_VALUES,
  },
  ccnum => {
    type      => 'textfield',
    size      => 16,
    maxlength => 16,
    minlength => 14,
    default   => '',
  },
  ccexp_m => {
    type      => 'scrolling_list',
    size      => 1,
    default   => '',
    values    => \@CCEXPM_VALUES,
  },
  ccexp_y => {
    type      => 'scrolling_list',
    size      => 1,
    default   => '',
    values    => \@CCEXPY_VALUES,
  },
};

## multi-screen modes
my %Modes = (
  'preview' => \&do_preview,
  'billing' => \&do_billing,
  'finish'  => \&do_finish,
);

## ACLs to control flow
my %ACL = (
  'billing-processing'  => 1,
  'finish-processing'   => 2,
  'billing-complete'    => 4,
  'finish-complete'     => 8,
);

my $C       = NDC::Conf->new();
my $Q       = CGI->new();
my %F       = $Q->Vars();
my $ERRSTR  = '';

######################################################################
## main ##############################################################
######################################################################
$|=1;
delete @ENV{qw(IFS CDPATH ENV BASH_ENV)};

&debug($Q->header());

&fatal_error('Missing vendor') unless (length $C->vendors()->{ $F{'vendorid'} });

if (!defined $F{'mode'}) {
  $Modes{'preview'}->();
} elsif ($Modes{"$F{'mode'}"}) {
  if ($F{'mode'} eq 'billing' && $F{'recalc'}) {
    $Modes{'preview'}->();
  } else {
    $Modes{"$F{'mode'}"}->();
  }
} else {
  &fatal_error('Invalid mode type');
}

exit;

######################################################################
## subs ##############################################################
######################################################################

######################################################################
sub do_preview {
  &show_preview_page( &mk_prodlist(\%F) );
}

######################################################################
sub do_billing {
  my ($prodlist);

  ## in case we are coming in from an error in 'finish' mode
  $F{'mode'} = 'billing';

  if (! $F{'sessid'}) {
    $F{'sessid'} = &start_new_session();
  } else {
    &do_preview() unless &vrfy_sessid(\$F{'sessid'});
  }

  &do_preview() unless &vrfy_acl([]);

  if (defined $F{'acl'} && $F{'acl'} & $ACL{$F{'mode'}.'-complete'}) {
    &show_billing_page( &restore_snapshot( \$F{'sessid'} ) );
  } elsif ($F{'acl'} & $ACL{$F{'mode'}.'-processing'}) {
    for (my $i = 0; $i < 15; $i++) {
      sleep(1);
      &show_billing_page( &restore_snapshot( \$F{'sessid'} ) )
        if (&get_acl() & $ACL{$F{'mode'}.'-complete'});
    }
    $ERRSTR = 'Processes are out of sync and can not recover due to the '.
              'form being <i>submitted more than once</i>.  '.
              'Please wait 15 minutes and try again.';
    &show_preview_page(&mk_prodlist(\%F));
  }
  &update_acl('processing');

  $prodlist = &mk_prodlist(\%F);
  if (! &vrfy_prodlist($prodlist) ) {
    &update_acl('failed');
    &show_preview_page($prodlist);
  }

  if (${ &calc_total($prodlist) } == 0.0) {
    $ERRSTR = 'You failed to select any products.';
    &update_acl('failed');
    &show_preview_page($prodlist);
  }

  &save_snapshot({
    prodlist => $prodlist,
    total => ${ &calc_total($prodlist) }, vendorid => $F{'vendorid'},
    });
  &update_acl('complete');
  &show_billing_page({ prodlist => $prodlist });
}

######################################################################
sub do_finish {
  my ($snapshot, $prodlist, $logid);

  $F{'mode'} = 'finish';

  if (! $F{'sessid'}) {
    $F{'sessid'} = &start_new_session();
  } else {
    &do_preview() unless &vrfy_sessid(\$F{'sessid'});
  }

  &do_preview() unless &vrfy_acl(['billing']);

  if (defined $F{'acl'} && $F{'acl'} & $ACL{$F{'mode'}.'-complete'}) {
    &show_finish_page( &restore_log( \ (&thaw(&restore_snapshot( \$F{'sessid'} )))[0]->{'logid'} ));
  } elsif ($F{'acl'} & $ACL{$F{'mode'}.'-processing'}) {
    for (my $i = 0; $i < 15; $i++) {
      sleep(1);
      &show_billing_page( &restore_snapshot( \$F{'sessid'} ) )
        if (&get_acl() & $ACL{$F{'mode'}.'-complete'});
    }
    $ERRSTR = 'Processes are out of sync and can not recover due to the '.
              'form being <i>submitted more than once</i>.  '.
              'Please wait 15 minutes and try again.';
    &show_preview_page(&mk_prodlist(\%F));
  }
  &update_acl('processing');

  ($snapshot) = &thaw(&restore_snapshot( \$F{'sessid'} ));
  $prodlist = $snapshot->{prodlist};
  if (! &vrfy_prodlist($prodlist) ) {
    &update_acl('failed');
    &show_preview_page($prodlist);
  }

  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_method(\$F{'ship_method'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_class(\$F{'ship_class'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_name(\$F{'ship_name'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_addr(\$F{'ship_addr'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_city(\$F{'ship_city'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_state(\$F{'ship_state'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_zip(\$F{'ship_zip'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_country(\$F{'ship_country'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ship_phone(\$F{'ship_phone'});

  if ((defined $F{'bill_name'}  && $F{'bill_name'} ne '') ||
      (defined $F{'bill_addr'}  && $F{'bill_addr'} ne '') ||
      (defined $F{'bill_city'}  && $F{'bill_city'} ne '') ||
      (defined $F{'bill_zip'}   && $F{'bill_zip'} ne '')) {
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_name(\$F{'bill_name'});
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_addr(\$F{'bill_addr'});
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_city(\$F{'bill_city'});
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_state(\$F{'bill_state'});
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_zip(\$F{'bill_zip'});
    &show_billing_page({ prodlist => $prodlist }) unless &vrfy_bill_country(\$F{'bill_country'});
  } else {
    $F{'bill_name'}     = $F{'ship_name'};
    $F{'bill_addr'}     = $F{'ship_addr'};
    $F{'bill_city'}     = $F{'ship_city'};
    $F{'bill_state'}    = $F{'ship_state'};
    $F{'bill_zip'}      = $F{'ship_zip'};
    $F{'bill_country'}  = $F{'ship_country'};
  }

  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_email(\$F{'email'});

  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_cctype(\$F{'cctype'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ccnum(\$F{'ccnum'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ccexp_m(\$F{'ccexp_m'});
  &show_billing_page({ prodlist => $prodlist }) unless &vrfy_ccexp_y(\$F{'ccexp_y'});

  &show_billing_page({ prodlist => $prodlist }) unless &save_cardinfo(${ &calc_total($prodlist) }, $prodlist);
  $logid = &log_transaction($prodlist);

  &save_snapshot({
    vendorid      => $F{'vendorid'},
    prodlist      => $prodlist,
    total         => ${ &calc_total($prodlist) },
    orderid       => $F{'orderid'},
    bill_name     => $F{'bill_name'},
    bill_addr     => $F{'bill_addr'},
    bill_city     => $F{'bill_city'},
    bill_state    => $F{'bill_state'},
    bill_zip      => $F{'bill_zip'},
    bill_country  => $F{'bill_country'},
    ship_method   => $F{'ship_method'},
    ship_class    => $F{'ship_class'},
    ship_name     => $F{'ship_name'},
    ship_addr     => $F{'ship_addr'},
    ship_city     => $F{'ship_city'},
    ship_state    => $F{'ship_state'},
    ship_zip      => $F{'ship_zip'},
    ship_country  => $F{'ship_country'},
    ship_phone    => $F{'ship_phone'},
    email         => $F{'email'},
    logid         => $logid, });

  my $T = NDC::Transaction->new();
  $T->email_ordernotice(\ $F{'cardid'});
  #$T->email_customernotice();#&email_alert( &restore_log($logid) );

  &update_acl('complete');
  &show_finish_page( &restore_log( \$logid ) );
}

######################################################################
sub show_preview_page {
  my $prodlist = shift;
  my $tmpl = $C->tmpl("$F{vendorid}/order_preview");
  $tmpl->param(
    products  => &mk_preview_tmpl_obj($prodlist),
    total     => &mk_currency( &calc_total($prodlist) ),
    vendorid  => $F{'vendorid'},
    error     => $ERRSTR,
  );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_billing_page {
  my $snapshot = shift;
  my $ice = &freeze( $snapshot->{prodlist} );
  my $flds = {};

  &create_flds($FIELDS, $flds);
  &update_acl('failed') if ($ERRSTR);

  my $tmpl = $C->tmpl("$F{vendorid}/order_billing");
  $tmpl->param($flds);
  $tmpl->param(
    products  => &mk_billing_tmpl_obj( $snapshot->{prodlist} ),
    sessid    => $F{'sessid'},
    sum       => &md5_hex($ice),
    total     => &mk_currency( &calc_total( $snapshot->{prodlist} ) ),
    vendorid  => $F{'vendorid'},
    error     => $ERRSTR,
  );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub show_finish_page {
  my $log = shift;
  my $prodlist = (&thaw($log->{prodlist}))[0];
  my $tmpl = $C->tmpl("$F{vendorid}/order_finish");
  $tmpl->param(
    bill_name     => &encode_entities( $log->{bill_name} ),
    bill_addr     => &encode_entities( $log->{bill_addr} ),
    bill_city     => &encode_entities( $log->{bill_city} ),
    bill_state    => &encode_entities( $log->{bill_state} ),
    bill_zip      => &encode_entities( $log->{bill_zip} ),
    bill_country  => &encode_entities( $log->{bill_country} ),
    ship_name     => &encode_entities( $log->{ship_name} ),
    ship_addr     => &encode_entities( $log->{ship_addr} ),
    ship_city     => &encode_entities( $log->{ship_city} ),
    ship_state    => &encode_entities( $log->{ship_state} ),
    ship_zip      => &encode_entities( $log->{ship_zip} ),
    ship_country  => &encode_entities( $log->{ship_country} ),
    ship_phone    => &encode_entities( $log->{ship_phone} ),
    email         => &encode_entities( $log->{email} ),
    orderid       => &encode_entities( $log->{orderid} ),
    saletime      => &encode_entities( $log->{saletime} ),
    amount        => &mk_currency( \sprintf("%.2f", $log->{amount}) ),
    products      => &mk_billing_tmpl_obj( $prodlist ),
    ship_method   => $FIELDS->{ship_method}->{labels}->{$log}->{ship_method},
    show_notice   => ($log->{ship_class} eq 'home') ? 1 : 0,
  );
  print $Q->header();
  print $tmpl->output();
  exit;
}

######################################################################
sub log_transaction {
  my $prodlist = shift;
  my $sth;

  ## log
  $C->db_query('INSERT INTO transactions '.
               '(saletime,orderid,cardid,amount,ccnum,email, '.
               'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country, '.
               'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country, '.
               'ship_method,ship_class,ship_phone,ip,vendorid,prodlist) '.
               'VALUES (NOW(),?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [
      $F{'orderid'},$F{'cardid'},$F{'amount'},reverse(substr(reverse($F{'ccnum'}), 0, 4)),$F{'email'},
      $F{'bill_name'},$F{'bill_addr'},$F{'bill_city'},$F{'bill_state'},$F{'bill_zip'},$F{'ship_country'},
      $F{'ship_name'},$F{'ship_addr'},$F{'ship_city'},$F{'ship_state'},$F{'ship_zip'},$F{'ship_country'},
      $F{'ship_method'},$F{'ship_class'},$F{'ship_phone'},&ip2int($ENV{'REMOTE_ADDR'}),
      $F{'vendorid'}, &freeze($prodlist) ]);

  ## get sid to use later
  $sth = $C->db_query('SELECT sid FROM transactions WHERE sid=LAST_INSERT_ID()');
  return ($sth->fetchrow_array())[0];
}

######################################################################
sub mk_prodlist {
  my $f = shift;
  my (%hash, $sid, $sth);
  foreach my $k (grep { /^qty\d+$/ } keys %$f) {
    ($sid = $k) =~ s/^qty//;
    $hash{$sid}->{qty} = $f->{$k};

    ## prevent non-existant products from being processed
    $sth = $C->db_remote_cached_query('SELECT COUNT(*) FROM specials WHERE sid=?', [$sid]);
    if ($sth->rows()) {
      $sth->finish();
    } else {
      $sth->finish();
      next;
    }

    my $prod = NDC::Special->new();
    $prod->load_by_sid($sid);
    $hash{$sid}->{obj} = $prod;
  }
  return \%hash;
}

######################################################################
sub mk_billing_tmpl_obj {
  my $ref = shift;

  my @tmp;
  foreach my $i (keys %$ref) {
    next unless $ref->{$i}->{qty};
    my %row = (
      title     => &encode_entities( $ref->{$i}->{obj}->{title} ),
      manuf     => &encode_entities( $ref->{$i}->{obj}->{manuf} ),
      item_num  => &encode_entities( $ref->{$i}->{obj}->{item_num} ),
      price     => &mk_currency( \sprintf("%.2f", $ref->{$i}->{obj}->{price}) ),
      qty       => $ref->{$i}->{qty},
      total     => &mk_currency( \sprintf("%.2f", ($ref->{$i}->{qty})
                    ? $ref->{$i}->{qty} * $ref->{$i}->{obj}->{price}
                    : 0.0 ) ),
    );
    push @tmp, \%row;
  }
  return \@tmp;
}

######################################################################
sub mk_preview_tmpl_obj {
  my $ref = shift;

  my @tmp;
  foreach my $i (keys %$ref) {
    my %row = (
      sid       => $i,
      title     => &encode_entities( $ref->{$i}->{obj}->{title} ),
      manuf     => &encode_entities( $ref->{$i}->{obj}->{manuf} ),
      item_num  => &encode_entities( $ref->{$i}->{obj}->{item_num} ),
      price     => &mk_currency( \sprintf("%.2f", $ref->{$i}->{obj}->{price}) ),
      qty       => $ref->{$i}->{qty},
      total     => &mk_currency( \sprintf("%.2f", ($ref->{$i}->{qty})
                    ? $ref->{$i}->{qty} * $ref->{$i}->{obj}->{price}
                    : 0.0 ) ),
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
sub gen_orderid {
  my @chars = ('A'..'Z');
  srand();
  return 'N'.join('', @chars[map{rand @chars} (1 .. 14)]);
}

######################################################################
sub create_flds {
  my $flds      = $_[0];
  my $fld_list  = $_[1];
  my ($fld, $type, $entry, $label, $p);

  foreach (keys %$flds) {
    $p = $flds->{$_};
    $p->{name} = $_;
    $type = $p->{type};
    my $hash = {};
    foreach $entry (@{$CGI_FIELDS->{$type}}) {
      $hash->{$entry} = $p->{$entry} || '';
    }
    $fld = $Q->$type($hash);
    $fld_list->{"${_}"} = $fld;
  }
  return 0;
}

######################################################################
sub calc_total {
  my $ref = shift;
  my $t = 0;
  foreach my $i (keys %$ref) {
    $t += $ref->{$i}->{qty} * $ref->{$i}->{obj}->{price} if ($ref->{$i}->{qty});
  }
  $t = sprintf("%.2f", $t);
  return \$t;
}

######################################################################
sub start_new_session {
  my ($sessid, $ip, $no_session, @chars, $sth);

  $ip  = &ip2int($ENV{'REMOTE_ADDR'});
  @chars = ('a'..'z', 'A'..'Z', '0'..'9');
  srand();

  $no_session = 10;
  while ($no_session > 1) {
    $sessid = join("", @chars[map{rand @chars} (1 .. 32)]);
    $C->db_query('LOCK TABLES sessions WRITE');
    $sth = $C->db_query('SELECT sessid FROM sessions WHERE sessid=?', [$sessid]);
    if ($sth->rows == 0) {
      $C->db_query('INSERT INTO sessions (sessid,ip,lasttime,acl,data)'.
                   ' VALUES (?,?,NOW(),?,?)',
                   [$sessid, $ip, 0, '']);
      $C->db_query('UNLOCK TABLES');
      $no_session = 0;
    } else {
      $C->db_query('UNLOCK TABLES');
      sleep 1;
    }
  }
  &fatal_error('Unable to create session.') if ($no_session);
  return $sessid;
}

######################################################################
sub save_cardinfo {
  ($F{'amount'}, my $prodlist) = @_;

  $F{'vendor'} = $C->vendors()->{ $F{'vendorid'} };
  $F{'orderid'} = &gen_orderid();
  #$F{'ccexp'}   = sprintf("%02d", $F{'ccexp_m'}) . substr($F{'ccexp_y'},2,2);
  my $ship_method = $FIELDS->{ship_method}->{labels}->{$F{ship_method}};

  my $text = <<MESSAGE_TEXT;
Order Information\r
=================\r
Vendor:		$F{vendor}\r
Order ID:	$F{orderid}\r
Amount:		\$$F{amount}\r
Email Address:	$F{email}\r
\r
Credit Card Information\r
=======================\r
Card Type:	$F{cctype}\r
Card Number:	$F{ccnum}\r
Expiration:	$F{ccexp_m}/$F{ccexp_y}\r
\r
Billing Information\r
===================\r
Name:		$F{bill_name}\r
Address:	$F{bill_addr}\r
City:		$F{bill_city}\r
State:		$F{bill_state}\r
Postal Code:	$F{bill_zip}\r
Country:		$F{bill_country}\r
\r
Shipping Information\r
====================\r
Method:	        $ship_method\r
Destination:	$F{ship_class}\r
Name:		$F{ship_name}\r
Address:	$F{ship_addr}\r
City:		$F{ship_city}\r
State:		$F{ship_state}\r
Postal Code:	$F{ship_zip}\r
Country:	$F{ship_country}\r
Phone:		$F{ship_phone}\r
\r
Products Ordered\r
================\r
MESSAGE_TEXT

  foreach my $i (keys %$prodlist) {
    next unless $prodlist->{$i}->{qty};
    $text .=  $prodlist->{$i}->{obj}->{manuf} .' '.
              $prodlist->{$i}->{obj}->{title}  .' ['.
              $prodlist->{$i}->{obj}->{item_num} ."]\r\n  \$".
              &mk_currency( \sprintf("%.2f", $prodlist->{$i}->{obj}->{price}) ) .' x '.
              $prodlist->{$i}->{qty} .' = $'.
              &mk_currency( \sprintf("%.2f", ($prodlist->{$i}->{qty})
                ? $prodlist->{$i}->{qty} * $prodlist->{$i}->{obj}->{price}
                : 0.0 ) ) ."\r\n\r\n";
  }

  $text = $O->gpg_encrypt(\$text);
  &fatal_error('Encryption failed.  Please contact site administrator.')
    unless (length($$text));
  $C->db_query('INSERT INTO cards (data,orderid) VALUES (?,?)', [ $$text, $F{'orderid'} ] );

  ## get sid to use later
  my $sth = $C->db_query('SELECT sid FROM cards WHERE sid=LAST_INSERT_ID()');
  $F{'cardid'} = ($sth->fetchrow_array())[0];
  return 1;
}

######################################################################
sub save_snapshot {
  my $objptr = shift;
  $C->db_query('UPDATE sessions SET data=? WHERE sessid=?',
    [ &freeze( $objptr ), $F{'sessid'} ] );
}

######################################################################
sub restore_snapshot {
  my $sth = $C->db_query('SELECT data FROM sessions WHERE sessid=?', [${$_[0]}]);
  return ($sth->fetchrow_array())[0];
}

######################################################################
sub restore_log {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%b %e, %Y / %H:%i:%s") AS saletime,'.
                         'orderid,amount,ccnum,email,prodlist,ship_method,ship_class,ship_phone,'.
                         'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country,'.
                         'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country,'.
                         'vendorid FROM transactions WHERE sid=?', [${$_[0]}]);
  return $sth->fetchrow_hashref();
}

######################################################################
sub is_valid_ccnum {
  my $ref = shift;
  my ($sum, $weight, $mul);

  return 0 if ($$ref =~ /[^\d\s-]/);
  $$ref =~ s/\D//g;
  return 0 unless (length($$ref) >= 13);

  $mul = 1;
  foreach my $i (reverse split //, $$ref) {
    $weight = $i * $mul;
    $sum += ($weight > 9) ? $weight - 9 : $weight;
    $mul = 3 - $mul;
  }
  return ($sum % 10) ? 0 : 1;
}

######################################################################
sub vrfy_sessid {
  my $ref = shift || \'';
  my $sth;

  do { $ERRSTR = 'Invalid Session ID.  Starting new session.'; return 0; }
    unless ($$ref && $$ref =~ /^([a-zA-Z0-9]{32})$/);
  $$ref = $1;

  $sth = $C->db_query('SELECT COUNT(*) FROM sessions WHERE sessid=?', [$$ref]);
  do { $ERRSTR = 'Invalid Session ID.  Starting new session.'; return 0; }
    unless ($sth->fetchrow_array());
  $sth->finish();

  ## update session timestamp
  &save_lasttime;
  return 1;
}

######################################################################
sub vrfy_prodlist {
  my $ref = shift;
  my $sth;

  foreach my $i (keys %$ref) {
    $sth = $C->db_remote_cached_query('SELECT COUNT(*) FROM specials '.
      'WHERE sid=? AND vendorid=?', [$i, $F{'vendorid'}]);
    if (! $sth->rows() ) {
      $ERRSTR = 'Invalid Product Number passed: '. &encode_entities($i);
      return 0;
    }
    $sth->finish();
  }
  return 1;
}

######################################################################
sub vrfy_acl {
  my $steps = shift;
  my ($acl, $sth);

  $sth = $C->db_query('SELECT acl FROM sessions WHERE sessid=?', [$F{'sessid'}]);
  $acl = $sth->fetchrow_array();
  $sth->finish();

  foreach my $i (@$steps) {
    do { $ERRSTR = 'Invalid ACL'; return 0; }
      unless ($acl & $ACL{$i.'-complete'});
  }

  $F{'acl'} = $acl;
  return 1;
}

######################################################################
sub vrfy_email {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to select an Email Address.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Email Address can contain no more than '. $FIELDS->{'email'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'email'}->{'maxlength'});
  do { $ERRSTR = 'Email Address must contain at least '. $FIELDS->{'email'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'email'}->{'minlength'});
  do { $ERRSTR = 'Email Address is improperly formatted.'; return 0; }
    unless ($$ref =~ /^([\w\d._+-]+@(?:\w(?:[\w\d-]*[\w\d])?\.)+\w{2,5})$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_ship_method {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to select a Shipping Method.'; return 0; }
    unless ($$ref);

  foreach my $i (@SHIPMETHOD_VALUES) { return ($$ref = $i) if ($i eq $$ref); }

  $ERRSTR = 'Invalid Shipping Method passed.';
  return 0;
}

######################################################################
sub vrfy_ship_class {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to select a Shipping Destination.'; return 0; }
    unless ($$ref);

  foreach my $i (@SHIPCLASS_VALUES) { return ($$ref = $i) if ($i eq $$ref); }

  $ERRSTR = 'Invalid Shipping Destination passed.';
  return 0;
}

######################################################################
sub vrfy_ship_name {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter your Full Name.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Shipping Name can contain no more than '. $FIELDS->{'ship_name'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_name'}->{'maxlength'});
  do { $ERRSTR = 'Shipping Name must contain at least '. $FIELDS->{'ship_name'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_name'}->{'minlength'});
  do { $ERRSTR = 'Shipping Name contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_ship_addr {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter an Shipping Address.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Shipping Address can contain no more than '. $FIELDS->{'ship_addr'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_addr'}->{'maxlength'});
  do { $ERRSTR = 'Shipping Address must contain at least '. $FIELDS->{'ship_addr'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_addr'}->{'minlength'});
  do { $ERRSTR = 'Shipping Address contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  do { $ERRSTR = 'Shipping Address cannot be a Post Office Box.'; return 0; }
    unless ($$ref !~ /^(p\.?\s*o\.?\s*\s+box|post\s+office\s+box)/i);
  return 1;
}

######################################################################
sub vrfy_ship_city {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Shipping City.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Shipping City can contain no more than '. $FIELDS->{'ship_city'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_city'}->{'maxlength'});
  do { $ERRSTR = 'Shipping City must contain at least '. $FIELDS->{'ship_city'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_city'}->{'minlength'});
  do { $ERRSTR = 'Shipping City contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_ship_state {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;
  $$ref = uc($$ref);

  do { $ERRSTR = 'Invalid Shipping State passed.'; return 0 }
    unless (defined $$ref);
  do { $ERRSTR = 'Shipping State can contain no more than '. $FIELDS->{'ship_state'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_state'}->{'maxlength'});
  do { $ERRSTR = 'Shipping State must contain at least '. $FIELDS->{'ship_state'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_state'}->{'minlength'});
  do { $ERRSTR = 'Shipping State contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([A-Z]{2})$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_ship_zip {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Shipping Postal Code.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Shipping Postal Code can contain no more than '. $FIELDS->{'ship_zip'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_zip'}->{'maxlength'});
  do { $ERRSTR = 'Shipping Postal Code must contain at least '. $FIELDS->{'ship_zip'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_zip'}->{'minlength'});
  do { $ERRSTR = 'Shipping Postal Code is formatted incorrectly.'; return 0; }
    unless ($$ref =~ /^(\d{5,9})$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_ship_country {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Shipping Country.'; return 0; }
    unless ($$ref);

  foreach my $i (@{ $O->country_values() }) { return ($$ref = $i) if ($i eq $$ref); }

  $ERRSTR = 'Invalid Shipping Country passed.';
  return 0;
}

######################################################################
sub vrfy_ship_phone {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;
  $$ref =~ s/\s{2,}/ /;

  do { $ERRSTR = 'You failed to enter a Phone Number.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Phone Number can contain no more than '. $FIELDS->{'ship_phone'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'ship_phone'}->{'maxlength'});
  do { $ERRSTR = 'Phone Number must contain at least '. $FIELDS->{'ship_phone'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'ship_phone'}->{'minlength'});
  do { $ERRSTR = 'Phone Number is formatted incorrectly.'; return 0; }
    unless ($$ref =~ /^(\+?[0-9- ]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_name {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter your Billing Name.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Billing Name can contain no more than '. $FIELDS->{'bill_name'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'bill_name'}->{'maxlength'});
  do { $ERRSTR = 'Billing Name must contain at least '. $FIELDS->{'bill_name'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'bill_name'}->{'minlength'});
  do { $ERRSTR = 'Billing Name contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_addr {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Billing Address.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Billing Address can contain no more than '. $FIELDS->{'bill_addr'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'bill_addr'}->{'maxlength'});
  do { $ERRSTR = 'Billing Address must contain at least '. $FIELDS->{'bill_addr'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'bill_addr'}->{'minlength'});
  do { $ERRSTR = 'Billing Address contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_city {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Billing City.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Billing City can contain no more than '. $FIELDS->{'bill_city'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'bill_city'}->{'maxlength'});
  do { $ERRSTR = 'Billing City must contain at least '. $FIELDS->{'bill_city'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'bill_city'}->{'minlength'});
  do { $ERRSTR = 'Billing City contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([\x20-\x7f]+)$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_state {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;
  $$ref = uc($$ref);

  do { $ERRSTR = 'Invalid Billing State passed.'; return 0 }
    unless (defined $$ref);
  do { $ERRSTR = 'Billing State can contain no more than '. $FIELDS->{'bill_state'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'bill_state'}->{'maxlength'});
  do { $ERRSTR = 'Billing State must contain at least '. $FIELDS->{'bill_state'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'bill_state'}->{'minlength'});
  do { $ERRSTR = 'Billing State contains illegal characters.'; return 0; }
    unless ($$ref =~ /^([A-Z]{2})$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_zip {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Billing Postal Code.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Billing Postal Code can contain no more than '. $FIELDS->{'bill_zip'}->{'maxlength'} .' characters.'; return 0; }
    unless (length($$ref) <= $FIELDS->{'bill_zip'}->{'maxlength'});
  do { $ERRSTR = 'Billing Postal Code must contain at least '. $FIELDS->{'bill_zip'}->{'minlength'} .' characters.'; return 0; }
    unless (length($$ref) >= $FIELDS->{'bill_zip'}->{'minlength'});
  do { $ERRSTR = 'Billing Postal Code is formatted incorrectly.'; return 0; }
    unless ($$ref =~ /^(\d{5,9})$/);
  $$ref = $1;
  return 1;
}

######################################################################
sub vrfy_bill_country {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Billing Country.'; return 0; }
    unless ($$ref);

  foreach my $i (@{ $O->country_values() }) { return ($$ref = $i) if ($i eq $$ref); }

  $ERRSTR = 'Invalid Billing Country passed.';
  return 0;
}

######################################################################
sub vrfy_cctype {
  my $ref = shift || \'';

  do { $ERRSTR = 'Invalid Credit Card Type.'; return 0 }
    unless (defined $$ref);

  foreach my $i (@CCTYPE_VALUES) {
    return ($$ref = $i) if ($i eq $$ref);
  }

  $ERRSTR = 'Invalid Credit Card Type.';
  return 0;
}

######################################################################
sub vrfy_ccnum {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'You failed to enter a Credit Card Number.'; return 0; }
    unless ($$ref);
  do { $ERRSTR = 'Credit Card Number is invalid.'; return 0; }
    unless (&is_valid_ccnum($ref));
  $$ref =~ /^(.*)$/;  ## untaint
  $$ref = $1;         ## `-> validated by &is_valid_ccnum
  return 1;
}

######################################################################
sub vrfy_ccexp_m {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'Invalid Expiration Date.'; return 0 }
    unless (defined $$ref);

  foreach my $i (@CCEXPM_VALUES) {
    return ($$ref = $i) if ($i eq $$ref);
  }

  $ERRSTR = 'Invalid Expiration Date.';
  return 1;
}

######################################################################
sub vrfy_ccexp_y {
  my $ref = shift || \'';
  $$ref =~ s/^\s*(.*)\s*$/$1/;

  do { $ERRSTR = 'Invalid Expiration Date.'; return 0 }
    unless (defined $$ref);

  foreach my $i (@CCEXPY_VALUES) {
    return ($$ref = $i) if ($i eq $$ref);
  }

  $ERRSTR = 'Invalid Expiration Date.';
  return 1;
}

######################################################################
sub update_acl {
  my $type = shift;
  my ($acl, $sth);

  $sth = $C->db_query('SELECT acl FROM sessions WHERE sessid=?', [$F{'sessid'}]);
  $acl = $sth->fetchrow_array();
  $sth->finish();

  if ($type eq 'complete') {
    $acl |= $ACL{$F{'mode'}.'-complete'};
    $acl ^= $ACL{$F{'mode'}.'-processing'};
  } elsif ($type eq 'processing') {
    $acl |= $ACL{$F{'mode'}.'-processing'};
  } else {
    $acl ^= $ACL{$F{'mode'}.'-processing'};
  }
  $C->db_query('UPDATE sessions SET acl=? WHERE sessid=?', [$acl, $F{'sessid'}]);
}

######################################################################
sub get_acl {
  my $sth = $C->db_query('SELECT acl FROM sessions WHERE sessid=?', [$F{'sessid'}]);
  return $sth->fetchrow_array();
}

######################################################################
sub save_lasttime {
  $C->db_query('UPDATE sessions SET lasttime=NOW() WHERE sessid=?',
               [$F{'sessid'}]);
}

######################################################################
sub ip2int {
  my $ip = shift or &fatal_error("ip2int: invalid parameters.");
  my $int = 0;

  my @octs = split /\./, $ip;
  for (my $i = 0; $i < 4; $i++) {
    $int <<= 8;
    $int += $octs[$i];
  }
  return $int;
}

######################################################################
sub fatal_error {
  my $errstr = shift || '';
  print $Q->header();
  print "<html><head><title>Fatal Error Occurred</title><head>
<body><h1>Fatal Error Occurred</h1>$errstr</body></html>";
  exit;
}

######################################################################
sub debug {
  return unless ($DEBUG);
  print @_;
} 

1;
## vim: ts=2 et :
