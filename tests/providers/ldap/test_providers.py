# This file is part of Flask-MultiAuth.
# Copyright (C) 2015 CERN
#
# Flask-MultiAuth is free software; you can redistribute it
# and/or modify it under the terms of the Revised BSD License.

from __future__ import unicode_literals

import pytest
from flask import Flask
from ldap import INVALID_CREDENTIALS
from mock import MagicMock

from flask_multiauth import MultiAuth
from flask_multiauth.exceptions import IdentityRetrievalFailed, InvalidCredentials, NoSuchUser
from flask_multiauth.providers.ldap import LDAPAuthProvider, LDAPGroup, LDAPIdentityProvider


@pytest.mark.parametrize(('settings', 'data'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'
    }}, {'username': 'alaindi', 'password': 'LemotdepassedeLDAP'}),
))
def test_authenticate(mocker, settings, data):
    def user_dn(user):
        return 'dn={0},dc=example,dc=com'.format(user)
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(user_dn(data['username']), {settings['ldap']['uid']: [data['username']]}))
    ldap_conn = MagicMock(simple_bind_s=MagicMock())
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize', return_value=ldap_conn)

    multiauth = MagicMock()
    auth_provider = LDAPAuthProvider(multiauth, 'LDAP test provider', settings)
    auth_provider.process_local_login(data)
    ldap_conn.simple_bind_s.assert_called_with(user_dn(data['username']), data['password'])
    auth_info = multiauth.handle_auth_success.call_args[0][0]
    assert auth_info.data['identifier'] == data['username']


@pytest.mark.parametrize(('settings', 'data'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'
    }}, {'username': 'alaindi', 'password': 'LemotdepassedeLDAP'}),
))
def test_authenticate_invalid_user(mocker, settings, data):
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(None, {'cn': ['Configuration']}))
    ldap_conn = MagicMock(simple_bind_s=MagicMock())
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize', return_value=ldap_conn)

    auth_provider = LDAPAuthProvider(None, 'LDAP test provider', settings)
    with pytest.raises(NoSuchUser):
        auth_provider.process_local_login(data)


@pytest.mark.parametrize(('settings', 'data'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'
    }}, {'username': 'alaindi', 'password': 'LemotdepassedeLDAP'}),
))
def test_authenticate_invalid_credentials(mocker, settings, data):
    def user_dn(user):
        return 'dn={0},dc=example,dc=com'.format(user)
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(user_dn(data['username']), {settings['ldap']['uid']: [data['username']]}))
    ldap_conn = MagicMock(simple_bind_s=MagicMock(side_effect=[None, INVALID_CREDENTIALS]))
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize', return_value=ldap_conn)

    auth_provider = LDAPAuthProvider(None, 'LDAP test provider', settings)
    with pytest.raises(InvalidCredentials):
        auth_provider.process_local_login(data)
    ldap_conn.simple_bind_s.assert_called_with(user_dn(data['username']), data['password'])


@pytest.mark.parametrize(('settings', 'group_dn', 'subgroups', 'expected'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {},
     {'group_dn_1'}),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'group_dn_1': [('group_dn_1.1', {}), ('group_dn_1.2', {})]},
     {'group_dn_1', 'group_dn_1.1', 'group_dn_1.2'}),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'group_dn_1': [('group_dn_1.1', {}), ('group_dn_1.2', {})],
      'group_dn_1.2': [('group_dn_1.2.1', {})],
      'group_dn_1.2.1': [('group_dn_1.2.1.1', {}), ('group_dn_1.2.1.2', {}), ('group_dn_1.2.1.3', {})],
      'group_dn_1.2.1.3': []},
     {'group_dn_1', 'group_dn_1.1', 'group_dn_1.2', 'group_dn_1.2.1', 'group_dn_1.2.1.1', 'group_dn_1.2.1.2',
      'group_dn_1.2.1.3'})
))
def test_iter_group(mocker, settings, group_dn, subgroups, expected):
    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)
    group = LDAPGroup(idp, 'LDAP test group', group_dn)
    visited_groups = []
    iter_group = group._iter_group()
    # should not throw StopIteration as the initial group dn must be returned first
    current_dn = next(iter_group)
    with pytest.raises(StopIteration):
        while current_dn:
            visited_groups.append(current_dn)
            current_dn = iter_group.send(subgroups.get(current_dn, []))

    assert len(visited_groups) == len(expected)
    assert set(visited_groups) == expected


@pytest.mark.parametrize(('settings', 'group_dn', 'mock_data', 'expected'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'groups': ['group_dn_1'], 'subgroups': {}, 'users': {}},
     []),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'groups': ['group_dn_1'], 'subgroups': {},
      'users': {'group_dn_1': [('user_1', {'uid': ['user_1']}), ('user_2', {'uid': ['user_2']})]}},
     ['user_1', 'user_2']),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'groups': ['group_dn_1', 'group_dn_1.1'],
      'subgroups': {'group_dn_1': [('group_dn_1.1', {})]},
      'users': {'group_dn_1': [('user_1', {'uid': ['user_1']}), ('user_2', {'uid': ['user_2']})],
                'group_dn_1.1': [('user_3', {'uid': ['user_3']}), ('user_4', {'uid': ['user_4']})]}},
     ['user_1', 'user_2', 'user_3', 'user_4']),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'uid': 'uid'}},
     'group_dn_1',
     {'groups': ['group_dn_1', 'group_dn_1.1', 'group_dn_1.1.1', 'group_dn_1.1.2'],
      'subgroups': {'group_dn_1': [('group_dn_1.1', {})]},
      'users': {'group_dn_1': [('user_1', {'uid': ['user_1']}), ('user_2', {'uid': ['user_2']})],
                'group_dn_1.1': [('user_3', {'uid': ['user_3']}), ('user_4', {'uid': ['user_4']})],
                'group_dn_1.1.2': [('user_5', {'uid': ['user_5']}), ('user_6', {'uid': ['user_6']})],
                'group_dn_1.1.3': [('user_7', {'uid': ['user_7']}), ('user_8', {'uid': ['user_8']})]}},
     ['user_1', 'user_2', 'user_3', 'user_4', 'user_5', 'user_6', 'user_7', 'user_8'])
))
def test_get_members(mocker, settings, group_dn, mock_data, expected):
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize')
    mocker.patch('flask_multiauth.providers.ldap.providers.build_group_search_filter',
                 side_effect=MagicMock(side_effect=mock_data['groups']))
    mocker.patch('flask_multiauth.providers.ldap.providers.build_user_search_filter',
                 side_effect=MagicMock(side_effect=mock_data['groups']))
    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)

    idp._search_groups = MagicMock(side_effect=lambda x: mock_data['subgroups'].get(x, []))
    idp._search_users = MagicMock(side_effect=lambda x: mock_data['users'].get(x, []))
    group = LDAPGroup(idp, 'LDAP test group', group_dn)

    with pytest.raises(StopIteration):
        members = group.get_members()
        while True:
            member = next(members)
            assert member.provider.name == idp.name
            assert member.identifier == expected.pop(0)


@pytest.mark.parametrize(('settings', 'group_mock', 'user_mock', 'expected'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': []}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': []},
     False),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': ['group_token<001>']}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': ['group_token<001>']},
     True),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': ['group_token<002>']}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': ['group_token<001>', 'group_token<003>']},
     False),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': ['group_token<002>']}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': ['group_token<001>', 'group_token<002>',
                                                                       'group_token<003>']},
     True),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': ['group_token<001>', 'group_token<003>']}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': ['group_token<002>']},
     False),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid'}},
     {'dn': 'group_dn', 'data': {'objectSid': ['group_token<001>', 'group_token<002>', 'group_token<003>']}},
     {'dn': 'user_dn', 'data': {'uid': ['user_uid']}, 'token_groups': ['group_token<002>']},
     True),
))
def test_has_member_ad(mocker, settings, group_mock, user_mock, expected):
    def get_token_groups(user_dn):
        if user_mock['dn'] != user_dn:
            pytest.fail('expected {0}, got {1}'.format(user_mock['dn'], user_dn))
        return user_mock['token_groups']
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize')
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(user_mock['dn'], user_mock['data']))
    mocker.patch('flask_multiauth.providers.ldap.providers.get_group_by_id',
                 return_value=(group_mock['dn'], group_mock['data']))
    mocker.patch('flask_multiauth.providers.ldap.providers.get_token_groups_from_user_dn', side_effect=get_token_groups)

    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)
    group = LDAPGroup(idp, 'LDAP test group', group_mock['dn'])
    assert group.has_member(user_mock['data']['uid'][0]) == expected


@pytest.mark.parametrize(('settings', 'group_dn', 'user_mock', 'expected'), (
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
     'group_dn',
     {'dn': 'user_dn', 'data': {'uid': ['user_uid'], 'member_of': []}},
     False),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
     'group_dn',
     {'dn': 'user_dn', 'data': {'uid': ['user_uid'], 'member_of': ['other_group_dn']}},
     False),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
     'group_dn',
     {'dn': 'user_dn', 'data': {'uid': ['user_uid'], 'member_of': ['group_dn']}},
     True),
    ({'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
     'group_dn',
     {'dn': 'user_dn', 'data': {'uid': ['user_uid'], 'member_of': ['other_group_dn', 'group_dn']}},
     True),
))
def test_has_member_slapd(mocker, settings, group_dn, user_mock, expected):
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize')
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(user_mock['dn'], user_mock['data']))

    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)
    group = LDAPGroup(idp, 'LDAP test group', group_dn)
    assert group.has_member(user_mock['data']['uid'][0]) == expected


@pytest.mark.parametrize('settings', (
    {'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
    {'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}}
))
def test_has_member_bad_identifier(mocker, settings):
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize')
    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)
    group = LDAPGroup(idp, 'LDAP test group', 'group_dn')

    with pytest.raises(IdentityRetrievalFailed):
        group.has_member(None)


@pytest.mark.parametrize('settings', (
    {'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': True,
        'uid': 'uid',
        'member_of_attr': 'member_of'}},
    {'ldap': {
        'uri': 'ldaps://ldap.example.com:636',
        'bind_dn': 'uid=admin,DC=example,DC=com',
        'bind_password': 'LemotdepassedeLDAP',
        'tls': True,
        'starttls': True,
        'timeout': 10,
        'ad_group_style': False,
        'uid': 'uid',
        'member_of_attr': 'member_of'}}
))
def test_has_member_unkown_user(mocker, settings):
    mocker.patch('flask_multiauth.providers.ldap.util.ldap.initialize')
    mocker.patch('flask_multiauth.providers.ldap.providers.get_user_by_id',
                 return_value=(None, {'cn': ['Configuration']}))
    app = Flask('test')
    multiauth = MultiAuth(app)
    with app.app_context():
        idp = LDAPIdentityProvider(multiauth, 'LDAP test idp', settings)
    group = LDAPGroup(idp, 'LDAP test group', 'group_dn')

    with pytest.raises(IdentityRetrievalFailed):
        group.has_member('unkown_user')
