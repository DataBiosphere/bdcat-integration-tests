import os
import unittest


def controlled_access(test_item):
    mode = os.environ.get("BDCAT_INTEGRATION_TESTMODE", "workspace_access")
    return unittest.skipUnless("controlled_access" in mode, "Skipping controlled access test")(test_item)
