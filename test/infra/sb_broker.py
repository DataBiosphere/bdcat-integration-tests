import logging
import os
import random
import string
import time
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Optional, List

import requests

logger = logging.getLogger(__name__)

BROKER_URL = os.getenv('BDCAT_SB_BROKER_URL', 'https://qa-broker.sbgenomics.com')
BROKER_TOKEN = os.getenv('BDCAT_SB_BROKER_TOKEN')


@unique
class SBEnv(Enum):

    """Internal SB environment names for BDC"""

    staging = 'f4c-staging-vayu'
    production = 'ffc'


def new_task_id(sb_environment: SBEnv, new_task: dict) -> str:
    """Generate a unique task ID for test runs"""
    date = datetime.now(tz=timezone.utc)

    return 'bdc-{}-{}{}-{}-{}'.format(
        sb_environment.name,
        new_task['test_plan_id'],
        '-subset' if new_task.get('test_ids') else '',
        date.strftime('%Y%m%d-%H%M%S'),

        # extra randomness for when test runs are started in the same second
        ''.join(random.sample(string.ascii_lowercase, 3))
    )


class SevenBridgesBrokerClient:

    """HTTP client for the SevenBridges QA broker

    The SevenBridges QA broker is a service exposed on the public internet
    that acts as an intermediary for running tests on the internal
    infrastructure of SevenBridges.

    A token obtained manually is needed for authentication.
    """

    def __init__(self, token=BROKER_TOKEN, base_url=BROKER_URL):
        if token is not None:
            self._headers = {'Authorization': f'Bearer {token}'}
        else:
            self._headers = {}

        self._base_url = base_url
        self._session = requests.Session()

    @staticmethod
    def _check_response(resp, *, expected_code):
        if resp.status_code != expected_code:
            raise requests.HTTPError(
                f'[{resp.request.method} {resp.url} {resp.reason}] '
                f'Expected 200, got {resp.status_code}: {resp.text}'
            )

    def request(self, method, path, *, json=None, params=None):
        url = self._base_url + path
        return self._session.request(method, url,
                                     headers=self._headers,
                                     json=json, params=params)

    def new_test_run(self, sb_environment: SBEnv, test_plan: str,
                     subset: Optional[List[str]] = None) -> dict:
        """Start a new test run

        :param sb_environment: Target SevenBridges environment.
        :param test_plan: SevenBridges-internal tests path.
        :param subset: Subset of test names from the test plan to run.
        :raises requests.HTTPError: Test run could not be started.
        """
        new_task = {
            'environment': sb_environment.value,
            'test_plan_id': test_plan,
        }
        if subset is not None:
            new_task['test_ids'] = subset

        task_id = new_task_id(sb_environment, new_task)
        logger.info('Starting a new test run of %s: %s', test_plan, task_id)
        resp = self.request('PUT', f'/tasks/{task_id}',
                            json=new_task,
                            params=dict(force_retries=1))
        self._check_response(resp, expected_code=201)

        return resp.json()

    def wait_until_done(self, task: dict, timeout=1800, poll_frequency=15) -> dict:
        """Wait for a task to be in a READY state

        https://docs.celeryproject.org/en/stable/_modules/celery/states.html#state

        :param task: Task data.
        :param timeout: How many seconds to wait before raising a TimeoutError.
        :param poll_frequency: How often (in seconds) to check task state while waiting.
        :raises TimeoutError: Not in a READY state after the given amount of time.
        :raises requests.HTTPError: Test run state could not be refreshed.
        :raises RuntimeError: Test run task is failed or revoked for some reason.
        """
        task_id = task['id']
        ready_states = {'SUCCESS', 'FAILURE', 'REVOKED'}
        start_time = time.monotonic()
        logger.info('Waiting for test run %s to complete', task_id)

        while time.monotonic() - start_time < timeout:
            # Refresh task state
            resp = self.request('GET', f'/tasks/{task_id}')
            self._check_response(resp, expected_code=200)
            task = resp.json()
            logger.info('Test run %s is %s', task_id, task['state'])

            if task['state'] in ready_states:
                if task['state'] == 'SUCCESS':
                    logger.info('Test run report: %s',
                                f'{self._base_url}/reports/{task_id}')
                    return task

                raise RuntimeError('Test run {} is {}: {}'.format(
                    task_id, task['state'], repr(task)
                ))

            time.sleep(poll_frequency)

        raise TimeoutError(f'Task not ready after {timeout}s: {repr(task)}')

    def assert_all_tests_passed(self, task: dict):
        """Get the test run report and assert that all tests have passed

        :param task: Task data.
        :raises requests.HTTPError: Could not get test run report.
        """
        task_id = task['id']
        resp = self.request('GET', f'/reports/{task_id}')
        self._check_response(resp, expected_code=200)
        report = resp.json()

        failed_tests = []
        for test_result in report['results']:
            if test_result['state'] not in ('PASSED', 'SKIPPED'):
                failed_tests.append(test_result['id'])
                logger.info('[%s] Failed test: %s', task_id, test_result['id'])

        assert len(failed_tests) == 0


def execute(sb_environment: SBEnv, test_plan: str,
            subset: Optional[List[str]] = None):
    broker = SevenBridgesBrokerClient()

    task = broker.new_test_run(sb_environment, test_plan, subset=subset)
    task = broker.wait_until_done(task)
    broker.assert_all_tests_passed(task)
