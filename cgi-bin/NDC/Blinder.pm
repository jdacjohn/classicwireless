package NDC::Blinder;
#------------------------------------------------------------------------------
# Blinder.pm - Utilities for Simple String Encryption/Decryption
#
# Copyright (C) 2006 2k3 Technologies
#
# $Author: Jarnold $
# $Date: 4/05/06 10:11a $
# $Revision: 1 $
#
# change History:
# 04042006:  Initial Version - jarnold
#------------------------------------------------------------------------------

use lib '.';
use strict;
use CGI;

sub new { return bless {},__PACKAGE__ }

our $DEBUG = 0;
our $DEBUG_INIT = 0;
my $Q = CGI->new();

#------------------------------------------------------------------------------
# Generate a seed to be used in an encryption based on the
# input.
#
# Change History:  
# 04042006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub generate_seed {
  my ($self,$seedString) = @_;
  my @chars = split(//,$seedString);
  my $ord1 = ord(@chars[0]);
  my $ord2 = ord(@chars[length($seedString) - 1]);
  &debug("SeedString = " . $seedString . "\n");
  &debug("seedString.length = " . length($seedString) . "\n");
  &debug("Ord1 = " . $ord1 . "  Ord2 = " . $ord2 . "\n");
  
  my $sum = 0;
  foreach my $char (@chars) {
    $sum += ord($char);
  }
  &debug("Sum of Chars = " . $sum . "\n");
  
  my $modval = ($sum % length($seedString));
  &debug("modval = " . $modval . "\n");
  my $seed = $ord1 - $ord2 + $modval;
  &debug("Seed = " . $seed . "\n");
  return $seed;
}

#------------------------------------------------------------------------------
# Return an encrypted string
#
# Change History: 
# 04042006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub blind {
  my ($self,$inputStr,$seed) = @_;
  my $encrypt = '';
  my $length = length($inputStr);
  &debug("Length of String: " . $length . "\n");
  &debug("Input String = " . $inputStr . "\n");
  
  my @chars = split(//,reverse($inputStr));
  foreach my $char (@chars) {
    my $num = ord($char);
    my $newchar = chr($num + $seed);
    $encrypt .= $newchar;
  }
  
  return $encrypt;
}

#------------------------------------------------------------------------------
# Return an unencrypted string
#
# Change History:
# 04042006 - Initial Version - jarnold
#------------------------------------------------------------------------------
sub unblind {
  my ($self,$input,$seed) = @_;
  my @chars = split(//,$input);
  my $cleartext = '';
  
  foreach my $char (@chars) {
    my $num = ord($char);
    my $newnum = $num - $seed;
    my $newchar = chr($newnum);
    $cleartext = $cleartext . $newchar;
  }

  return reverse($cleartext);
  
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