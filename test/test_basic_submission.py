#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os
import json

import google.cloud.storage

import firecloud.api
from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.utils import retry, fetch_terra_drs_url, md5sum, download, GEN3_ENDPOINTS, GS_SCHEMA
from test.infra.testmode import controlled_access

logger = logging.getLogger(__name__)


class TestGen3DataAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen3_endpoint = GEN3_ENDPOINTS['prod']
        with open(os.environ['GEN3KEY'], 'r') as f:
            cls.gen3_key = json.loads(f.read())
        cls.gen3_auth_client = Gen3Auth(endpoint=cls.gen3_endpoint, refresh_token=cls.gen3_key)
        cls.gen3_sub_client = Gen3Submission(endpoint=cls.gen3_endpoint, auth_provider=cls.gen3_auth_client)
        cls.google_storage_client = google.cloud.storage.Client(project=os.environ['GOOGLE_PROJECT_ID'])

    def test_drs_in_terra(self):
        json_response = fetch_terra_drs_url(drs_url="drs://dg.712C/fa640b0e-9779-452f-99a6-16d833d15bd0")
        # Response should be:
        # {'dos': {'data_object': {'aliases': [],
        #                          'checksums': [{'checksum': '8bec761c8a626356eb34dbdfe20649b4', 'type': 'md5'}],
        #                          'created': '2020-01-15T17:46:25.694142',
        #                          'description': '',
        #                          'id': 'dg.712C/fa640b0e-9779-452f-99a6-16d833d15bd0',
        #                          'mime_type': '',
        #                          'name': None,
        #                          'size': 1386553,
        #                          'updated': '2020-01-15T17:46:25.694148',
        #                          'urls':
        #                          [{'url': 'gs://fc-56ac46ea-efc4-4683-b6d5-6d95bed41c5e/CCDG_13607/Project_CCDG_13607_B01_GRM_WGS.cram.2019-02-06/Sample_HG01131/analysis/HG01131.final.cram.crai'}],
        #                          'version': 'd87455aa'}}}
        google_url_paths = [url['url'] for url in json_response['dos']['data_object']['urls'] if url['url'].startswith(GS_SCHEMA)]

        assert len(google_url_paths) == 1
        google_url_path = google_url_paths[0]
        assert 'HG01131.final.cram.crai' in google_url_path

    @controlled_access
    def test_drs_in_terra(self):
        json_response = fetch_terra_drs_url(drs_url="drs://dg.712C/fa640b0e-9779-452f-99a6-16d833d15bd0")
        google_url_paths = [url['url'] for url in json_response['dos']['data_object']['urls'] if url['url'].startswith(GS_SCHEMA)]

        assert len(google_url_paths) == 1
        google_url_path = google_url_paths[0]
        assert 'HG01131.final.cram.crai' in google_url_path

        bucket_name = google_url_path[len(gs_prefix):].split('/')[0]

        bucket = self.google_storage_client.bucket(bucket_name, user_project=os.environ['GOOGLE_PROJECT_ID'])
        blob_key = google_url_path[len(f'{gs_prefix}{bucket}/'):]
        blob = bucket.blob(blob_key)
        download_path = os.path.join(pkg_root, 'test', google_url_path.split('/')[-1])

        expected_md5sums = [checksum for checksum in json_response['dos']['data_object']['checksums'] if checksum['type'] == 'md5']
        assert len(expected_md5sums) == 1
        expected_md5sum = expected_md5sums[0]

        assert md5sum(download_path) == expected_md5sum
        print(f"Terra download finished: {download_path}")

    def test_data_introspect(self):
        response = self.gen3_sub_client.get_programs()  # {'links': ['/v0/submission/parent', '/v0/submission/topmed', '/v0/submission/open_access', '/v0/submission/tutorial']}
        response = self.gen3_sub_client.query(query_txt='{project(first:0){project_id id}}')

        program = 'topmed'
        project = 'BAGS_GRU-IRB'
        # sample_id = 'c4422337-2b52-4cb0-8180-a069c1c9efb4'

        response = self.gen3_sub_client.get_projects(program=program)
        response = self.gen3_sub_client.get_project_dictionary(program=program, project=project)
        output_path = 'sample_node.tsv'
        response = self.gen3_sub_client.export_node(program=program,
                                                    project=project,
                                                    node_type="sample",
                                                    fileformat="tsv",
                                                    filename=output_path)

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
