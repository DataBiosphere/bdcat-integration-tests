#!/usr/bin/env python3
import logging
import unittest
import json
import time
import datetime
import os
import sys

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
print("This is the package root{0}".format(pkg_root))
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
                        import_drs_with_direct_gen3_access_token,
                        BILLING_PROJECT,
                        STAGE)

logger = logging.getLogger(__name__)

# TODO: this is the old normal sized file, but we can just test with it and then use the bigger one
large_pfb = 'https://cdistest-public-test-bucket.s3.amazonaws.com/export_2020-06-02T17_33_36.avro'


class TestPerformance(unittest.TestCase):
    def test_large_pfb_handoff_from_gen3_to_terra(self):
        time_stamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
        workspace_name = f'drs_test_{time_stamp}_delete_me'

        with self.subTest('Create a terra workspace.'):
            response = create_terra_workspace(workspace=workspace_name)
            self.assertTrue('workspaceId' in response)
            self.assertTrue(response['createdBy'] == 'biodata.integration.test.mule@gmail.com')

        with self.subTest('Import static pfb into the terra workspace.'):
            response = import_pfb(workspace=workspace_name, pfb_file=large_pfb)
            self.assertTrue('jobId' in response)

        with self.subTest('Check on the import static pfb job status.'):
            response = pfb_job_status_in_terra(workspace=workspace_name, job_id=response['jobId'])
            # this should take < ??????????
            while response['status'] in ['Translating', 'ReadyForUpsert', 'Upserting', 'Pending']:
                time.sleep(2)
                response = pfb_job_status_in_terra(workspace=workspace_name, job_id=response['jobId'])
            self.assertTrue(response['status'] == 'Done',
                            msg=f'Expecting status: "Done" but got "{response["status"]}".\n'
                                f'Full response: {json.dumps(response, indent=4)}')

        with self.subTest('Delete the terra workspace.'):
            response = delete_terra_workspace(workspace=workspace_name)
            if not response.ok:
                raise RuntimeError(
                    f'Could not delete the workspace "{workspace_name}": [{response.status_code}] {response}')
            if response.status_code != 202:
                logger.critical(f'Response {response.status_code} has changed: {response}')
            response = delete_terra_workspace(workspace=workspace_name)
            self.assertTrue(response.status_code == 404)


if __name__ == "__main__":
    unittest.main()
