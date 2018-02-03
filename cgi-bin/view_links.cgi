#!/usr/bin/perl -T
##
## view_links.cgi - Show Links Page
##
## Copyright (C) 2006 2k3 John Arnold
##


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

sub do_default {
  # Get the Industry links first
  my $query = "select link_id,logo_file,xdim,ydim,link,link_text from links where link_type = 'I' order by link_id";
	$sth = $C->db_query_no_parms($query);
	my @i_links = ();
  my $i_links_lr = ();
  my $i = 0;
	while(my $row = $sth->fetchrow_hashref()) {
		$i++;
    if($row->{logo_file}) {
			$row->{logo} = $C->links_dir_URL() . "/$row->{logo_file}";
		}
		## get rid of the fields not used in the template
		delete($row->{logo_file});
    delete($row->{link_id});
    ## add the 'ready' row to the news_items array
    #push(@i_links_pair,$row);
    ## figure out what side we should be writing two
    if (($i % 2) == 0) {
      $i_links_lr->{logo_r} = $row->{logo};
      $i_links_lr->{r_x} = $row->{xdim};
      $i_links_lr->{r_y} = $row->{ydim};
      $i_links_lr->{link_r} = $row->{link};
      $i_links_lr->{link_text_r} = $row->{link_text};
      push(@i_links,$i_links_lr);
      $i_links_lr = ();
    } else {
      $i_links_lr->{logo_l} = $row->{logo};
      $i_links_lr->{l_x} = $row->{xdim};
      $i_links_lr->{l_y} = $row->{ydim};
      $i_links_lr->{link_l} = $row->{link};
      $i_links_lr->{link_text_l} = $row->{link_text};
    }
	}
  # Push the last row on if we need it
  if (($i % 2) > 0) {
    push(@i_links,$i_links_lr);
  }
  
  # Now get the local links
  my $query = "select link_id,logo_file,link,link_text,link_label from links where link_type = 'L' order by link_id";
	$sth = $C->db_query_no_parms($query);
	my @l_links = ();

	while(my $row = $sth->fetchrow_hashref()) {
		#if($row->{logo_file}) {
		#	$row->{logo} = $C->links_dir_URL() . "/$row->{logo_file}";
		#}
		## get rid of the fields not used in the template
		delete($row->{logo_file});
    delete($row->{link_id});
    ## add the 'ready' row to the news_items array
		push(@l_links,$row);
	}

	show_links(\@i_links,\@l_links);
	$sth->finish;
}

## show links
sub show_links {
	my ($i_links,$l_links) = @_;
	my $template = $C->tmpl("links_list");
	$template->param(
		i_links => $i_links,
		l_links => $l_links,
		);
	print $Q->header(-type=>'text/html');
	print $template->output();
}
