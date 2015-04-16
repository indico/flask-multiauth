# This file is part of Flask-MultiAuth.
# Copyright (C) 2015 CERN
#
# Flask-MultiAuth is free software; you can redistribute it
# and/or modify it under the terms of the Revised BSD License.

from __future__ import unicode_literals

from flask import request, current_app, url_for, redirect

from flask_multiauth._compat import iteritems
from flask_multiauth.auth import AuthProvider
from flask_multiauth.data import AuthInfo, IdentityInfo
from flask_multiauth.exceptions import MultiAuthException, AuthenticationFailed, IdentityRetrievalFailed
from flask_multiauth.identity import IdentityProvider
from flask_multiauth.util import login_view


class ShibbolethAuthProvider(AuthProvider):
    """Provides authentication for Shibboleth.

    This provider expects to find a Shibboleth module configured in
    Apache server running the application.
    """

    def __init__(self, *args, **kwargs):
        super(ShibbolethAuthProvider, self).__init__(*args, **kwargs)
        self.settings.setdefault('attrs_prefix', 'ADFS_')
        if not self.settings.get('callback_uri'):
            raise MultiAuthException("`callback_uri` must be specified in the provider settings")
        self.authorized_endpoint = '_flaskmultiauth_shibboleth_' + self.name
        current_app.add_url_rule(self.settings['callback_uri'], self.authorized_endpoint,
                                 self._authorize_callback, methods=('GET', 'POST'))

    def initiate_external_login(self):
        return redirect(url_for(self.authorized_endpoint))

    @login_view
    def _authorize_callback(self):
        attributes = {k: v for k, v in iteritems(request.environ) if k.startswith(self.settings['attrs_prefix'])}
        if not attributes:
            raise AuthenticationFailed("No valid data received")
        return_value = self.multiauth.handle_auth_info(AuthInfo(self, **attributes))
        return return_value or self.multiauth.redirect_success()


class ShibbolethIdentityProvider(IdentityProvider):
    """Provides identity information for Shibboleth

    This provider expects to find a Shibboleth module configured in the
    Apache server running the application.
    """

    def __init__(self, *args, **kwargs):
        super(ShibbolethIdentityProvider, self).__init__(*args, **kwargs)
        self.settings.setdefault('identifier_field', 'ADFS_LOGIN')

    def get_identity_from_auth(self, auth_info):
        identifier = auth_info.data[self.settings['identifier_field']]
        if not identifier:
            raise IdentityRetrievalFailed("Identifier field '{}' is not present"
                                          .format(self.settings['identifier_field']))
        return IdentityInfo(self, identifier=auth_info.data[self.settings['identifier_field']], **auth_info.data)
