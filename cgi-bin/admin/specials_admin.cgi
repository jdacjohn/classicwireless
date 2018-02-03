#!/usr/bin/perl -T
# $Id: specials_admin.cgi,v 1.17 2004/03/19 20:47:55 cameron Exp $

use strict;
use lib '..';
use CGI;
use DBI;
use HTML::Template;
use HTML::Entities qw(encode_entities);
use NDC::Conf;
use NDC::Verify;
use Image::Size;
use Image::Magick;
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
  'setfp'=>\&do_set,
  'default'=>\&do_default
);

# hack hack hack
#if($F{'item_num'} =~ /\s/) {
  #$F{item_num} =~ s/\s//g;
#}

if(defined($F{'mode'}) && exists($modes{$F{mode}})) {
  $modes{$F{'mode'}}->();
}
else {
  $modes{'default'}->();
}

$NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
exit;

##############################################################
#subs

#------------------------------------------------------------------------------
# Display the Specials Add page.
#
# Change History:
#
# 1.  Added the vendor id argument to the call to $mk_vendor_tmpl_obj so the
#     selected vendor would persist on user input error. - 2/28/06 - jarnold
# 2.  Removed the static Conf.pm vendors hash from the call to mk_vendor_tmpl_obj
#     as we're now pulling that info from the database. 03.02.2006 - jarnold
#------------------------------------------------------------------------------
sub show_add {
  my $error = shift;

  my $template = $C->tmpl('admin_specials_add');
  $template->param(%$error) if $error;
  $template->param(vendors => &mk_vendor_tmpl_obj(\$F{vendorid}) );
  # Build row used to display orientation options
  &debug("Selected orientation = " . $F{orientation} . "<br>");
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
# Display the Admin view of the specials list
#------------------------------------------------------------------------------
sub show_view {
  my ($list,$error) = @_;
    
  my $template = $C->tmpl('admin_specials_list');
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
  my $template = $C->tmpl('admin_specials_modify');
  $template->param(%$params) if $params;
  $template->param(sid=>$F{'sid'});
  
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
  
  die "No ID passed to show_delete()" unless $$params{'sid'};

  my $template = $C->tmpl('admin_specials_delete');
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
# Default method for exec with no args
#------------------------------------------------------------------------------
sub do_default {
  show_default();
}

#------------------------------------------------------------------------------
# Show the Specials Admin home page
#------------------------------------------------------------------------------
sub show_default {
  my $template = $C->tmpl('admin_specials');
  print $Q->header(-type=>'text/html');
  print $template->output();
}

#------------------------------------------------------------------------------
# Set up the parameters for the Specials Admin Add Page.
# Change History:
# 1. Changed call to create_thumbnail to send vendor id as new arg - 2/28/08
#    jarnold
# 2. Added BMP file type to list of valid file types. 2/28/06 - jarnold
# 3. Changed call to create_thumbnail to use orientation - 3.1.06 - jarnold
# 4. Added error checking for orientation. 3.1.06 - jarnold
#------------------------------------------------------------------------------
sub do_add {

  unless($ENV{'REQUEST_METHOD'} eq 'POST') {
    show_add();
  }
  else {
    my %error = ();

    # first deal with the photo.
    my $fh = $Q->upload('photo');
    my ($size_x,$size_y,$type);
    my $photo_ext;

    if(defined($fh)) {
      ($size_x,$size_y,$type) = imgsize($fh);
      if(uc($type) =~ /^(JPG|GIF|PNG|BMP)$/) {
        $photo_ext = lc($1);
      }
      else {
        $error{photo_error} = "Wrong photo type. Photos must be in JPEG (.jpg), GIF (.gif), BMP (.bmp) or PNG (.png) format";
      }
      unless(vrfy_string(\$F{'orientation'})) {
        $error{orient_error} = "You must select an image orientation from the radio buttons at the bottom of the screen";
      }
    }

    unless(vrfy_string(\$F{'title'})) {
      $error{title_error} = "Either you didn't enter a title or it contained invalid characters";
    }  
  
    unless(vrfy_int(\$F{'vendorid'})) {
      $error{vendorid_error} = "You must select a vendor from the list shown below";
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
    
    unless(vrfy_int(\$F{'qty'})) {
      $error{qty_error} = "You must enter a valid quantity (enter 0 for none)";
    }

    # Remove any '$' signs from the price
    $F{'price'} =~ s/[\$,]//;
    
    unless(vrfy_float(\$F{'price'})) {
      $error{price_error} = "You must enter a valid price (enter 0 for no price)";
    }
    
    if(%error) {
      $error{'title'} = $F{'title'};
      $error{'item_num'} = $F{'item_num'};
      $error{'manuf'} = $F{'manuf'};
      $error{'descr'} = $F{'descr'};
      $error{'price'} = $F{'price'};
      $error{'qty'} = $F{'qty'};
      
      show_add(\%error);
    }
    else {
      
      my $query = "INSERT INTO specials (vendorid,item_num,title,manuf,descr,price,qty";
      my @params = ($F{'vendorid'},$F{'item_num'},$F{'title'},$F{'manuf'},$F{'descr'},$F{'price'},$F{'qty'});
      
      # save image
      if(defined($fh)) {
        my $buffer;
        my $itemstr = $C->sanitize_string($F{item_num});
        
        mkdir($C->specials_dir(). "/$F{vendorid}") unless (-e $C->specials_dir(). "/$F{vendorid}");
        my $file_out = $C->specials_dir() . "/$F{vendorid}/${itemstr}.$photo_ext";
        open(IMAGEOUT,">$file_out") or die "Couldn't open $file_out for writing: $!\n";
        binmode(IMAGEOUT);
        flock(IMAGEOUT,LOCK_EX);
        while(read($fh,$buffer,1024)) {
          print IMAGEOUT $buffer;
        }
        flock(IMAGEOUT,LOCK_UN);
        close(IMAGEOUT);

        # now create a thumbnail
        create_thumbnail($file_out,$size_x,$size_y,$F{orientation});
        $query .= ",phto_ext";
        push(@params,$photo_ext);
      }
      $query .= ") VALUES (?,?,?,?,?,?,?";
      $query .= ",?" if defined($fh);
      $query .= ")";
      
      $sth = $C->db_query($query,\@params);
      $sth->finish();

      show_success("Internet Special ($F{'title'} item #: $F{'item_num'}) has been added to the database");
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
  $sth = $C->db_query("SELECT sid,title,vendorid,item_num,descr,price,manuf,qty,phto_ext,fp1,fp2 FROM specials");

  my @list_loop = ();
  while(my $row = $sth->fetchrow_hashref()) {
    my $itemstr = $C->sanitize_string($row->{item_num});
    delete($row->{fp1}) if($row->{fp1} != 1);
    delete($row->{fp2}) if($row->{fp2} != 1);
    $row->{price} = sprintf("\$%.2f",$row->{price});
    $row->{thumb} = $C->specials_dir_URL() . "/$row->{vendorid}/${itemstr}_thumb.$row->{phto_ext}";
    $row->{photo} = $C->specials_dir_URL() . "/$row->{vendorid}/${itemstr}.$row->{phto_ext}" if ($row->{phto_ext});
    $row->{vendorid} = $C->vendors()->{$row->{vendorid}};
    delete($row->{phto_ext});
    push(@list_loop, $row);
  }
  
  $sth->finish();
  show_view(\@list_loop);
}

#------------------------------------------------------------------------------
#
# Change History 
#
# 1. Changed call to create_thumbnail to take vendor id as arg - 2/28/06
# 2. Changed call to create_thumbnail to use orientation instead of vendor id
#    3.1.06 - jarnold
# 3. Added error checking for orientation. 3.1.06 - jarnold
# 4. Added BMP file support. 3.1.06 - jarnold
#------------------------------------------------------------------------------
sub do_modify {
  die "No ID passed to show_modify()" unless $F{'sid'};

  $sth = $C->db_query("SELECT vendorid,item_num,title,manuf,descr,price,qty,phto_ext FROM specials WHERE sid=?",[$F{'sid'}]);
  my ($vendorid,$item_num,$title,$manuf,$descr,$price,$qty,$photo_ext) = $sth->fetchrow();
  $sth->finish();  
  
  my $itemstr = $C->sanitize_string($item_num);
  my $thumb = $C->specials_dir_URL() . "/$vendorid/${itemstr}_thumb.$photo_ext";
  my $photo = $C->specials_dir_URL() . "/$vendorid/${itemstr}.$photo_ext";
  my $photopath = $C->specials_dir() . "/$vendorid/${itemstr}.$photo_ext";
  my $thumbpath = $C->specials_dir() . "/$vendorid/${itemstr}_thumb.$photo_ext";

  if(!defined($F{'update'})) {
    my %params = (
          vendors=> &mk_vendor_tmpl_obj(\$vendorid ),
          item_num=>$item_num,
          title=>$title,
          manuf=>$manuf,
          descr=>$descr,
          price=>$price,
          qty=>$qty,
          thumb=>$thumb,
          photo=>$photo,);
    show_modify(\%params);
  }
  else {
    my %error = ();

    # first deal with the photo.
    my $fh = $Q->upload('photo');
    my ($size_x,$size_y,$type);
    my $photo_ext;

    if(defined($fh)) {
      ($size_x,$size_y,$type) = imgsize($fh);
      if($type =~ /^(JPG|GIF|PNG|BMP)$/) {
        $photo_ext = lc($1);
      }
      else {
        $error{photo_error} = "Wrong photo type. Photos must be in JPEG (.jpg), GIF (.gif), BMP (.bmp) or PNG (.png) format";
      }
      unless(vrfy_string(\$F{'orientation'})) {
        $error{orient_error} = "You must select an image orientation from the radio buttons at the bottom of the screen";
      }
    }

    unless(vrfy_string(\$F{'title'})) {
      $error{title_error} = "Either you did not enter a title or it contained invalid characters";
    }  

    unless(vrfy_int(\$F{'vendorid'})) {
      $error{vendorid_error} = "You must enter a vendor";
    }

    $F{'item_num'} = uc($F{'item_num'});  
    unless(vrfy_string(\$F{'item_num'})) {
      $error{item_num_error} = "Please enter a valid item number";
    }
  
    unless(vrfy_string(\$F{'manuf'})) {
      $error{manuf_error} = "Either you did not enter a manufacturer or it contained invalid characters";
    }

    unless(vrfy_blob(\$F{'descr'})) {
      $error{descr_error} = "Either you did not enter a description or it contained invalid characters";
    }

    unless(vrfy_float(\$F{'price'})) {
      $error{price_error} = "Either you did not enter a price or it contained invalid characters";
    }

    unless(vrfy_int(\$F{'qty'})) {
      $error{qty_error} = "You must enter a quantity, (enter 0 for none)";
    }

    if(%error) {
      $error{'title'} = $F{'title'};
      $error{'vendorid'} = $F{'vendorid'};
      $error{'item_num'} = $F{'item_num'};
      $error{'manuf'} = $F{'manuf'};
      $error{'descr'} = $F{'descr'};
      $error{'price'} = $F{'price'};
      $error{'qty'} = $F{'qty'};
      $error{'thumb'} = $thumb;
      $error{'photo'} = $photo;
      $error{'sid'} = $F{'sid'};
      
      show_modify(\%error);
    }
    else {
      my $query = "UPDATE specials SET vendorid=?, item_num=?,title=?,manuf=?,descr=?,price=?,qty=?";
      my @params = ($F{'vendorid'}, $F{'item_num'},$F{'title'},$F{'manuf'},$F{'descr'},$F{'price'},$F{'qty'});
      
      # save image
      if(defined($fh)) {
        my $buffer;
        
        my $itemstr = $C->sanitize_string($F{item_num});
        mkdir($C->specials_dir(). "/$F{vendorid}") unless (-e $C->specials_dir(). "/$F{vendorid}");
        my $file_out = $C->specials_dir() . "/$F{vendorid}/${itemstr}.$photo_ext";
        open(IMAGEOUT,">$file_out") or die "Couldn't open $file_out for writing: $!\n";
        binmode(IMAGEOUT);
        flock(IMAGEOUT,LOCK_EX);
        while(read($fh,$buffer,1024)) {
          print IMAGEOUT $buffer;
        }
        flock(IMAGEOUT,LOCK_UN);
        close(IMAGEOUT);

        # now create a thumbnail
        create_thumbnail($file_out,$size_x,$size_y,$F{orientation});
        $query .= ",phto_ext=?";
        push(@params,$photo_ext);
      }

      $query .= " WHERE sid=?";
      push(@params,$F{'sid'});

      $sth = $C->db_query($query,\@params);
      $sth->finish();

      show_success("Internet Special $F{'title'} (item #: $F{'item_num'}) has been updated successfully");
    }
  }
}

#------------------------------------------------------------------------------
# Set up the parameters for the Specials Admin delete page.
# Change History:
#------------------------------------------------------------------------------
sub do_delete {
  die "No ID passed to delete\n" unless $F{'sid'};
  
  if(!defined($F{'confirm'})) {
    $sth = $C->db_query("SELECT title,vendorid,item_num,fp1,fp2 FROM specials WHERE sid=?",[$F{'sid'}]);
    my($title,$vendorid,$item_num,$fp1,$fp2) = $sth->fetchrow();
    my $warning;
    if($fp1 == 1 || $fp2 == 1) {
      $warning = "Warning: This item appears on the frontpage. If you delete this item a random special will appear in it's place";
    }

    my %params = (  sid=>$F{'sid'},
          title=>$title,
          vendor=> $C->vendors()->{$vendorid},
          item_num=>$item_num,
          warning=>$warning,);

    $sth->finish();
    show_delete(\%params);
  }
  else {
    my $query1 = "SELECT title,vendorid,item_num,phto_ext FROM specials WHERE sid=?";
    $sth = $C->db_query($query1,[$F{'sid'}]);
    my ($title,$vendorid,$item,$photo_ext) = $sth->fetchrow;
    $sth->finish;  

    # Just warn on these if they fail, it won't break the program
    # if they do (it will just leave the images on the server)

    &debug("F{item} = " . $F{item} . "  local var item = " . $item . "<br>");
    my $itemstr = $C->sanitize_string($item);
    &debug("itemstr = " . $itemstr . "<br>");
    my $image = $C->specials_dir . "/$vendorid/${itemstr}.$photo_ext";
    my $thumb = $C->specials_dir . "/$vendorid/${itemstr}_thumb.$photo_ext";

    unlink($image) or warn "Couldn't unlink $image: $!\n";
    unlink($thumb) or warn "Couldn't unlink $thumb: $!\n";
    
    my $query2 = "DELETE FROM specials WHERE sid=?";
    $sth = $C->db_query($query2,[$F{'sid'}]);
    $sth->finish();

    show_success("Internet Special $title (item #: $item) has been deleted from the database");
  }
}
    
#------------------------------------------------------------------------------
# Set the specials to be shown on the homepage
#------------------------------------------------------------------------------
sub do_set {
  # make sure someone isn't screwing around
  unless(vrfy_int(\$F{fp1})) {
    die "fp1 was not an integer!";
  }
  unless(vrfy_int(\$F{fp2})) {
    die "fp2 was not an integer!";
  }

  my $query1 = "UPDATE specials SET fp1=NULL, fp2=NULL WHERE fp1 IS NOT NULL OR fp2 IS NOT NULL";
  $sth = $C->db_query($query1);
  $sth->finish();

  my $query2 = "UPDATE specials SET fp1=? WHERE sid=?";
  $sth = $C->db_query($query2,[1,$F{'fp1'}]);
  $sth->finish();

  my $query3 = "UPDATE specials SET fp2=? WHERE sid=?";
  $sth = $C->db_query($query3,[1,$F{'fp2'}]);
  $sth->finish();

  do_view();
}

#------------------------------------------------------------------------------
# Create an orientation-based thumbnail for a new special
# Change History
# 1. Changed to use Imager instead of Image::Magick 2/26/06 - jarnold
# 2. Changed to accept vendorid as input for thumbnail size calculation 2/28/06
#    jarnold
# 3. Added .bmp filetype to list of handled file types - 2/28/06 - jarnold
# 4. Removed vendorid from arg list and added orientation. 2.28.06 - jarnold
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
# HTML::Template helper
# Change History:
# 1. 03.02.2006 - Changed to pull vendor info from the db instead of using the
#                 static Conf.pm hash - jarnold
#------------------------------------------------------------------------------
sub mk_vendor_tmpl_obj {
  my $selected = shift;
  $selected = \'' unless (defined $selected);

  my $query = 'select sid,name from vendor';
  my @dbp = ();
  $sth = $C->db_query($query,\@dbp);
  my @vendors = ();
  while (my $row = $sth->fetchrow_hashref()) {
    $row->{id} = $row->{sid};
    $row->{selected} = ($$selected eq $row->{id}) ? 1 : 0;
    delete($row->{sid});
    push(@vendors,$row);
  }
  return \@vendors;
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
