#!/usr/bin/env python
# coding: utf-8
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
    parser.add_argument("--quiet", default=False, help='Suppress printing run messages.')
    args = parser.parse_args(argv)

    job_trigger_url = args.host + '/api/v4/projects/' + str(args.project) + '/trigger/pipeline?token=' + TOKEN + '&ref=' + args.branch

    response = requests.post(job_trigger_url)
    response.raise_for_status()
    test_url = response.json()['web_url']
    pipeline = test_url.split('/')[-1].strip()
    status = 'pending'

    if not args.quiet:
        print('Starting integration tests.  Checking status in 10 seconds.\n'
              'See: ' + test_url)

    job_status_url = args.host + '/api/v4/projects/' + str(args.project) + '/pipelines/' + pipeline
    while status in ('pending', 'running'):
        time.sleep(10)
        response = requests.get(job_status_url,
                                headers={'PRIVATE-TOKEN': PRIVATE_TOKEN})
        response.raise_for_status()
        status = response.json()['status']
        if not args.quiet:
            print('Status is: ' + status)
            print('Checking status again in 10 seconds.')

    if status == 'failed':
        raise RuntimeError('Integration Tests have Failed: ' + test_url)

    if not args.quiet:
        print('Exiting.  Status was: ' + status)
        print('See: ' + test_url)


if __name__ == '__main__':
    main()
