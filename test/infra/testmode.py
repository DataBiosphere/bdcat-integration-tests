import os
import unittest


def controlled_access(test_item):
    mode = os.environ.get("BDCAT_INTEGRATION_TESTMODE", "workspace_access")
    return unittest.skipUnless("controlled_access" in mode, "Skipping controlled access test")(test_item)


def staging_only(test_item):
    return unittest.skipUnless(os.environ.get('BDCAT_STAGE', 'staging') == 'staging',
                               "Skipping.  Test is staging only.")(test_item)


def production_only(test_item):
    return unittest.skipUnless(os.environ.get('BDCAT_STAGE', 'staging') == 'prod',
                               "Skipping.  Test is production only.")(test_item)


def uses_sb_broker(test_item):
    return unittest.skipUnless(os.environ.get("BDCAT_SB_BROKER_TOKEN"),
                               "Skipping.  Missing BDCAT_SB_BROKER_TOKEN environment variable.")(test_item)
