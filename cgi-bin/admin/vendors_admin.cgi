#!/usr/bin/perl -T
# $Id: vendors_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $

use strict;
use lib '..';
use CGI::Carp 'fatalsToBrowser'; # for testing
use CGI;
use DBI;
use HTML::Template;
use NDC::Conf;
use NDC::Verify;
use NDC::SearchLibrary;
use Image::Size;
use Imager;
use Fcntl ':flock';
use File::MMagic;
use File::Copy;
use URI::Escape;

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $FM = File::MMagic->new();

my $sth;
our $DEBUG = 0;
our $DEBUG_INIT = 0;

$C->encode_html(\%F);


my %modes = (
	add=>\&do_add,
	view=>\&do_view,
	modify=>\&do_modify,
	delete=>\&do_delete,
	cancelmod=>\&do_cancelmod,
	default=>\&do_default
);

if(defined($F{mode}) && exists($modes{$F{mode}})) {
	$modes{$F{mode}}->();
}
else {
	$modes{'default'}->();
}

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

#------------------------------------------------------------------------------
# Display the default vendor admin home page.
# Change History:
# 1. Initial Version 3.2.06 - jarnold
#------------------------------------------------------------------------------
sub do_default {
	show_default();
}

#------------------------------------------------------------------------------
# Show the vendor admin home page.
# Change History:
# 1. Initial Version 3.2.06 - jarnold
#------------------------------------------------------------------------------
sub show_default {
	my $template = $C->tmpl('admin_vendors');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Process add vendor requests.
# Change History:
# 1. 03.02.2006  Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'vendor_name'})) {
			$error{vendor_name_error} = "Either you did not enter a vendor name or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'homepage'})) {
			$error{homepage_error} = "You must indicate whether or not a link to the vendor's online specials will be placed on the website homepage";
		}

		if(%error) {
			$error{'vendor_name'} = $F{'vendor_name'};
			show_add(\%error);
		}
		else {
			my $showHome = 0;
      if ($F{homepage} eq 'yes') {
        $showHome = 1;
      }
      my $query = "INSERT INTO vendor (name,show_home) VALUES (?,?)";
	    $sth = $C->db_query($query,[$F{'vendor_name'},$showHome]);
			$sth->finish();
      
      # Create the directory for specials images and thumbnails
      $query = 'select sid from vendor where name = ?';
      $sth = $C->db_query($query,[$F{'vendor_name'}]);
      my ($vendor_id) = $sth->fetchrow();
      mkdir($C->specials_dir(). "/$vendor_id") unless (-e $C->specials_dir(). "/$vendor_id");

			show_success("Vendor $F{'vendor_name'} has been added successfully.");
		}
	}
}

#------------------------------------------------------------------------------
# Show the admin view of all vendors
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_view {
	my $query1 = "SELECT COUNT(*) FROM vendor";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow();

	my $numpages = int($numrows / $C->rpp_vendors());
	if($numrows % $C->rpp_vendors()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select sid,name,show_home from vendor";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_vendors();

	$sth = $C->db_query($query,\@dbp);

	my @vendors = ();
	while(my $row = $sth->fetchrow_hashref) {
    $row->{vendor_id} = $row->{sid};
    $row->{vendor_name} = $row->{name};
    if ($row->{show_home}) {
      $row->{homepage} = 'Y';
    } else {
      $row->{homepage} = 'N';
    }
    ## get rid of the fields not used in the template
		delete($row->{sid});
    delete($row->{name});
    delete($row->{show_home});
		push(@vendors,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_vendors();
	my $prev = $start - $C->rpp_vendors();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_vendors()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_vendors() - 1;
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
		push(@pages,{s=>$C->rpp_vendors() * $count,page=>$_,tp=>$tp});
		$count ++;
	}
	$sth->finish();

	show_view(\@vendors,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);
}

# ---------------------------------------------------------------------
# Modify an existing vendor.
# Change History:
# 1. 03.02.2006 - jarnold
# ---------------------------------------------------------------------
sub do_modify {
	die "No vendor id passed to modify" unless $F{'vendor_id'};
	my $query = "select sid,name from vendor where sid = ?";
	$sth = $C->db_query($query,[$F{'vendor_id'}]);
	my $vendor_info = $sth->fetchrow_hashref();
	$sth->finish;
  $vendor_info->{vendor_id} = $vendor_info->{sid};
  $vendor_info->{vendor_name} = $vendor_info->{name};
	delete($vendor_info->{sid});
  delete($vendor_info->{name});

  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify($vendor_info);
	}
	else { # updates defined
		die "No vendor id passed to modify" unless $F{'vendor_id'};
		my %error = ();

		unless(vrfy_string(\$F{'vendor_name'})) {
			$error{vendor_name_error} = "Either you didn't enter a vendor name or it contains invalid characters";
		}
		unless(vrfy_string(\$F{'homepage'})) {
			$error{homepage_error} = "You must indicate whether or not a link to the vendor's online specials will be placed on the website homepage";
		}

		if(%error) {
			$error{'vendor_name'} = $F{'vendor_name'};
			$error{'vendor_id'} = $F{'vendor_id'};
			show_modify(\%error);
		}
		else { # execute the update
      my $query = "update vendor set name=?,show_home=? where sid=?";
			$sth = $C->db_query($query,[$F{'vendor_name'},$F{'homepage'},$F{'vendor_id'}]);
			$sth->finish();
			show_success("'$F{'vendor_name'}' has been updated");
	  }  # end execute the update
	} # end updates defined
}

#------------------------------------------------------------------------------
# Delete a vendor from the system.
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_delete {
	die "No vendor_id passed to do_delete()!" unless $F{vendor_id};
  
	my $sth = $C->db_query("SELECT sid,name FROM vendor WHERE sid=?",[$F{'vendor_id'}]);
	my ($sid,$vendor_name) = $sth->fetchrow();
	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({vendor_name=>$vendor_name});
	}
	else {
    # Delete the vendor and all related information
    # First delete everything from the specials
		$sth = $C->db_query("delete from specials where vendorid = ?",[$sid]);
		$sth->finish();
    # Delete products
    $sth = $C->db_query("delete from products where vendorid = ?",[$sid]);
    $sth->finish();
    # Delete the vendor
    $sth = $C->db_query("delete from vendor where sid = ?",[$sid]);
    $sth->finish();

		# delete the images/specials directory for the vendor
    my $path = $C->specials_dir(). "/$sid";
		if(-e $path) {
      opendir (DIR, "$path/");
      my @files = readdir(DIR);
      closedir (DIR);

      foreach my $file (@files) {
        &debug("File to delete: " . $file . "<br>");
        if (($file ne '.') && ($file ne '..')) {
          if ($file =~ /^([-\@\w.]+)$/) {
            $file = $1;
            my $filename = $path . "/" . $file;
            &debug("Tainted filename:  " . $filename . "<br>");
            unlink($filename) or warn "Could not delete $filename: $!\n";
          } 
        }
      }
      # remove the directory
      rmdir($path) or warn "Couldn't remove $path: $!\n";
		}

		show_success("Vendor '$vendor_name' and all related products and specials have been deleted from the system");
	}
}

#------------------------------------------------------------------------------
# Show the add new vendor page.
# Change History:
# 1.  03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_add {
	my $error = shift;
	my $template = $C->tmpl('admin_vendors_add');
	$template->param(%$error) if $error;

  # Build row used to display homepage options
  &debug("Homepage Selection = " . $F{homepage} . "<br>");
  my %yrow = ();
  my @rbuttons = ();
  %yrow->{home} = 'yes';
  %yrow->{label} = 'Yes';
  if ($F{homepage} eq 'yes') {
    %yrow->{selected} = 1;
  }
  push(@rbuttons,\%yrow);
  my %nrow = ();
  %nrow->{home} = 'no';
  %nrow->{label} = 'No';
  if ($F{homepage} eq 'no') {
    %nrow->{selected} = 1;
  }
  push(@rbuttons,\%nrow);
  $template->param(rbuttons=>\@rbuttons);
  
	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Show the populated vendor modify screen
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_modify {
	my $params = shift;
  my $template = $C->tmpl('admin_vendors_modify');
	$template->param(%$params) if $params;

  # Build row used to display homepage options
  &debug("Homepage Selection = " . $F{homepage} . "<br>");
  my %yrow = ();
  my @rbuttons = ();
  %yrow->{home} = 'yes';
  %yrow->{label} = 'Yes';
  if ($F{homepage} eq 'yes') {
    %yrow->{selected} = 1;
  }
  push(@rbuttons,\%yrow);
  my %nrow = ();
  %nrow->{home} = 'no';
  %nrow->{label} = 'No';
  if ($F{homepage} eq 'no') {
    %nrow->{selected} = 1;
  }
  push(@rbuttons,\%nrow);
  $template->param(rbuttons=>\@rbuttons);

	print $Q->header(-type=>'text/html');
	print $template->output();
}

#------------------------------------------------------------------------------
# Show the delete page for the vendor admin section
# Change History:
# 1. 03.02.2006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_delete {
	my $params = shift;
	die "No vendor_id passed to show_delete()!" unless $F{'vendor_id'};

	my $template = $C->tmpl('admin_vendors_delete');
	$template->param(vendor_id=>$F{'vendor_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# -----------------------------------------------------------------------------
# Display the admin view of all Vendors
# Change History:
# 1. 03.02.2006  Initial Version - jarnold
# -----------------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_vendors_list');
	$template->param(vendors=>$list);	#loop
	$template->param('next'=>$$next);
	$template->param(prev=>$$prev);
	$template->param(show_next=>$$show_next);
	$template->param(show_prev=>$$show_prev);
	$template->param(pages=>$pages); #loop
	$template->param(qstring=>$$qstring);

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

sub show_success {
	my $msg = shift;
	my $template = $C->tmpl('success');
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
