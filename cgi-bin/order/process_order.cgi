#!/usr/bin/perl -T
##
## process_orders.cgi - Order processing script
##
## Copyright (C) 2006 2k3 Technologies
##
## $Author: Jarnold $
## $Date: 4/05/06 10:37a $
## $Revision: 3 $
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
use NDC::Order;

## multi-screen modes
my %Modes = (
  'default'  => \&do_default,
  'view'     => \&do_view_open_orders,
  'resend'   => \&do_view_resend,
  'ack'      => \&do_view_ack,
  'close'    => \&do_view_close,
  'detail'   => \&do_view_detail,
  'print'    => \&do_print_detail,
  'notify'   =>\&do_resend,
  'sendack'  =>\&do_acknowledge,
  'wrap'     =>\&do_close_out,
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
  'amex' => 'American Express',
  'disc' => 'Discover',
  'mc'   => 'MasterCard',
);

my $Q = CGI->new();
my $C = NDC::Conf->new();
my $O = NDC::Order->new();
my %F = $Q->Vars();
my $blinder = NDC::Blinder->new();
my $run_mode = $C->run_mode();

my $ERRSTR = '';
our $DEBUG = 0;
our $DEBUG_INIT = 0;

my $NOTICE_ADDR = '';
if ($run_mode eq 'production') {
  $NOTICE_ADDR = 'sales@classicwireless.org';
} else {
  $NOTICE_ADDR = 'jarnold@2k3technologies.com';
}
my $SENDMAIL    = '/usr/sbin/sendmail';


## main 
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
#------------------------------------------------------------------------------
# Entry-point routines
#------------------------------------------------------------------------------
sub do_default {
  &show_default();
}

#------------------------------------------------------------------------------
# Close out the order and delete the credit card information from the database
#
# Change History:
# 04032006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_close_out {
  die "No order id passed to do_close_out!" unless $F{'id'};
  my $query = 'select orderid,cardid,saletime from transactions where sid = ?';
  my $sth = $C->db_query($query,[$F{'id'}]);
  my ($orderNumber,$ccid,$saletime) = $sth->fetchrow();
  $sth->finish();
  if (!$F{'confirm'}) {
    &confirm_close($orderNumber);
  } else {
  # close this order out.
  $query = 'delete from cards where sid = ?';
  $sth = $C->db_query($query,[$ccid]);
  $sth->finish();
  $query = "update transactions set bill_addr2 = '', status = 'closed', saletime = ?, close_date = NOW() where sid = ?";
  $sth = $C->db_query($query,[$saletime,$F{'id'}]);
  $sth->finish();
  &show_success("Order Number " . $orderNumber . " has been closed and all credit card information associated with it has " .
    "been deleted from the system.");
  }
  
}
#------------------------------------------------------------------------------
# Send an acknowledgement of the reciept of order to the customer
#
# Change History:
# 04032006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_acknowledge {
  die "No order id passed to do_acknowledge!" unless $F{'id'};
  my $query = 'select prodlist,email,ship_name,orderid,cc_type,ccnum,amount,saletime from transactions where sid = ?';
  my $sth = $C->db_query($query,[$F{'id'}]);
  my $ref = $sth->fetchrow_hashref();
  
  my $prodlist = &mk_view_tmpl_obj($ref->{prodlist});
  my @products = @$prodlist;
  my $productsText = "Products Ordered\r\n================\r\n";
  foreach my $product (@products) {
    next unless $product->{qty};
    $productsText .=  $product->{manuf} .' '.
              $product->{title}  .' ['.
              $product->{item_num} ."]\r\n  \$".
              &mk_currency( \sprintf("%.2f", $product->{price}) ) .' x '.
              $product->{qty} .' = $'.
              &mk_currency( \sprintf("%.2f", ($product->{qty})
                ? $product->{qty} * $product->{price}
                : 0.0 ) ) ."\r\n\r\n";
  }
  my $email = $ref->{email};
  my $name = $ref->{ship_name};
  my $orderNumber = $ref->{orderid};
  my $ccType = %cctypes->{$ref->{cc_type}};
  my $ccNum = 'xxxx-xxxx-xxxx-' . reverse($ref->{ccnum});
  my $amount = &mk_currency(\sprintf("%.2f", $ref->{amount}));
  my $saletime = $ref->{saletime};
  
  $sth->finish();
  &email_send_ack($productsText,$email,$name,$orderNumber,$ccType,$ccNum,$amount);
  $query = "update transactions set status = 'ack',saletime = ?, ack_date = NOW() where sid = ?";
  $sth = $C->db_query($query,[$saletime,$F{'id'}]);
  $sth->finish();
  &show_success("Order Acknowledgement for Order Number " . $orderNumber . " has been sent successfully.");
  
}
#------------------------------------------------------------------------------
# Resend the original order notification to the sales team.
#
# Change History:
# 03.28.2006 - Initial Version - jarnold
# 04.05.2006 - Added cc exp and full cc number to email
#------------------------------------------------------------------------------
sub do_resend {
  die "No order id passed to do_resend!" unless $F{'id'};
  ## We Have to:  Get the order information from the transactions table.
  ##  Get the CC information from the cards table
  ##  Build the message 
  ## Send the message
  ## This uses methods from order.cgi - transaction.pm
  my $query = 'select orderid,vendorid,cardid,amount,email,ccnum,bill_name,' .
              'bill_addr,bill_city,bill_state,bill_zip,bill_country,ship_method,' .
              'ship_class,ship_name,ship_addr,ship_city,ship_state,ship_zip,' .
              'ship_country,ship_phone,prodlist,cc_type,cc_exp,bill_addr2 from transactions where sid = ?';
  my $sth = $C->db_query($query,[$F{'id'}]);
  my $ref = $sth->fetchrow_hashref();
  my $prodlist = &mk_view_tmpl_obj($ref->{prodlist});
  my @products = @$prodlist;
  my %msgfields = ();
  # Populate the known message fields
  %msgfields->{orderId} = $ref->{orderid};
  %msgfields->{amount} = &mk_currency(\sprintf("%.2f", $ref->{amount}));
  %msgfields->{email} = $ref->{email};
  %msgfields->{ccType} = %cctypes->{$ref->{cc_type}};
  if (%msgfields->{ccType} eq '') { %msgfields->{ccType} = 'Not Available'; }
  %msgfields->{ccExp} = $ref->{cc_exp};
  if (%msgfields->{ccExp} eq '') { %msgfields->{ccExp} = 'Not Available'; }
  
  
  %msgfields->{billName} = $ref->{bill_name};
  %msgfields->{billAddr} = $ref->{bill_addr};
  %msgfields->{billCity} = $ref->{bill_city};
  %msgfields->{billState} = $ref->{bill_state};
  %msgfields->{billZip} = $ref->{bill_zip};
  %msgfields->{billCountry} = $ref->{bill_country};
  
  %msgfields->{shipMethod} = $ref->{ship_method};
  %msgfields->{shipClass} = $ref->{ship_class};
  
  %msgfields->{shipName} = $ref->{ship_name};
  %msgfields->{shipAddr} = $ref->{ship_addr};
  %msgfields->{shipCity} = $ref->{ship_city};
  %msgfields->{shipState} = $ref->{ship_state};
  %msgfields->{shipZip} = $ref->{ship_zip};
  %msgfields->{shipCountry} = $ref->{ship_country};
  %msgfields->{shipPhone} = $ref->{ship_phone};

  if ($ref->{bill_addr2} eq '') {
    %msgfields->{ccNum} = 'xxxx-xxxx-xxxx-' . $ref->{ccnum};
  } else {
    my $seed = $blinder->generate_seed($ref->{ship_name});
    %msgfields->{ccNum} = $blinder->unblind($ref->{bill_addr2},$seed);
  }
  my $query2 = 'select name from vendor where sid = ?';
  my $sth2 = $C->db_query($query2,[$ref->{vendorid}]);
  %msgfields->{vendorId} = $sth2->fetchrow();
  $sth2->finish();
  $sth->finish();

  
  &debug("Order Id = " . $F{'id'} . "<br>");
  &debug("Product List = " . @products . "<br>");

  my $text =  "\r\nOrder Information\r\n=================\r\n" .
              "Vendor:		" . %msgfields->{vendorId} ."\r\n" .
              "Order ID:	      " . %msgfields->{orderId} . "\r\n" .
              "Amount:		" . %msgfields->{amount} . "\r\n" .
              "Email Address:	". %msgfields->{email} . "\r\n\r\n" .
              "Credit Card Information\r\n=======================\r\n" .
              "Card Type:	      " . %msgfields->{ccType} . "\r\n" .
              "Card Number:	". %msgfields->{ccNum} . "\r\n" .
              "Exp Date:         " . %msgfields->{ccExp} . "\r\n\r\n" .
              "Billing Information\r\n===================\r\n" .
              "Name:             " . %msgfields->{billName} . "\r\n" .
              "Address:  	      " . %msgfields->{billAddr} . "\r\n" .
              "City:		      " . %msgfields->{billCity} . "\r\n" .
              "State:		" . %msgfields->{billState} . "\r\n" .
              "Postal Code:	" . %msgfields->{billZip} . "\r\n" .
              "Country:		" . %msgfields->{billCountry} . "\r\n\r\n" .
              "Shipping Information\r\n====================\r\n" .
              "Method:	      " . %msgfields->{shipMethod} . "\r\n" .
              "Destination:	" . %msgfields->{shipClass} . "\r\n" .
              "Name:		      " . %msgfields->{shipName} . "\r\n" .
              "Address:	      " . %msgfields->{shipAddr} . "\r\n" .
              "City:		      " . %msgfields->{shipCity} . "\r\n" .
              "State:		" . %msgfields->{shipState} . "\r\n" .
              "Postal Code:	" . %msgfields->{shipZip} . "\r\n" .
              "Country:	      " . %msgfields->{shipCountry} . "\r\n" .
              "Phone:		" . %msgfields->{shipPhone} . "\r\n\r\n" .
              "Products Ordered\r\n================\r\n";

  foreach my $product (@products) {
    next unless $product->{qty};
    $text .=  $product->{manuf} .' '.
              $product->{title}  .' ['.
              $product->{item_num} ."]\r\n  \$".
              &mk_currency( \sprintf("%.2f", $product->{price}) ) .' x '.
              $product->{qty} .' = $'.
              &mk_currency( \sprintf("%.2f", ($product->{qty})
                ? $product->{qty} * $product->{price}
                : 0.0 ) ) ."\r\n\r\n";
  }
  
  &email_resend_notice($text);
  &show_success("Order Resend Notification for Order Number " . %msgfields->{orderId} . " has completed successfully.");
}
#------------------------------------------------------------------------------
# Set up the printer-friendly detail view of a closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_print_detail {
  &show_print_detail($ERRSTR) unless &vrfy_order_sid(\$F{'id'});
  &show_print_detail();
}

#------------------------------------------------------------------------------
# Set up the detail view of a closed order
#
# Change History:
# 03.16.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view_detail {
  &show_detail($ERRSTR) unless &vrfy_order_sid(\$F{'id'});
  &show_detail();
}

#------------------------------------------------------------------------------
#  Set up the view close open orders display.
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view_close {
	my $query = "select count(*) from transactions where status != 'closed'";
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

  $query = "select DATE_FORMAT(saletime,'%m.%d.%Y') as saledate,sid,orderid,bill_name,amount from transactions where status != 'closed'";
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
  
  &show_pending_close(\@orders,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
#  Set up the view ack open orders display.
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view_ack {
	my $query = "select count(*) from transactions where status != 'closed' and status != 'ack'";
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

  $query = "select DATE_FORMAT(saletime,'%m.%d.%Y') as saledate,sid,orderid,bill_name,amount from transactions where status != 'closed' and status != 'ack'";
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
  
  &show_pending_ack(\@orders,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
#  Set up the view resend open orders display.
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view_resend {
	my $query = "select count(*) from transactions where status != 'closed'";
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

  $query = "select DATE_FORMAT(saletime,'%m.%d.%Y') as saledate,sid,orderid,bill_name,amount from transactions where status != 'closed'";
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
  
  &show_pending_resend(\@orders,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
#  Set up the view open orders display.
#
# Change History:
# 03.17.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view_open_orders {
	my $query = "select count(*) from transactions where status != 'closed'";
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

  $query = "select DATE_FORMAT(saletime,'%m.%d.%Y') as saledate,sid,orderid,bill_name,amount from transactions where status != 'closed'";
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
  
  &show_pending(\@orders,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
# Show the default home page for the Order Processing Admin area
#
# Change History:
# 03.17.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_default {
  my $tmpl = $C->tmpl('order/process_order');
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Show printer-friendly details for a selected open order
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
  &debug("Product List = " . $ref->{prodlist} . "<br>");
  &debug("Length of Product List in show_print_detail = " . length($ref->{prodlist}) . "<br>");
  $ref->{amount} = &mk_currency( \sprintf("%.2f", $ref->{amount}) );
  $ref->{sid} = $F{'id'};
  $ref->{status} = %statusi->{$ref->{status}};
  $ref->{cc_type} = %cctypes->{$ref->{cc_type}};
  if ($ref->{ack_date} eq '00.00.0000') {
    $ref->{ack_date} = '';
  }
  if ($ref->{close_date} eq '00.00.0000') {
    $ref->{close_date} = '';
  }
delete($ref->{bill_addr2});

  my $tmpl = $C->tmpl('order/order_detail_pf');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Show all orders not closed for closing
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_pending_close {
  my ($orders,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $tmpl = $C->tmpl('order/open_order_close');
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
# Show all orders not closed for ack
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_pending_ack {
  my ($orders,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $tmpl = $C->tmpl('order/open_order_ack');
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
# Show all orders not closed for resend
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_pending_resend {
  my ($orders,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $tmpl = $C->tmpl('order/open_order_resend');
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
# Show all orders not closed
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_pending {
  my ($orders,$next,$prev,$show_next,$show_prev,$pages) = @_;
  my $tmpl = $C->tmpl('order/open_order_list');
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
# Show details for a selected open order
#
# Change History:
# 03.21.2006 - Initial Version - jarnold
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
  if ($ref->{ack_date} eq '00.00.0000') {
    $ref->{ack_date} = '';
  }
  if ($ref->{close_date} eq '00.00.0000') {
    $ref->{close_date} = '';
  }
delete($ref->{bill_addr2});

  my $tmpl = $C->tmpl('order/order_detail');
  $tmpl->param( %$ref );
  print $Q->header();
  print $tmpl->output();
  exit;
}

#------------------------------------------------------------------------------
# Confirm the close request before actually closing it.
#
# Change History:
# 04032006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub confirm_close {
	my $orderNumber = shift;
	my $template = $C->tmpl('order/order_confirm_close');
	$template->param(orderNumber=>$orderNumber);
  $template->param(id=>$F{'id'});
	print $Q->header();
	print $template->output();
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
  my $count = 0;
  foreach my $i (keys %$prodlist ) {
    next unless $prodlist->{$i}->{qty};
    $count++;
    &debug("Product Count = " . $count . "<br>");
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
  &debug("Length of tmp array in mk_view_tmpl_obj = " . @tmp . "<br>");
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

#------------------------------------------------------------------------------
# Use sendmail to regenerate the order notice
#
# Change History:
# 04032006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub email_resend_notice {
  my $msgText = shift;
  if ($run_mode eq 'production') {
    $msgText = $O->gpg_encrypt($msgText);
  }

  open(MAIL, "|$SENDMAIL -t") or croak "Failed to create new mail: $!\n";
  print MAIL <<_MESSAGE_;
From: Classic Wireless Sales <webmaster\@classicwireless.org>
To: $NOTICE_ADDR
Subject: Online Order Resend Notification

-- RESEND OF PREVIOUS ORDER INFORMATION --
-- CONTACT CUSTOMER FOR FULL CREDIT CARD/PAYMENT INFORMATION --
$msgText
_MESSAGE_
  close(MAIL);
  return 0;
}

#------------------------------------------------------------------------------
# Use sendmail to acknowledge order receipt
#
# Change History:
# 04032006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub email_send_ack {
  my ($productsText,$recipientEmail,$name,$orderNumber,$ccType,$ccNum,$amount) = @_;

  open(MAIL, "|$SENDMAIL -t") or croak "Failed to create new mail: $!\n";
  print MAIL <<_MESSAGE_;
From: Classic Wireless Sales <webmaster\@classicwireless.org>
To: $recipientEmail
Subject: Classic Wireless On-Line Order Acknowledgement

Dear $name,

Thank you for your order!  This email has been sent to notify you that Classic Wireless has
received your order and will be processing it shortly.  Your order number is $orderNumber.  Please
retain this order number in the event that any questions arise regarding your order and you need
to contact us.

The details of your order are:

$productsText
Payment Information:

Credit Card Type:      $ccType
Credit Card (Last 4):  $ccNum
Amount:                $amount

Please note that the amount indicated above does *not* include any shipping and handling charges
associated with this order and that these amounts will be added to the final amount charged to your
credit card.  Shipping and handling charges will vary according to the number and size of items ordered
and the shipping method chosen.

If you have any questions regarding your order, please do not hesitate to contact us!

Email:  sales\@classicwireless.org (Please include your order number in the subject line)
\r\nToll Free: 1.888.698.0123

Thank You For Your Order!
_MESSAGE_
  close(MAIL);
  return 0;
}

######################################################################
sub fatal_error {
  my $errstr = shift || '';
  print $Q->header;
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

sub show_success {
	my $msg = shift;
	my $template = $C->tmpl('order/success');
	$template->param(msg=>$msg);
	print $Q->header(-type=>'text/html');
	print $template->output;
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
