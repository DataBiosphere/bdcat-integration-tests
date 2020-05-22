#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os
import json
import time
import shutil
import google.cloud.storage

from firecloud import fiss
from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.utils import GEN3_ENDPOINTS, GS_SCHEMA

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


if __name__ == "__main__":
    unittest.main()
