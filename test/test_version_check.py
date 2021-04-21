#!/usr/bin/env python3
import logging
import unittest
import requests
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)
class TestGen3VersionsAcrossEnvironments(unittest.TestCase):
    def test_staging_versus_prod_version(self):
        log.info("this is a test")
        bdcat_prod_version = "2021.04"
        bdcat_staging_version = "2021.05"
        self.assertGreaterEqual(bdcat_staging_version, bdcat_prod_version)
if __name__ == "__main__":
    unittest.main()
