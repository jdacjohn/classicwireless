#!/usr/bin/perl -T
# $Id: news_admin.cgi,v 1.19 2006/01/18 14:01:46 jarnold Exp $

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
use Image::Magick;
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

sub do_default {
	show_default();
}

sub show_default {
	my $template = $C->tmpl('admin_news');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();

		unless(vrfy_string(\$F{'headline'})) {
			$error{headline_error} = "Either you didn't enter a headline or it contained invalid characters";
		}

		unless(vrfy_string(\$F{'subtitle'})) {
			$error{subtitle_error} = "Either you didn't enter a subtitle or it contained invalid characters";
		}

#		unless(vrfy_string(\$F{'event_date'})) {
#			$error{event_date_error} = "Either you didn't enter a date or it contained invalid characters";
#		}

#		unless(vrfy_string(\$F{'location_1'})) {
#			$error{location_1_error} = "Either you didn't enter a location or it contained invalid characters";
#		}

#		unless(vrfy_string(\$F{'location_2'})) {
#			$error{location_2_error} = "Either you didn't enter a city or it contained invalid characters";
#		}

		unless(vrfy_blob(\$F{'content'})) {
			$error{content_error} = "You must enter a text for the news item";
		}

		my $filename = $Q->param('logo_file');
		# show_error($filename);
		# this type check has to be done before the file name gets
		# mangled so that's why its here.
		my $type;
		my $fh;
		if($filename) {
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
			$fh = $Q->upload('logo_file');

		}

		$filename =~ s/\s/_/g;
    #show_error($filename);
		#unless(defined($fh)) {
		#	$error{'logo_file_error'} = "Please select a document to upload";
		#}

#		unless(vrfy_string(\$F{'link'})) {
#			$error{link_error} = "Either you didn't enter a URL or it contained invalid characters";
#		}

#		unless(vrfy_blob(\$F{'link_text'})) {
#			$error{link_text_error} = "Either you didn't enter text for the URL or it contained invalid characters";
#		}

		if(%error) {
			$error{'headline'} = $F{'headline'};
			$error{'subtitle'} = $F{'subtitle'};
#			$error{'event_date'} = $F{'event_date'};
#			$error{'location_1'} = $F{'location_1'};
#			$error{'location_2'} = $F{'location_2'};
			$error{'content'} = $F{'content'};
#			$error{'link'} = $F{'link'};
#			$error{'link_text'} = $F{'link_text'};

			show_add(\%error);
		}
		else {
			my $headline = $C->sanitize_string($F{'headline'});

			if (defined($fh)) {
			  # stupid windows
			  if($filename =~ /\\/) {
				  my @tmp = split(/\\/,$filename);
				  $filename = pop(@tmp);
			  }

			  my $file = $C->news_dir() . "/" . $C->sanitize_string($filename);
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

      ## prepend http:// to the link, if entered
      my $link;
      if ($F{'link'}) {
        $link = $F{'link'};
        if ($link !~ /^http/) {
          $link = "http://" . $link;
        }
      }
			my $query = "INSERT INTO news (headline,subtitle,content,logo_file,event_date,location_1,location_2,link,link_text) VALUES (?,?,?,?,?,?,?,?,?)";
			$sth = $C->db_query($query,[$F{'headline'},$F{'subtitle'},$F{'content'},$C->sanitize_string($filename),$F{'event_date'},$F{'location_1'},$F{'location_2'},$link,$F{'link_text'}]);
			$sth->finish();

			show_success("News Item $F{'headline'} has been added successfully.");
		}
	}
}

sub do_view {
	my $query1 = "SELECT COUNT(*) FROM news";
	my @dbp = ();

	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp_news());
	if($numrows % $C->rpp_news()) {
		$numpages ++;
	}
	$sth->finish;

	my $query = "select news_id,headline,subtitle,content,logo_file,event_date,location_1,location_2,link,link_text from news";
	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp_news();

	$sth = $C->db_query($query,\@dbp);

	my @news_items = ();
	while(my $row = $sth->fetchrow_hashref) {
		if($row->{logo_file}) {
			$row->{logo} = $C->news_dir_URL() . "/$row->{logo_file}";
		}

		## get rid of the fields not used in the template
		delete($row->{logo_file});

		push(@news_items,$row);
	}
	$sth->finish;

	my $next = $start + $C->rpp_news();
	my $prev = $start - $C->rpp_news();

	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1;

	# don't show the previous button unless there are previous
	# items
	my $show_prev = 1 unless $start == 0;

	# don't show next button unless there are more items
	my $show_next = 1 unless $next >= $numrows;

	# page loop
	my @pages = ();
	my $qstring;

	my $pageon = int($start / $C->rpp_news()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}

	my $startpage = $pageon - 5;

	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + $C->rpp_news() - 1;
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
		push(@pages,{s=>$C->rpp_news() * $count,page=>$_,tp=>$tp});
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

	show_view(\@news_items,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);
}

# ---------------------------------------------------------------------
# Modify an existing news item.
# 01/19/2006 - jarnold
# ---------------------------------------------------------------------
sub do_modify {
	die "No news id passed to modify" unless $F{'news_id'};

	my $query = "select news_id,headline,subtitle,content,logo_file,event_date,location_1,location_2,link,link_text from news where news_id = ?";
	$sth = $C->db_query($query,[$F{'news_id'}]);
	my $news_info = $sth->fetchrow_hashref;
	$sth->finish;
	my $logo_save;
	if($news_info->{logo_file}) {
		$news_info->{logo} = $C->news_dir_URL() . "/$news_info->{logo_file}";
		$logo_save = $news_info->{logo_file};
		}
	delete($news_info->{logo_file});

  # show the update screen if the user clicked modify from the view screen
	if(!defined($F{'update'})) {
		show_modify($news_info);
	}
	else { # updates defined
		die "No news id passed to modify" unless $F{'news_id'};
		my %error = ();

		unless(vrfy_string(\$F{'headline'})) {
			$error{headline_error} = "Either you didn't enter a headline or it contained invalid characters";
		}

		unless(vrfy_string(\$F{'subtitle'})) {
			$error{subtitle_error} = "Either you didn't enter a subtitle or it contained invalid characters";
		}

		unless(vrfy_blob(\$F{'content'})) {
			$error{content_error} = "You must enter a text for the news item";
		}

		my $filename = $Q->param('logo_file');
    # this type check has to be done before the file name gets
		# mangled so that's why its here.
    my $fh;
		my $type;
		if($filename) {
		  #show_error($filename);
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
			$fh = $Q->upload('logo_file');
      #show_error($fh);
			$filename =~ s/\s/_/g;
		}

		if(%error) {
			$error{'headline'} = $F{'headline'};
			$error{'subtitle'} = $F{'subtitle'};
			$error{'content'} = $F{'content'};
			show_modify(\%error);
		}
		else { # execute the update
			my $filestr = $C->sanitize_string($filename);

      # delete the old logo file if a new one is specified and write the new logo file
      #show_error("new logo file: " . $filename . "  Old logo file:  " . $F{'logo'});
      if ($logo_save && $filename) { # if new logo
        #show_error("Trying to delete old logo file..." . $logo_save);
		    if(-e $C->news_dir_URL() . "/$logo_save") {
			    unlink($C->news_dir_URL() . "/$logo_save") or warn "Couldn't unlink $logo_save: $!\n";
		    }

		    if(defined($fh)) {
		    #show_error($fh);
			    # stupid windows
			    if($filename =~ /\\/) {
				    my @tmp = split(/\\/,$filename);
				    $filename = pop(@tmp);
			    }

			    my $file = $C->news_dir() . "/" . $C->sanitize_string($filename);
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
      }
      ## prepend http:// to the link, if entered - never mind
      my $link;
      if ($F{'link'}) {
        $link = $F{'link'};
        if ($link !~ /^http/) {
          $link = "http://" . $link;
        }
      }
      my $query = "update news set headline=?,subtitle=?,content=?,logo_file=?,event_date=?,location_1=?,location_2=?,link=?,link_text=? where news_id=?";
			$sth = $C->db_query($query,[$F{'headline'},$F{'subtitle'},$F{'content'},$C->sanitize_string($filename),$F{'event_date'},$F{'location_1'},$F{'location_2'},$link,$F{'link_text'},$F{'news_id'}]);
			$sth->finish();
			show_success("'$F{'headline'}' has been modified");
	  }  # end execute the update
	} # end updates defined
}

sub do_delete {
	die "No news_id passed to do_delete()!" unless $F{'news_id'};

	my $sth = $C->db_query("SELECT headline,logo_file FROM news WHERE news_id=?",[$F{'news_id'}]);
	my ($headline,$filename) = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
    show_delete({headline=>$headline});
	}
	else {
		$sth = $C->db_query("delete from news where news_id = ?",[$F{'news_id'}]);
		$sth->finish();

		my $path = $C->news_dir() . "/$filename";
		if(-e $path) {
			unlink($path) or warn "Couldn't unlink $path: $!\n";
		}

		show_success("News article '$headline' has been deleted");
	}
}

sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_news_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
	my $params = shift;
  my $template = $C->tmpl('admin_news_modify');
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
	die "No news_id passed to show_delete()!" unless $F{'news_id'};

	my $template = $C->tmpl('admin_news_delete');
	$template->param(news_id=>$F{'news_id'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

# ---------------------------------------------------------------------
# Display the admin view of all news items
# 01/18/06 - jarnold
# ---------------------------------------------------------------------
sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_news_list');
	$template->param(news_items=>$list);	#loop
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
