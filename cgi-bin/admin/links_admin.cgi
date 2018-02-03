#!/usr/bin/perl -T
# $Id: links_admin.cgi,v 1.19 2006/02/02 12:13:46 jarnold Exp $

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

$C->encode_html(\%F);

my $sth;
my $size_x;
my $size_y;

my %modes = (
	add=>\&do_add,
	view=>\&do_view,
	modify=>\&do_modify,
	'delete'=>\&do_delete,
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


#############################################################
# mmmmmm subs

#############################################################
# Attempt to create a thumbnail from the link image using
# Imager::scale()
#############################################################
sub create_thumbnail {

  my ($file_out) = @_;
  # I know its a hack but I just want to pass this routine the path+filename
  my @tmp = split(/\//,$file_out);
  my $file = pop(@tmp);
  my $dir = join("/",@tmp);
  my ($ext) = $file =~ /\.(jpg|gif|png|bmp)$/;
  $file =~ s/\.$ext//;
  my $format;
  if (uc($ext) eq 'JPG') {
    $format = 'jpeg';
  } else {
    $format = $ext;
  }
  
  mkdir($dir) unless (-e $dir);
  #my @keys = %Imager::formats;
  #my $formats = "";
  #foreach (@keys) {
  #  $formats = $formats . $_ . " ";
  #}
  #show_error("Supported Formats: " . $formats);

  # Copy the original and work only on the thumb file.
  copy($file_out,"$dir/${file}_tmp.$ext") or die "Couldn't copy $file_out to $dir/${file}_tmp.$ext: $!\n";

  # Resize x proportionally to y
  if($size_x > $C->max_link_thumb_width || $size_y > $C->max_link_thumb_height) {
    # Read the image from the file into $image
    my $image = Imager->new();
    my $newImage = Imager->new();
    $image->read(file=>"$dir/${file}_tmp.$ext",type=>$format) or die "Cannot Read Image File:   " . $image->errstr();
    # create a scaled copy of the image
    $newImage = $image->scale(xpixels=>$C->max_link_thumb_width,ypixels=>$C->max_link_thumb_height,type=>'min');
    $size_x = $newImage->getwidth();
    $size_y = $newImage->getheight();
    #show_error("Width = " . $size_x . "  Height = " . $size_y);
    $newImage->write(file=>"$dir/${file}_tmp.$ext",$ext) or die "Cannot Write Image File:  " . $newImage->errstr;
    # copy the temp file back to the original and then delete the tmp file
    copy("$dir/${file}_tmp.$ext",$file_out) or die "Couldn't copy $dir/${file}_thumb.$ext to $file_out: $!\n";
    unlink("$dir/${file}_tmp.$ext") or warn "Couldn't unlink $dir/${file}_tmp.$ext: $!\n";
  }
}


sub do_default {
	show_default();
}

sub show_default {
	my $template = $C->tmpl('admin_links');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		unless(vrfy_string(\$F{'link_type'})) {
			$error{link_type_error} = "Please select a Link Type - Either Local or Industry";
		}
		unless(vrfy_string(\$F{'link'})) {
			$error{link_error} = "Either you didn't enter a URL for a link or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'link_text'})) {
			$error{link_error} = "Either you didn't enter a text for a link or it contained invalid characters";
		}

		my $filename = $Q->param('logo_file');
		# this type check has to be done before the file name gets
		# mangled so that's why its here.
		my $type;
		my $fh;
		if($filename) {
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
      $fh = $Q->upload('logo_file');
      ($size_x,$size_y) = imgsize($filename);
		}
		$filename =~ s/\s/_/g;

		if(%error) {
			$error{'link'} = $F{'link'};
			$error{'link_text'} = $F{'link_text'};
			$error{'link_type'} = $F{'link_type'};
			show_add(\%error);
		}
		else {

			if (defined($fh)) {
			  # stupid windows
			  if($filename =~ /\\/) {
				  my @tmp = split(/\\/,$filename);
				  $filename = pop(@tmp);
			  }

			  my $file = $C->links_dir() . "/" . $C->sanitize_string($filename);
		    #show_error($file);
			  $file =~ m/^(.*)$/;
			  $file = $1;
			  my $buffer;
		    #show_error($file);
			  open(FILE,">$file") or die "Couldn't open $file: $!";
			  binmode(FILE);
			  flock(FILE,LOCK_EX) or die "Couldn't flock\n";
			  while(read($fh,$buffer,1024)) {
				  print FILE $buffer;
			  }
			  #flock(FILE,LOCK_UN);
			  close(FILE);

        # create a thumbnail?
    #show_error("LOCK_EX = " . LOCK_EX . "  LOCK_UN = " . LOCK_UN);
        create_thumbnail($file);
        }

      ## prepend http:// to the link, if entered
      my $link;
      if ($F{'link'}) {
        $link = $F{'link'};
        if ($link !~ /^http/) {
          $link = "http://" . $link;
        }
      }
      
			my $query = "INSERT INTO links (link_type,logo_file,xdim,ydim,link,link_text,link_label) VALUES (?,?,?,?,?,?,?)";
	    $sth = $C->db_query($query,[$F{'link_type'},$C->sanitize_string($filename),$size_x,$size_y,$link,$F{'link_text'},$F{'link_label'}]);
			$sth->finish();

			show_success("Link $F{'link_text'} has been added successfully.");
		}
	}
}

sub do_view {
	my $query1 = "SELECT COUNT(*) FROM links";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_news());
	if($numrows % $C->rpp_news()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select link_id,link_type,logo_file,xdim,ydim,link,link_text,link_label from links";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_links();

	$sth = $C->db_query($query,\@dbp);

	my @links = ();
	while(my $row = $sth->fetchrow_hashref) {
		if($row->{logo_file}) {
			$row->{logo} = $C->links_dir_URL() . "/$row->{logo_file}";
		}
    if ($row->{link_type} eq 'L') {
      $row->{ltype} = 'Local';
    } else {
      $row->{ltype} = 'Industry';
    }
		## get rid of the fields not used in the template
		delete($row->{logo_file});
    delete($row->{link_type});
		push(@links,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_links();
	my $prev = $start - $C->rpp_links();
	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;
	# don't show the previous button unless there are previous items
	my $show_prev = 1 unless $start == 0;
	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;
	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_links()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	my $startpage = $pageon - 5;
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_links() - 1;
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
		push(@pages,{s=>$C->rpp_links() * $count,page=>$_,tp=>$tp});
		$count ++;
	}
	# for the item pulldown
	#my $query3 = "SELECT DISTINCT item_num FROM library";
	#$sth = $C->db_query($query3);

	#my @pulldown = ();
	#while(my $row = $sth->fetchrow_hashref) {
	#	if($F{'item_num'} eq $row->{item_num}) {
	#		$row->{selected} = 1;
	#	}
	#	push(@pulldown,$row);
	#}

	$sth->finish();

	show_view(\@links,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);
}

# ---------------------------------------------------------------------
# Modify an existing link.
# 01/19/2006 - jarnold
# ---------------------------------------------------------------------
sub do_modify {
	die "No link id passed to modify" unless $F{'link_id'};

	my $query = "select link_id,link_type,logo_file,xdim,ydim,link,link_text,link_label from links where link_id = ?";
	$sth = $C->db_query($query,[$F{'link_id'}]);
	my $link_info = $sth->fetchrow_hashref;
	$sth->finish;
	my $logo_save;
	if($link_info->{logo_file}) {
		$link_info->{logo} = $C->links_dir_URL() . "/$link_info->{logo_file}";
		$logo_save = $link_info->{logo_file};
		}
  if ($link_info->{link_type} eq 'L') {
    $link_info->{local} = 1;
  } else {
    $link_info->{industry} = 1;
  }
	delete($link_info->{logo_file});
  delete($link_info->{link_type});

  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify($link_info);
	}
	else { # updates defined
		die "No link id passed to modify" unless $F{'link_id'};
		my %error = ();

		unless(vrfy_string(\$F{'link_type'})) {
			$error{link_type_error} = "Please select a Link Type - Either Local or Industry";
		}
		unless(vrfy_string(\$F{'link'})) {
			$error{link_error} = "Either you didn't enter a URL for a link or it contained invalid characters";
		}
		unless(vrfy_string(\$F{'link_text'})) {
			$error{link_error} = "Either you didn't enter a text for a link or it contained invalid characters";
		}

		my $filename = $Q->param('logo_file');
    # this type check has to be done before the file name gets
		# mangled so that's why its here.
    my $fh;
		my $type;
    my ($size_x,$size_y);
		if($filename) {
		  #show_error($filename);
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
			$fh = $Q->upload('logo_file');
      ($size_x,$size_y) = imgsize($filename);
      #show_error($fh);
			$filename =~ s/\s/_/g;
		}

		if(%error) {
			$error{'link_type'} = $F{'link_type'};
			$error{'link'} = $F{'link'};
			$error{'link_text'} = $F{'link_text'};
			show_modify(\%error);
		}
		else { # execute the update
			my $filestr = $C->sanitize_string($filename);

      # delete the old logo file if a new one is specified and write the new logo file
      #show_error("new logo file: " . $filename . "  Old logo file:  " . $F{'logo'});
      if ($logo_save && $filename) { # if new logo
        #show_error("Trying to delete old logo file..." . $logo_save);
		    if(-e $C->links_dir_URL() . "/$logo_save") {
			    unlink($C->links_dir_URL() . "/$logo_save") or warn "Couldn't unlink $logo_save: $!\n";
		    }

		    if(defined($fh)) {
		    #show_error($fh);
			    # stupid windows
			    if($filename =~ /\\/) {
				    my @tmp = split(/\\/,$filename);
				    $filename = pop(@tmp);
			    }

			    my $file = $C->links_dir() . "/" . $C->sanitize_string($filename);
		      #show_error($file);
			    $file =~ m/^(.*)$/;
			    $file = $1;
		      #show_error($file);
			    my $buffer;
			    open(FILE,">$file") or die "Couldn't open $file: $!";
			    binmode(FILE);
			    flock(FILE,LOCK_EX) or die "Couldn't flock\n";

			    # debug
			    # show_error($filename);
          # show_error($fh);

			    #	print "defined count, entering loop\n";
			    while(read($fh,$buffer,1024)) {
				    print FILE $buffer;
			    }
			    flock(FILE,LOCK_UN);
			    close(FILE);
        }
      } # end if new logo
      else { # we have to keep the old logo
        $filename = $logo_save;
        ($size_x,$size_y) = imgsize($filename);
      }
      ## prepend http:// to the link, if entered - never mind
      my $link;
      if ($F{'link'}) {
        $link = $F{'link'};
        if ($link !~ /^http/) {
          $link = "http://" . $link;
        }
      }
      my $query = "update links set link_type=?,logo_file=?,xdim=?,ydim=?,link=?,link_text=?,link_label=? where link_id=?";
			$sth = $C->db_query($query,[$F{'link_type'},$C->sanitize_string($filename),$size_x,$size_y,$link,$F{'link_text'},$F{'link_label'},$F{'link_id'}]);
			$sth->finish();
			show_success("'$F{'link_text'}' has been modified");
	  }  # end execute the update
	} # end updates defined
}

sub do_delete {
	die "No link_id passed to do_delete()!" unless $F{'link_id'};

	my $sth = $C->db_query("SELECT link_text,logo_file FROM links WHERE link_id=?",[$F{'link_id'}]);
	my ($link_text,$filename) = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({link_text=>$link_text});
	}
	else {
		$sth = $C->db_query("delete from links where link_id = ?",[$F{'link_id'}]);
		$sth->finish();

		my $path = $C->links_dir() . "/$filename";
		if(-e $path) {
			unlink($path) or warn "Couldn't unlink $path: $!\n";
		}

		show_success("Link for '$link_text' has been deleted");
	}
}

sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_links_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
	my $params = shift;
  my $template = $C->tmpl('admin_links_modify');
	$template->param(%$params) if $params;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_confirm_modify {
	my ($params,$warnings) = @_;
	delete($params->{update});
	my $template = $C->tmpl('admin_library_confirm_modify');
	$template->param(%$params);
	$template->param(warnings=>$warnings);

	print $Q->header();
	print $template->output();
}

sub show_delete {
	my $params = shift;
	die "No link_id passed to show_delete()!" unless $F{'link_id'};

	my $template = $C->tmpl('admin_links_delete');
	$template->param(link_id=>$F{'link_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all links
# 01/18/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_links_list');
	$template->param(links=>$list);	#loop
	#$template->param(pulldown=>$pulldown); #loop
	$template->param('next'=>$$next);
	$template->param(prev=>$$prev);
	$template->param(show_next=>$$show_next);
	$template->param(show_prev=>$$show_prev);
	$template->param(pages=>$pages); #loop
	$template->param(qstring=>$$qstring);

	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_success {
	my $msg = shift;
	my $template = $C->tmpl('success');
	$template->param(msg=>$msg);
	print $Q->header(-type=>'text/html');
	print $template->output;
}

##
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();
  exit;
}
