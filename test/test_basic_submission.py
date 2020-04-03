#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os
import json

import firecloud.api
from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.utils import fetch_google_secret

logger = logging.getLogger(__name__)


class TestGen3DataAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen3_endpoint = 'https://gen3.biodatacatalyst.nhlbi.nih.gov'
        cls.gen3_key = json.loads(fetch_google_secret('gen3_api_token'))
        cls.gen3_auth_client = Gen3Auth(endpoint=cls.gen3_endpoint, refresh_token=cls.gen3_key)
        cls.gen3_sub_client = Gen3Submission(endpoint=cls.gen3_endpoint, auth_provider=cls.gen3_auth_client)

    def test_data_introspect(self):
        response = self.gen3_sub_client.get_programs()  # {'links': ['/v0/submission/parent', '/v0/submission/topmed', '/v0/submission/open_access', '/v0/submission/tutorial']}
        print(response)

        response = self.gen3_sub_client.query(query_txt='{project(first:0){project_id id}}')
        print(response)

        program = 'topmed'
        project = 'BAGS_GRU-IRB'
        # sample_id = 'c4422337-2b52-4cb0-8180-a069c1c9efb4'

        response = self.gen3_sub_client.get_projects(program=program)
        print(response)

        response = self.gen3_sub_client.get_project_dictionary(program=program, project=project)
        print(response)

        output_path = 'sample_node.tsv'
        response = self.gen3_sub_client.export_node(program=program,
                                                    project=project,
                                                    node_type="sample",
                                                    fileformat="tsv",
                                                    filename=output_path)
        print(response)

        assert os.path.exists(output_path)
        os.remove(output_path)


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
