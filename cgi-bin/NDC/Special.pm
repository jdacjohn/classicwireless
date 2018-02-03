package NDC::Special;
##
## Special.pm - Specials Class
##
## Copyright (C) 2002 Bitstreet Internet
##
## $Id: Special.pm,v 1.2 2004/03/19 20:46:16 cameron Exp $

use lib '.';
use strict;
use NDC::Conf;
use Carp ();

###
sub new($%) {
  my ($class, %args) = @_;
  my $self = {};

  $self->{vendorid} = (defined $args{vendorid}) ? $args{vendorid} : '';
  $self->{item_num} = (defined $args{item_num}) ? $args{item_num} : '';
  $self->{title} = (defined $args{title}) ? $args{title} : '';
  $self->{manuf} = (defined $args{manuf}) ? $args{manuf} : '';
  $self->{price} = (defined $args{price}) ? $args{price} : '';
  $self->{descr} = (defined $args{descr}) ? $args{descr} : '';

  bless($self, $class);
  return $self;
}

###
sub load_by_sid($$) {
  my ($self, $sid) = @_;
  my $C = NDC::Conf->new();
  my $sth = $C->db_query('SELECT vendorid,item_num,title,manuf,price,descr '.
                         'FROM specials WHERE sid=?', [$sid]);

  ( $self->{vendorid},
    $self->{item_num},
    $self->{title},
    $self->{manuf},
    $self->{price},
    $self->{descr} ) = $sth->fetchrow_array();
  $sth->finish();
}

1;
# vim: set ts=2 et :
