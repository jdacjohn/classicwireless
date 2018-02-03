package NDC::Order;
##
## Order.pm - Utilities for online ordering
##
## Copyright (C) Bitstreet Internet
##
## $Id: Order.pm,v 1.4 2004/03/22 05:04:44 cameron Exp $

use lib '.';
use strict;
use CGI::Carp qw(fatalsToBrowser);
use CGI qw(-no_xhtml);
use NDC::Conf;

sub new { return bless {},__PACKAGE__ }

######################################################################
## vars ##############################################################
######################################################################
my $runmode = NDC::Conf->run_mode();
my $DEBUG_INIT = 0;
my $DEBUG = 1;
my $Q = CGI->new();

our @COUNTRY_VALUES = qw(
    AD AE AF AG AI AL AM AN AO AQ AR AS AT AU AW AZ BA BB BD BE BF BG BH BI BJ
    BM BN BO BR BS BT BV BW BY BZ CA CC CF CG CH CI CK CL CM CN CO CR CS CU CV
    CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR FX GA GB
    GD GE GF GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL
    IN IO IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK
    LR LS LT LU LV LY MA MC MD MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX
    MY MZ NA NC NE NF NG NI NL NO NP NR NT NU NZ OM PA PE PF PG PH PK PL PM PN
    PR PT PW PY QA RE RO RU RW SA Sb SC SD SE SG SH SI SJ SK SL SM SN SO SR ST
    SU SV SY SZ TC TD TF TG TH TJ TK TM TN TO TP TR TT TV TW TZ UA UG UK UM US
    UY UZ VA VC VE VG VI VN VU WF WS YE YT YU ZA ZM ZR ZW );

our $COUNTRY_LABELS = {
		'AD'	=>	q|Andorra|,
		'AE'	=>	q|United Arab Emirates|,
		'AF'	=>	q|Afghanistan|,
		'AG'	=>	q|Antigua and Barbuda|,
		'AI'	=>	q|Anguilla|,
		'AL'	=>	q|Albania|,
		'AM'	=>	q|Armenia|,
		'AN'	=>	q|Netherlands Antilles|,
		'AO'	=>	q|Angola|,
		'AQ'	=>	q|Antarctica|,
		'AR'	=>	q|Argentina|,
		'AS'	=>	q|American Samoa|,
		'AT'	=>	q|Austria|,
		'AU'	=>	q|Australia|,
		'AW'	=>	q|Aruba|,
		'AZ'	=>	q|Azerbaijan|,
		'BA'	=>	q|Bosnia and Herzegovina|,
		'BB'	=>	q|Barbados|,
		'BD'	=>	q|Bangladesh|,
		'BE'	=>	q|Belgium|,
		'BF'	=>	q|Burkina Faso|,
		'BG'	=>	q|Bulgaria|,
		'BH'	=>	q|Bahrain|,
		'BI'	=>	q|Burundi|,
		'BJ'	=>	q|Benin|,
		'BM'	=>	q|Bermuda|,
		'BN'	=>	q|Brunei Darussalam|,
		'BO'	=>	q|Bolivia|,
		'BR'	=>	q|Brazil|,
		'BS'	=>	q|Bahamas|,
		'BT'	=>	q|Bhutan|,
		'BV'	=>	q|Bouvet Island|,
		'BW'	=>	q|Botswana|,
		'BY'	=>	q|Belarus|,
		'BZ'	=>	q|Belize|,
		'CA'	=>	q|Canada|,
		'CC'	=>	q|Cocos (Keeling) Islands|,
		'CF'	=>	q|Central African Republic|,
		'CG'	=>	q|Congo|,
		'CH'	=>	q|Switzerland|,
		'CI'	=>	q|Cote D'Ivoire (Ivory Coast)|,
		'CK'	=>	q|Cook Islands|,
		'CL'	=>	q|Chile|,
		'CM'	=>	q|Cameroon|,
		'CN'	=>	q|China|,
		'CO'	=>	q|Colombia|,
		'CR'	=>	q|Costa Rica|,
		'CS'	=>	q|Czechoslovakia (former)|,
		'CU'	=>	q|Cuba|,
		'CV'	=>	q|Cape Verde|,
		'CX'	=>	q|Christmas Island|,
		'CY'	=>	q|Cyprus|,
		'CZ'	=>	q|Czech Republic|,
		'DE'	=>	q|Germany|,
		'DJ'	=>	q|Djibouti|,
		'DK'	=>	q|Denmark|,
		'DM'	=>	q|Dominica|,
		'DO'	=>	q|Dominican Republic|,
		'DZ'	=>	q|Algeria|,
		'EC'	=>	q|Ecuador|,
		'EE'	=>	q|Estonia|,
		'EG'	=>	q|Egypt|,
		'EH'	=>	q|Western Sahara|,
		'ER'	=>	q|Eritrea|,
		'ES'	=>	q|Spain|,
		'ET'	=>	q|Ethiopia|,
		'FI'	=>	q|Finland|,
		'FJ'	=>	q|Fiji|,
		'FK'	=>	q|Falkland Islands (Malvinas)|,
		'FM'	=>	q|Micronesia|,
		'FO'	=>	q|Faroe Islands|,
		'FR'	=>	q|France|,
		'FX'	=>	q|France, Metropolitan|,
		'GA'	=>	q|Gabon|,
		'GB'	=>	q|Great Britain (UK)|,
		'GD'	=>	q|Grenada|,
		'GE'	=>	q|Georgia|,
		'GF'	=>	q|French Guiana|,
		'GH'	=>	q|Ghana|,
		'GI'	=>	q|Gibraltar|,
		'GL'	=>	q|Greenland|,
		'GM'	=>	q|Gambia|,
		'GN'	=>	q|Guinea|,
		'GP'	=>	q|Guadeloupe|,
		'GQ'	=>	q|Equatorial Guinea|,
		'GR'	=>	q|Greece|,
		'GS'	=>	q|S. Georgia and S. Sandwich Isls.|,
		'GT'	=>	q|Guatemala|,
		'GU'	=>	q|Guam|,
		'GW'	=>	q|Guinea-Bissau|,
		'GY'	=>	q|Guyana|,
		'HK'	=>	q|Hong Kong|,
		'HM'	=>	q|Heard and McDonald Islands|,
		'HN'	=>	q|Honduras|,
		'HR'	=>	q|Croatia (Hrvatska)|,
		'HT'	=>	q|Haiti|,
		'HU'	=>	q|Hungary|,
		'ID'	=>	q|Indonesia|,
		'IE'	=>	q|Ireland|,
		'IL'	=>	q|Israel|,
		'IN'	=>	q|India|,
		'IO'	=>	q|British Indian Ocean Territory|,
		'IQ'	=>	q|Iraq|,
		'IR'	=>	q|Iran|,
		'IS'	=>	q|Iceland|,
		'IT'	=>	q|Italy|,
		'JM'	=>	q|Jamaica|,
		'JO'	=>	q|Jordan|,
		'JP'	=>	q|Japan|,
		'KE'	=>	q|Kenya|,
		'KG'	=>	q|Kyrgyzstan|,
		'KH'	=>	q|Cambodia|,
		'KI'	=>	q|Kiribati|,
		'KM'	=>	q|Comoros|,
		'KN'	=>	q|Saint Kitts and Nevis|,
		'KP'	=>	q|Korea (North)|,
		'KR'	=>	q|Korea (South)|,
		'KW'	=>	q|Kuwait|,
		'KY'	=>	q|Cayman Islands|,
		'KZ'	=>	q|Kazakhstan|,
		'LA'	=>	q|Laos|,
		'LB'	=>	q|Lebanon|,
		'LC'	=>	q|Saint Lucia|,
		'LI'	=>	q|Liechtenstein|,
		'LK'	=>	q|Sri Lanka|,
		'LR'	=>	q|Liberia|,
		'LS'	=>	q|Lesotho|,
		'LT'	=>	q|Lithuania|,
		'LU'	=>	q|Luxembourg|,
		'LV'	=>	q|Latvia|,
		'LY'	=>	q|Libya|,
		'MA'	=>	q|Morocco|,
		'MC'	=>	q|Monaco|,
		'MD'	=>	q|Moldova|,
		'MG'	=>	q|Madagascar|,
		'MH'	=>	q|Marshall Islands|,
		'MK'	=>	q|Macedonia|,
		'ML'	=>	q|Mali|,
		'MM'	=>	q|Myanmar|,
		'MN'	=>	q|Mongolia|,
		'MO'	=>	q|Macau|,
		'MP'	=>	q|Northern Mariana Islands|,
		'MQ'	=>	q|Martinique|,
		'MR'	=>	q|Mauritania|,
		'MS'	=>	q|Montserrat|,
		'MT'	=>	q|Malta|,
		'MU'	=>	q|Mauritius|,
		'MV'	=>	q|Maldives|,
		'MW'	=>	q|Malawi|,
		'MX'	=>	q|Mexico|,
		'MY'	=>	q|Malaysia|,
		'MZ'	=>	q|Mozambique|,
		'NA'	=>	q|Namibia|,
		'NC'	=>	q|New Caledonia|,
		'NE'	=>	q|Niger|,
		'NF'	=>	q|Norfolk Island|,
		'NG'	=>	q|Nigeria|,
		'NI'	=>	q|Nicaragua|,
		'NL'	=>	q|Netherlands|,
		'NO'	=>	q|Norway|,
		'NP'	=>	q|Nepal|,
		'NR'	=>	q|Nauru|,
		'NT'	=>	q|Neutral Zone|,
		'NU'	=>	q|Niue|,
		'NZ'	=>	q|New Zealand (Aotearoa)|,
		'OM'	=>	q|Oman|,
		'PA'	=>	q|Panama|,
		'PE'	=>	q|Peru|,
		'PF'	=>	q|French Polynesia|,
		'PG'	=>	q|Papua New Guinea|,
		'PH'	=>	q|Philippines|,
		'PK'	=>	q|Pakistan|,
		'PL'	=>	q|Poland|,
		'PM'	=>	q|St. Pierre and Miquelon|,
		'PN'	=>	q|Pitcairn|,
		'PR'	=>	q|Puerto Rico|,
		'PT'	=>	q|Portugal|,
		'PW'	=>	q|Palau|,
		'PY'	=>	q|Paraguay|,
		'QA'	=>	q|Qatar|,
		'RE'	=>	q|Reunion|,
		'RO'	=>	q|Romania|,
		'RU'	=>	q|Russian Federation|,
		'RW'	=>	q|Rwanda|,
		'SA'	=>	q|Saudi Arabia|,
		'Sb'	=>	q|Solomon Islands|,
		'SC'	=>	q|Seychelles|,
		'SD'	=>	q|Sudan|,
		'SE'	=>	q|Sweden|,
		'SG'	=>	q|Singapore|,
		'SH'	=>	q|St. Helena|,
		'SI'	=>	q|Slovenia|,
		'SJ'	=>	q|Svalbard and Jan Mayen Islands|,
		'SK'	=>	q|Slovak Republic|,
		'SL'	=>	q|Sierra Leone|,
		'SM'	=>	q|San Marino|,
		'SN'	=>	q|Senegal|,
		'SO'	=>	q|Somalia|,
		'SR'	=>	q|Suriname|,
		'ST'	=>	q|Sao Tome and Principe|,
		'SU'	=>	q|USSR (former)|,
		'SV'	=>	q|El Salvador|,
		'SY'	=>	q|Syria|,
		'SZ'	=>	q|Swaziland|,
		'TC'	=>	q|Turks and Caicos Islands|,
		'TD'	=>	q|Chad|,
		'TF'	=>	q|French Southern Territories|,
		'TG'	=>	q|Togo|,
		'TH'	=>	q|Thailand|,
		'TJ'	=>	q|Tajikistan|,
		'TK'	=>	q|Tokelau|,
		'TM'	=>	q|Turkmenistan|,
		'TN'	=>	q|Tunisia|,
		'TO'	=>	q|Tonga|,
		'TP'	=>	q|East Timor|,
		'TR'	=>	q|Turkey|,
		'TT'	=>	q|Trinidad and Tobago|,
		'TV'	=>	q|Tuvalu|,
		'TW'	=>	q|Taiwan|,
		'TZ'	=>	q|Tanzania|,
		'UA'	=>	q|Ukraine|,
		'UG'	=>	q|Uganda|,
		'UK'	=>	q|United Kingdom|,
		'UM'	=>	q|US Minor Outlying Islands|,
		'US'	=>	q|United States|,
		'UY'	=>	q|Uruguay|,
		'UZ'	=>	q|Uzbekistan|,
		'VA'	=>	q|Vatican City State (Holy See)|,
		'VC'	=>	q|Saint Vincent and the Grenadines|,
		'VE'	=>	q|Venezuela|,
		'VG'	=>	q|Virgin Islands (British)|,
		'VI'	=>	q|Virgin Islands (U.S.)|,
		'VN'	=>	q|Viet Nam|,
		'VU'	=>	q|Vanuatu|,
		'WF'	=>	q|Wallis and Futuna Islands|,
		'WS'	=>	q|Samoa|,
		'YE'	=>	q|Yemen|,
		'YT'	=>	q|Mayotte|,
		'YU'	=>	q|Yugoslavia|,
		'ZA'	=>	q|South Africa|,
		'ZM'	=>	q|Zambia|,
		'ZR'	=>	q|Zaire|,
		'ZW'	=>	q|Zimbabwe|,
};


######################################################################
## subs ##############################################################
######################################################################

sub country_values { return \@COUNTRY_VALUES; }
sub country_labels { return $COUNTRY_LABELS; }

######################################################################
sub gpg_encrypt {
  my ($self, $textref) = @_;
  my ($pid, @ciphertext);

  require IO::Handle;
  require GnuPG::Interface;

  my $GPG     = GnuPG::Interface->new();
  my $INPUT   = IO::Handle->new();
  my $OUTPUT  = IO::Handle->new();
  my $ERROR   = IO::Handle->new();
  my $STATUS  = IO::Handle->new();
  if ($runmode eq 'dev') {
    $ENV{'PATH'} = '/usr/GNU/GnuPG';
  }
  my $HANDLES = GnuPG::Handles->new(stdin  => $INPUT,
                                    stdout => $OUTPUT,
                                    stderr => $ERROR,
                                    status => $STATUS,
                                    );

  &debug('<br><br><br><br><br><br><br><br>');
  &debug("Initializing GPG...<br>\n");
  if ($runmode eq 'dev') {
    $GPG->options->hash_init( homedir     => '/home/ssl/vhosts/cgi-bin/classicwireless/.gnupg',
                              armor       => 1,
                              recipients  => [ 'jarnold@2k3technologies.com' ],
                            );
  } else {
    $GPG->options->hash_init( homedir     => '/www/cgi-bin/secure.bitstreet.net/classicwireless/.gnupg',
                              armor       => 1,
                              recipients  => [ 'sales@classicwireless.org' ],
                            );
  }
  $GPG->options->meta_interactive(0);

  &debug("Setting up encryption...<br>\n");
  $GPG->passphrase( 'ndcsales' );
  &debug("Set passphrase...encrypting handles <br>\n");
  $pid = $GPG->encrypt( handles => $HANDLES );

  &debug("Writing to GPG input...<br>\n");
  print $INPUT $$textref;
  close $INPUT;

  &debug("Retrieving ciphertext...<br>\n");
  @ciphertext = <$OUTPUT>;
  close $OUTPUT;

  waitpid $pid, 0;


  if ($DEBUG) {
    my @error = <$ERROR>; close $ERROR;
    my @status = <$STATUS>; close $STATUS;
    &debug("error = " . @error . "<br>");
    &debug("status= " . @status . "<br>");
  }
  return \ join('', @ciphertext);
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

