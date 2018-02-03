#!/usr/bin/perl -T
##
## view_specials.pl - Show internet specials
##
## Copyright (C) 2006 2k3 Technologies
##
## $Author: Jarnold $  $Date: 3/09/06 8:48p $  $Revision: 1 $

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
	default=>\&do_default,
  category=>\&do_view_by_cat
);

## main 
if(exists($modes{$F{'mode'}})) {
	$modes{$F{'mode'}}->();
}
else {
	$modes{default}->();
}

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

#------------------------------------------------------------------------------
# Set up the parameters for the default (view) action
# Change History
# 1.  03.09.2006 - Initial Version
#------------------------------------------------------------------------------
sub do_default {
	&do_view_by_cat();
}

#------------------------------------------------------------------------------
# Display specials based on user input from the homepage shop now list
#
# Change History:
# 1.  03.09.2006  - Initial Version
#------------------------------------------------------------------------------
sub do_view_by_cat {
  die "No category id passed to view_by_cat" unless $F{'cat_id'};
	
  my $query = 'select count(*) from photos where category=?';
	$sth = $C->db_query($query,[$F{'cat_id'}]);
  my $numrows = $sth->fetchrow();
  $sth->finish();
	my $numpages = int($numrows / $C->rpp_photos());
	if($numrows % $C->rpp_photos()) {
		$numpages ++;
	}
  # Get the category for info for the page display
  $query = 'select category,header from photo_cats where sid=?';
  $sth = $C->db_query($query,[$F{'cat_id'}]);
  my ($category,$header) = $sth->fetchrow();
  $sth->finish();
  
	my $start = $F{'s'} || 0; # s = starting row
	my $query = "select photo_file,photo_ext,caption from photos where category=?" . " LIMIT $start, " . $C->rpp_photos();
  $sth = $C->db_query($query,[$F{'cat_id'}]);

	my @photos = ();

	while(my $row = $sth->fetchrow_hashref()) {
    $row->{photo} = $C->photos_dir_URL() . "/$header/$row->{photo_file}_web.$row->{photo_ext}";
		delete($row->{photo_ext});
    delete($row->{photo_file});
		push(@photos,$row);
	}
	$sth->finish;

  my $next = $start + $C->rpp_photos() + 5;
	my $prev = $start - $C->rpp_photos() - 5;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $prev < 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next > $numrows;
	# page loop
	my @pages = ();

	my $pageon = $start + 1;
	my $startpage = $prev + 1;
	my $endpage = $next - 1;

	foreach($startpage .. $endpage) {
		my $tp = 0;
    if (($_ > 0) && ($_ <= $numrows)) {
      if($_ eq $pageon) {
        $tp = 1;
      }
      push(@pages,{s=>($_ - 1),page=>$_,tp=>$tp,cat_id=>$F{'cat_id'}});
    }
	}
	$sth->finish();
  $next = $start + 1;
  $prev = $start - 1;

	show_photos(\@photos,\$category,\$next,\$prev,\$show_next,\$show_prev,\@pages);
}

#------------------------------------------------------------------------------
# Show specials in category
# Change History:
#------------------------------------------------------------------------------
sub show_photos {
	my ($photos,$category,$next,$prev,$show_next,$show_prev,$pages) = @_;

	my $template = $C->tmpl("photos_list");
	$template->param(category=> $$category);
	$template->param(photos=>$photos); #photos loop
  $template->param(next=>$$next);
  $template->param(prev=>$$prev);
  $template->param(show_next=>$$show_next);
  $template->param(show_prev=>$$show_prev);
  $template->param(pages=>$pages); #pages loop
  $template->param(cat_id=>$F{'cat_id'});

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
