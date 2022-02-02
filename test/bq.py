import datetime
import logging
import time

from google.api_core.exceptions import ServiceUnavailable
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from test.utils import retry

log = logging.getLogger(__name__)


class Client:

    def __init__(self, project='platform-dev-178517'):
        credentials = Credentials.from_service_account_file('gcp-creds.json')
        self.client = bigquery.Client(project=project, credentials=credentials)

    @retry(errors={ServiceUnavailable})
    def add_row(self, table_id: str, duration: float):
        rows_to_insert = [
            {'t': str(datetime.datetime.now()), 'd': duration}
        ]
        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            raise RuntimeError(f'Encountered errors while inserting rows: {errors}')

    def list_table(self, table_id, limit=10):
        q = self.client.query(f'SELECT * FROM `{table_id}` LIMIT {limit}')
        return list(q.result())


def log_duration(table, start):
    try:
        # Track time in minutes
        Client().add_row(table, (time.time() - start) / 60)
    except Exception:
        # We don't want failed logging to fail the whole test
        log.warning('Failed to log run time to BigQuery', exc_info=True)
