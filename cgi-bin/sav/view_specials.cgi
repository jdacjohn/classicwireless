#!/usr/bin/perl -T
##
## view_specials.pl - Show internet specials
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: view_specials.cgi,v 1.15 2004/03/22 21:17:26 cameron Exp $

use strict;
use lib '.';
use CGI;
use DBI;
use HTML::Template;
use NDC::Conf;
use CGI::Carp 'fatalsToBrowser';

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();

our $DEBUG = 0;
our $DEBUG_INIT = 0;

my $sth;

my %modes = ( 
	homepage=>\&do_homepage,
	default=>\&do_default,
  shop_now=>\&do_shop_now,
  hp_vendors=>\&do_hp_vendors,
  category=>\&do_view_by_cat
);

################################################
## main ########################################
################################################

$F{'vendorid'} = 100 unless $F{'vendorid'};

if(exists($modes{$F{'mode'}})) {
	$modes{$F{'mode'}}->();
}
else {
	$modes{default}->();
}

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

################################################
## subs ########################################
################################################

#------------------------------------------------------------------------------
# Set up the parameters for the 'shop now' specials list
# Change History:
#------------------------------------------------------------------------------
sub do_shop_now {
  # reserved for relatively recent versions of mysql
  #my $query = "select listname,sid from categories where sid in (select distinct(category) from products where item_num in (select item_num from specials)) order by listname";
  
  # old version mysql statement! grrr... 
  my $query = 'select a.listname,a.sid,b.category,b.item_num,c.item_num from categories a, products b, specials c where a.sid = b.category and b.item_num = c.item_num order by a.sid ';
	$sth = $C->db_query_no_parms($query);
  my %temphash = ();
  while (my $row = $sth->fetchrow_hashref()) {
  #&debug("tblresults hash: " . $row->{'sid'} . "/" . $row->{'listname'} . "<br>");
    %temphash->{$row->{'sid'}} = $row->{'listname'}
  }
  my @categories = ();
  while ((my($sid,$listname)) = each(%temphash)) {
    my %row = ();
    #&debug("SID = " . $sid . "  ListName = " . $listname . "<br>");
    %row->{'cat_name'} = $listname;
    %row->{'cat_sid'} = $sid;
    push(@categories,\%row);
  }
  # Reserved for relatively recent versions of mysql
  #my @categories = ();
  #while (my $row = $sth->fetchrow_hashref()) {
  #  $row->{'cat_name'} = $row->{'listname'};
  #  $row->{'cat_sid'} = $row->{'sid'};
  #  delete($row->{'listname'});
  #  delete($row->{'sid'});
  #  push(@categories,$row);
  #}
	$sth->finish();
	show_shopnow(\@categories);
}

#------------------------------------------------------------------------------
# Set up the parameters for the 'Now Featuring' vendors list
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_hp_vendors {
  my $query = "select sid,name from vendor where sid <> 100 and show_home = 1";
	$sth = $C->db_query_no_parms($query);
  my @vendors = ();
  while (my $row = $sth->fetchrow_hashref()) {
  &debug("tblresults hash: " . $row->{'sid'} . "/" . $row->{'listname'} . "<br>");
    $row->{vendor_name} = $row->{name};
    delete($row->{name});
    push(@vendors,$row);
  }
	$sth->finish();
	show_hp_vendors(\@vendors);
}

#------------------------------------------------------------------------------
# Set up the parameters for the specials to be shown on the homepage
# Change History:
#------------------------------------------------------------------------------
sub do_homepage {
	die 'Invalid section passed to do_homepage()' unless $F{'section'} =~ /^(1|2)$/;
	my $section = "fp$F{'section'}";
	my $query = "SELECT sid FROM specials WHERE $section=?";
	$sth = $C->db_query($query,[1]);
	my $sid = $sth->fetchrow();
	$sth->finish();

	my $params = do_lookup($sid);
	
	# limit sizes for the homepage
	if(length($params->{title}) > $C->hp_title_chars()) {
		$params->{title} = substr($params->{title},0,$C->hp_title_chars() - 4);
		$params->{title} =~ s/[^\s]*$//;
		$params->{title} .= ' ...';
	}

	if(length($params->{descr}) > $C->hp_descr_chars()) {
		$params->{descr} = substr($params->{descr},0,$C->hp_descr_chars() - 4);
		$params->{descr} =~ s/[^\s]*$//;
		$params->{descr} .= ' ...';
	}	

	show_homepage($params);
}

#------------------------------------------------------------------------------
# ?
# Change History:
#------------------------------------------------------------------------------
sub do_lookup {
  my $sid = shift;
  my $query = 'SELECT sid,vendorid,item_num,title,manuf,descr,qty,price,phto_ext FROM specials WHERE sid=?';
  $sth = $C->db_query($query,[$sid]);

  my $params = $sth->fetchrow_hashref();
  $params->{descr} = 'SOLD OUT' unless $params->{qty};
  delete($params->{qty});

  if($params->{phto_ext}) {
    $params->{photo} = $C->specials_dir_URL() . "/$params->{vendorid}/$params->{item_num}_thumb.$params->{phto_ext}";
  }
  $params->{price} = sprintf('$%.2f',$params->{price});
  $sth->finish;
  delete($params->{phto_ext});
  return $params;
}	

#------------------------------------------------------------------------------
# Set up the parameters for the default (view) action
# Change History
# 1. Changed to use vendor database table and generic vendor templates - jarnold
# 2. Added code in while loop to get vendor-specific thumbnail widths and heights
#    - jarnold
# 3. Removed code added in (2) in support of orientation-based thumbnails.
#    3.1.06 - jarnold
#------------------------------------------------------------------------------
sub do_default {
	my $query = 'SELECT sid,item_num,title,manuf,descr,price,phto_ext FROM specials '.
			'WHERE qty > ? AND vendorid=? ORDER BY '.
			$C->get_spec_sort( $F{vendorid} );
	$sth = $C->db_query($query,[0,$F{vendorid}]);
	my @specials = ();

	while(my $row = $sth->fetchrow_hashref()) {
		if($row->{phto_ext}) {
			$row->{photo} = $C->specials_dir_URL() . "/$F{vendorid}/".$C->sanitize_string($row->{item_num}) ."_thumb.$row->{phto_ext}";
			# Added to make specials images clickable to larger image.
			$row->{photo_lrg} = $C->specials_dir_URL() . "/$F{vendorid}/".$C->sanitize_string($row->{item_num}) . ".$row->{phto_ext}";
		}
		delete($row->{phto_ext});
		$row->{price} = sprintf('$%.2f',$row->{price});
		push(@specials,$row);
	}
	$sth->finish();
  $query = 'select name from vendor where sid = ?';
  $sth = $C->db_query($query,[$F{vendorid}]);
  my ($vendor_name) = $sth->fetchrow();
  $sth->finish();
  &debug("Vendor Name = " . $vendor_name);
	show_special_list(\@specials,\$vendor_name);
}

#------------------------------------------------------------------------------
# Display specials based on user input from the homepage shop now list
#
# Change History:
# 1. Added code to get vendor-specific thumbnail width and height in while loop
#    - jarnold
# 2. Removed code added in (1) to move to orientation-based thumbnails
#    3.1.06 - jarnold
#------------------------------------------------------------------------------
sub do_view_by_cat {
  die "No category id passed to view_by_cat" unless $F{catlist};
  &debug("Category id = " . $F{catlist});
	
  my $query = 'select a.vendorid,a.sid,a.item_num,a.title,a.manuf,a.descr,a.price,a.phto_ext,b.category from specials a, products b '.
			'WHERE a.qty > ? AND b.category=? and a.item_num = b.item_num ORDER BY a.vendorid,a.item_num';
	$sth = $C->db_query($query,[0,$F{catlist}]);
	my @specials = ();

	while(my $row = $sth->fetchrow_hashref()) {
		if($row->{phto_ext}) {
			$row->{photo} = $C->specials_dir_URL() . "/$row->{vendorid}/" .$C->sanitize_string($row->{item_num}) ."_thumb.$row->{phto_ext}";
			# Added to make specials images clickable to larger image.
			$row->{photo_lrg} = $C->specials_dir_URL() . "/$row->{vendorid}/" .$C->sanitize_string($row->{item_num}) . ".$row->{phto_ext}";
		}
		delete($row->{phto_ext});
		$row->{vendor_id} = $row->{vendorid};
		delete($row->{vendorid});
    delete($row->{category});
		$row->{price} = sprintf('$%.2f',$row->{price});
		push(@specials,$row);
	}
	$sth->finish;

  # Get the cat name
  $query = 'select name from categories where sid = ?';
  $sth = $C->db_query($query,[$F{'catlist'}]);
  my $catname = $sth->fetchrow();

	show_shopnow_specials(\@specials,\$catname);
}

#------------------------------------------------------------------------------
# Show all specials
# Change History:
# 1. Changed to use vendor database and a single template.
#------------------------------------------------------------------------------
sub show_special_list {
	my ($specials,$vendor_name) = @_;
	my $template = $C->tmpl("vendor/specials_list_customer");
	$template->param(
		vendorid => $F{vendorid},
		specials => $specials,
    vendorname => $$vendor_name,
		);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Show specials in category
# Change History:
#------------------------------------------------------------------------------
sub show_shopnow_specials {
	my ($specials,$catname) = @_;
	my $template = $C->tmpl("shopnow_specials");
	$template->param(
		'category' => $$catname,
		specials => $specials,
		);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Show homepage vendors
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_hp_vendors {
	my ($vendors) = @_;
	my $template = $C->tmpl("homepage_vendors");
	$template->param(vendors=>$vendors);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# show specials for the homepage
# Change History:
#------------------------------------------------------------------------------
sub show_homepage {
	my $params = shift;
	my $template = $C->tmpl('specials_homepage');
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# show shop now lists for the homepage
# Change History:
#------------------------------------------------------------------------------
sub show_shopnow {
	my $list = shift;
	my $template = $C->tmpl('shopnow');
	$template->param(categories=>$list);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

###############################################################################
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header();
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
