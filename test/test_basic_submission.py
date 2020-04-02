#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os

import firecloud.api

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

logger = logging.getLogger(__name__)


class TestFirecloud(unittest.TestCase):
    def test_firecloud_submission_unauthorized(self):
        response = firecloud.api.create_submission(
            wnamespace='default',
            workspace='default',
            cnamespace='default',
            config={},
            entity=None,
            etype=None,
            expression=None,
            use_callcache=True)

        assert '401 Unauthorized' in response.content.decode('utf-8')
        assert response.status_code == 401


if __name__ == "__main__":
    unittest.main()
