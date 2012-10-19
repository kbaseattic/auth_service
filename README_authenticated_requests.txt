
   This is a terminal session showing how to fetch a Globus Online token using curl, and then submitting an authenticated request
to the authorization service using the "access_token" field returned from Globus Online:

ubuntu@sychan-temp2:/kb/dev_container/modules/auth$ curl -k -# --user kbasetest:@Suite525 'https://nexus.api.globusonline.org/goauth/token?client_id=papa&grant_type=client_credentials' | python -mjson.tool
######################################################################## 100.0%
{
    "access_token": "un=kbasetest|tokenid=3be5a452-0d97-11e2-81d0-12313809f035|expiry=1380831397|client_id=kbasetest|token_type=Bearer|SigningSubject=https://nexus.api.globusonline.org/goauth/keys/efc9fd6e-0ba9-11e2-81d0-12313809f035|sig=7ae1687147d52a5717f5ebc15a64cda67f8648332944220d1e578f847fd1899ed5abd7b7bd4b4e9b568bd959f35517b5722e12f044e173bd23337103643279330b26c897a89e21f44e27ead4bb75ab510dca9f08734b7aa6bc7ab4554821fd70a90a8151f44968cc510e6a64b3b5ff2f7736c199e8a711e151c7422f7d8816db", 
    "access_token_hash": "736372797074000d0000000800000001c8b8073aa1d98e78554bd8ac1fdec33f62eb53c977d6ae437418f1a49a3975ed625a2468d23d8b0b7b5e8359668856ee9058af31698d6eb2c444db6c2153a147bcce2a2f9d6f1786a1c4db83afbab84ca7e00f4826df6503f72880c2b280144392a4656f5c6d420b9d728e3cf9af323a955532d089b11735d54ea43c2ffec53669e3b244589d14d3754b1fc7683503e33595f885e7161291f7c4a6f4b774af7c66679bf5038c106445458d7b608ca2b1", 
    "client_id": "kbasetest", 
    "expires_in": 31536000, 
    "expiry": 1380831397, 
    "issued_on": 1349295397, 
    "lifetime": 31536000, 
    "scopes": [
        "https://transfer.api.globusonline.org"
    ], 
    "token_id": "3be5a452-0d97-11e2-81d0-12313809f035", 
    "token_type": "Bearer", 
    "user_name": "kbasetest"
}
ubuntu@sychan-temp2:/kb/dev_container/modules/auth$ curl -# -H "Authorization: OAuth un=kbasetest|tokenid=3be5a452-0d97-11e2-81d0-12313809f035|expiry=1380831397|client_id=kbasetest|token_type=Bearer|SigningSubject=https://nexus.api.globusonline.org/goauth/keys/efc9fd6e-0ba9-11e2-81d0-12313809f035|sig=7ae1687147d52a5717f5ebc15a64cda67f8648332944220d1e578f847fd1899ed5abd7b7bd4b4e9b568bd959f35517b5722e12f044e173bd23337103643279330b26c897a89e21f44e27ead4bb75ab510dca9f08734b7aa6bc7ab4554821fd70a90a8151f44968cc510e6a64b3b5ff2f7736c199e8a711e151c7422f7d8816db" http://localhost:7039/Roles | python -mjson.tool
######################################################################## 100.0%
{
    "contact": {
        "email": "sychan@lbl.gov"
    }, 
    "documentation": "https://docs.google.com/document/d/1CTkthDUPwNzMF22maLyNIktI1sHdWPwtd3lJk0aFb20/edit", 
    "id": "KBase Authorization", 
    "resources": {
        "create": "Boolean value - does this role provide the create privilege", 
        "delete": "List of kbase object ids (strings) that this role allows delete privs", 
        "description": "Description of the role (required)", 
        "grant": "List of kbase authz role_ids (strings) that this role allows grant privs", 
        "impersonate": "List of kbase user_ids (strings) that this role allows impersonate privs", 
        "members": "A list of the user_ids who are members of this group", 
        "modify": "List of kbase object ids (strings) that this role allows modify privs", 
        "read": "List of kbase object ids (strings) that this role allows read privs", 
        "role_id": "Unique human readable identifer for role (required)", 
        "role_owner": "Owner(creator) of this role", 
        "role_updater": "User_ids that can update this role"
    }, 
    "usage": "This is a standard REST service. Note that read handler takes\nMongoDB filtering and JSON field selection options passed as\nURL parameters 'filter' and 'fields' respectively.\nPlease look at MongoDB pymongo collection documentation for details.\nRead and Create are currently open to all authenticated users in role \"kbase_users\", but\ndelete requires ownership of the document (in field role_owner),\nupdate requires ownership or membership in the target document's role_updaters list\n"
}

