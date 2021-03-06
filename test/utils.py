import os
import json
import requests
import hashlib
import functools
import time

from typing import List, Set
from requests.exceptions import HTTPError

from terra_notebook_utils import gs


GEN3_ENDPOINTS = {
    'staging': 'https://staging.gen3.biodatacatalyst.nhlbi.nih.gov/',
    'prod': 'https://gen3.biodatacatalyst.nhlbi.nih.gov/'
}

try:
    GOOGLE_PROJECT_NAME = os.environ["GOOGLE_PROJECT_NAME"]
except KeyError:
    raise RuntimeError('GOOGLE_PROJECT_NAME is unset.  Please set GOOGLE_PROJECT_ID.')


def retry(intervals: List = [1, 1, 2, 4, 8],
          errors: Set = {HTTPError},
          error_codes: Set = {}):
    """
    Retry a function if it fails with any Exception defined in the "errors" set, every x seconds,
    where x is defined by a list of floats in "intervals".  If "error_codes" are specified,
    retry on the HTTPError return codes defined in "error_codes".

    Cases to consider:

        error_codes ={} && errors={}
            Don't retry on anything.

        error_codes ={500} && errors={}
        error_codes ={500} && errors={HTTPError}
            Retry only on HTTPErrors that return status_code 500.

        error_codes ={} && errors={HTTPError}
            Retry on all HTTPErrors regardless of error code.

        error_codes ={} && errors={AssertionError}
            Only retry on AssertionErrors.

    :param List[float] intervals: A list of times in seconds we keep retrying until returning failure.
        Defaults to retrying with the following exponential backoff before failing:
            1s, 1s, 2s, 4s, 8s

    :param errors: Exceptions to catch and retry on.  Defaults to: {HTTPError}.

    :param error_codes: HTTPError return codes to retry on.  The default is an empty set.

    :return: The result of the wrapped function or raise.
    """
    def decorate(func):
        @functools.wraps(func)
        def call(*args, **kwargs):
            if error_codes:
                errors.add(HTTPError)
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(errors) as e:
                    if not intervals:
                        raise
                    interval = intervals.pop(0)
                    if isinstance(e, HTTPError):
                        if error_codes and e.response.status_code not in error_codes:
                            raise
                    print(f"Error in {func}: {e}. Retrying after {interval} s...")
                    time.sleep(interval)
        return call
    return decorate


def md5sum(file_name):
    hash = hashlib.md5()
    with open(file_name, 'rb') as f:
        for block in iter(lambda: f.read(size=100000), b''):
            hash.update(block)
    return hash.hexdigest()


def fetch_google_secret(secret):
    from google.cloud.secretmanager import SecretManagerServiceClient

    client = SecretManagerServiceClient()
    response = client.access_secret_version(f'projects/{GOOGLE_PROJECT_NAME}/secrets/{secret}/versions/latest')
    return response.payload.data.decode('utf-8')


@retry(error_codes={500, 502, 503, 504})
def run_workflow():
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    workspace = 'DRS-Test-Workspace'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/submissions'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    data = {
        "methodConfigurationNamespace": "drs_tests",
        "methodConfigurationName": "md5sum",
        "entityType": "data_access_test_drs_uris_set",
        "entityName": "md5sum_2020-05-19T17-52-42",
        "expression": "this.data_access_test_drs_uriss",
        "useCallCache": False,
        "deleteIntermediateOutputFiles": True,
        "workflowFailureMode": "NoNewCalls"
    }

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504})
def import_dockstore_wf_into_terra():
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    workspace = 'BDC_Dockstore_Import_Test'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/methodconfigs'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    data = {
        "namespace": billing_project,
        "name": "UM_aligner_wdl",
        "rootEntityType": "",
        "inputs": {},
        "outputs": {},
        "prerequisites": {},
        "methodRepoMethod": {
            "sourceRepo": "dockstore",
            "methodPath": "github.com/DataBiosphere/topmed-workflows/UM_aligner_wdl",
            "methodVersion": "1.32.0"
        },
        "methodConfigVersion": 1,
        "deleted": False
    }

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504})
def check_workflow_presence_in_terra_workspace():
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    workspace = 'BDC_Dockstore_Import_Test'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/methodconfigs?allRepos=true'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504})
def delete_workflow_presence_in_terra_workspace():
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    workspace = 'BDC_Dockstore_Import_Test'
    billing_project = 'drs-billing-project'
    workflow = 'UM_aligner_wdl'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/methodconfigs/{billing_project}/{workflow}'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.delete(endpoint, headers=headers)
    resp.raise_for_status()
    return {}


@retry(error_codes={500, 502, 503, 504})
def check_workflow_status(submission_id):
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    workspace = 'DRS-Test-Workspace'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/submissions/{submission_id}'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504})
def check_terra_health():
    # note: the same endpoint seems to be at: https://api.alpha.firecloud.org/status
    endpoint = 'https://firecloud-orchestration.dsde-alpha.broadinstitute.org/status'

    resp = requests.get(endpoint)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504})
def create_terra_workspace(workspace):
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    endpoint = f'{domain}/api/workspaces'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    data = dict(namespace='drs-billing-project',
                name=workspace,
                authorizationDomain=[],
                attributes={'description': ''},
                copyFilesWithPrefix='notebooks/')

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if resp.ok:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


@retry(error_codes={500, 502, 503, 504})
def delete_terra_workspace(workspace):
    domain = 'https://rawls.dsde-alpha.broadinstitute.org'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}'

    token = gs.get_access_token()
    headers = {'Accept': 'text/plain',
               'Authorization': f'Bearer {token}'}

    resp = requests.delete(endpoint, headers=headers)

    return resp


@retry(error_codes={500, 502, 503, 504})
def import_pfb(workspace):
    domain = 'https://firecloud-orchestration.dsde-alpha.broadinstitute.org'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/importPFB'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}
    data = dict(url='https://cdistest-public-test-bucket.s3.amazonaws.com/export_2020-06-02T17_33_36.avro')

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if resp.ok:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


@retry(error_codes={500, 502, 503, 504})
def pfb_job_status_in_terra(workspace, job_id):
    domain = 'https://firecloud-orchestration.dsde-alpha.broadinstitute.org'
    billing_project = 'drs-billing-project'
    endpoint = f'{domain}/api/workspaces/{billing_project}/{workspace}/importPFB/{job_id}'
    token = gs.get_access_token()

    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)

    if resp.ok:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


def add_requester_pays_arg_to_url(url, billing_project='drs-billing-project'):
    endpoint, args = url.split('?', 1)
    return f'{endpoint}?userProject={billing_project}&{args}'


@retry(error_codes={500, 502, 503, 504})
def import_drs_from_gen3(guid: str) -> requests.Response:
    """
    Import the first byte of a DRS URI using gen3.

    Makes two calls, first one to gen3, which returns the link needed to make the second
    call to the google API and fetch directly from the google bucket.
    """
    if guid.startswith('drs://'):
        guid = guid[len('drs://'):]
    else:
        raise ValueError(f'DRS URI is missing the "drs://" schema.  Please specify a DRS URI, not: {guid}')
    gen3_endpoint = f'https://staging.gen3.biodatacatalyst.nhlbi.nih.gov/user/data/download/{guid}'
    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}
    gen3_resp = requests.get(gen3_endpoint, headers=headers)

    if gen3_resp.ok:

        # Example of the url that gen3 returns:
        #   google_uri = 'https://storage.googleapis.com/fc-56ac46ea-efc4-4683-b6d5-6d95bed41c5e/CCDG_13607/Project_CCDG_13607_B01_GRM_WGS.gVCF.2019-02-06/Sample_HG03611/analysis/HG03611.haplotypeCalls.er.raw.g.vcf.gz'
        #   access_id_arg = 'GoogleAccessId=cirrus@stagingdatastage.iam.gserviceaccount.com'
        #   expires_arg = 'Expires=1607381713'
        #   signature_arg = 'Signature=hugehashofmanycharsincluding%=='
        #   endpoint_looks_like = f'{google_uri}?{access_id_arg}&{expires_arg}&{signature_arg}'
        gs_endpoint = gen3_resp.json()["url"]
        gs_endpoint_w_requester_pays = add_requester_pays_arg_to_url(gs_endpoint)

        # Use 'Range' header to only download the first two bytes
        # https://cloud.google.com/storage/docs/json_api/v1/parameters#range
        headers['Range'] = 'bytes=0-1'

        gs_resp = requests.get(gs_endpoint_w_requester_pays, headers=headers)
        if gs_resp.ok:
            return gs_resp
        else:
            print(f'Gen3 url call succeeded for: {gen3_endpoint} with: {gen3_resp.json()} ...\n'
                  f'BUT the subsequent google called failed: {gs_endpoint_w_requester_pays} with: {gs_resp.content}')
            gs_resp.raise_for_status()
    else:
        print(f'Gen3 url call failed for: {gen3_endpoint} with: {gen3_resp.content}')
        gen3_resp.raise_for_status()
