#!/usr/bin/perl -T

# $Id: vrfy_item.cgi,v 1.2 2002/09/10 10:23:01 cbrown Exp $

# vrfy_item -- Check an item's location.

use strict;
use lib "..";
use HTML::Template;
use CGI;
use CGI::Carp 'fatalsToBrowser';
use DBI;
use NDC::Conf;

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $sth;

my %modes = (
	default=>\&do_default,
);

$modes{default}->();

exit;

#############################################
## subs

sub do_default {
	die "No ID passed to vrfy_id!\n" unless $F{item_num};

	my %output = ();
		
	my $query1 = "SELECT item_num FROM products WHERE item_num=?";
	$sth = $C->db_query($query1,[$F{item_num}]);
		
	my $p_itemnum = $sth->fetchrow();
	$sth->finish();
	
	$p_itemnum and $output{products} = 1;
	
	my $query2 = "SELECT item_num FROM specials WHERE item_num=?";
	$sth = $C->db_query($query2,[$F{item_num}]);

	my $s_itemnum = $sth->fetchrow();
	$sth->finish();

	$s_itemnum and $output{specials} = 1;

	my $query3 = "SELECT item_num FROM library WHERE item_num=?";
	$sth = $C->db_query($query3,[$F{item_num}]);
	my $l_itemnum = $sth->fetchrow();
	$sth->finish();

	$l_itemnum and $output{library} = 1;
	
	$output{item_num} = $F{item_num};

	show_default(\%output);
}


sub show_default {
	my $output = shift;

	my $template = $C->tmpl('vrfy_item');
	$template->param(%$output);
	print $Q->header();
	print $template->output();
}
