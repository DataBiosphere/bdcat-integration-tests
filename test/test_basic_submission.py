#!/usr/bin/env python3
import logging
import sys
import unittest
import os
import json
import time
import shutil
import requests
import datetime
import warnings

import terra_notebook_utils as tnu

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.infra.testmode import staging_only
from test.utils import (run_workflow,
                        create_terra_workspace,
                        delete_terra_workspace,
                        pfb_job_status_in_terra,
                        import_pfb,
                        retry,
                        check_terra_health,
                        import_dockstore_wf_into_terra,
                        check_workflow_presence_in_terra_workspace,
                        delete_workflow_presence_in_terra_workspace,
                        check_workflow_status,
                        import_drs_from_gen3,
                        STAGE)

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
        if not os.path.exists(gcloud_cred_dir):
            os.makedirs(gcloud_cred_dir, exist_ok=True)
        try:
            shutil.copy(os.environ['TEST_MULE_CREDENTIALS'],
                        os.path.expanduser('~/.config/gcloud/application_default_credentials.json'))
        except shutil.SameFileError:
            pass
        print(f'Terra [{STAGE}] Health Status:\n\n{json.dumps(check_terra_health(), indent=4)}')

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            delete_workflow_presence_in_terra_workspace()
        except:
            pass

    @retry(errors={requests.exceptions.HTTPError}, error_codes={409})
    def test_dockstore_import_in_terra(self):
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

    @staging_only
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
        # also configurable manually via MD5SUM_TEST_TIMEOUT if held in a pending state
        timeout = twenty_minutes = int(os.environ.get('MD5SUM_TEST_TIMEOUT', 20 * 60))
        while status != 'Done':
            response = check_workflow_status(submission_id=submission_id)
            time.sleep(20)
            timeout -= 20
            status = response['status']
            print(f"md5sum workflow state is: {response['workflows'][0]['status']}.  Checking again in 20 seconds.")
            if timeout < 0:
                print(json.dumps(response, indent=4))
                raise RuntimeError('The md5sum workflow run timed out.  '
                                   f'Expected 4 minutes, but took longer than '
                                   f'{float(twenty_minutes - timeout) / 60.0} minutes.')

        with self.subTest('Dockstore Workflow Run Completed Successfully'):
            if response['workflows'][0]['status'] != "Succeeded":
                raise RuntimeError(f'The md5sum workflow did not succeed:\n{json.dumps(response, indent=4)}')

    def test_pfb_handoff_from_gen3_to_terra(self):
        time_stamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
        workspace_name = f'drs_test_{time_stamp}_delete_me'

        with self.subTest('Create a terra workspace.'):
            response = create_terra_workspace(workspace=workspace_name)
            self.assertTrue('workspaceId' in response)
            self.assertTrue(response['createdBy'] == 'biodata.integration.test.mule@gmail.com')

        with self.subTest('Import static pfb into the terra workspace.'):
            response = import_pfb(workspace=workspace_name)
            self.assertTrue('jobId' in response)

        with self.subTest('Check on the import static pfb job status.'):
            response = pfb_job_status_in_terra(workspace=workspace_name, job_id=response['jobId'])
            # this should take < 60 seconds
            while response['status'] in ['Translating', 'ReadyForUpsert', 'Upserting', 'Pending']:
                time.sleep(2)
                response = pfb_job_status_in_terra(workspace=workspace_name, job_id=response['jobId'])
            self.assertTrue(response['status'] == 'Done',
                            msg=f'Expecting status: "Done" but got "{response["status"]}".\n'
                                f'Full response: {json.dumps(response, indent=4)}')

        with self.subTest('Delete the terra workspace.'):
            response = delete_terra_workspace(workspace=workspace_name)
            self.assertTrue(response.status_code == 202)
            response = delete_terra_workspace(workspace=workspace_name)
            self.assertTrue(response.status_code == 404)

    @staging_only
    def test_controlled_data_access(self):
        # this DRS URI only exists on staging/alpha
        os.environ['TERRA_DEPLOYMENT_ENV'] = 'alpha'
        tnu.drs.head('drs://dg.712C/04fbb96d-68c9-4922-801e-9b1350be3b94')
        del os.environ['TERRA_DEPLOYMENT_ENV']

    @staging_only
    def test_import_drs_from_gen3(self):
        # file is ~1gb, so only download the first byte to check for access
        import_drs_from_gen3('drs://dg.712C/95dc0845-d895-489f-aaf8-583a676037f7')

        # TODO: Investigate the following:
        # the following file is 5b, but we get a "Not enough segments" Error, so there may be problems with small files:
        # <p class="body">Error Message:</p>\n          <p class="introduction">Not enough segments</p>\n          \n          <div>\n            \n            <p class="body">Please try again!</p>
        # import_drs_from_gen3('drs://dg.712C/b7a10338-6fb6-4201-adde-0ee933e069bc')


if __name__ == "__main__":
    unittest.main()
