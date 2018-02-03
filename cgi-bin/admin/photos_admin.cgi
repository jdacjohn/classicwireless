#!/usr/bin/perl -T
# $Author: Jarnold $
# $Date: 3/09/06 6:28p $
# $Revision: 5 $

use strict;
use lib '..';
use CGI;
use DBI;
use HTML::Template;
use HTML::Entities qw(encode_entities);
use NDC::Conf;
use NDC::Verify;
use Image::Size;
#use Image::Magick;
use Imager;
use File::Copy;
use Fcntl ':flock';
use CGI::Carp 'fatalsToBrowser';

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $sth;
our $DEBUG = 0;
our $DEBUG_INIT = 0;

$C->encode_html(\%F);

my %modes = (
  'add'=>\&do_add,
  'modify'=>\&do_modify,
  'delete'=>\&do_delete,
  'view'=>\&do_view,
  'default'=>\&do_default
);

if(defined($F{'mode'}) && exists($modes{$F{mode}})) {
  $modes{$F{'mode'}}->();
}
else {
  $modes{'default'}->();
}

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

#------------------------------------------------------------------------------
# Display the Photos Add page.
#
# Change History:
#
# 1.  03.09.2006:  Initial Version - jarnold
#------------------------------------------------------------------------------
sub show_add {
  my $error = shift;

  my $template = $C->tmpl('admin_photos_add');
  $template->param(cats => &mk_category_tmpl_obj(\$F{'catid'}) );
  $template->param(%$error) if $error;
  # Build row used to display orientation options
  &debug("Selected orientation = " . $F{orientation} . "<br>");
  my %hrow = ();
  my @rbuttons = ();
  %hrow->{orient} = 'horz';
  %hrow->{label} = 'Horizontal';
  if ($F{'orientation'} eq 'horz') {
    %hrow->{selected} = 1;
  }
  push(@rbuttons,\%hrow);
  my %vrow = ();
  %vrow->{orient} = 'vert';
  %vrow->{label} = 'Vertical';
  if ($F{'orientation'} eq 'vert') {
    %vrow->{selected} = 1;
  }
  push(@rbuttons,\%vrow);
  $template->param(rbuttons=>\@rbuttons);
  print $Q->header(-type=>'text/html');
  print $template->output;
}

#------------------------------------------------------------------------------
# Display the Admin view of the specials list
#------------------------------------------------------------------------------
sub show_view {
  my ($list,$error) = @_;
    
  my $template = $C->tmpl('admin_photos_list');
  $template->param(list_loop=>$list); # list is already a ref
  $template->param(%$error) if $error;

  print $Q->header(-type=>'text/html');
  print $template->output;
}
  
#------------------------------------------------------------------------------
# Display the Admin Specials Modify Page
#
# Change History:
#------------------------------------------------------------------------------
sub show_modify {
  my $params = shift;
  my $template = $C->tmpl('admin_photos_modify');
  $template->param(%$params) if $params;
  $template->param(photo_id=>$F{'photo_id'});
  
  # Build row used to display orientation options
  my %hrow = ();
  my @rbuttons = ();
  %hrow->{orient} = 'horz';
  %hrow->{label} = 'Horizontal';
  if ($F{orientation} eq 'horz') {
    %hrow->{selected} = 1;
  }
  push(@rbuttons,\%hrow);
  my %vrow = ();
  %vrow->{orient} = 'vert';
  %vrow->{label} = 'Vertical';
  if ($F{orientation} eq 'vert') {
    %vrow->{selected} = 1;
  }
  push(@rbuttons,\%vrow);
  $template->param(rbuttons=>\@rbuttons);

  print $Q->header(-type=>'text/html');
  print $template->output;
}

#------------------------------------------------------------------------------
# Display the Admin Specials Delete Page
#
# Change History:
#------------------------------------------------------------------------------
sub show_delete {
  my $params = shift;
  # the confirm delete page
  
  die "No ID passed to show_delete()" unless $$params{'photo_id'};

  my $template = $C->tmpl('admin_photos_delete');
  $template->param(%$params);  
  print $Q->header(-type=>'text/html');
  print $template->output;
}

#------------------------------------------------------------------------------
# Display operational success message
#------------------------------------------------------------------------------
sub show_success {
  my $msg = shift;
  my $template = $C->tmpl('success');
  $template->param(msg=>$msg);
  print $Q->header(-type=>'text/html');
  print $template->output;
}

#------------------------------------------------------------------------------
# Display operational success message
#------------------------------------------------------------------------------
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header(-type=>'text/html');
  print $template->output;
  exit;
}

#------------------------------------------------------------------------------
# Default method for exec with no args
#------------------------------------------------------------------------------
sub do_default {
  show_default();
}

#------------------------------------------------------------------------------
# Show the Specials Admin home page
#------------------------------------------------------------------------------
sub show_default {
  my $template = $C->tmpl('admin_photos');
  print $Q->header(-type=>'text/html');
  print $template->output();
}

#------------------------------------------------------------------------------
# Set up the parameters for the Photos Admin Add Page.
# Change History:
# 1. 03.09.2006:  -  Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_add {

  unless($ENV{'REQUEST_METHOD'} eq 'POST') {
    show_add();
  }
  else {
    my %error = ();

    # first deal with the photo.
    my $filename = $Q->param('photo');
    my $fh = $Q->upload('photo');
    my ($size_x,$size_y,$type);
    my $photo_ext;
		$filename =~ s/\s/_/g;
    if(defined($fh)) {
      ($size_x,$size_y,$type) = imgsize($fh);
      if(uc($type) =~ /^(JPG|GIF|PNG|BMP)$/) {
        $photo_ext = lc($1);
        $filename =~ s#.$photo_ext##;
        $filename .= time();
      }
      else {
        $error{photo_error} = "Wrong photo type. Photos must be in JPEG (.jpg), GIF (.gif), BMP (.bmp) or PNG (.png) format";
      }
      unless(vrfy_string(\$F{'orientation'})) {
        $error{orient_error} = "You must select an image orientation from the radio buttons at the bottom of the screen";
      }
    } else {
      $error{photo_error} = "You must select a photo to upload";
    }

    unless(vrfy_int(\$F{'catid'})) {
      $error{category_error} = "You must select a category for the photo";
    }
    
    if(%error) {
      $error{'caption'} = $F{'caption'};
      show_add(\%error);
    }
    else {
      # save image
      my ($category,$header);
      if(defined($fh)) {

      # stupid windows - this strips the path information from the filename for requests generated by Internet Exploder
		  if($filename =~ /\\/) {
			  my @tmp = split(/\\/,$filename);
			  $filename = pop(@tmp);
		  }
      
        #show_error($filename);
        # Get the category header to make the image directory if necessary
        my $query = 'select category,header from photo_cats where sid = ?';
        $sth = $C->db_query($query,[$F{'catid'}]);
        ($category,$header) = $sth->fetchrow();
        $sth->finish();
        
        my $buffer;
        
        mkdir($C->photos_dir(). "/$header") unless (-e $C->photos_dir(). "/$header");
        my $file_out = $C->photos_dir() . "/$header/$filename.$photo_ext";
        # Untaint the file name

        if ($file_out =~ /^([-\/\@\w.]+)$/) {
          $file_out = $1;
        } else {
          die "Bad data in file_out: " . $file_out;
        }
        open(IMAGEOUT,">$file_out") or die "Couldn't open $file_out for writing: $!\n";
        binmode(IMAGEOUT);
        flock(IMAGEOUT,LOCK_EX);
        while(read($fh,$buffer,1024)) {
          print IMAGEOUT $buffer;
        }
        flock(IMAGEOUT,LOCK_UN);
        close(IMAGEOUT);

        # now resize the image to a displayable web size and thumbnail files
        create_webimages($file_out,$size_x,$size_y,$F{orientation});
        # Create a Thumbnail
        #create_thumbnail($file_out,$size_x,$size_y,$F{orientation});
        # delete the original file
        unlink($file_out);
      }
      my $query = 'insert into photos (category,photo_file,photo_ext,caption) values(?,?,?,?)';
      my @params = ($F{'catid'},$filename,$photo_ext,$F{'caption'});
      $sth = $C->db_query($query,\@params);
      $sth->finish();

      show_success("New photo " . $filename . " has been added to the " . $category . " category.<br>View the results <a href='" . $C->photos_dir_URL() . "/$header/${filename}_web.$photo_ext'>here</a>");
    }
  }
}  

#------------------------------------------------------------------------------
# Show the admin view of all specials.
# Change History:
#
# 1. Added code to get the vendor-specific display width and height for thumbnails
#    02.28.06 - jarnold
# 2. Removed width/height construction in support of orientation based thumbnail
#    creation.  3.1.06 - jarnold
#------------------------------------------------------------------------------
sub do_view {
  $sth = $C->db_query("SELECT photo_id,category,photo_file,photo_ext,caption FROM photos order by photo_id");

  my @list_loop = ();
  while(my $row = $sth->fetchrow_hashref()) {
    # Get the category info to show on the results page
    my $query = 'select category,header from photo_cats where sid = ?';
    my $sth2 = $C->db_query($query,[$row->{category}]);
    my ($category,$header) = $sth2->fetchrow();
    $sth2->finish();
    $row->{thumb} = $C->photos_dir_URL() . "/$header/$row->{photo_file}_thumb.$row->{photo_ext}";
    $row->{photo} = $C->photos_dir_URL() . "/$header/$row->{photo_file}_web.$row->{photo_ext}";
    $row->{category} = $category;
    $row->{file} = "$row->{photo_file} .$row->{photo_ext}";
    delete($row->{photo_ext});
    delete($row->{photo_file});
    push(@list_loop, $row);
  }
  
  $sth->finish();
  show_view(\@list_loop);
}

#------------------------------------------------------------------------------
#
# Change History 
#
# 1.  03.09.2006  - Initial Version - jarnold
#------------------------------------------------------------------------------
sub do_modify {
  die "No ID passed to show_modify()" unless $F{'photo_id'};

  $sth = $C->db_query("SELECT category,photo_file,photo_ext,caption FROM photos WHERE photo_id=?",[$F{'photo_id'}]);
  my ($cat_id,$photo_file,$photo_ext,$caption) = $sth->fetchrow();
  $sth->finish();  
  $sth = $C->db_query('select category,header from photo_cats where sid=?',[$cat_id]);
  my($category,$header) = $sth->fetchrow();
  $sth->finish();
  
  my $thumb = $C->photos_dir_URL() . "/$header/${photo_file}_thumb.$photo_ext";
  my $cur_photo = $C->photos_dir_URL() . "/$header/${photo_file}_web.$photo_ext";
  my $photopath = $C->photos_dir() . "/$header/${photo_file}_web.$photo_ext";
  my $thumbpath = $C->specials_dir() . "/$header/${photo_file}_thumb.$photo_ext";

  if(!defined($F{'update'})) {
  &debug("We are not seeing the update value... Going straight back now.<br>");
    my %params = (
          cats=> &mk_category_tmpl_obj(\$cat_id ),
          caption=>$caption,
          thumb=>$thumb,
          cur_photo=>$cur_photo,);
    show_modify(\%params);
  }
  else {
    my %error = ();

    # first deal with the photo.
    my $filename = $Q->param('photo');
    my $fh = $Q->upload('photo');
    my ($size_x,$size_y,$type);
    my $photo_ext;
		$filename =~ s/\s/_/g;
    &debug("Filename = " . $filename);

    if(defined($fh)) {
      ($size_x,$size_y,$type) = imgsize($fh);
      if($type =~ /^(JPG|GIF|PNG|BMP)$/) {
        $photo_ext = lc($1);
        $filename =~ s#.$photo_ext##;
        &debug("  Filename = " . $filename . "<br>");
        $filename .= time();
      }
      else {
        $error{photo_error} = "Wrong photo type. Photos must be in JPEG (.jpg), GIF (.gif), BMP (.bmp) or PNG (.png) format";
      }
      unless(vrfy_string(\$F{'orientation'})) {
        $error{orient_error} = "You must select an image orientation from the radio buttons at the bottom of the screen";
      }
    }

    unless(vrfy_int(\$F{'catid'})) {
      $error{category_error} = "You must select a category";
    }
    
    if(%error) {
      $error{'caption'} = $F{'caption'};
      show_modify(\%error);
    }
    else {
      # save the new image and delete the old one.
      my $update = 'update photos set category=?,caption=?';
      my @dbps = ($F{'catid'},$F{'caption'});
      
      if(defined($fh)) {
        # Delete the old image first
        my $sth = $C->db_query('select photo_file,photo_ext from photos where photo_id=?',[$F{'photo_id'}]);
        my ($photo_file,$photo_ext) = $sth->fetchrow();
        $sth->finish();
        $sth = $C->db_query('select header from photo_cats where sid=?',[$F{'catid'}]);
        my ($header) = $sth->fetchrow();
        $sth->finish();
        
        my $webimage = $C->photos_dir . "/$header/${photo_file}_web.$photo_ext";
        my $thumbimage = $C->photos_dir . "/$header/${photo_file}_thumb.$photo_ext";
        unlink($webimage) or die "Could not delete old image " . $webimage;
        unlink($thumbimage) or die "Could not delete old thumb " . $thumbimage;
        
        # Get the new image file
        my $buffer;
        
        # stupid windows - this strips the path information from the filename for requests generated by Internet Exploder
        if($filename =~ /\\/) {
          my @tmp = split(/\\/,$filename);
          $filename = pop(@tmp);
        }
        
        mkdir($C->photos_dir(). "/$header") unless (-e $C->photos_dir(). "/$header");
        my $file_out = $C->photos_dir() . "/$header/$filename.$photo_ext";
        # Untaint the file name
        if ($file_out =~ /^([-\/\@\w.]+)$/) {
          $file_out = $1;
        } else {
          die "Bad data in file_out: " . $file_out;
        }
        open(IMAGEOUT,">$file_out") or die "Couldn't open $file_out for writing: $!\n";
        binmode(IMAGEOUT);
        flock(IMAGEOUT,LOCK_EX);
        while(read($fh,$buffer,1024)) {
          print IMAGEOUT $buffer;
        }
        flock(IMAGEOUT,LOCK_UN);
        close(IMAGEOUT);

        # now resize the image to a displayable web size
        create_webimage($file_out,$size_x,$size_y,$F{orientation});
        # Create a Thumbnail
        create_thumbnail($file_out,$size_x,$size_y,$F{orientation});
        # delete the original file
        unlink($file_out);
        
        $update .= ",photo_file=?,photo_ext=? ";
        push(@dbps,$filename);
        push(@dbps,$photo_ext);
      }

      $update .= " WHERE photo_id=?";
      push(@dbps,$F{'photo_id'});

      $sth = $C->db_query($update,\@dbps);
      $sth->finish();

      show_success("Photograph $filename in cateogry $category has been successfully updated.<br>View the results <a href='" . $C->photos_dir_URL() . "/$header/${filename}_web.$photo_ext'>here</a>");
    }
  }
}

#------------------------------------------------------------------------------
# Set up the parameters for the Specials Admin delete page.
# Change History:
#------------------------------------------------------------------------------
sub do_delete {
  die "No ID passed to delete\n" unless $F{'photo_id'};

  $sth = $C->db_query("SELECT photo_file,photo_ext,category FROM photos WHERE photo_id=?",[$F{'photo_id'}]);
  my($photo_file,$photo_ext,$catid) = $sth->fetchrow();
  $sth->finish();
  
  if(!defined($F{'confirm'})) {

    my %params = (  
      photo_id=>$F{'photo_id'},
      photo=>"$photo_file.$photo_ext",
    );
    show_delete(\%params);
  }
  else {
    # Get the cat header to use for file deletions
    $sth = $C->db_query('select header from photo_cats where sid=?',[$catid]);
    my ($header) = $sth->fetchrow();
    $sth->finish();
    
    # Delete the image and thumb files - Just warn on these if they fail, it won't break the program
    # if they do (it will just leave the images on the server)
    my $image = $C->photos_dir . "/$header/${photo_file}_web.$photo_ext";
    my $thumb = $C->photos_dir . "/$header/${photo_file}_thumb.$photo_ext";
    unlink($image) or warn "Couldn't unlink $image: $!\n";
    unlink($thumb) or warn "Couldn't unlink $thumb: $!\n";
    
    my $query2 = "DELETE FROM photos WHERE photo_id=?";
    $sth = $C->db_query($query2,[$F{'photo_id'}]);
    $sth->finish();

    show_success("Photo $photo_file.$photo_ext has been deleted from the system.<br><a href='/cgi-bin/admin/photos_admin.cgi?mode=view'>[return]</a>");
  }
}
    
#------------------------------------------------------------------------------
# Create an orientation-based thumbnail for a new special
# Change History
# 1. 03.09.2006:  Initial Version - jarnold
#------------------------------------------------------------------------------
sub create_thumbnail {
  my ($file_out,$x,$y,$orientation) = @_;
  
  # I know its a hack but I just want to pass this routine the path+filename
  # Who wrote this?
  my @tmp = split(/\//,$file_out);
  my $file = pop(@tmp);
  my $dir = join("/",@tmp);

  my ($ext) = $file =~ /\.(jpg|gif|png|bmp)$/;
  my $format = $ext;
  &debug("File Extension = " . $ext . "<br>");
  if ($format eq 'jpg') { $format = 'jpeg' }
  $file =~ s/\.$ext//;
  
  mkdir($dir) unless (-e $dir);
  
  # Copy the original and work only on the thumb file.
  &debug("Line 458");
  copy($file_out,"$dir/${file}_thumb.$ext") or die "Couldn't copy $file_out to $dir/${file}_thumb.$ext: $!\n";
  &debug("Line 460");
  
  ## Get the max thumb x and y based on image orientation
  my $max_x;
  my $max_y;
  if ($orientation eq 'vert') {
    $max_x = $C->v_thumb_width();
    $max_y = $C->v_thumb_height();
  } else {
    $max_x = $C->h_thumb_width();
    $max_y = $C->h_thumb_height();
  }
  
  if($x > $max_x || $y > $max_y) {
    # Read the image from the file into $image
    my $image = Imager->new();
    my $newImage = Imager->new();
    $image->read(file=>"$dir/${file}_thumb.$ext",type=>$format) or die "Cannot Read Image File:   " . $image->errstr();
    # create a scaled copy of the image
    if ($orientation eq 'vert') {
      $newImage = $image->scale(xpixels=>$max_x,ypixels=>$max_y,type=>'min');
    } else {
      $newImage = $image->scaleX(pixels=>$max_x);
      $newImage = $newImage->scaleY(pixels=>$max_y);
    }
    my $size_x = $newImage->getwidth();
    my $size_y = $newImage->getheight();
    &debug("Thumbnail Image dimensions:  x = " . $size_x . "  y = " . $size_y . "<br>");
    &debug("Width = " . $size_x . "  Height = " . $size_y);
    $newImage->write(file=>"$dir/${file}_thumb.$ext",$ext) or die "Cannot Write Image File:  " . $newImage->errstr;
  }
  
}

#------------------------------------------------------------------------------
# Create an orientation-based webimage for a new photo
# Change History
# 1. 03.09.2006:  Initial Version - jarnold
#------------------------------------------------------------------------------
sub create_webimage {
  my ($file_out,$x,$y,$orientation) = @_;
  
  # I know its a hack but I just want to pass this routine the path+filename
  # Who wrote this?
  my @tmp = split(/\//,$file_out);
  my $file = pop(@tmp);
  my $dir = join("/",@tmp);

  my ($ext) = $file =~ /\.(jpg|gif|png|bmp)$/;
  my $format = $ext;
  &debug("File Extension = " . $ext . "<br>");
  if ($format eq 'jpg') { $format = 'jpeg' }
  $file =~ s/\.$ext//;
  
  mkdir($dir) unless (-e $dir);
  
  # Copy the original and work only on the web file.
  &debug("Line 458");
  copy($file_out,"$dir/${file}_web.$ext") or die "Couldn't copy $file_out to $dir/${file}_web.$ext: $!\n";
  &debug("Line 460");
  
  ## Get the max thumb x and y based on image orientation
  my $max_x;
  my $max_y;
  if ($orientation eq 'vert') {
    $max_x = $C->v_max_constr_width();
    $max_y = $C->v_max_constr_height();
  } else {
    $max_x = $C->h_max_constr_width();
    $max_y = $C->h_max_constr_height();
  }
  
  if($x > $max_x || $y > $max_y) {
    # Read the image from the file into $image
    my $image = Imager->new();
    my $newImage = Imager->new();
    $image->read(file=>"$dir/${file}_web.$ext",type=>$format) or die "Cannot Read Image File:   " . $image->errstr();
    # create a scaled copy of the image
    if ($orientation eq 'vert') {
      $newImage = $image->scale(xpixels=>$max_x,ypixels=>$max_y,type=>'min');
    } else {
      $newImage = $image->scaleX(pixels=>$max_x);
      $newImage = $newImage->scaleY(pixels=>$max_y);
    }
    my $size_x = $newImage->getwidth();
    my $size_y = $newImage->getheight();
    &debug("Thumbnail Image dimensions:  x = " . $size_x . "  y = " . $size_y . "<br>");
    &debug("Width = " . $size_x . "  Height = " . $size_y);
    $newImage->write(file=>"$dir/${file}_web.$ext",$ext) or die "Cannot Write Image File:  " . $newImage->errstr;
  }
  
}

#------------------------------------------------------------------------------
# Create an orientation-based webimage and thumbnail for a new photo
# Change History
# 1. 03.09.2006:  Initial Version - jarnold
#------------------------------------------------------------------------------
sub create_webimages {
  my ($file_out,$x,$y,$orientation) = @_;
  
  # I know its a hack but I just want to pass this routine the path+filename
  # Who wrote this?
  my @tmp = split(/\//,$file_out);
  my $file = pop(@tmp);
  my $dir = join("/",@tmp);

  my ($ext) = $file =~ /\.(jpg|gif|png|bmp)$/;
  my $format = $ext;
  &debug("File Extension = " . $ext . "<br>");
  if ($format eq 'jpg') { $format = 'jpeg' }
  $file =~ s/\.$ext//;
  
  mkdir($dir) unless (-e $dir);
  
  # Copy the original and work only on the web file.
  copy($file_out,"$dir/${file}_web.$ext") or die "Couldn't copy $file_out to $dir/${file}_web.$ext: $!\n";
  copy($file_out,"$dir/${file}_thumb.$ext") or die "Couldn't copy $file_out to $dir/${file}_thumb.$ext: $!\n";
  
  ## Get the max thumb x and y for the web image file based on image orientation 
  my $max_x;
  my $max_y;
  if ($orientation eq 'vert') {
    $max_x = $C->v_max_constr_width();
    $max_y = $C->v_max_constr_height();
  } else {
    $max_x = $C->h_max_constr_width();
    $max_y = $C->h_max_constr_height();
  }
  my $image = Imager->new();
  my $newImage = Imager->new();
  if($x > $max_x || $y > $max_y) {
    # Read the image from the file into $image
    $image->read(file=>"$dir/${file}_web.$ext",type=>$format) or die "Cannot Read Image File:   " . $image->errstr();
    # create a scaled copy of the image
    if ($orientation eq 'vert') {
      $newImage = $image->scale(xpixels=>$max_x,ypixels=>$max_y,type=>'min');
    } else {
      $newImage = $image->scaleX(pixels=>$max_x);
      $newImage = $newImage->scaleY(pixels=>$max_y);
    }
    $newImage->write(file=>"$dir/${file}_web.$ext",$ext) or die "Cannot Write Image File:  " . $newImage->errstr;
  }
  
  # Now do the thumbnail
  if ($orientation eq 'vert') {
    $max_x = $C->v_thumb_width();
    $max_y = $C->v_thumb_height();
  } else {
    $max_x = $C->h_thumb_width();
    $max_y = $C->h_thumb_height();
  }
  
  if($x > $max_x || $y > $max_y) {
    # Read the image from the file into $image
    $image->read(file=>"$dir/${file}_thumb.$ext",type=>$format) or die "Cannot Read Image File:   " . $image->errstr();
    # create a scaled copy of the image
    if ($orientation eq 'vert') {
      $newImage = $image->scale(xpixels=>$max_x,ypixels=>$max_y,type=>'min');
    } else {
      $newImage = $image->scaleX(pixels=>$max_x);
      $newImage = $newImage->scaleY(pixels=>$max_y);
    }
    $newImage->write(file=>"$dir/${file}_thumb.$ext",$ext) or die "Cannot Write Image File:  " . $newImage->errstr;
  }
}

#------------------------------------------------------------------------------
# HTML::Template helper
# Change History:
# 1. 03.09.2006:  - Initial Version jarnold
#------------------------------------------------------------------------------
sub mk_category_tmpl_obj {
  my $selected = shift;
  $selected = \'' unless (defined $selected);

  my $query = 'select sid,category from photo_cats order by category';
  my @dbp = ();
  $sth = $C->db_query($query,\@dbp);
  my @cats = ();
  while (my $row = $sth->fetchrow_hashref()) {
    $row->{selected} = ($$selected eq $row->{sid}) ? 1 : 0;
    push(@cats,$row);
  }
  return \@cats;
}
######################################################################
sub debug_init {
  $DEBUG_INIT = 1;
  print $Q->header(-type=>'text/html');
}

sub debug {
  return unless ($DEBUG);
  if (!$DEBUG_INIT) {
    &debug_init();
  }
  print @_;
} 

1;
