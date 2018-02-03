#!/usr/bin/perl -T
##
## order_history.cgi - View historical information related to customer
## orders.
##
## Copyright (C) 2006 2k3 Technologies
##
## $Author: Jarnold $
## $Date: 4/05/06 10:14a $
## $Revision: 2 $
## Change History:
## 03.15.2006 - Initial Version - jarnold

use lib '..';
use strict;
use NDC::Conf;
use NDC::Transaction;
use CGI;
use CGI::Carp('fatalsToBrowser');
use HTML::Entities;
use HTML::Template;
use FreezeThaw qw(thaw);
use NDC::Blinder;

## multi-screen modes
my %Modes = (
  'default' => \&do_default,
  'view'    => \&do_history,
  'detail'  => \&do_detail_view,
  'print'   =>\&do_print,
);

my %sortCriteria = (
  'c1' => 'orderid',
  'c2' => 'saletime',
  'c3' => 'bill_name',
  'c4' => 'amount',
);

my %sortOrders = (
  'a' => 'ASC',
  'd' => 'DESC',
);

my %statusi = (
  'pend'   => 'Pending',
  'ack'    => 'Acknowledged',
  'closed' => 'Closed',
);

my %cctypes = (
  'visa' => 'Visa',
  'disc' => 'Discover',
  'amex' => 'American Express',
  'mc'   => 'MasterCard',
);

my $Q = CGI->new();
my $C = NDC::Conf->new();
my %F = $Q->Vars();
my $blinder = NDC::Blinder->new();

my $ERRSTR = '';
our $DEBUG = 0;
our $DEBUG_INIT = 0;


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

# Entry Points

#------------------------------------------------------------------------------
# Show the default order history entry page
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_default {
  &show_default();
}

#------------------------------------------------------------------------------
# Set up the list of closed orders
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_history {
	my $query = "select count(*) from transactions where status = 'closed'";
  my @dbps = ();
  my $sth = $C->db_query($query,\@dbps);
	my $numrows = $sth->fetchrow;
  #&debug("Num Rows = " . $numrows . "<br />");
  
	my $numpages = int($numrows / $C->rpp_orders());
	if($numrows % $C->rpp_orders()) {
		$numpages ++;
	}
	$sth->finish;

	my $start = $F{'s'} || 0; # s = starting row

  $query = "select DATE_FORMAT(saletime,'%m.%d.%Y') as saledate,sid,orderid,bill_name,amount from transactions where status='closed'";
  if ($F{'sort'}) {
    $query .= " order by " . %sortCriteria->{$F{'sort'}} . " " . %sortOrders->{$F{'t'}};
  }
  $query .= " LIMIT $start, " . $C->rpp_orders();
  
  $sth = $C->db_query($query,\@dbps);

  my @orders = ();
  while (my $row = $sth->fetchrow_hashref()) {
    $row->{sale_amount} = &mk_currency(\sprintf("%.2f", $row->{amount}));
    $row->{customer} = &encode_entities($row->{bill_name});
    delete($row->{amount});
    delete($row->{bill_name});
    push(@orders,$row);
  }
  $sth->finish();
  
  my $next = $start + $C->rpp_orders();
	my $prev = $start - $C->rpp_orders();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();

	my $pageon = int($start / $C->rpp_orders()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_orders() - 1;
	if($endpage > $numpages) {
		$startpage = $startpage - ($endpage - $numpages);
		$endpage = $numpages;
	}
	if($startpage < 1) { $startpage = 1; }
	my $count = $startpage - 1;

	foreach($startpage .. $endpage) {
		my $tp = 0;
		if($_ eq $pageon) {
			$tp = 1;
		}
    if ($F{'sort'}) {
      push(@pages,{s=>$C->rpp_orders() * $count,page=>$_,tp=>$tp,lastsort=>$F{'sort'},lastorder=>$F{'t'}});
    } else {
      push(@pages,{s=>$C->rpp_orders() * $count,page=>$_,tp=>$tp});
    }
		$count ++;
	}
  
  &show_history(\@orders,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
# Set up the detail view of a closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_detail_view {
  &show_detail($ERRSTR) unless &vrfy_order_sid(\$F{'id'});
  &show_detail();
}

#------------------------------------------------------------------------------
# Set up the printer-friendly detail view of a closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_print {
  &show_print_detail($ERRSTR) unless &vrfy_order_sid(\$F{'id'});
  &show_print_detail();
}

#------------------------------------------------------------------------------
# Show the order history admin page
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_default {
  my $tmpl = $C->tmpl('order/order_history');
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Show a list of all closed orders
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_history {
  my ($orders,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $tmpl = $C->tmpl('order/order_history_list');
  $tmpl->param(orders=>$orders); # orders loop
  $tmpl->param(next=>$$next);
  $tmpl->param(prev=>$$prev);
  $tmpl->param(show_next=>$$show_next);
  $tmpl->param(show_prev=>$$show_prev);
  $tmpl->param(pages=>$pages);
  if ($F{'sort'}) {
    $tmpl->param(lastsort=>$F{'sort'});
    $tmpl->param(lastorder=>$F{'t'});
  }
  print $Q->header(-type=>'text/html');
  print $ERRSTR if ($ERRSTR);
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Show details for a selected closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
# 04.04.2006 - Modified to pull cc_exp and full cc num
#------------------------------------------------------------------------------
sub show_detail {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%m.%d.%Y") AS saletime,'.
                         'DATE_FORMAT(ack_date,"%m.%d.%Y") AS ack_date,'.
                         'DATE_FORMAT(close_date,"%m.%d.%Y") AS close_date,'.
                         'orderid,amount,ccnum,cc_type,cc_exp,bill_addr2,prodlist,'.
                         'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country,'.
                         'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country,'.
                         'ship_phone,ship_class,ship_method,status FROM transactions WHERE sid=?',
                          [ $F{'id'} ] );
  my $ref = $sth->fetchrow_hashref();
  $sth->finish();

  $ref->{prodlist} = &mk_view_tmpl_obj( $ref->{prodlist} );
  $ref->{amount} = &mk_currency( \sprintf("%.2f", $ref->{amount}) );
  $ref->{sid} = $F{'id'};
  $ref->{status} = %statusi->{$ref->{status}};
  $ref->{cc_type} = %cctypes->{$ref->{cc_type}};
  
  delete($ref->{bill_addr2});
  
  my $tmpl = $C->tmpl('order/order_history_detail');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Show printer-friendly details for a selected closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_print_detail {
  my $sth = $C->db_query('SELECT DATE_FORMAT(saletime,"%m.%d.%Y") AS saletime,'.
                         'DATE_FORMAT(ack_date,"%m.%d.%Y") AS ack_date,'.
                         'DATE_FORMAT(close_date,"%m.%d.%Y") AS close_date,'.
                         'orderid,amount,ccnum,cc_type,cc_exp,bill_addr2,prodlist,'.
                         'bill_name,bill_addr,bill_city,bill_state,bill_zip,bill_country,'.
                         'ship_name,ship_addr,ship_city,ship_state,ship_zip,ship_country,'.
                         'ship_phone,ship_class,ship_method,status FROM transactions WHERE sid=?',
                          [ $F{'id'} ] );
  my $ref = $sth->fetchrow_hashref();
  $sth->finish();

  $ref->{prodlist} = &mk_view_tmpl_obj( $ref->{prodlist} );
  $ref->{amount} = &mk_currency( \sprintf("%.2f", $ref->{amount}) );
  $ref->{sid} = $F{'id'};
  $ref->{status} = %statusi->{$ref->{status}};
  $ref->{cc_type} = %cctypes->{$ref->{cc_type}};
  delete($ref->{bill_addr2});
  
  my $tmpl = $C->tmpl('order/order_history_detail_pf');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
#  Subroutines
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# -- Get the product information belonging to the order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
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
    push(@tmp,\%row);
  }
  return \@tmp;
}

#------------------------------------------------------------------------------
# -- Document
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub mk_currency {
  my $ref = shift;
  $$ref =~ s/(^[-+]?\d+?(?=(?>(?:\d{3})+)(?!\d))|\G\d{3}(?=\d))/$1,/g;
  return $$ref;
}

#------------------------------------------------------------------------------
# -- Document
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub get_cardid_from_order_sid {
  my $ref = shift;
  my $sth = $C->db_query('SELECT cardid FROM transactions WHERE sid=?', [ $$ref ]);
  return ($sth->fetchrow_array())[0];
}

#------------------------------------------------------------------------------
# -- Document
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub get_orderid_from_sid {
  my $ref = shift;
  my $sth = $C->db_query('SELECT orderid FROM transactions WHERE sid=?', [ $$ref ]);
  return ($sth->fetchrow_array())[0];
}

#------------------------------------------------------------------------------
# -- Document
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub vrfy_order_sid {
  my $ref = shift || \'';
  my $sth;

  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($$ref && $$ref =~ /^(\d+)$/);
  $$ref = $1;

  $sth = $C->db_query('SELECT COUNT(*) FROM transactions WHERE sid=?', [$$ref]);
  do { $ERRSTR = 'Invalid Order Number.'; return 0; }
    unless ($sth->fetchrow_array());
  $sth->finish();

  return 1;
}

#------------------------------------------------------------------------------
# -- Document
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub fatal_error {
  my $errstr = shift || '';
  print $Q->header(-type=>'text/html');
  print "<html><head><title>Fatal Error Occurred</title><head>
<body><h1>Fatal Error Occurred</h1>$errstr</body></html>";
  exit;
}

#------------------------------------------------------------------------------
#  Error Reporting and Debugging 
#------------------------------------------------------------------------------
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header(-type=>'text/html');
  print $template->output();
  exit;
}

sub debug_init {
  $DEBUG_INIT = 1;
  print $Q->header(-type=>'text/html');
}

sub debug {
  if ($DEBUG) {
    if (!$DEBUG_INIT) {
      debug_init();
    }
    my $msg = shift;
    print $msg;
  }
}
