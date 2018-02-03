package NDC::Import;
##
## Import.pm - Utilities for importing Excel spreadsheets into our database
##
## Copyright (C) Bitstreet Internet
##
## $Id: Import.pm,v 1.16 2004/03/22 19:47:08 cameron Exp $

use lib '.';
use strict;
use NDC::Conf;
use CGI::Carp qw(fatalsToBrowser);
use Spreadsheet::ParseExcel_XLHTML;


sub new { return bless {},__PACKAGE__ }

######################################################################
## vars ##############################################################
######################################################################

## path to upload directory where Excel files should be located
my $UPLOAD_DIR = '/home/classicwireless/upload';

## 
my $FILES = {
  'mobileportableradios.xls' => {
    desc  => 'New Mobile & Portable Radios',
    found => 0,
    age   => 'n',
    cat   => '1',
  },
  'usedmobilesportablesfile.xls' => {
    desc  => 'Used Mobile & Portable Radios',
    found => 0,
    age   => 'u',
    cat   => '1',
  },
  'pagerfile.xls' => {
    desc  => 'New Pagers',
    found => 0,
    age   => 'n',
    cat   => '2',
  },
  'usedpagerfile.xls' => {
    desc  => 'Used Pagers',
    found => 0,
    age   => 'u',
    cat   => '2',
  },
  'programsfile.xls' => {
    desc  => 'New Programs',
    found => 0,
    age   => 'n',
    cat   => '3',
  },
  'usedprogramsfile.xls' => {
    desc  => 'Used Programs',
    found => 0,
    age   => 'u',
    cat   => '3',
  },
  'repairfile.xls' => {
    desc  => 'New Repairs',
    found => 0,
    age   => 'n',
    cat   => '4',
  },
  'usedrepairfile.xls' => {
    desc  => 'Used Repairs',
    found => 0,
    age   => 'u',
    cat   => '4',
  },
  'speakerfile.xls' => {
    desc  => 'New Speakers',
    found => 0,
    age   => 'n',
    cat   => '5',
  },
  'usedspeakerfile.xls' => {
    desc  => 'Used Speakers',
    found => 0,
    age   => 'u',
    cat   => '5',
  },
  'accessoriesfile.xls' => {
    desc  => 'New Accessories',
    found => 0,
    age   => 'n',
    cat   => '6',
  },
  'usedaccessoriesfile.xls' => {
    desc  => 'Used Accessories',
    found => 0,
    age   => 'u',
    cat   => '6',
  },
  'antennafile.xls' => {
    desc  => 'New Antennas',
    found => 0,
    age   => 'n',
    cat   => '7',
  },
  'usedantennafile.xls' => {
    desc  => 'Used Antennas',
    found => 0,
    age   => 'u',
    cat   => '7',
  },
  'assemblyfile.xls' => {
    desc  => 'New Assembly',
    found => 0,
    age   => 'n',
    cat   => '8',
  },
  'usedassemblyfile.xls' => {
    desc  => 'Used Assembly',
    found => 0,
    age   => 'u',
    cat   => '8',
  },
  'batteriesfile.xls' => {
    desc  => 'New Batteries',
    found => 0,
    age   => 'n',
    cat   => '9',
  },
  'usedbatteriesfile.xls' => {
    desc  => 'Used Batteries',
    found => 0,
    age   => 'u',
    cat   => '9',
  },
  'casefile.xls' => {
    desc  => 'New Cases',
    found => 0,
    age   => 'n',
    cat   => '10',
  },
  'usedcasefile.xls' => {
    desc  => 'Used Cases',
    found => 0,
    age   => 'u',
    cat   => '10',
  },
  'chargersfile.xls' => {
    desc  => 'New Chargers',
    found => 0,
    age   => 'n',
    cat   => '11',
  },
  'usedchargersfile.xls' => {
    desc  => 'Used Chargers',
    found => 0,
    age   => 'u',
    cat   => '11',
  },
  'installsfile.xls' => {
    desc  => 'New Installs',
    found => 0,
    age   => 'n',
    cat   => '12',
  },
  'usedinstallsfile.xls' => {
    desc  => 'Used Installs',
    found => 0,
    age   => 'u',
    cat   => '12',
  },
  'microphonefile.xls' => {
    desc  => 'New Microphones',
    found => 0,
    age   => 'n',
    cat   => '13',
  },
  'usedmicrophonefile.xls' => {
    desc  => 'Used Microphones',
    found => 0,
    age   => 'u',
    cat   => '13',
  },
  'otherequipmentfile.xls' => {
    desc  => 'New Other Equipment',
    found => 0,
    age   => 'n',
    cat   => '14',
  },
  'usedotherequipmentfile.xls' => {
    desc  => 'Used Other Equipment',
    found => 0,
    age   => 'u',
    cat   => '14',
  },
  'combinersfile.xls' => {
    desc  => 'New Combiners',
    found => 0,
    age   => 'n',
    cat   => '15',
  },
  'usedcombinersfile.xls' => {
    desc  => 'Used Combiners',
    found => 0,
    age   => 'u',
    cat   => '15',
  },
  'combiningequipmentfile.xls' => {
    desc  => 'New Combining Equipment',
    found => 0,
    age   => 'n',
    cat   => '16',
  },
  'usedcombiningequipmentfile.xls' => {
    desc  => 'Used Combining Equipment',
    found => 0,
    age   => 'u',
    cat   => '16',
  },
  'microwavefile.xls' => {
    desc  => 'New Microwaves',
    found => 0,
    age   => 'n',
    cat   => '17',
  },
  'usedmicrowavefile.xls' => {
    desc  => 'Used Microwaves',
    found => 0,
    age   => 'u',
    cat   => '17',
  },
  'multicouplersfile.xls' => {
    desc  => 'New Multicoupliers',
    found => 0,
    age   => 'n',
    cat   => '18',
  },
  'usedmulticouplersfile.xls' => {
    desc  => 'Used Multicoupliers',
    found => 0,
    age   => 'u',
    cat   => '18',
  },
  'powersuppliesfile.xls' => {
    desc  => 'New Power Supplies',
    found => 0,
    age   => 'n',
    cat   => '19',
  },
  'usedpowersuppliesfile.xls' => {
    desc  => 'Used Power Supplies',
    found => 0,
    age   => 'u',
    cat   => '19',
  },
  'usedpowersuppliesfile.xls' => {
    desc  => 'Used Power Supplies',
    found => 0,
    age   => 'u',
    cat   => '19',
  },
  'repeatersfile.xls' => {
    desc  => 'New Repeaters',
    found => 0,
    age   => 'n',
    cat   => '20',
  },
  'usedrepeatersfile.xls' => {
    desc  => 'Used Repeaters',
    found => 0,
    age   => 'u',
    cat   => '20',
  },
  'bracketsfile.xls' => {
    desc  => 'New Brackets',
    found => 0,
    age   => 'n',
    cat   => '21',
  },
  'usedbracketsfile.xls' => {
    desc  => 'Used Brackets',
    found => 0,
    age   => 'u',
    cat   => '21',
  },
  'batteryeliminatorsfile.xls' => {
    desc  => 'New Battery Eliminators',
    found => 0,
    age   => 'n',
    cat   => '22',
  },
  'usedbatteryeliminatorsfile.xls' => {
    desc  => 'Used Battery Eliminators',
    found => 0,
    age   => 'u',
    cat   => '22',
  },
  'speakermicrophonesfile.xls' => {
    desc  => 'New Speaker Microphones',
    found => 0,
    age   => 'n',
    cat   => '25',
  },
  'usedspeakermicrophonesfile.xls' => {
    desc  => 'Used Speaker Microphones',
    found => 0,
    age   => 'u',
    cat   => '25',
  },
  'radiohousingkitsfile.xls' => {
    desc  => 'New Radio Housing Kits',
    found => 0,
    age   => 'n',
    cat   => '26',
  },
  'usedradiohousingkitsfile.xls' => {
    desc  => 'Used Radio Housing Kits',
    found => 0,
    age   => 'u',
    cat   => '26',
  },
  'handsfreekitsfile.xls' => {
    desc  => 'New Hands Free Kits',
    found => 0,
    age   => 'n',
    cat   => '27',
  },
  'usedhandsfreekitsfile.xls' => {
    desc  => 'Used Hands Free Kits',
    found => 0,
    age   => 'u',
    cat   => '27',
  },
  'advancecommunicatorsfile.xls' => {
    desc  => 'New Advance Communicators',
    found => 0,
    age   => 'n',
    cat   => '28',
  },
  'usedadvancecommunicatorsfile.xls' => {
    desc  => 'Used Advance Communicators',
    found => 0,
    age   => 'u',
    cat   => '28',
  },
  'poweramplifiersfile.xls' => {
    desc  => 'New Power Amplifiers',
    found => 0,
    age   => 'n',
    cat   => '29',
  },
  'usedpoweramplifiersfile.xls' => {
    desc  => 'Used Power Amplifiers',
    found => 0,
    age   => 'u',
    cat   => '29',
  },
  'powermonitorfile.xls' => {
    desc  => 'New Power Monitors',
    found => 0,
    age   => 'n',
    cat   => '30',
  },
  'usedpowermonitorfile.xls' => {
    desc  => 'Used Power Monitors',
    found => 0,
    age   => 'u',
    cat   => '30',
  },
  'powerprotectionfile.xls' => {
    desc  => 'New Power Protection',
    found => 0,
    age   => 'n',
    cat   => '31',
  },
  'usedpowerprotectionfile.xls' => {
    desc  => 'Used Power Protection',
    found => 0,
    age   => 'u',
    cat   => '31',
  },
  'controllersfile.xls' => {
    desc  => 'New Controllers',
    found => 0,
    age   => 'n',
    cat   => '32',
  },
  'usedcontrollersfile.xls' => {
    desc  => 'Used Controllers',
    found => 0,
    age   => 'u',
    cat   => '32',
  },
  'connectorsfile.xls' => {
    desc  => 'New Connectors',
    found => 0,
    age   => 'n',
    cat   => '33',
  },
  'usedconnectorsfile.xls' => {
    desc  => 'Used Connectors',
    found => 0,
    age   => 'u',
    cat   => '33',
  },
  'towermiscfile.xls' => {
    desc  => 'New Tower Miscellaneous',
    found => 0,
    age   => 'n',
    cat   => '34',
  },
  'usedtowermiscfile.xls' => {
    desc  => 'Used Tower Miscellaneous',
    found => 0,
    age   => 'u',
    cat   => '34',
  },
  'groundingfile.xls' => {
    desc  => 'New Grounding',
    found => 0,
    age   => 'n',
    cat   => '35',
  },
  'usedgroundingfile.xls' => {
    desc  => 'Used Grounding',
    found => 0,
    age   => 'u',
    cat   => '35',
  },
  'nextelmiscfile.xls' => {
    desc  => 'New Nextel Miscellaneous',
    found => 0,
    age   => 'n',
    cat   => '36',
  },
  'usednextelmiscfile.xls' => {
    desc  => 'Used Nextel Miscellaneous',
    found => 0,
    age   => 'u',
    cat   => '36',
  },
  'testequipmentfile.xls' => {
    desc  => 'New Test Equipment',
    found => 0,
    age   => 'n',
    cat   => '37',
  },
  'usedtestequipmentfile.xls' => {
    desc  => 'Used Test Equipment',
    found => 0,
    age   => 'u',
    cat   => '37',
  },
};

######################################################################
## subs ##############################################################
######################################################################

######################################################################
sub process_xls {
  my ($class, $file_ref) = @_;
  my %data = ();
  my ($vendr, $itemn, $descr, $manuf, $quant, $price, $format);
  my $C = NDC::Conf->new();

  die "$$file_ref does not exist" unless (-e "$UPLOAD_DIR/$$file_ref");
  my $xls = new Spreadsheet::ParseExcel_XLHTML;

# Debug statement
#show_error("PATH = ".$ENV{'PATH'});

  my $book = $xls->Parse("$UPLOAD_DIR/$$file_ref");
  for my $sheet (@{$book->{Worksheet}}) {
    ## delete all records for this category from existing table
    my $sth = $C->db_query(
          'DELETE FROM products WHERE age=? AND category=?',
          [ $FILES->{$$file_ref}->{"age"}, $FILES->{$$file_ref}->{"cat"} ] );
    $sth->finish();

    for my $i ($sheet->{MinRow}..$sheet->{MaxRow}) {
      next unless ($i); # skip first line / header
      next unless (
        defined $sheet->{Cells}[$i][0] &&
        defined $sheet->{Cells}[$i][1] &&
        defined $sheet->{Cells}[$i][2] &&
        defined $sheet->{Cells}[$i][3] &&
        defined $sheet->{Cells}[$i][4] );
      ## clean up input
      ($vendr = $sheet->{Cells}[$i][0]->Value()) =~ s/^\s*(.*)\s*$/$1/;
      ($itemn = $sheet->{Cells}[$i][1]->Value()) =~ s/^\s*(.*)\s*$/$1/;
      ($descr = $sheet->{Cells}[$i][2]->Value()) =~ s/^\s*(.*)\s*$/$1/;
      ($manuf = $sheet->{Cells}[$i][3]->Value()) =~ s/^\s*(.*)\s*$/$1/;
      ($quant = $sheet->{Cells}[$i][4]->Value()) =~ s/^\s*(.*)\s*$/$1/;
      ($price = $sheet->{Cells}[$i][5]->Value()) =~ s/[\$,]//g;
      $format = (defined $sheet->{Cells}[$i][6]) ? $sheet->{Cells}[$i][6]->Value() : '';

      $sth = $C->db_query(
        'INSERT INTO products (vendorid,item_num,descr,manuf,quantity,price,'.
        'format,age,category) VALUES (?,?,?,?,?,?,?,?,?)',
        [ $vendr, uc($itemn), $descr, $manuf, $quant, $price, $format,
        $FILES->{$$file_ref}->{"age"}, $FILES->{$$file_ref}->{"cat"}, ] );
      $sth->finish();
    }
  }
}

######################################################################
sub get_check_tmpl_obj {
  my ($self) = shift;
  ## pass 1 to run &locate_files
  &locate_files() if (shift);

  my @tmp;
  foreach my $f (sort keys %$FILES) {
    my %row = (
      desc  => $FILES->{$f}->{'desc'},
      found => $FILES->{$f}->{'found'},
    );
    push @tmp, \%row;
  }
  return \@tmp;
}

######################################################################
## locate $FILES and update ->{found} value
sub locate_files {
  &clean_files();
  foreach my $f (keys %$FILES) {
    $FILES->{$f}->{'found'} = (-e "$UPLOAD_DIR/$f");
  }
}

######################################################################
## remove & chars from filenames
sub clean_files {
  opendir(DIR, $UPLOAD_DIR) || die "can't open upload directory: $!";
  foreach my $f (grep { /xls$/i } readdir(DIR)) {
    (my $n = $f) =~ s/&//g;
    next unless ($f ne $n);
    die "Invalid filename" unless $f =~ m/^([a-zA-Z.&-]+)$/; $f = $1;
    die "Invalid filename" unless $n =~ m/^([a-zA-Z.-]+)$/; $n = $1;
    rename "$UPLOAD_DIR/$f", "$UPLOAD_DIR/$n";
  }
  closedir(DIR);
}

######################################################################
sub get_files { return $FILES; }

######################################################################
sub set_files_found {
  my ($self, $ref) = @_;
  foreach my $f (keys %$ref) {
    $FILES->{$f}->{'found'} = $ref->{$f}->{'found'}  if ( $FILES->{$f} );
  }
}

######################################################################
sub unlink_xls {
  my ($class, $ref) = @_;
  unlink("$UPLOAD_DIR/$$ref");
}

##
sub show_error {
  my $C = NDC::Conf->new();
  my $Q = new CGI;
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();
  exit;
}

1;
# vim: set ts=2 et :
