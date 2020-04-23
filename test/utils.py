import os
import json
import requests
import hashlib
import functools
import time

from typing import List, Set
from requests.exceptions import HTTPError

from terra_notebook_utils import gs, GS_SCHEMA

GEN3_ENDPOINTS = {
    'staging': 'https://staging.gen3.biodatacatalyst.nhlbi.nih.gov/',
    'prod': 'https://gen3.biodatacatalyst.nhlbi.nih.gov/'
}

MARTHA_ENDPOINTS = {
    'dev': 'https://us-central1-broad-dsde-dev.cloudfunctions.net/martha_v2',
    'staging': 'https://us-central1-broad-dsde-alpha.cloudfunctions.net/martha_v2',
    'prod': 'https://us-central1-broad-dsde-prod.cloudfunctions.net/martha_v2'
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
    return response.payload.data.decode('UTF-8')


@retry(error_codes={500, 502, 503, 504})
def fetch_terra_drs_url(drs_url, martha_stage='dev'):
    headers = {'content-type': 'application/json'}
    if martha_stage != 'dev':
        headers['authorization'] = f"Bearer {fetch_google_secret(secret='')}"  # TODO: set this

    resp = requests.post(MARTHA_ENDPOINTS[martha_stage], headers=headers, data=json.dumps(dict(url=drs_url)))
    if 200 == resp.status_code:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()


def _parse_gs_url(gs_url):
    if gs_url.startswith(GS_SCHEMA):
        bucket_name, object_key = gs_url[len(GS_SCHEMA):].split("/", 1)
        return bucket_name, object_key
    else:
        raise RuntimeError(f'Invalid gs url schema.  {gs_url} does not start with {GS_SCHEMA}')


def resolve_drs_for_gs_storage(drs_url):
    drs_info = fetch_terra_drs_url(drs_url)
    print(drs_info)
    credentials_data = drs_info['googleServiceAccount']['data']
    for url_info in drs_info['dos']['data_object']['urls']:
        if url_info['url'].startswith(GS_SCHEMA):
            data_url = url_info['url']
            break
    else:
        raise Exception(f"Unable to resolve GS url for {drs_url}")
    bucket_name, key = _parse_gs_url(data_url)
    client = gs.get_client(credentials_data, project=credentials_data['project_id'])
    return client, bucket_name, key


def download(drs_url: str, filepath: str):
    client, bucket_name, key = resolve_drs_for_gs_storage(drs_url)
    blob = client.bucket(bucket_name, user_project=GOOGLE_PROJECT_NAME).blob(key)
    with open(filepath, "wb") as fh:
        blob.download_to_file(fh)

# import subprocess
# o = subprocess.check_call(['gcloud', 'auth', 'application-default', 'login', '--no-launch-browser'])
# print(o)
