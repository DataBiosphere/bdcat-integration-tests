import os
import json
import requests
import hashlib


def md5sum(file_name):
    hash = hashlib.md5()
    with open(file_name, 'rb') as f:
        for block in iter(lambda: f.read(size=100000), b''):
            hash.update(block)
    return hash.hexdigest()


def fetch_google_secret(secret):
    from google.cloud.secretmanager import SecretManagerServiceClient

    client = SecretManagerServiceClient()
    try:
        project = os.environ["GOOGLE_PROJECT_NAME"]
    except KeyError:
        raise RuntimeError('GOOGLE_PROJECT_NAME is unset.  Please set GOOGLE_PROJECT_ID.')
    response = client.access_secret_version(f'projects/{project}/secrets/{secret}/versions/latest')
    return response.payload.data.decode('UTF-8')


# TODO: Amend terra-notebook-utils function to make generic
#  https://github.com/DataBiosphere/terra-notebook-utils/blob/a97f4dbbe92725e0abf31405e8f1b1b6ede6113d/terra_notebook_utils/drs.py#L17-L30
def fetch_drs_info(drs_url):
    martha_dev_url = "https://us-central1-broad-dsde-dev.cloudfunctions.net/martha_v2"
    headers = {
        # 'authorization': f"Bearer {access_token}",  # not used in dev
        'content-type': "application/json"
    }
    resp = requests.post(martha_dev_url, headers=headers, data=json.dumps(dict(url=drs_url)))
    if 200 == resp.status_code:
        return resp.json()
    else:
        print(resp.content)
        resp.raise_for_status()
