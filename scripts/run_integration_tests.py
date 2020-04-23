import requests
import time

PRIVATE_TOKEN = os.environ['BDCAT_PRIVATE_TEST_TOKEN']
TOKEN = os.environ['BDCAT_TEST_TOKEN']
BRANCH = 'master'
ENDPOINT = 'https://biodata-integration-tests.net'

def main():
    response = requests.post(f'{ENDPOINT}/api/v4/projects/3/trigger/pipeline?token={TOKEN}&ref={BRANCH}')
    response.raise_for_status()
    PIPELINE = response.json()['web_url'].split('/')[-1].strip()
    status = 'pending'

    while status in ('pending', 'running'):
        time.sleep(10)
        response = requests.get(f'{ENDPOINT}/api/v4/projects/3/pipelines/{PIPELINE}',
                                headers={'PRIVATE-TOKEN': PRIVATE_TOKEN})
        status = response.json()['status']

    if status == 'failed':
        raise RuntimeError('Integration Tests have Failed.')
    print(f'Exiting.  Status was: {status}')


if __name__ == '__main__':
    main()
