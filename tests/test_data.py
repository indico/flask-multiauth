# This file is part of Flask-MultiAuth.
# Copyright (C) 2015 CERN
#
# Flask-MultiAuth is free software; you can redistribute it
# and/or modify it under the terms of the Revised BSD License.

from __future__ import unicode_literals

import pytest

from flask_multiauth import AuthInfo


def test_authinfo():
    with pytest.raises(ValueError):
        AuthInfo(None)
    ai = AuthInfo(None, foo='bar')
    assert ai.data == {'foo': 'bar'}


@pytest.mark.parametrize(('mapping', 'output_data'), (
    ({},             {'foo': 'bar', 'meow': 1337}),
    ({'oof': 'foo'}, {'oof': 'bar', 'meow': 1337}),
))
def test_authinfo_map(mapping, output_data):
    ai = AuthInfo(None, foo='bar', meow=1337)
    original_data = ai.data.copy()
    ai2 = ai.map(mapping)
    assert ai2.data == output_data
    assert ai.data == original_data


def test_authinfo_map_invalid():
    ai = AuthInfo(None, foo='bar')
    with pytest.raises(KeyError):
        ai.map({'foo': 'nop'})