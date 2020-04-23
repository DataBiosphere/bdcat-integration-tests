import requests
import time
import os
import sys
import argparse

PRIVATE_TOKEN = os.environ['GITLAB_READ_TOKEN']
TOKEN = os.environ['GITLAB_TRIGGER_TOKEN']
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

    print(f'Starting integration tests.  Status: {status}.  Checking back in 10 seconds.')
    while status in ('pending', 'running'):
        time.sleep(10)
        response = requests.get(f'{o.host}/api/v4/projects/{o.project}/pipelines/{pipeline}',
                                headers={'PRIVATE-TOKEN': PRIVATE_TOKEN})
        try:
            status = response.json()['status']
            print(f'Status is: {status}.  Checking status again in 10 seconds.')
        except:
            print(response.content)
            exit(0)

    if status == 'failed':
        raise RuntimeError('Integration Tests have Failed.')
    print(f'Exiting.  Status was: {status}')


if __name__ == '__main__':
    main()
