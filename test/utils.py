import os


def fetch_google_secret(secret):
    from google.cloud.secretmanager import SecretManagerServiceClient

    client = SecretManagerServiceClient()
    try:
        project = os.environ["GOOGLE_PROJECT_ID"]
    except KeyError:
        raise RuntimeError('GOOGLE_PROJECT_ID is unset.  Please set GOOGLE_PROJECT_ID.')
    response = client.access_secret_version(f'projects/{project}/secrets/{secret}/versions/latest')
    return response.payload.data.decode('UTF-8')
