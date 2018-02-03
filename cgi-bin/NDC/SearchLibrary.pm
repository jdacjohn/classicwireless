package NDC::SearchLibrary;
##
## NDC::SearchLibrary - Library search utilities
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: SearchLibrary.pm,v 1.2 2002/09/19 17:19:36 cameron Exp $

# I put this here because I want to use it with
# both library admin and view_library

use strict;
use Exporter;
use vars qw(@ISA @EXPORT);

@ISA = qw(Exporter);
@EXPORT = qw(&search_library);

sub search_library {
	my ($F,$query) = @_; # reference to global $F, and $query	

	unless($F->{search}) {
		return $query;
	}

	my $where;	
	$query .= " WHERE";
	my @words = parse_keywords($F->{search});
	foreach(@words) {	
		my $w = " item_num LIKE '\%$_%'";
		$w .= " OR manuf LIKE '\%$_%'";
		$w .= " OR title LIKE '\%$_%'";
		$w .= " OR descr LIKE '\%$_%'";
		$w .= " OR file LIKE '\%$_%'";
		$where .= " AND" if $where;
		$where .= " $w";
	}
	
	$query .= $where;
	return $query;
}

sub parse_keywords {
	my $string = shift;
	my @parts = ();
	
	while($string =~ /(["'])(.*?)\1/) {
		push(@parts,$2);
		my $tmp = $1.$2.$1;
		$string =~ s/$tmp//;
	}

	# remove extra spaces
	$string =~ s/\s{2,}/ /g;

	my @tmp2 = split(/ /,$string);
	push(@parts,@tmp2);

	my @return = ();
	foreach(@parts) {
		next unless /[A-Za-z0-9]/;
		push(@return,$_);
	}
	return(@return);
}


