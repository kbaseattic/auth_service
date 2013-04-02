var user_callback;

$(function() {
      
      // Placeholder for user defined callback function
      var $ld = $(document.createElement('div')).attr('id','login-dialog').attr('title','KBase Login');
      $ld.load('{{base_url}}{% url session.login-form %}' ).appendTo('body');
      $ld.attr('style','height: "auto" ');

      $ld.dialog(
          {
              autoOpen : false,
              modal : true,
              resizable: true,
	      width : 'auto',
              buttons : {
                  Cancel : function () {
                      $( this ).dialog('close');
                  },
                  Login : function() {

                      var username = $("#login-username").val();
                      var password = $("#login-password").val();

                      $(this).trigger('message', username);

                      login.call(this, username, password, function(success, args) {

                                     if ( success ) {
                                         $(this).trigger('clearMessages');
                                         $("#login-entrance").hide();
                                         $("#login-loggedinusername").text(args.username);
                                         $("#login-loggedinsession").text(args.kbase_sessionid);
                                         $("#login-userdisplay").show();
                                         $(this).dialog('close');
					 if (user_callback) {
					     user_callback( args);
					 }
                                     }
                                     else {
                                         $(this).trigger('error', args.message);
                                     }
                                 });

                  },
                  Logout : function() {
		      logout();
                      $(this).trigger('clearMessages');
		      $('#form_input').show();
		      $(".ui-dialog-buttonpane button:contains('Login')").button("enable");
		      $(".ui-dialog-buttonpane button:contains('Logout')").button("disable");

                  },
              },
              open : function() {
                  $('form', $(this))[0].reset();
                  $(this).trigger('clearMessages');
                  $(this).unbind('keypress');
		  $(".ui-dialog-buttonpane button:contains('Logout')").button("disable");
                  $(this).keypress(function(e) {
                                       if (e.keyCode == $.ui.keyCode.ENTER) {
                                           $('button:last', $(this).parent()).trigger("click");
                                           e.stopPropagation();
                                       }
                                   });
              },
          }
      );

      $ld.bind('error', function(event, msg) {
		   $(this).attr('style','height: "auto" ');
                   $(this).trigger('clearMessages');
                   $("#login-error").show();
                   $("#login-errormsg").html(msg);
               });

      $ld.bind('message', function(event, msg) {
		   $(this).attr('style','height: "auto" ');
                   $(this).trigger('clearMessages');
                   $("#login-pending").show();
                   $("#login-pendinguser").html(msg);
               });

      $ld.bind('already_logged_in', function(event, msg) {
		   $(this).attr('style','height: "auto" ');
                   $(this).trigger('clearMessages');
                   $("#login-pending").hide();
                   $("#form_input").hide();
                   $("#already_logged_in").show();
                   $("#logged_in_user").html(msg); 
		   $(".ui-dialog-buttonpane button:contains('Login')").button("disable");
		   $(".ui-dialog-buttonpane button:contains('Logout')").button("enable");

               });

      $ld.bind('clearMessages', function(event) {
                   $("#login-error").hide();
                   $("#login-pending").hide();
                   $("#already_logged_in").hide();
               });

      $( "#login-widget button" ).button();

  });

function login(username, password, callback) {

    // STEVE -


    // do whatever you need to do here to log the user into of the system
    // Right now the callback function takes a boolean and an object. the boolean
    // is whether or not the login was successful, and the object is just an arbitrary context.
    //
    // Right now, the important args keys that should be populated are:
    //
    // username - the user logged in. This can be the actual username, or a human readable name.
    //            we can break that out into separate keys if that seems useful.
    // message  - any status message provided. Usually a reason the login failed.

    //this is the boolean that gets passed into the callback to determine whether or not it was a succesful login.
    var status = 1;
    //and the arbitrary args, pre-populated with the username for your convenience.
    var args = { username : username };

    // this is just here to simulate the time of a login negotiation taking place. Set the value to 0
    // when in production to skip the arbitrary 1 second delay.
    // When running as a demo, it also randomly fails to login sometimes.
    var logindemo = 1;

    // here's a couple of simple cases that need to be handled somewhere. Figured I'd just toss 'em into this function
    // to keep 'em all in one place.
    var that = this;
    if (username.length == 0) {
        args.message = 'Cannot login w/o username';
        status = 0;
        callback.call(that, status, args);
    } else if (password.length == 0) {
        args.message = 'Cannot login w/o password';
        status = 0;
        callback.call(that, status, args);

    } else {
	var form_params = {
	    'user_id' : username,
	    'password' : password,
	    'cookie' : 1,
	    'fields' : 'token,user_id,name'
	};
	if (! user_callback) {
	//    form_params.cookie = "only";
	}
        $.ajax({ type: "POST",
		 url: "https://www.kbase.us/services/authorization/Sessions/Login",
		 //data : { 'user_id' : username,
		 //	  'password' : password,
		 //	  'cookie' : 'only' },
		 data : form_params,
		 dataType: "json",
		 crossDomain : true,
		 xhrFields: { withCredentials: true },
		 success: function (data,res,jqXHR) {
		     var args = {};
		     var cookie = '';
		     // Look for a kbase_session cookie
		     if (user_callback) {
			 if ('token' in data) {
			     args = data
			     callback.call(that,1,args)
			 } else {
			     args.message = data.error_msg;
			     callback.call(that,0,args);
			 }
		     } else {
			 var i,x,y,ARRcookies=document.cookie.split(";");
			 for (i=0;i<ARRcookies.length;i++) {
			     x=ARRcookies[i].substr(0,ARRcookies[i].indexOf("="));
			     y=ARRcookies[i].substr(ARRcookies[i].indexOf("=")+1);
			     x=x.replace(/^\s+|\s+$/g,"");
			     if (x=='kbase_session') {
				 cookie = unescape(y);
			     }
			 }
			 if ( cookie ) {
			     var m = /un=(\w+)\|kbase_sessionid=(\w+)/g.exec( cookie );
			     args.username = m[1];
			     args.kbase_sessionid = m[2];
			     callback.call(that,1,args)
			 } else {
			     args.message = 'Failed to authenticate';
			     callback.call(that,0,args);
			 }
		     }
		 },
		 error: function (jqXHR, textStatus, errorThrown) {
		     // If we have a useless error message, replace with
		     // friendly, but useless error message
		     if (textStatus == "error") {
			 textStatus = "Error connecting to KBase login server";
		     }
		     callback.call(that,0, { 'message' : textStatus })
		 },
		 xhrFields: {
		     withCredentials: true
		 },
		 beforeSend : function(xhr){
		     // make cross-site requests
		     xhr.withCredentials = true;
		 },
	       });
    }
}

function get_kbase_cookie() {
    var cookie = '';
    var args = {};
    
    // Look for a kbase_session cookie
    var i,x,y,ARRcookies=document.cookie.split(";");
    for (i=0;i<ARRcookies.length;i++) {
	x=ARRcookies[i].substr(0,ARRcookies[i].indexOf("="));
	y=ARRcookies[i].substr(ARRcookies[i].indexOf("=")+1);
	x=x.replace(/^\s+|\s+$/g,"");
	if (x=='kbase_session') {
	    cookie = unescape(y);
	}
    }
    var m = /un=(\w+)\|kbase_sessionid=(\w+)/g.exec( cookie );
    if (m) {
	args.username = m[1];
	args.kbase_sessionid = m[2];
    }
    return( args);
}


function logout() {

    // Expire the current session cookie
    cookie = 'kbase_session=; domain=.kbase.us; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/';
    document.cookie = cookie;

    //automatically prompt to log in again
    $('#login-dialog').dialog('open');
}

function login_dialog( callback ) {
    var args = get_kbase_cookie();

    $('#login-dialog').dialog('open');
    if (callback) {
	user_callback = callback;
    }

    if ('username' in args) {
	$('#login-dialog').trigger('already_logged_in', args.username)
    }
}