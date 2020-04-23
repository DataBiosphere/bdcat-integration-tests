import requests
import time
import argparse

PRIVATE_TOKEN = os.environ['BDCAT_PRIVATE_TEST_TOKEN']
TOKEN = os.environ['BDCAT_TEST_TOKEN']
DEFAULT_HOST = 'https://biodata-integration-tests.net'
DEFAULT_BRANCH = 'master'
DEFAULT_PROJECT_NUM = 3

def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Gitlab Test Trigger')
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT_NUM)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--host", default=DEFAULT_HOST)
    o = parser.parse_args(argv)

    response = requests.post(f'{o.host}/api/v4/projects/{o.project}/trigger/pipeline?token={TOKEN}&ref={o.branch}')
    response.raise_for_status()
    pipeline = response.json()['web_url'].split('/')[-1].strip()
    status = 'pending'

    while status in ('pending', 'running'):
        time.sleep(10)
        response = requests.get(f'{o.host}/api/v4/projects/{o.project}/pipelines/{pipeline}',
                                headers={'PRIVATE-TOKEN': PRIVATE_TOKEN})
        status = response.json()['status']

    if status == 'failed':
        raise RuntimeError('Integration Tests have Failed.')
    print(f'Exiting.  Status was: {status}')


if __name__ == '__main__':
    main()
