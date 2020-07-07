#!/usr/bin/env python
# coding: utf-8

import requests
import os
import sys
import argparse
import json

SLACK_WEBHOOK = os.environ['SLACK_WEBHOOK']

# https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
GITLAB_USER_NAME = os.environ['GITLAB_USER_NAME']
CI_JOB_URL = os.environ['CI_JOB_URL']


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Post integration testing status to the nhlbi-biodatacatalyst slack.')
    parser.add_argument("--quiet", default=True, help='Suppress printing run messages.')
    args = parser.parse_args(argv)

    slack_notification_url = 'https://hooks.slack.com/services/' + SLACK_WEBHOOK
    headers = {
        'Content-type': 'application/json'
    }
    data = {
        'text': GITLAB_USER_NAME + ' triggered: ' + CI_JOB_URL
    }

    response = requests.post(slack_notification_url, data=json.dumps(data), headers=headers)
    response.raise_for_status()

    if not args.quiet:
        print(response.json())


if __name__ == '__main__':
    main()
