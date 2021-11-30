import os
import json
import requests
import hashlib
import functools
import time
import jwt
import base64

from typing import List, Set, Optional
from requests.exceptions import HTTPError, ConnectionError

from terra_notebook_utils import gs

STAGE = os.environ.get('BDCAT_STAGE', 'staging')

if STAGE == 'prod':
    GEN3_DOMAIN = 'https://gen3.biodatacatalyst.nhlbi.nih.gov'
    RAWLS_DOMAIN = 'https://rawls.dsde-prod.broadinstitute.org'
    ORC_DOMAIN = 'https://firecloud-orchestration.dsde-prod.broadinstitute.org'
    BILLING_PROJECT = 'broad-integration-testing'
elif STAGE == 'staging':
    GEN3_DOMAIN = 'https://staging.gen3.biodatacatalyst.nhlbi.nih.gov'
    RAWLS_DOMAIN = 'https://rawls.dsde-alpha.broadinstitute.org'
    ORC_DOMAIN = 'https://firecloud-orchestration.dsde-alpha.broadinstitute.org'
    BILLING_PROJECT = 'drs-billing-project'
else:
    raise ValueError('Please set BDCAT_STAGE to "prod" or "staging".')


def retry(intervals: Optional[List] = None,
          errors: Optional[Set] = None,
          error_codes: Optional[Set] = None):
    """
    Retry a function if it fails with any Exception defined in the "errors" set, every x seconds,
    where x is defined by a list of floats in "intervals".  If "error_codes" are specified,
    retry on the HTTPError return codes defined in "error_codes".

    Cases to consider:

        error_codes ={} && errors={}
            Retry on any Exception.

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

    :param errors: Exceptions to catch and retry on.

    :param error_codes: HTTPError return codes to retry on.  The default is an empty set.

    :return: The result of the wrapped function or raise.
    """
    if intervals is None:
        intervals = [1, 1, 2, 4, 8]
    if error_codes is None:
        error_codes = set()
    if not error_codes and not errors:
        errors = {Exception}
    if error_codes and not errors:
        errors = {HTTPError}

    def decorate(func):
        @functools.wraps(func)
        def call(*args, **kwargs):
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


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def run_workflow():
    workspace = 'DRS-Test-Workspace'
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/submissions'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    # staging input: https://gen3.biodatacatalyst.nhlbi.nih.gov/files/dg.712C/fa640b0e-9779-452f-99a6-16d833d15bd0
    # md5sum: e87ecd9c771524dcc646c8baf6f8d3e2
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
    if STAGE == 'prod':
        # prod input: https://gen3.biodatacatalyst.nhlbi.nih.gov/files/dg.4503/d52a7cc6-67a5-4bd6-9041-a5dad3f3650a
        # md5sum: e87ecd9c771524dcc646c8baf6f8d3e2
        del data["entityType"]
        del data["entityName"]

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def import_dockstore_wf_into_terra():
    workspace = 'BDC_Dockstore_Import_Test'
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/methodconfigs'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    data = {
        "namespace": BILLING_PROJECT,
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


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def check_workflow_presence_in_terra_workspace():
    workspace = 'BDC_Dockstore_Import_Test'
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/methodconfigs?allRepos=true'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def delete_workflow_presence_in_terra_workspace():
    workspace = 'BDC_Dockstore_Import_Test'
    workflow = 'UM_aligner_wdl'
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/methodconfigs/{BILLING_PROJECT}/{workflow}'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.delete(endpoint, headers=headers)
    resp.raise_for_status()
    return {}


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def check_workflow_status(submission_id):
    workspace = 'DRS-Test-Workspace'
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/submissions/{submission_id}'

    token = gs.get_access_token()
    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def check_terra_health():
    # note: the same endpoint seems to be at: https://api.alpha.firecloud.org/status
    endpoint = f'{ORC_DOMAIN}/status'

    resp = requests.get(endpoint)
    resp.raise_for_status()
    return resp.json()


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def create_terra_workspace(workspace):
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    data = dict(namespace=BILLING_PROJECT,
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


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def delete_terra_workspace(workspace):
    endpoint = f'{RAWLS_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}'

    token = gs.get_access_token()
    headers = {'Accept': 'text/plain',
               'Authorization': f'Bearer {token}'}

    resp = requests.delete(endpoint, headers=headers)

    return resp


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
# def import_pfb(workspace):
def import_pfb(workspace, pfb_file):
    endpoint = f'{ORC_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/importPFB'

    token = gs.get_access_token()
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}
    # data = dict(url='https://cdistest-public-test-bucket.s3.amazonaws.com/export_2020-06-02T17_33_36.avro')
    data = dict(url=pfb_file)

    resp = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if resp.ok:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def pfb_job_status_in_terra(workspace, job_id):
    endpoint = f'{ORC_DOMAIN}/api/workspaces/{BILLING_PROJECT}/{workspace}/importPFB/{job_id}'
    token = gs.get_access_token()

    headers = {'Accept': 'application/json',
               'Authorization': f'Bearer {token}'}

    resp = requests.get(endpoint, headers=headers)

    if resp.ok:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


def add_requester_pays_arg_to_url(url):
    endpoint, args = url.split('?', 1)
    return f'{endpoint}?userProject={BILLING_PROJECT}&{args}'


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def import_drs_with_direct_gen3_access_token(guid: str) -> requests.Response:
    if guid.startswith('drs://'):
        guid = guid[len('drs://'):]
    else:
        raise ValueError(f'DRS URI is missing the "drs://" schema.  Please specify a DRS URI, not: {guid}')

    gen3_api_key = base64.decodebytes(os.environ['GEN3_API_KEY'].encode('utf-8')).decode('utf-8')

    decoded_api_key = jwt.decode(gen3_api_key, verify=False)
    hostname = decoded_api_key['iss'].replace('/user', '')

    response = requests.post(f'{hostname}/user/credentials/api/access_token',
                             data={"api_key": gen3_api_key, "Content-Type": "application/json"}).json()
    access_token = response['access_token']
    return requests.head(f'https://staging.gen3.biodatacatalyst.nhlbi.nih.gov/user/data/download/{guid}',
                         headers={"Authorization": f"Bearer {access_token}"})


@retry(error_codes={500, 502, 503, 504}, errors={HTTPError, ConnectionError})
def import_drs_from_gen3(guid: str, raise_for_status=True) -> requests.Response:
    """
    Import the first byte of a DRS URI using gen3.

    Makes two calls, first one to gen3, which returns the link needed to make the second
    call to the google API and fetch directly from the google bucket.
    """
    if guid.startswith('drs://'):
        guid = guid[len('drs://'):]
    else:
        raise ValueError(f'DRS URI is missing the "drs://" schema.  Please specify a DRS URI, not: {guid}')
    gen3_endpoint = f'{GEN3_DOMAIN}/user/data/download/{guid}'
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
            if raise_for_status:
                print(f'Gen3 url call succeeded for: {gen3_endpoint} with: {gen3_resp.json()} ...\n'
                      f'BUT the subsequent google called failed: {gs_endpoint_w_requester_pays} with: {gs_resp.content}')
                gs_resp.raise_for_status()
            return gs_resp
    else:
        if raise_for_status:
            print(f'Gen3 url call failed for: {gen3_endpoint} with: {gen3_resp.content}')
            gen3_resp.raise_for_status()
        return gen3_resp
