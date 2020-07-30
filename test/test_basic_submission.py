#!/usr/bin/env python
# coding: utf-8
import logging
import sys
import unittest
import os
import json
import time
import shutil
import requests
import warnings
import google.cloud.storage

from gen3.submission import Gen3Submission
from gen3.auth import Gen3Auth

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.utils import (run_workflow,
                        import_dockstore_wf_into_terra,
                        check_workflow_presence_in_terra_workspace,
                        delete_workflow_presence_in_terra_workspace,
                        check_workflow_status,
                        GEN3_ENDPOINTS,
                        GS_SCHEMA)

logger = logging.getLogger(__name__)


class TestGen3DataAccess(unittest.TestCase):
    def setUp(self):
        # Stolen shamelessly: https://github.com/DataBiosphere/terra-notebook-utils/pull/59
        # Suppress the annoying google gcloud _CLOUD_SDK_CREDENTIALS_WARNING warnings
        warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials")
        # Suppress unclosed socket warnings
        warnings.simplefilter("ignore", ResourceWarning)

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

    def test_dockstore_import_in_terra(self):
        """"""
        # import the workflow into terra
        response = import_dockstore_wf_into_terra()
        method_info = response['methodConfiguration']['methodRepoMethod']
        with self.subTest('Dockstore Import Response: sourceRepo'):
            self.assertEqual(method_info['sourceRepo'], 'dockstore')
        with self.subTest('Dockstore Import Response: methodPath'):
            self.assertEqual(method_info['methodPath'], 'github.com/DataBiosphere/topmed-workflows/UM_aligner_wdl')
        with self.subTest('Dockstore Import Response: methodVersion'):
            self.assertEqual(method_info['methodVersion'], '1.32.0')

        # check that a second attempt gives a 409 error
        try:
            import_dockstore_wf_into_terra()
        except requests.exceptions.HTTPError as e:
            with self.subTest('Dockstore Import Response: 409 conflict'):
                self.assertEqual(e.response.status_code, 409)

        # check status that the workflow is seen in terra
        wf_seen_in_terra = False
        response = check_workflow_presence_in_terra_workspace()
        for wf_response in response:
            method_info = wf_response['methodRepoMethod']
            if method_info['methodPath'] == 'github.com/DataBiosphere/topmed-workflows/UM_aligner_wdl' \
                    and method_info['sourceRepo'] == 'dockstore' \
                    and method_info['methodVersion'] == '1.32.0':
                wf_seen_in_terra = True
                break
        with self.subTest('Dockstore Check Workflow Seen'):
            self.assertTrue(wf_seen_in_terra)

        # delete the workflow
        delete_workflow_presence_in_terra_workspace()

        # check status that the workflow is no longer seen in terra
        wf_seen_in_terra = False
        response = check_workflow_presence_in_terra_workspace()
        for wf_response in response:
            method_info = wf_response['methodRepoMethod']
            if method_info['methodPath'] == 'github.com/DataBiosphere/topmed-workflows/UM_aligner_wdl' \
                    and method_info['sourceRepo'] == 'dockstore' \
                    and method_info['methodVersion'] == '1.32.0':
                wf_seen_in_terra = True
                break
        with self.subTest('Dockstore Check Workflow Not Seen'):
            self.assertFalse(wf_seen_in_terra)


    def test_drs_workflow_in_terra(self):
        """This test runs md5sum in a fixed workspace using a drs url from gen3."""
        response = run_workflow()
        status = response['status']
        with self.subTest('Dockstore Workflow Run Submitted'):
            self.assertEqual(status, 'Submitted')
        with self.subTest('Dockstore Workflow Run Responds with DRS.'):
            self.assertTrue(response['workflows'][0]['inputResolutions'][0]['value'].startswith('drs://'))

        submission_id = response['submissionId']

        # md5sum should run for about 4 minutes, but may take far longer(?); give a generous timeout
        timeout = 10 * 60  # 10 minutes
        while status == 'Submitted':
            response = check_workflow_status(submission_id=submission_id)
            time.sleep(10)
            timeout -= 10
            print(response)
            status = response['status']
            if timeout < 0:
                raise RuntimeError('The md5sum workflow run timed out.  '
                                   f'Expected 4 minutes, but took longer than {float(timeout) / 60.0} minutes.')

        with self.subTest('Dockstore Workflow Run Completed Successfully'):
            self.assertEqual(status, "Done")

    def test_terra_health(self):
        firecloud_status = 'https://api.alpha.firecloud.org/status'
        response = requests.get(firecloud_status).json()

        with self.subTest('Basic Terra Health Check'):
            self.assertTrue(response['ok'] == True)

        with self.subTest('Basic Terra Systems Health Check'):
            self.assertTrue(response['systems'] == {
                "Thurloe": {
                  "ok": True
                },
                "Sam": {
                  "ok": True
                },
                "Consent": {
                  "ok": True
                },
                "is_admin_sa_registered": {
                  "ok": True
                },
                "Rawls": {
                  "ok": True
                },
                "Agora": {
                  "ok": True
                },
                "is_trial_billing_sa_registered": {
                  "ok": True
                },
                "GoogleBuckets": {
                  "ok": True
                },
                "LibraryIndex": {
                  "ok": True
                },
                "OntologyIndex": {
                  "ok": True
                }
              })


if __name__ == "__main__":
    unittest.main()
