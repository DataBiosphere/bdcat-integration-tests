#!/usr/bin/env python3
import logging
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from test.infra.testmode import staging_only, production_only, uses_sb_broker
from test.infra import sb_broker

logger = logging.getLogger(__name__)


class TestBDCIntegration(unittest.TestCase):

    """Test SevenBridges integration with BDC"""

    @staging_only
    @uses_sb_broker
    def test_bdc_staging(self):
        sb_broker.execute(sb_broker.SBEnv.staging, 'sbgtests.plans.bdc')

    @production_only
    @uses_sb_broker
    def test_bdc_production(self):
        sb_broker.execute(sb_broker.SBEnv.production, 'sbgtests.plans.bdc')


if __name__ == "__main__":
    unittest.main()
