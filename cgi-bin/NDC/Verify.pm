package NDC::Verify;
##
## NDC::Verify - Utilities functions for validating input
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Author: Jarnold $
## $Date: 3/20/06 4:57p $
## $Revision: 2 $
##
## Change History:
## 03.20.2006 - Modified vrfy_float to pass on values less than 1.0 that do not contain a leading 0 before the decimal. - jarnold

use strict;
use Exporter;

our @ISA = qw(Exporter);
our @EXPORT = qw(&vrfy_int &vrfy_float &vrfy_string &vrfy_word &vrfy_blob);

#sub new { return bless {},__PACKAGE__ }

sub vrfy_int {
	my $ref = shift;
	return 0 unless $$ref =~ /^(\d+)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_float {
	my $ref = shift;
	return 0 unless $$ref =~ /^(\d*(?:\.\d+)?)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_string {
	my $ref = shift;
	return 0 unless $$ref =~ /^([\x20-\x7f]+)$/;
	$$ref = $1;
	return 1;
}

sub vrfy_word {
	my $ref = shift;
	return 0 unless $$ref =~ /^([A-Za-z0-9\._\-]+)$/;
	$$ref = $1;
	return 1;
}

# pretty much the same as string but includes \n && \r
sub vrfy_blob {
	my $ref = shift;
	return 0 unless $$ref =~ /^([\x20-\x7f\n\r]+)$/;
	$$ref = $1;
	return 1;
}
	

1;
