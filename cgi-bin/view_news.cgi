#!/usr/bin/perl -T
##
## view_news.cgi - Show news items
##
## Copyright (C) 2006 2k3 John Arnold
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

my $sth;

my %modes = (
	homepage=>\&do_homepage,
	default=>\&do_default
);

################################################
## main ########################################
################################################

$F{'vendorid'} = 100
	unless $C->vendors()->{ $F{'vendorid'} };

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

sub do_default {
#	my $query = 'SELECT sid,item_num,title,manuf,descr,price,phto_ext FROM specials '.
#			'WHERE qty > ? AND vendorid=? ORDER BY '.
#			$C->get_spec_sort( $F{vendorid} );
  my $query = 'select news_id,headline,subtitle,content,logo_file,event_date,link,link_text,location_1,location_2 from news order by news_id';
	$sth = $C->db_query_no_parms($query);
	my @news_items = ();

	while(my $row = $sth->fetchrow_hashref()) {
		if($row->{logo_file}) {
			$row->{logo} = $C->news_dir_URL() . "/$row->{logo_file}";
		}
		## get rid of the fields not used in the template
		delete($row->{logo_file});
    delete($row->{news_id});
    ## add the 'ready' row to the news_items array
		push(@news_items,$row);
	}

	show_news(\@news_items);
	$sth->finish;
}

## show news items
sub show_news {
	my $news_items = shift;
	my $template = $C->tmpl("news_list");
	$template->param(
		news_items => $news_items,
		);
	print $Q->header(-type=>'text/html');
	print $template->output();
}
