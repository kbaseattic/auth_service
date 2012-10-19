use strict;
use warnings;
use Test::More tests => 26 ;
use LWP::UserAgent ;
use JSON;

use Bio::KBase::AuthToken ;


# test server for authorization
my $server = "http://140.221.92.49:7039/Roles/";

my $json     = JSON->new->allow_nonref;

#
#  Test 1 - Can a new object be created without user?
#

my $object_empty = Bio::KBase::AuthToken->new; # create a new object
ok( defined $object_empty, "Did an object get defined for AuthToken without user" );   

            
#
#  Test 2 - Is the object in the right class?
#
isa_ok( $object_empty, 'Bio::KBase::AuthToken', "Is it in the right class (Bio::KBase::AuthToken)" );   




# my $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest',
# 				    'password' => '@Suite525');




#
#  Test 3 - Are the methods valid?
#

can_ok($object_empty, qw[validate]);

#
#  Test 4 - Is the token valid
#

ok( !($object_empty->validate()) , "Empty token does not validate");


#
# Test 5 Can a new object be created user?
#
my $object = Bio::KBase::AuthToken->new('user_id' => 'kbasetest',
					'password' => '@Suite525');

ok( defined $object, "Did an object get defined for AuthToken without user" );   

#
#  Test 6 - Is the object in the right class?
#
isa_ok( $object, 'Bio::KBase::AuthToken', "Is it in the right class (Bio::KBase::AuthToken)" );   


#
#  Test 7 - Are the methods valid?
#
can_ok($object, qw[validate token]);


#
#  Test 8 - Is the token valid
#

ok( $object->validate() , "Valid token");


#
# Test authorization
# 

my $ua     = LWP::UserAgent->new();

#
# Testing existing roles for kbasetest user
# 

$ua->default_header( "Authorization" => "OAuth " . $object->token);
$ua->default_header( "Content-Type" => "application/json");

#
# Test 9 Test authorization error code
#

my $res = $ua->get( $server );
ok( $res->code , "Request for Roles with valid token returns error code");

#
# Test 10 Test valid response
#

ok( ($res->code == 200) , "Request is successfull");


#
# Test 11 Check content type
#

ok( ($res->header('Content-Type') =~ /application\/json/ ) , "Returning content Type is JSON : " . $res->header('Content-Type') );


#
# Test 12 Check content
#
ok( $res->content , 'Received data ' .  $res->content  );


#
# Test 13 Check content , expecting json
#

my $struct = undef ;
eval{ $struct = $json->decode( $res->content ) ; };
ok( !($@)  , "Is content valid json (perl json parser is not picky)");

#
# Test 14 Check content , for role data struct
#

ok (ref $struct , "Returned reference to Role hash") ;


#
# Test 15 - 18 Check query filter
#
my $filter="filter={ \"members\" : \"sychan\"}" ;
#my $filter='filter={ "members" :{ "$regex" : ".*test.*" }';
my $res = $ua->get( $server. "?$filter" );

ok( $res->code , "Request returns error code");
ok( ($res->code == 200) , "Request is valid");
ok( $res->content , 'Received data' );
ok( ($res->header('Content-Type') =~ /application\/json/ ) , "Content Type is JSON : " . $res->header('Content-Type') ); 
    




#
# Test put 
#


my $role = {
    "role_owner" => "kbasetest",
    "role_id"=> "kbase_test_users",
    "description"=> "List of user ids who are considered KBase users",
    "members"=> [
	"kbasetest",
	],
	"role_updater"=> [
	    "kbtest",
	],
	"read"=> [],
	"create"=> [],
	"modify"=> [],
	"impersonate"=> [],
	"delete"=> [],
} ;



#
# Test 19 - 22 create role
# 

my $jtext = $json->encode($role);
my $res   = $ua->post($jtext);

ok( $res->code          , "Request returns error code");
ok( ($res->code == 200) , "Request is valid (".$res->code.")");
ok( $res->content       , 'Received data: ' .  $res->content );
ok( ($res->header('Content-Type') =~ /application\/json/ ) , "Content Type is JSON : " . $res->header('Content-Type') ); 



#
# Test add user
# 


my $role = {
    "role_owner" => "kbasetest",
    "role_id"=> "kbase_test_users",
    "description"=> "List of user ids who are considered KBase users",
    "members"=> [
	"kbasetest",
	"papa",
	],
	"role_updater"=> [
	    "kbtest",
	],
	"read"=> [],
	"create"=> [],
	"modify"=> [],
	"impersonate"=> [],
	"delete"=> [],
} ;

my $jtext = $json->encode($role);
my $res   = $ua->put($jtext);

ok( $res->code          , "Request returns error code");
ok( $res->content       , 'Received data: ' .  $res->content );
ok( ($res->code == 200) , "Request is valid (".$res->code.")");
ok( ($res->header('Content-Type') =~ /application\/json/ ) , "Content Type is JSON : " . $res->header('Content-Type') ); 



#
# Test retrive role for user
#

#
# Test delete role
#


#
# Test data structure if json
# 

# if ($res->header('Content-Type') eq "application/json") {
#     my $data = $json->decode( $res->decoded_content ); 
# }


# my $res = $ua->get( $server. "Roles?$filter" );




# printf "Client: Recieved a response: %d %s\n", $res->code, $res->content;

#     # ^Roles/(?P<role_id>[^/]+)$
#     # ^Roles/?$
#     # ^admin/
#     # ^authstatus/?$

# $res = $ua->get( $server. "Roles" );
# $res = $ua->get( $server. "Roles" );
# $res = $ua->get( $server. "authstatus" );
# $res = $ua->get( $server. "admin" );

