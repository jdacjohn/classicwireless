/* Table defs for Nextel NDC project */
 
CREATE TABLE products (
	sid		integer unsigned DEFAULT '' NOT NULL auto_increment,
	vendorid	integer unsigned DEFAULT '' NOT NULL,
	item_num	char(48) DEFAULT '' NOT NULL,
	age		char(1) DEFAULT '' NOT NULL,
	category	integer unsigned DEFAULT '' NOT NULL,
	manuf		varchar(32) DEFAULT '' NOT NULL,
	quantity	integer unsigned DEFAULT '' NOT NULL,
	price		float DEFAULT '' NOT NULL,
	format		varchar(32) DEFAULT '',
	descr		text DEFAULT '',
	PRIMARY KEY 	(sid),
	INDEX		(item_num)
);

CREATE TABLE library (
	sid		integer unsigned DEFAULT '' NOT NULL auto_increment,
	item_num	char(48) DEFAULT '' NOT NULL,
	title		varchar(32) DEFAULT '' NOT NULL,
	manuf		varchar(32) DEFAULT '' NOT NULL,
	descr		text DEFAULT '',
	file		varchar(64) DEFAULT '' NOT NULL,
	PRIMARY KEY	(sid),
	INDEX		(item_num)
);

CREATE TABLE specials (
	sid		integer unsigned DEFAULT '' NOT NULL auto_increment,
	vendorid	integer unsigned DEFAULT '' NOT NULL,
	item_num	char(48) DEFAULT '' NOT NULL,
	title		varchar(32) DEFAULT '' NOT NULL,
	manuf		varchar(32) DEFAULT '' NOT NULL,
	price		float DEFAULT '' NOT NULL,
	qty		integer unsigned DEFAULT 0,
	fp1		tinyint,
	fp2		tinyint,
	phto_ext	varchar(8) DEFAULT '' NOT NULL,
	descr		text DEFAULT '',
	PRIMARY KEY	(sid),
	INDEX		(item_num)
);

CREATE TABLE categories (
	sid		integer unsigned DEFAULT '' NOT NULL,
	name		varchar(48) DEFAULT '' NOT NULL,
	PRIMARY KEY	(sid)
);

CREATE TABLE sessions (
	sessid		char(32) DEFAULT '' NOT NULL,
	ip		integer unsigned DEFAULT '' NOT NULL,
	lasttime	timestamp DEFAULT '' NOT NULL,
	acl		smallint unsigned DEFAULT '' NOT NULL,
	data		blob DEFAULT '',
	PRIMARY KEY     (sessid)
);

CREATE TABLE transactions (
	sid		integer unsigned DEFAULT '' NOT NULL auto_increment,
	orderid		varchar(32) DEFAULT '' NOT NULL,
	vendorid	integer unsigned DEFAULT '' NOT NULL,
	cardid		integer unsigned DEFAULT '' NOT NULL,
	saletime	timestamp DEFAULT '' NOT NULL,
	amount		float DEFAULT '' NOT NULL,
	ccnum		char(4) DEFAULT '' NOT NULL,
	bill_name	varchar(48) DEFAULT '' NOT NULL,
	bill_addr	varchar(48) DEFAULT '' NOT NULL,
	bill_city	varchar(48) DEFAULT '' NOT NULL,
	bill_state	char(2) DEFAULT '' NOT NULL,
	bill_zip	varchar(10) DEFAULT '' NOT NULL,
	bill_country	char(2) DEFAULT '' NOT NULL,
	ship_class	varchar(12) DEFAULT '' NOT NULL,
	ship_name	varchar(48) DEFAULT '' NOT NULL,
	ship_addr	varchar(48) DEFAULT '' NOT NULL,
	ship_city	varchar(48) DEFAULT '' NOT NULL,
	ship_state	char(2) DEFAULT '' NOT NULL,
	ship_zip	varchar(10) DEFAULT '' NOT NULL,
	ship_country	char(2) DEFAULT '' NOT NULL,
	ship_phone	varchar(16) DEFAULT '' NOT NULL,
	ip		integer unsigned DEFAULT '' NOT NULL,
	prodlist	blob DEFAULT '',
	PRIMARY KEY     (sid)
);

CREATE TABLE cards (
	sid		integer unsigned DEFAULT '' NOT NULL auto_increment,
	orderid		varchar(32) DEFAULT '' NOT NULL,
	data		blob DEFAULT '',
	PRIMARY KEY	(sid)
);
/* vim: set ts=8 noet : */
