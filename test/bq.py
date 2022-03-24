import datetime
import logging

from google.api_core.exceptions import ServiceUnavailable
from google.cloud import bigquery
from google.cloud.exceptions import Conflict
from google.oauth2.service_account import Credentials

from test.utils import retry

log = logging.getLogger(__name__)


class Client:

    def __init__(self, project='platform-dev-178517'):
        credentials = Credentials.from_service_account_file('gcp-creds.json')
        self.client = bigquery.Client(project=project, credentials=credentials)

    @retry(errors={ServiceUnavailable})
    def add_row(self, table_id: str, row: dict):
        rows_to_insert = [row]
        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            raise RuntimeError(f'Encountered errors while inserting rows: {errors}')

    def list_table(self, table_id, limit=10):
        q = self.client.query(f'SELECT * FROM `{table_id}` LIMIT {limit}')
        return list(q.result())

    def create_table(self, table_id, schema):
        table = bigquery.Table(table_id, schema=schema)
        try:
            table = self.client.create_table(table)
            log.info(f'Created table {table.project}.{table.dataset_id}.{table.table_id}')
        except Conflict:
            log.warning(f'Table {table.project}.{table.dataset_id}.{table.table_id} already exists')

    def create_test_table(self, table_id):
        schema = [
            bigquery.SchemaField('t', 'TIMESTAMP', mode='REQUIRED'),
            bigquery.SchemaField('u', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('d', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('m', 'INTEGER', mode='REQUIRED')
        ]
        self.create_table(table_id, schema)

    def log_test_results(self, test_name, status, timestamp, create=False):
        table_id = f'platform-dev-178517.bdc.integration_tests_{test_name}'
        if status != 'skip':
            if status == 'success':
                field = 'u'
            elif status in ('failure', 'error'):
                field = 'd'
            else:
                raise ValueError(f'Unexpected status: {status!r} for test: {test_name!r}')
            row = {f: (1 if f == field else 0) for f in ('u', 'd', 'm')}
            row['t'] = str(timestamp)
            if create:
                self.create_test_table(table_id)
            self.add_row(table_id, row)


def log_duration(table, duration):
    try:
        # Track time in minutes
        Client().add_row(table, {'t': str(datetime.datetime.now()), 'd': duration / 60})

    except Exception:
        # We don't want failed logging to fail the whole test
        log.warning('Failed to log run time to BigQuery', exc_info=True)
