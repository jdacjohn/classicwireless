#!/usr/bin/perl -T
# $Id: library_admin.cgi,v 1.19 2002/09/11 14:01:46 cbrown Exp $

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
	my $template = $C->tmpl('admin_library');
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub do_add {
	unless($ENV{'REQUEST_METHOD'} eq 'POST') {
		show_add();
	}
	else {
		my %error = ();
		
		unless(vrfy_string(\$F{'title'})) {
			$error{title_error} = "Either you didn't enter a title or it contained invalid characters";
		}	
	
		$F{'item_num'} = uc($F{'item_num'});
		unless(vrfy_string(\$F{'item_num'})) {
			$error{item_num_error} = "You must enter a valid item number";
		}
	
		unless(vrfy_string(\$F{'manuf'})) {
			$error{manuf_error} = "You must enter a valid manufacturer";
		}

		unless(vrfy_blob(\$F{'descr'})) {
			$error{descr_error} = "You must enter a valid description";
		}

		my $filename = $Q->param('file');

		# this type check has to be done before the file name gets
		# mangled so that's why its here.
		my $type;
		my $fh;
		if($filename) {
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
			$fh = $Q->upload('file');
		}

		$filename =~ s/\s/_/g;

		unless(defined($fh)) {
			$error{'file_error'} = "Please select a document to upload";
		}

		if(%error) {
			$error{'title'} = $F{'title'};
			$error{'item_num'} = $F{'item_num'};
			$error{'manuf'} = $F{'manuf'};
			$error{'descr'} = $F{'descr'};

			show_add(\%error);
		}
		else {
			my $itemstr = $C->sanitize_string($F{'item_num'});

			# check for this item's directory. If it does not exist create it		
			unless(-e $C->libraryfiles() . "/$itemstr" && -d $C->libraryfiles() . "/$itemstr") {
				mkdir($C->libraryfiles() . "/$itemstr",0755) or die "Couldn't make directory for " . $C->libraryfiles() . "/$itemstr: $!";
			}
	
			# stupid windows
			if($filename =~ /\\/) {
				my @tmp = split(/\\/,$filename);
				$filename = pop(@tmp);
			}
			
			my $file = $C->libraryfiles() . "/$itemstr/". $C->sanitize_string($filename);
			$file =~ m/^(.*)$/;
			$file = $1;
			my $buffer;
			open(FILE,">$file") or die "Couldn't open $file: $!";
			flock(FILE,LOCK_EX) or die "Couldn't flock\n";
			#	print "defined count, entering loop\n";
			while(read($fh,$buffer,1024)) {
				print FILE $buffer;
			}
			flock(FILE,LOCK_UN);
			close(FILE);
			if($type =~ /^image/i) {
				my ($x,$y,$ftype) = imgsize($file);
				create_thumb($file,$x,$y);
			}
			
			my $query = "INSERT INTO library (item_num,title,manuf,descr,file) VALUES (?,?,?,?,?)";
			$sth = $C->db_query($query,[$F{'item_num'},$F{'title'},$F{'manuf'},$F{'descr'},$C->sanitize_string($filename)]);
			$sth->finish();

			show_success("Library item $F{'title'} has been added successfully.");
		}
	}
}

sub do_view {
	my $query1 = "SELECT COUNT(*) FROM library";
	my @dbp = ();
	$query1 = search_library(\%F,$query1);

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

	my $query = "SELECT sid,item_num,title,descr,file FROM library";
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
		$row->{filesize} = $C->get_filesize($C->libraryfiles() . '/'.
			$C->sanitize_string($row->{item_num}) .'/'.
			$C->sanitize_string($row->{file}) );
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
	my $show_next = 1 unless $next >= $numrows;

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

	show_view(\@list,\$next,\$prev,\$show_next,\$show_prev,\@pages,\$qstring);
}

sub do_modify {
	die "No sid passed to modify" unless $F{'sid'};
	
	my $query = "SELECT sid,title,item_num,manuf,descr,file FROM library WHERE sid=?";
	$sth = $C->db_query($query,[$F{'sid'}]);
	my $lib_info = $sth->fetchrow_hashref;
	$sth->finish;

	if(!defined($F{'update'})) {

		$lib_info->{icon} = get_icon($lib_info->{file},$lib_info->{item_num});
		show_modify($lib_info); # $lib_info is already a reference
	}
	else {
		die "No sid passed to modify" unless $F{'sid'};
		my %error = ();
		
		unless(vrfy_string(\$F{'title'})) {
			$error{title_error} = "Either you didn't enter a title or it contained invalid characters";
		}	
		
		$F{item_num} = uc($F{'item_num'});	
		unless(vrfy_string(\$F{'item_num'})) {
			$error{item_num_error} = "You must enter a valid item number";
		}
	
		unless(vrfy_string(\$F{'manuf'})) {
			$error{manuf_error} = "You must enter a valid manufacturer";
		}


		unless(vrfy_blob(\$F{'descr'})) {
			$error{descr_error} = "You must enter a valid description";
		}

		my $filename = $Q->param('file');

		# this type check has to be done before the file name gets
		# mangled so that's why its here.
		
		my $fh;
		my $type;
		if($filename) {
			$type = $Q->uploadInfo($filename)->{'Content-Type'};
			$fh = $Q->upload('file');
		
			$filename =~ s/\s/_/g;		
			if($filename =~ /\\/) {
				my @tmp = split(/\\/,$filename);
				$filename = pop(@tmp);
			}
		}
		# document won't be required here
		
		if(%error) {
			$error{'title'} = $F{'title'};
			$error{'item_num'} = $F{'item_num'};
			$error{'manuf'} = $F{'manuf'};
			$error{'descr'} = $F{'descr'};
			$error{'sid'} = $F{'sid'};
			$error{'file'} = $lib_info->{file};
			$error{icon} = get_icon($lib_info->{file},$lib_info->{item_num});
			
			show_modify(\%error);
		}
		else {
			my $itemstr = $C->sanitize_string($F{item_num});
			my $filestr = $C->sanitize_string($filename);

			my $tmp = $C->libraryfiles() . "/$itemstr";
			unless(-e $tmp && -d $tmp) {
				mkdir($tmp,0775) or die "Couldn't make directory $tmp: $!\n"; 
			}
		
			my @modwarning = ();
			if(!$F{confirm_modify} && $F{item_num} ne $lib_info->{item_num}) {
				push(@modwarning,{msg=>'By changing the item number the database will associate this document with new products. This document will no longer be associated with the existing products.'});
			
			
				# save to a temp file if the item already exists and add to the warnings
				if(-e $C->libraryfiles() . "/$itemstr/$filestr" && defined($fh)) {
					$filestr = time() . "_$filestr";
					push(@modwarning,{msg=>"There is already a file named $filename associated with the new Item number. If you proceed the existing file will be deleted",lfile=>$filename});
				}
				elsif(-e $C->libraryfiles() . "/$itemstr/$lib_info->{file}") {
					push(@modwarning,{msg=>"There is already a file named $lib_info->{file} associated with $F{item_num}. If you proceed the existing file will be deleted",lfile=>$lib_info->{file}});
				}
				elsif(!defined($fh)) {
					push(@modwarning,{lfile=>$lib_info->{file}});
				}
			}
			elsif($F{confirm_modify}) {
				my @files = $Q->param('lfile'); # just names, not handles.
				my $newfile;
				foreach my $f (@files) {
					next unless vrfy_string(\$f);
					$f = $C->sanitize_string($f);
					if($f =~ /^\d{10}_(.+)$/) {
						$newfile = $1;
					}
					else {
						$newfile = $f;
					}

					my $f1 = $C->libraryfiles() . "/$itemstr/". $C->sanitize_string($f);
					my $f2 = $C->libraryfiles() . "/$lib_info->{item_num}/". $C->sanitize_string($f);
					
					my $tofile = $C->libraryfiles() . "/$itemstr/$newfile";
	
					if(-e $f1) {
						move($f1,$tofile) or die "Couldn't move $f1 to $tofile: $!";
					}
					if(-e $f2) {
						move($f2,$tofile) or die "Couldn't move $f2 to $tofile: $!";
					}
					
					my($nf,$ext) = split(/\./,$newfile);
					my($of,$ext_2) = split(/\./,$f);
					my $thumb1 = $C->libraryfiles() . "/$itemstr/${of}_thumb.$ext_2";
					my $thumb2 = $C->libraryfiles() . "/$lib_info->{item_num}/${of}_thumb.$ext_2";
					my $tothumb = $C->libraryfiles() . "/$itemstr/${nf}_thumb.$ext";

					if(-e $thumb1) {
						move($thumb1,$tothumb) or die "Couldn't move $thumb1 to $tothumb: $!";
					}
					if(-e $thumb2) {
						move($thumb2,$tothumb) or die "Couldn't move $thumb2 to $tothumb: $!";
					}
				}
				$filename = $newfile;
				rmdir($C->libraryfiles() . "/$lib_info->{item_num}"); # this will only happen if the dir is empty.
			}

			if(defined($fh) && vrfy_string(\$filename)) {
				
				my $buffer;

				# Remove old files (if they have the same name they'll get over-written
				unless(@modwarning && !$F{confirm_modify}) {
					if($filename ne $lib_info->{file}) { 
						unlink($C->libraryfiles() . "/$lib_info->{item_num}/$lib_info->{file}") or warn "Couldn't unlink $lib_info->{file}: $!\n";
					}	
				
					my($tmpfile,$tmpext) = split(/\./,$lib_info->{file});
				
					my $thumbpath = $C->libraryfiles(). "/$lib_info->{item_num}/${tmpfile}_thumb.$tmpext";
				
					if(-e $thumbpath) {
						unlink($thumbpath) or warn "Couldn't unlink $thumbpath: $!\n";
					}
					rmdir($C->libraryfiles() . "/$lib_info->{item_num}") or warn "Didn't remove directory: $!\n";
				}
		
				my $file = $C->libraryfiles() . "/$itemstr/$filestr";
				open(FILE,">$file") or die "Couldn't open $file: $!";
				flock(FILE,LOCK_EX);
				while(read($fh,$buffer,1024)) {	
					print FILE $buffer;
				}
				flock(FILE,LOCK_UN);
				close(FILE);
				if($type =~ /^image/i) {
					my ($x,$y) = imgsize($file);
					create_thumb($file,$x,$y);
				}
			}
			else {
				$filename = $lib_info->{'file'} unless $filename;
			}
			
			if(@modwarning) {
				delete($F{mode});
				delete($F{file});
				delete($F{update});
				show_confirm_modify(\%F,\@modwarning);
			}
			else {	

				my $query = "UPDATE library SET item_num=?,title=?,manuf=?,descr=?,file=? WHERE sid=?";
				$sth = $C->db_query($query,[$F{'item_num'},$F{'title'},$F{'manuf'},$F{'descr'},$filestr,$F{'sid'}]);
				$sth->finish();
				show_success("$F{'title'} (Item #: $F{'item_num'}) has been modified");
			}
		}
	}
}

sub do_cancelmod {

	my $query = "SELECT item_num FROM library WHERE sid=?";
	$sth = $C->db_query($query,[$F{sid}]);
	my $dbitem_num = $C->sanitize_string($sth->fetchrow());
	my $itemstr = $C->sanitize_string($F{item_num});
	$sth->finish();

	my @lfiles = $Q->param('lfiles');
	foreach my $f (@lfiles) {
		$f = $C->sanitize_string($f);
		# I'm ignoring the warnings in this section
		unlink($C->libraryfiles() . "/$itemstr/$f");
		unlink($C->libraryfiles() . "/$dbitem_num/$f");
		my ($file,$ext) = split(/\./,$f);
		unlink($C->libraryfiles() . "/$itemstr/${file}_thumb.$ext");
		unlink($C->libraryfiles() . "/$dbitem_num/${file}_thumb.$ext");
	}
	delete($F{item_num});
	do_view();
}


sub do_delete {
	die "No sid passed to do_delete()!" unless $F{'sid'};
	
	my $sth = $C->db_query("SELECT item_num,title,file FROM library WHERE sid=?",[$F{'sid'}]);
	my ($item,$title,$filename) = $sth->fetchrow();

	$sth->finish;

	if(!$F{'confirm'}) {
		
		show_delete({item_num=>$item,title=>$title});
	}
	else {
		my $itemstr = $C->sanitize_string($item);

		$sth = $C->db_query("DELETE FROM library WHERE sid=?",[$F{'sid'}]);
		$sth->finish();

		my $path = $C->libraryfiles() . "/$itemstr/$filename";
		if(-e $path) {
			unlink($path) or warn "Couldn't unlink $path: $!\n";
		}

		my($tmpfile,$tmpext) = split(/\./,$filename);
		if(-e $C->libraryfiles() . "/$itemstr/${tmpfile}_thumb.$tmpext") {
			unlink($C->libraryfiles() . "/$itemstr/${tmpfile}_thumb.$tmpext") or warn "Couldn't unlink thumb $path: $!\n";
		}
		
		rmdir($C->libraryfiles() . "/$itemstr") ; # will happen if its empty

		show_success("$title (item #: $item) has been deleted");
	}
}
			
sub show_add {
	my $error = shift;

	my $template = $C->tmpl('admin_library_add');
	$template->param(%$error) if $error;
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_modify {
	my $params = shift;
	
	my $template = $C->tmpl('admin_library_modify');
	$template->param(%$params) if $params;
	$template->param(dir=> $C->sanitize_string($params->{item_num}));
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
	die "No sid passed to show_delete()!" unless $F{'sid'};
	
	my $template = $C->tmpl('admin_library_delete');
	$template->param(sid=>$F{'sid'});
	$template->param(%$params);
	print $Q->header(-type=>'text/html');
	print $template->output();
}

sub show_view {
	# all these are refs
	my($list,$next,$prev,$show_next,$show_prev,$pages,$qstring) = @_;

	my $template = $C->tmpl('admin_library_list');
	$template->param(list=>$list);	#loop
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

sub create_thumb {
	my ($file_out,$x,$y) = @_;
	# I know its a hack but I just want to pass this routine the path+filename

	my @tmp = split(/\//,$file_out);
	my $file = pop(@tmp);
	my $dir = join("/",@tmp);
	my ($ext) = $file =~ /\.([A-Za-z0-9]{3})$/;
	$file =~ s/\.$ext//;
	
	# Copy the original and work only on the thumb file.
	copy($file_out,"$dir/${file}_thumb.$ext") or die "Couldn't copy $file_out to $dir/${file}_thumb.$ext: $!\n";

	my $image = Image::Magick->new();

	open(IMAGEIN,"$dir/${file}_thumb.$ext") or die "Couldn't open $dir/${file}_thumb.$ext for reading: $!\n";
	flock(IMAGEIN,LOCK_SH);
	$image->Read(file=>\*IMAGEIN);
	flock(IMAGEIN,LOCK_UN);
	close(IMAGEIN);

	if( ($y / $x) >= ($C->max_thumb_height / $C->max_thumb_width) ) {
		$image->Resize(
			width=>int($x * $C->max_thumb_width / $y),
			height=>$C->max_thumb_height );
	} else {
		$image->Resize(
			width=>$C->max_thumb_width,
			height=>int($y * $C->max_thumb_height / $x) );
	}

	open(THUMB,">$dir/${file}_thumb.$ext") or die "Couldn't open $dir/${file}_thumb.$ext for writing: $!\n";
	flock(THUMB,LOCK_EX);
	$image->Write(file=>\*THUMB,filename=>"$dir/${file}_thumb.$ext");
	flock(THUMB,LOCK_UN);
	close(THUMB);
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
