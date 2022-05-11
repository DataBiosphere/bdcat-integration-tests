#!/usr/bin/env python3
import requests
import time
import os
import sys
import argparse

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.utils import retry

PRIVATE_TOKEN = os.environ['GITLAB_READ_TOKEN']
TOKEN = os.environ['GITLAB_TRIGGER_TOKEN']
DEFAULT_HOST = 'https://biodata-integration-tests.net'
DEFAULT_BRANCH = 'master'
DEFAULT_PROJECT_NUM = 3


@retry(error_codes={500, 502, 503, 504}, errors={requests.exceptions.HTTPError, ConnectionError})
def get_status(pipeline, host=DEFAULT_HOST, project=DEFAULT_PROJECT_NUM):
    job_status_url = f'{host}/api/v4/projects/{project}/pipelines/{pipeline}'
    response = requests.get(job_status_url, headers={'PRIVATE-TOKEN': PRIVATE_TOKEN})
    response.raise_for_status()
    return response.json()['status']


def wait_for_final_status(pipeline, host=DEFAULT_HOST, project=DEFAULT_PROJECT_NUM, quiet=False):
    status = 'pending'
    while status in ('pending', 'running'):
        time.sleep(10)
        status = get_status(pipeline=pipeline, host=host, project=project)
        if not quiet:
            print(f'Status is: {status}')
            print('Checking status again in 10 seconds.')
    return status


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Gitlab Test Trigger')
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT_NUM)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--quiet", default=False, help='Suppress printing run messages.')
    args = parser.parse_args(argv)

    job_trigger_url = f'{args.host}/api/v4/projects/{args.project}/trigger/pipeline?token={TOKEN}&ref={args.branch}'

    response = requests.post(job_trigger_url)
    response.raise_for_status()
    test_url = response.json()['web_url']
    pipeline = test_url.split('/')[-1].strip()

    if not args.quiet:
        print('Starting integration tests.  Checking status in 10 seconds.')
        print(f'See: {test_url}')

    status = wait_for_final_status(pipeline=pipeline, host=args.host, project=args.project, quiet=args.quiet)

    if status == 'failed':
        raise RuntimeError('Integration Tests have Failed: ' + test_url)

    if not args.quiet:
        print(f'Exiting.  Status was: {status}')
        print(f'See: {test_url}')


if __name__ == '__main__':
    main()
