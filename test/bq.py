import datetime
import logging

from google.cloud import bigquery
from google.oauth2.service_account import Credentials

log = logging.getLogger(__name__)


class Client:

    def __init__(self, project='platform-dev-178517'):
        credentials = Credentials.from_service_account_file('gcp-creds.json')
        self.client = bigquery.Client(project=project, credentials=credentials)

    def add_row(self, table_id: str, duration):
        rows_to_insert = [
            {'t': str(datetime.datetime.now()), 'd': round(duration)}
        ]
        errors = self.client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            raise RuntimeError(f'Encountered errors while inserting rows: {errors}')

    def list_table(self, table_id, limit=10):
        q = self.client.query(f'SELECT * FROM `{table_id}` LIMIT {limit}')
        return list(q.result())
