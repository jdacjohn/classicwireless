#!/usr/bin/perl -T
##
## view_library.cgi - Main library viewing script
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: view_library.cgi,v 1.7 2002/09/19 17:19:46 cameron Exp $

use strict;
use lib '.';
use CGI;
use CGI::Carp 'fatalsToBrowser';
use HTML::Template;
use NDC::Conf;
use NDC::SearchLibrary;
use DBI;
use File::MMagic;
use URI::Escape;

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $FM = new File::MMagic;

my $sth;

my %modes = (
	default=>\&do_default,
	);

$modes{default}->();

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

################################################3
# subs ...

sub do_default {
	my $query1 = "SELECT COUNT(*) FROM library";
	$query1 = search_library(\%F,$query1);
	my @dbp = ();
	
	unless($F{search}) {
		if($F{'item_num'}) {
			$query1 .= " WHERE item_num=?"; 
			push(@dbp,$F{'item_num'});
		}
	}
	$sth = $C->db_query($query1,\@dbp);
	my $numrows = $sth->fetchrow;

	my $numpages = int($numrows / $C->rpp());
	if($numrows % $C->rpp()) {
		$numpages ++;
	}

	$sth->finish;

	my $query = "SELECT item_num,manuf,title,descr,file FROM library";
	$query = search_library(\%F,$query);

	unless($F{search}) {
		@dbp = ();
		if($F{'item_num'}) {
			$query .= " WHERE item_num=?"; 
			push(@dbp,$F{'item_num'});
		}
	}

	my $start = $F{'s'} || 0; # s = starting row
	$query .= " LIMIT $start, " . $C->rpp();

	$sth = $C->db_query($query,\@dbp);
	
	my @list = ();
	while(my $row = $sth->fetchrow_hashref) {
		$row->{icon} = get_icon($row->{file},$row->{item_num});	
		$row->{filesize} = $C->get_filesize($C->libraryfiles() . "/".
			$C->sanitize_string($row->{item_num}) ."/$row->{file}");
		$row->{dir} = $C->sanitize_string($row->{item_num});
		delete($row->{item_num});
		push(@list,$row);	
	}
	$sth->finish;

	my $next = $start + $C->rpp();
	my $prev = $start - $C->rpp();

	# make sure we don't do a previous out of range
	$prev = 0 unless $prev > -1; 

	# don't show the previous button unless there are previous
	# items
	my $show_prev = 1 unless $start == 0;

	# don't show next button unless there are more items
	my $show_next = 1 unless $next > $numrows;

	# page loop
	my @pages = ();

	my $qstring;
	if($F{'search'}) {
		my $tmp = uri_escape($F{search});
		$qstring = "&amp;search=$tmp";
	}
	elsif($F{'item_num'}) {
		my $tmp = uri_escape($F{item_num});
		$qstring = "&amp;item_num=$tmp";
	}

	my $pageon = int($start / $C->rpp()) + 1;
	if($pageon < 1) {
		$pageon = 1;
	}
	
	my $startpage = $pageon - 5;
	
	if($startpage < 1) {
		$startpage = 1;
	}

	my $endpage = $startpage + 9;
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
		push(@pages,{s=>$C->rpp() * $count,page=>$_,qstring=>$qstring,tp=>$tp});
		$count ++;
	}

	show_default(\@list,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);
}

sub show_default {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages) = @_;

	my $template = $C->tmpl('library_user_list');
	$template->param(list=>$list);	#loop
	$template->param('next'=>$$next);
	$template->param(prev=>$$prev);
	$template->param(show_next=>$$show_next);
	$template->param(show_prev=>$$show_prev);
	$template->param(pages=>$pages); #loop
	
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub get_icon {
	my ($filename,$item) = @_;
	$filename = $C->sanitize_string($filename);
	$item = $C->sanitize_string($item);
	my $fpath = $C->libraryfiles() . "/$item/$filename";
	my $type = $FM->checktype_filename($fpath);
		
	my($file,$ext) = split(/\./,$filename);
		
	my $icon;
	if(-e $C->libraryfiles() . "/$item/${file}_thumb.$ext") {
		$icon = $C->library_URL() . "/$item/${file}_thumb.$ext";
	}
	elsif($type =~ /^application\/msword/) {
		$icon = $C->word_icon();
	}
	elsif($type =~ /^application\/pdf/) {
		$icon = $C->pdf_icon();
	}
	else {
		$icon = $C->unknown_icon();
	}
	return $icon;
}
