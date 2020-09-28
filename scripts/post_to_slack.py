#!/usr/bin/env python
# coding: utf-8
import requests
import os
import sys
import argparse
import json

from scripts.run_integration_tests import wait_for_final_status, DEFAULT_BRANCH, DEFAULT_HOST, DEFAULT_PROJECT_NUM

SLACK_WEBHOOK = os.environ['SLACK_WEBHOOK']

# https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
GITLAB_USER_NAME = os.environ['GITLAB_USER_NAME']
CI_JOB_URL = os.environ['CI_JOB_URL']
CI_PIPELINE_URL = os.environ['CI_PIPELINE_URL']


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Post integration testing status to slack.')
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT_NUM)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--quiet", default=True, help='Suppress printing run messages.')
    args = parser.parse_args(argv)

    slack_notification_url = 'https://hooks.slack.com/services/' + SLACK_WEBHOOK
    headers = {
        'Content-type': 'application/json'
    }
    status = wait_for_final_status(pipeline=CI_PIPELINE_URL.split('/')[-1],
                                   host=args.host,
                                   project=args.project,
                                   quiet=args.quiet)
    data = {
        'text': GITLAB_USER_NAME + ' triggered: <' + CI_JOB_URL + '>\n' +
                f'Status is: {status}'
    }

    response = requests.post(slack_notification_url, data=json.dumps(data), headers=headers)
    response.raise_for_status()

    if not args.quiet:
        print(response.json())


if __name__ == '__main__':
    main()
