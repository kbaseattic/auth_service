#!/usr/bin/env perl
#
# Test the Authentication Token code
#
# sychan@lbl.gov
# 8/13/2012

use lib "../lib/";
use lib "lib";
use Data::Dumper;
use HTTP::Daemon;
use HTTP::Request;
use LWP::UserAgent;
use JSON;
use Digest::MD5 qw( md5_base64);
use Test::More tests => 46;
use Storable qw(dclone);
use Test::Deep::NoTest qw(eq_deeply);
use Data::Dumper;


BEGIN {
    use_ok( Bio::KBase::AuthToken);
}

my @users = ();

sub testServer {
    my $d = shift;
    my $res = new HTTP::Response;
    my $msg = new HTTP::Message;
    my $at = new Bio::KBase::AuthToken;

    while (my $c = $d->accept()) {
	while (my $r = $c->get_request) {
	    note( sprintf "Server: Recieved a connection: %s %s\n\t%s\n", $r->method, $r->url->path, $r->content);
	    note( sprintf "        Authorization header: %s\n", $r->header('Authorization'));
	    my $body = sprintf("You sent a %s for %s.\n\n",$r->method(), $r->url->path);
	    my ($token) = $r->header('Authorization') =~ /OAuth (.+)/;
	    
	    if ($token) {
		$at->token( $token);
	    } else {
		$at->{'token'} = undef;
	    }
	    note( "Server received request with token: ".$token);
	    note( sprintf("Validation result on server side: %s", $at->validate() ? $at->validate() : 0 ));
	    if ($at->validate()) {
		$res->code(200);
		$body .= sprintf( "Successfully logged in as user %s\n",
				  $at->user_id);
	    } else {
		$res->code(401);
		$body .= sprintf("You failed to login: %s.\n", $at->error_message);
	    }
	    $res->content( $body);
	    $c->send_response($res);
	}
	$c->close;
	undef($c);
    }
}

sub testClient {
    my $server = shift;

    my $ua = LWP::UserAgent->new();

    ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'password' => '@Suite525'), "Logging in using papa account using username/password");
    ok($at->validate(), "Valid client token for user kbasetest");
    $ua->default_header( "Authorization" => "OAuth " . $at->token);

    ok( $res = $ua->get( $server."someurl"), "Submitting authenticated request to server");
    ok( ($res->code >= 200) && ($res->code < 300), "Querying server with token in Authorization header");
    note( sprintf "Client: Recieved a response: %d %s\n", $res->code, $res->content);

    # As a sanity check, trash the oauth_secret and make sure that
    # we get a negative result
    $ua->default_header( "Authorization" => "BogoToken ");

    note( "Client: Sending bad request (expecting failure)\n");
    ok( $res = $ua->get( $server."someurl"), "Submitting improperly authenticated request to server");
    ok( ($res->code < 200) || ($res->code >= 300), "Querying server with bad oauth creds, expected 401 error");
    note( sprintf "Client: Recieved a response: %d %s\n", $res->code, $res->content);

    # move back original .kbase-auth file
    if ( -e "~/.kbase-auth.testing") {
      `mv ~/.kbase-auth.testing ~/.kbase-auth`;
    }
}

if ( -e $Bio::KBase::AuthToken::authrc) {
    rename $Bio::KBase::AuthToken::authrc, $Bio::KBase::AuthToken::authrc.$$;
}

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'papa', 'password' => 'papapa'), "Logging in using papa account");
ok($at->validate(), "Validating token for papa user using username/password");

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'papa', 'password' => 'poopa'), "Logging in using papa account and bad password");
ok(!($at->validate()), "Testing that bad password fails");

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'papa_blah', 'password' => ''), "Logging in using bad account and bad password");
ok(!($at->validate()), "Testing that bad account/password fails");

ok( $at = Bio::KBase::AuthToken->new('user_id' => undef, ), "Logging in using undef user_id");
ok(!($at->validate()), "Testing that undef user_id fails");

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'password' => '@Suite525'), "Logging in using papa account using username/password");
ok($at->validate(), "Validating token from kbasetest username/password");

$rsakey = <<EOT;
-----BEGIN RSA PRIVATE KEY-----
MIICWgIBAAKBgQC1QVwNCLinZJfKBfFaQm2nZQM0JvwVhV5fwjiLkUPF51I2HfEX
h988fOc2aOWuhPxUYOnE6I5xqMeWVh5T/77tOLs14X7O6kkmQZhsURKeIv9TVwNM
KoHyBRoE70p+K1qAA7szhz4DE+L0OuNa7H6oFVmpoOPq5GBwFqnFZZwqTwIBIwKB
gENSyms9wO23phfWUlS5lnFgCIEVy1hzXZFII6GNuhZOmuDmjL+Y3eNEVeECY/Bd
R8eRteoNPDjYSiHlePqg0eJ1CclHYOTR/ngBmqNxh5fSgscSPHIuoKlEVRrQE2BY
xM+BxMV4Kz7cZ3YKHrgMvHeNBL1eAhlO9iH4ur6i/UlDAkEA2loWVhabzQ2m3DYN
6m7W5NLuBIqRyvNh/zX8gETqwDWynLri4AAcBcerDPghnXkJDqlM7AgG8W1z05A1
VLhjpQJBANSB2kFjVOfdKJwkfvnn82nf/peHODDKUiaIwD7RaKOJFOI9ULJ6s/fJ
qOtJv/Gnv563Sy3p7pSDtH4PGKjXY+MCQBK3Q748c8EebWNVFyK5Cxrtgh2lejX3
mq95p+28w6oTOzIBY+dQd241r5Nlub0KX9yvbP5J1LWbqteepXxKUa8CQHNcbyrP
hdz0ZoCmGQtSB8vCvWgzdkZfM+kIaFydkJNKamwv6fp9H95I5qudEG09zmwaXAL7
VaEUTAnq8CEkeA0CQQCC4JLKFblHiZdEFzn6jkYe4s9Nf6SX7A+Vn4hq1o9yVMzf
+fEfmgafrDgETuDY9fbv8DwfGtIgaWsbXbvXKdFd
-----END RSA PRIVATE KEY-----
EOT

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'client_secret' => $rsakey), "Logging in using kbasetest account using username/rsa_key");
ok($at->validate(), "Validating token for kbasetest username and rsakey");

ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'client_secret' => 'made2fail'), "Logging in using kbasetest account using bad rsa_key");
ok(!($at->validate()), "Validating failed RSA kbasetest login");

$badtoken = <<EOT2;
un=papa|clientid=papa|expiry=1376607863|SigningSubject=https://graph.not.api.test.globuscs.info/goauth/keys/861eb8e0-e634-11e1-ac2c-1231381a5994|sig=321ca03d17d984b70822e7414f20a73709f87ba4ed427ad7f41671dc58eae15911322a71787bdaece3885187da1158daf37f21eadd10ea2e75274ca0d8e3fc1f70ca7588078c2a4a96d1340f5ac26ccea89b406399486ba592be9f1d8ffe6273b7acdba8a0edf4154cb3da6caa6522f363d2f6f4d04e080d682e15b35f0bbc36
EOT2

ok( $at = Bio::KBase::AuthToken->new('token' => $badtoken), "Creating token with bad SigningSubject");
ok(!($at->validate()), "Validating that bad SigningSubject fails");
ok(($at->error_message() =~ /Token signed by unrecognized source/), "Checking for 'unrecognized source' error message");

# test out the keyfile functions
$keyfile = "/tmp/keyfile.$$";
open(TMP, ">$keyfile");
print TMP $rsakey;
close(TMP);
ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'keyfile' => $keyfile), "Logging in using kbasetest account using username/rsa_key with rsa_key specified in keyfile parameter");
ok($at->validate(), "Validating RSA kbasetest login with keyfile only");

# Test the same token, but encrypted with the passphrase "testing"
$rsa2 = <<EOT3;
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: DES-EDE3-CBC,CF421A48268DD7FD

9uREbfScTMIW7rRM8s8UVw9D7FllMI39NtpNKIOl9PVB3QJ/+deyd2AUgxoDCPrG
uhBOrErGofcCEeLGK3M9qOJspgx182gR/w98/i8Yzp6m2DNHIHAWO6tvCeLYwJtF
lPn3t7mswS0cmAzi2Fkp5UPK5AwhvK8bmZ01TTiCQLv4pAn4rPSZcw809pSjkyZL
8IvX3PBSRaCkKtFbDheZYFhTYhfOHtbSKwn4KyOYUs3EnqhFZOJJk0IpAbGWVQQP
dwl6YlCbE8kxsZBRE5QshIulYieTJRZSM4tR8RWZK5/v51OIuyX4FyXN2w/WH1H6
t92uM/nQkMlCK3xt/vyPjvRr2w+9E98qLiGw8p0+vsPH8ukZetEPzZYv+KcRgIQ+
0sbFKNG48+ESHGLmizPzDf9WlSftJaAh77OXgzs+30O7WrbYfGOXCVHvy5iTnZpd
b1KThmENf4YWLH7OwH3Xlb0vC8hV4AvL8yB9muVzSlODbUwOg9MdyMESzQuikm/l
vZQPX6Wk0JotXo7JG68LtMmXzDbHCAiv8RMTcYUJW5Rro5NfRyKZKvtKtv11JTnA
UL2EedAS+PUQ65i04eBCymMjcVSKL/Ew5y+PlsF9wNn9mGXOo1ktx7XP2ts5tlV7
8HW9SUFGmDS5c9bWxxbY9wVKigGV6yv7TgVOFid94RY91AXFGtvqBh/I5ZAGIP0N
oKWnUgRDW9LU0fvmRS/XPqJmg6/KLr4CkzZYiOSysILkAOWOmQ/bl88XTIxrZfBW
e219B0DDVRd35Ey7PVLmw0Wj5StxTmhV49C05qivNug=
-----END RSA PRIVATE KEY-----
EOT3

open(TMP, ">$keyfile");
print TMP $rsa2;
close(TMP);
ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'keyfile' => $keyfile,
				     'keyfile_passphrase' => 'testing'), "Logging in using kbasetest account using username/rsa_key with rsa_key specified in keyfile and keyfile_passphrase parameters");
ok($at->validate(), "Validating RSA kbasetest login with keyfile and passphrase");
ok( $at = Bio::KBase::AuthToken->new('user_id' => 'kbasetest', 'keyfile' => $keyfile,
					       'keyfile_passphrase' => 'test'), "Testing bad login token using kbasetest account using username/rsa_key with rsa_key specified in keyfile, and bad keyfile_passphrase parameters");
ok( ($at->error_message =~ /Bad key\/passphrase/), "Checking for bad passphrase error message." );
ok(!($at->validate()), "Validating failed RSA kbasetest login from improper passphrase");

note( "Creating files for testing ~/authrc");
$authrc = q({"password":"@Suite525","user_id":"kbasetest"});

open( TMP, ">".$Bio::KBase::AuthToken::authrc);
print TMP $authrc;
close( TMP);

ok( $at = Bio::KBase::AuthToken->new(), "Creating a new token object for testing authrc with password");
ok( $at->user_id() eq "kbasetest", "Verifying that kbasetest user was read from authrc");
ok( $at->validate(), "Verifying that kbasetest user token was acquired properly with userid and password");

$authrc = <<EOT6;
{"client_secret":"-----BEGIN RSA PRIVATE KEY-----\nMIICWgIBAAKBgQC1QVwNCLinZJfKBfFaQm2nZQM0JvwVhV5fwjiLkUPF51I2HfEX\nh988fOc2aOWuhPxUYOnE6I5xqMeWVh5T/77tOLs14X7O6kkmQZhsURKeIv9TVwNM\nKoHyBRoE70p+K1qAA7szhz4DE+L0OuNa7H6oFVmpoOPq5GBwFqnFZZwqTwIBIwKB\ngENSyms9wO23phfWUlS5lnFgCIEVy1hzXZFII6GNuhZOmuDmjL+Y3eNEVeECY/Bd\nR8eRteoNPDjYSiHlePqg0eJ1CclHYOTR/ngBmqNxh5fSgscSPHIuoKlEVRrQE2BY\nxM+BxMV4Kz7cZ3YKHrgMvHeNBL1eAhlO9iH4ur6i/UlDAkEA2loWVhabzQ2m3DYN\n6m7W5NLuBIqRyvNh/zX8gETqwDWynLri4AAcBcerDPghnXkJDqlM7AgG8W1z05A1\nVLhjpQJBANSB2kFjVOfdKJwkfvnn82nf/peHODDKUiaIwD7RaKOJFOI9ULJ6s/fJ\nqOtJv/Gnv563Sy3p7pSDtH4PGKjXY+MCQBK3Q748c8EebWNVFyK5Cxrtgh2lejX3\nmq95p+28w6oTOzIBY+dQd241r5Nlub0KX9yvbP5J1LWbqteepXxKUa8CQHNcbyrP\nhdz0ZoCmGQtSB8vCvWgzdkZfM+kIaFydkJNKamwv6fp9H95I5qudEG09zmwaXAL7\nVaEUTAnq8CEkeA0CQQCC4JLKFblHiZdEFzn6jkYe4s9Nf6SX7A+Vn4hq1o9yVMzf\n+fEfmgafrDgETuDY9fbv8DwfGtIgaWsbXbvXKdFd\n-----END RSA PRIVATE KEY-----\n","user_id":"kbasetest"}
EOT6

open( TMP, ">".$Bio::KBase::AuthToken::authrc);
print TMP $authrc;
close( TMP);

ok( $at = Bio::KBase::AuthToken->new(), "Creating a new token object for testing authrc with client_secret");
ok( $at->user_id() eq "kbasetest", "Verifying that kbasetest user was read from authrc");
ok( $at->validate(), "Verifying that kbasetest user token was acquired properly with userid and password");

$authrc = qq({"keyfile":"$keyfile","keyfile_passphrase":"testing","user_id":"kbasetest"});
open( TMP, ">".$Bio::KBase::AuthToken::authrc);
print TMP $authrc;
close( TMP);

ok( $at = Bio::KBase::AuthToken->new(), "Creating a new token object for testing authrc with RSA key and passphrase");
note( "Passphrase for keyfile was: ".$at->{'keyfile_passphrase'});
ok( $at->user_id() eq "kbasetest", "Verifying that kbasetest user was read from authrc");
ok( $at->validate(), "Verifying that kbasetest user token was acquired properly with userid, rsa key and passphrase");

ok( $at = Bio::KBase::AuthToken->new( ignore_authrc => 1), "Creating a blank object by ignoring the authrc file");
ok( ! defined($at->user_id()), "Verifying that authrc was ignored");

$authrc = qq({"keyfile":"$keyfile",","user_id":"kbasetest"});
open( TMP, ">".$Bio::KBase::AuthToken::authrc);
print TMP $authrc;
close( TMP);

ok( $at = Bio::KBase::AuthToken->new(), "Creating a new token object for testing authrc with RSA key and but no passphrase");
ok( ! defined($at->user_id()), "Verifying that authentication failed");
ok( ! $at->validate(), "Verifying that kbasetest user token was no acquired properly when missing passphrase");

unlink($Bio::KBase::AuthToken::authrc);
if ( -e $Bio::KBase::AuthToken::authrc.$$) {
    rename $Bio::KBase::AuthToken::authrc.$$, $Bio::KBase::AuthToken::authrc;
}
unlink( $keyfile);

ok( $d = HTTP::Daemon->new( LocalAddr => '127.0.0.1'), "Creating a HTTP::Daemon object for handling AuthServer") || die "Could not create HTTP::Daemon";

note("Server listening at ".$d->url);

my $child = fork();
if ($child) {
    note( "Running client in parent process $$");
    testClient( $d->url);
} else {
    note( "Running server in pid $$");
    testServer( $d);
}

kill 9, $child;

done_testing();

