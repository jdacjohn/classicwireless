#!/usr/bin/perl -T
##
## search_products.cgi - Product search script
##
## Copyright (C) 2002 Bitstreet Internet
## 
## $Id: search_products.cgi,v 1.10 2004/03/22 04:07:19 cameron Exp $

use strict;
use lib '.';
use NDC::Conf;
use NDC::Verify;
use CGI;
use HTML::Template;
use DBI;
use CGI::Carp 'fatalsToBrowser';
use URI::Escape;

my $C = new NDC::Conf;
my $Q = new CGI;
my %F = $Q->Vars();
my $sth;

our $DEBUG = 0;
our $DEBUG_INIT = 0;

my %modes = (
  search=>\&do_search,
  default=>\&do_default,
);

if(exists($modes{$F{'mode'}})) {
  $modes{$F{'mode'}}->();
}
else {
  $modes{default}->();
}

db_disconnect();
exit;

##############################################
## subs

sub do_default {
  # Used Products:
  my $query = "SELECT DISTINCT category FROM products WHERE item_num LIKE '%.U'";
  $sth = $C->db_query($query);

  my $dbh = $C->db_connect();
  my $query3 = "SELECT name FROM categories WHERE sid=?";
  my $sth2 = $dbh->prepare($query3);
  
  my @used = ();
  my @usednames = ();
  while(my $row = $sth->fetchrow_hashref()) {
    my $row2 = {};
    $sth2->execute($row->{category}) or die $sth2->errstr;
    $row2->{name} = $sth2->fetchrow();
    push(@used,$row);
    push(@usednames,$row2);
  }
  $sth->finish();

  # new products
  my $query2 = "SELECT DISTINCT category FROM products WHERE item_num NOT LIKE '%.U'";
  $sth = $C->db_query($query2);

  my @new = ();
  my @newnames = ();
  while(my $row = $sth->fetchrow_hashref()) {
    my $row2 = {};
    $sth2->execute($row->{category}) or die $sth2->errstr;
    $row2->{name} = $sth2->fetchrow();
    push(@new,$row);
    push(@newnames,$row2);
  }
  $sth->finish();
  $sth2->finish();
  $dbh->disconnect();

  show_default(\@used,\@new,\@usednames,\@newnames);
}

#------------------------------------------------------------------------------
# Get results to display for product search.
# Change History:
# 1. Added code to correctly build image and thumb filenames from item_num
#    values to match those built during admin add specials operations.
#    3.2.06 - jarnold
#------------------------------------------------------------------------------
sub do_search {
  # Check for sections and categories
  my $section = $F{'section'} || 'all';
  
  my $searchparams = "section=$section";

  my @categories = $Q->param('categories');

  # Check for bad characters j00 d0nt 0\/\/n m3 k1dd13z!
  my $msg = "Passed invalid character, quiting";
  if($F{'section'}) {
    vrfy_string(\$F{'section'}) or show_error($msg);
  }
  
  if($F{'keywords'}) {
    vrfy_blob(\$F{'keywords'}) or show_error($msg);
  }

  my $query = "SELECT products.vendorid,products.item_num,categories.name,products.manuf,products.quantity,products.price,products.descr,products.format FROM products,categories WHERE";
  
  my @params = ();
  my $where = " categories.sid=products.category";
  
  if($section eq 'used') {
    $where .= " AND item_num LIKE '%.U'";
  }
  elsif($section eq 'new') {
    $where .= " AND item_num NOT LIKE '%.U'";
  }

  # Broken - should be using OR, not AND.  Results in an empty set when more than
  # one category is selected.  fixed - jarnold 12012005
  if(@categories && !grep(/^all$/,@categories)) {
    $where .= " AND (";
    my $limit = scalar(@categories) - 1;
    my $ndx = 0;
    my $cat = "";
    for($ndx=0; $ndx <$ limit; $ndx++) {
      $cat = @categories[$ndx];
      vrfy_string(\$cat) or show_error($msg); # just in case.
      $searchparams .= "&amp;categories=$cat";
      $where .= " category=? OR ";
      push(@params,$cat);
    }
    $cat = @categories[$limit];
    $searchparams .= "&amp;categories=$cat";
    $where .= " category=?)";
    push(@params,$cat);
  }

  if($F{'keywords'}) {
    my $safe = uri_escape($F{'keywords'});
    $searchparams .= "&amp;keywords=$safe";

    # set up where clauses for both the description and the 
    # manufacturer

    
    # split up keywords if it appears to have words
    # separated by spaces
  
    if($F{keywords} =~ /\w+\s\w+/) {
      my $descrclause = "";
      my $manufclause = "";
      
      my @keys = parse_keywords($F{keywords});
      foreach(@keys) {
        $descrclause .= " AND descr LIKE '\%$_%'";
        $manufclause .= " AND manuf LIKE '\%$_%'";
      }
      $descrclause = $where . $descrclause;
      $manufclause = $where . $manufclause;
      push(@params,@params);
      $where = "$descrclause OR $manufclause";

    }
    else {    
      my $desc_key = " AND descr LIKE '\%$F{keywords}%'";
      my $manuf_key = " AND manuf LIKE '\%$F{keywords}%'";
      my $item_key = " AND item_num LIKE '\%$F{keywords}%'";

      $desc_key = $where . $desc_key;
      $manuf_key = $where . $manuf_key;
      $item_key = $where . $item_key;

      $where = "$desc_key OR $manuf_key OR $item_key";
      
      push(@params,@params,@params);
    }
  }
  
  $query .= $where;

  # set up the page stuff
  my $start = $F{'s'} || 0;
  $query .= " LIMIT $start, " . $C->rpp();

  # get the total rows in the products table
  my $countquery = "SELECT COUNT(*) FROM products,categories";
  $countquery .= " WHERE$where"; # just needed a param.

  $sth = $C->db_query($countquery,\@params);
  my $total_rows = $sth->fetchrow();
  $sth->finish;

  # Cameron I know you hate this but I need a dbh here so I can cache these
  # queries through the while loop.
  # it sets $DBH in the Conf package so it should use the same connection again later
  
  $NDC::Conf::DBH = $C->db_connect() unless $NDC::Conf::DBH;
  my $dbh = \$NDC::Conf::DBH;

  my $specials_query = 'SELECT sid,phto_ext FROM specials WHERE item_num=? AND vendorid=?';
  my $specials_sth = $$dbh->prepare($specials_query);

  my $lib_query = "SELECT sid FROM library WHERE item_num=? LIMIT 1";
  my $lib_sth = $$dbh->prepare($lib_query);

  &debug("Query for Product Search = " . $query . "<br>");
  $sth = $C->db_query($query,\@params);

  my @output = ();
  while(my $row = $sth->fetchrow_hashref()) {
    $specials_sth->execute($row->{'item_num'}, $row->{vendorid}) or die $specials_sth->errstr;
    ($$row{specialsid},$$row{photo_ext}) = $specials_sth->fetchrow(); # there can be only one 

    ## See if there are any library docs available for this item
    $lib_sth->execute($row->{'item_num'}) or die $lib_sth->errstr;    
    $row->{specdocs} = ($lib_sth->fetchrow()) ? 1 : 0;

    $row->{category} = $row->{name};
    $row->{used} = 1 if $row->{item_num} =~ /^.+\.U$/;
    $row->{price} = ($row->{price}) ? sprintf("\$%.2f",$row->{price}) : 'Market Value';
    $row->{vendor} = $C->vendors()->{ $row->{vendorid} };
    #Get rid of any spaces in the item_num so the thumbnail and image can actually be found.
    my $fixed_item_num = $C->sanitize_string($row->{item_num});
    &debug("Item Number = " . $row->{item_num} . "<br>");
    &debug("Thumb & Image files = " . $fixed_item_num . "<br>");
    $row->{file_pref} = $fixed_item_num;
    # Added the following replacement to get the description to break better across lines - jda 12012005
    #$row->{descr} =~ s$/$ * $g;

    delete($row->{name});
    push(@output,$row);
  }
  $lib_sth->finish();
  $specials_sth->finish();
  $sth->finish();
  

  my $next = $start + $C->rpp();
  my $prev = $start - $C->rpp();

  # don't get a previous out of range
  $prev = 0 unless $prev > -1;
  
  my $show_prev = 1 unless $start == 0;
  my $show_next = 1 unless $next > $total_rows;

  my $numpages = int($total_rows / $C->rpp());
  if($total_rows % $C->rpp()) {
    $numpages ++;
  }

  #page loop
  my @pages = ();

  #what page are we on?
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
    push(@pages,{s=>$C->rpp() * $count,page=>$_,searchparams=>$searchparams,tp=>$tp});
    $count ++;
  }

  show_search(\@output,\@pages,{'next'=>$next,'prev'=>$prev,show_next=>$show_next,show_prev=>$show_prev,searchparams=>$searchparams,totalrows=>$total_rows});
}

##
sub show_default {
  my ($used,$new,$usednames,$newnames) = @_;

  my $template = $C->tmpl('search',{loop_context_vars=>1});
  $template->param(  used=>$used,
            new=>$new,
            usedname=>$usednames,
            newnames=>$newnames,
          );
  print $Q->header();
  print $template->output();
}

## 
sub show_search {
  my ($output,$pages,$params) = @_;
  
  my $template = $C->tmpl('search_results');
  $template->param(  results=>$output,
            pages=>$pages,
            %$params);
  print $Q->header();
  print $template->output();
}

##
sub show_error {
  my $msg = shift;
  my $template = $C->tmpl('error_user');
  $template->param(msg=>$msg);
  print $Q->header();
  print $template->output();

  db_disconnect();
  exit;
}

##
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

##
sub db_disconnect {
  $NDC::Conf::DBH->disconnect() if $NDC::Conf::DBH;
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
