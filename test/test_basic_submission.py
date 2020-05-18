#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os
import json
import asyncio
import shutil
import google.cloud.storage

import firecloud.api
from firecloud import fiss
from gen3.tools import indexing
from gen3.index import Gen3Index
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
        gcloud_cred_dir = os.path.expanduser('~/.config/gcloud')
        cls.gen3_endpoint = GEN3_ENDPOINTS['staging']
        with open(os.environ['GEN3KEY'], 'r') as f:
            cls.gen3_key = json.loads(f.read())
        if not os.path.exists(gcloud_cred_dir):
            os.makedirs(gcloud_cred_dir, exist_ok=True)
        try:
            shutil.copy(os.environ['TEST_MULE_CREDENTIALS'],
                        os.path.expanduser('~/.config/gcloud/application_default_credentials.json'))
        except shutil.SameFileError:
            pass
        cls.gen3_auth_client = Gen3Auth(endpoint=cls.gen3_endpoint, refresh_token=cls.gen3_key)
        cls.gen3_sub_client = Gen3Submission(endpoint=cls.gen3_endpoint, auth_provider=cls.gen3_auth_client)
        cls.google_storage_client = google.cloud.storage.Client(project=os.environ['GOOGLE_PROJECT_ID'])
        cls.output_tsv_path = os.path.join(pkg_root, 'test_gen3_node.tsv')
        cls.gen3_manifest_path = os.path.join(pkg_root, 'test_gen3_manifest.csv')
        cls.drs_file_path = None

    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(cls.output_tsv_path):
            os.remove(cls.output_tsv_path)
        if os.path.exists(cls.gen3_manifest_path):
            os.remove(cls.gen3_manifest_path)
        if cls.drs_file_path and os.path.exists(cls.drs_file_path):
            os.remove(cls.drs_file_path)

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

        bucket_name = google_url_path[len(GS_SCHEMA):].split('/')[0]

        bucket = self.google_storage_client.bucket(bucket_name, user_project=os.environ['GOOGLE_PROJECT_ID'])
        blob_key = google_url_path[len(f'{GS_SCHEMA}{bucket}/'):]
        blob = bucket.blob(blob_key)
        download_path = os.path.join(pkg_root, 'test', google_url_path.split('/')[-1])

        expected_md5sums = [checksum for checksum in json_response['dos']['data_object']['checksums'] if checksum['type'] == 'md5']
        assert len(expected_md5sums) == 1
        expected_md5sum = expected_md5sums[0]

        assert md5sum(download_path) == expected_md5sum
        print(f"Terra download finished: {download_path}")

    def download_manifest_csv(self):
        """
        Downloads a gen3 manifest for the current stage.

        # example lines from file on gen3 staging:
        line1 = 'dg.712C/d397a887-4224-4cd5-a8ad-e86d1e9ce8ac,gs://fc-56ac46ea-efc4-4683-b6d5-6d95bed41c5e/CCDG_13607/Project_CCDG_13607_B01_GRM_WGS.gVCF.2019-02-06/Sample_NA19316/analysis/checksum/NA19316.haplotypeCalls.er.raw.g.vcf.gz.md5,,*,1f558a3ca8f52b1294e93f1af61daefc,70,'
        line2 = 'dg.712C/edda4670-6bb3-4a92-88a5-89ddbee5c73d,gs://fc-56ac46ea-efc4-4683-b6d5-6d95bed41c5e/CCDG_13607/Project_CCDG_13607_B01_GRM_WGS.gVCF.2019-02-06/Sample_NA19712/analysis/checksum/NA19712.haplotypeCalls.er.raw.g.vcf.gz.md5,,*,8a2a67ede7d7b8337044f6ee11e8eb43,70,'
        line3 = 'dg.712C/929d3bec-5eb4-47b4-aec2-d49f0e71b849,gs://fc-56ac46ea-efc4-4683-b6d5-6d95bed41c5e/CCDG_13607/Project_CCDG_13607_B01_GRM_WGS.gVCF.2019-02-06/Sample_NA20503/analysis/checksum/NA20503.haplotypeCalls.er.raw.g.vcf.gz.md5,,*,9db07144e9e79369433d8de538066dc8,70,'
        """
        # Part of their tutorial: https://github.com/uc-cdis/gen3sdk-python#download-manifest
        # Seems to break(?): https://github.com/uc-cdis/gen3sdk-python/issues/42
        # Streams errors but file downloads at least partially
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(
            indexing.async_download_object_manifest(
                self.gen3_endpoint,
                output_filename=self.gen3_manifest_path,
                num_processes=1,
                max_concurrent_requests=1,
            )
        )

    @controlled_access
    def test_gen3_drs_to_terra(self):
        # grab a gen3 manifest for our current stage; this will spray error messages left and right
        # but apparently still produces a file
        self.download_manifest_csv()

        with open(self.gen3_manifest_path, 'r') as f:
            for i, line in enumerate(f):
                if i != 0:
                    # grab the first one we see
                    line_item = line.split(",")
                    drs_uri = f'drs://{line_item[0]}'
                    gs_uri = line_item[1]
                    md5_hash = line_item[4]
                    self.drs_file_path = os.path.join(pkg_root, gs_uri.split('/')[-1])
                    break
        # "drs://dg.712C/929d3bec-5eb4-47b4-aec2-d49f0e71b849"
        json_response = download(drs_uri, filepath=self.drs_file_path, martha_stage='prod')
        print(json_response)

    @controlled_access
    def test_gen3(self):
        index = Gen3Index(self.gen3_endpoint)
        assert index.is_healthy() is True

        response = self.gen3_sub_client.get_programs()
        # print(json.dumps(response, indent=2))
        # {'links': ['/v0/submission/tutorial']}

        # response = firecloud.api.create_workspace(namespace=terra_billing_project,
        #                                           name='test2')
        # print(response.content)
        # response.raise_for_status()
        # # {"attributes": {}, "authorizationDomain": [], "bucketName": "fc-8a5a3ba1-98ae-45f1-bc86-22e55f1d3b24",
        # #  "createdBy": "biodata.integration.test.mule@gmail.com", "createdDate": "2020-05-02T06:26:11.696Z",
        # #  "isLocked": false, "lastModified": "2020-05-02T06:26:11.696Z", "name": "test2",
        # #  "namespace": "broad-integration-testing", "workflowCollectionName": "8a5a3ba1-98ae-45f1-bc86-22e55f1d3b24",
        # #  "workspaceId": "8a5a3ba1-98ae-45f1-bc86-22e55f1d3b24"}

        response = self.gen3_sub_client.query(query_txt='{project(first:0){project_id id}}')
        # print(json.dumps(response, indent=2))
        # {"data": {
        #     "project": [
        #         {
        #             "id": "2abc8ded-013b-5acd-a00e-d1fc8b050db6",
        #             "project_id": "tutorial-synthetic_data_set_open_access_1"
        #         },
        #         {
        #             "id": "2eef3f52-2ffd-58f9-9b5f-0339065dc475",
        #             "project_id": "tutorial-synthetic_data_set_1"
        #         },
        #         {
        #             "id": "ffd0aacf-1079-51e8-adae-53ea2ca55f7c",
        #             "project_id": "tutorial-synthetic_data_set_controlled_access_1"
        #         }]}}

        program = 'tutorial'
        project = 'synthetic_data_set_controlled_access_1'

        response = self.gen3_sub_client.get_projects(program=program)
        print(json.dumps(response, indent=2))
        # {
        #     "links": [
        #         "/v0/submission/tutorial/synthetic_data_set_open_access_1",
        #         "/v0/submission/tutorial/synthetic_data_set_1",
        #         "/v0/submission/tutorial/synthetic_data_set_controlled_access_1"
        #     ]
        # }

    @controlled_access
    def test_upload_gen3_manifest_to_terra(self):
        # gen3's test tsv apparently breaks Terra: b'{\n  "statusCode": 400,\n  "source": "FireCloud",\n  "timestamp": 1588401485851,\n  "causes": [],\n  "stackTrace": [],\n  "message": "Invalid first column header, entity type should end in _id"\n}\n'
        # otherwise both endpoints return successful responses and terra accepts a dummy tsv below
        # TODO: get gen3 to return staging tsv manifests with correct column headers plus a line of fake data
        # TODO: file a ticket to get gen3 to implement a sanity check around this
        terra_billing_project = os.environ['GOOGLE_TEST_ACCOUNT']
        program = 'tutorial'
        project = 'tutorial-synthetic_data_set_open_access_1'

        output_path = 'sample_node.tsv'
        response = self.gen3_sub_client.export_node(program=program,
                                                    project=project,
                                                    node_type="sample",
                                                    fileformat="tsv",
                                                    filename=output_path)
        print(json.dumps(response, indent=2))

        with open(self.output_tsv_path, 'r') as f:
            gen3_manifest = f.read()

        # TODO: import from terra_notebook_utils; doesn't pip install the "test" dir
        # TODO: don't hard-code stage
        resp = fiss.fapi.upload_entities(namespace=terra_billing_project,
                                         workspace=os.environ['TERRA_PROD_WORKSPACE'],

                                         # TODO: Replace the below with "gen3_manifest" once gen3 has made their changes
                                         entity_data="\t".join([f"entity:nothing_id", "foo", "bar"]) + '\na\tb\tc',
                                         model='flexible')
        print(resp.content)
        resp.raise_for_status()


# TODO: Swap credentials to include these
# class TestFirecloud(unittest.TestCase):
#     def test_firecloud_submission_unauthorized(self):
#         response = firecloud.api.create_submission(
#             wnamespace='default',
#             workspace='default',
#             cnamespace='default',
#             config={},
#             entity=None,
#             etype=None,
#             expression=None,
#             use_callcache=True)
#
#         assert '401 Unauthorized' in response.content.decode('utf-8')
#         assert response.status_code == 401


if __name__ == "__main__":
    unittest.main()
