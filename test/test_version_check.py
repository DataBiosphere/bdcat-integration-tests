#!/usr/bin/env python3
import logging
import os
import requests
import unittest

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


bdcat_prod_url = "https://gen3.biodatacatalyst.nhlbi.nih.gov"
bdcat_staging_url = "https://staging.gen3.biodatacatalyst.nhlbi.nih.gov"


class TestGen3VersionsAcrossEnvironments(unittest.TestCase):
    def test_staging_versus_prod_version(self):
        '''
        Assertions around release versions.

        It is acceptable for BDCat staging to be on the same version or ahead
        of BDCat PROD.
        If PROD is updated before staging, that means a new version
        has been released without proper cross-org testing.

        >>> bdcat_prod_version = "2021.12"
        >>> bdcat_staging_version = "2022.01"
        >>> bdcat_staging_version >= bdcat_prod_version
        True
        >>> bdcat_prod_version = "2021.05"
        >>> bdcat_staging_version = "2021.04"
        >>> bdcat_staging_version >= bdcat_prod_version
        False
        >>> bdcat_staging_version = "2021.06"
        >>> bdcat_prod_version = "2021.05"
        >>> bdcat_staging_version >= bdcat_prod_version
        True
        '''
        log.info("checking the gen3 release version on bdcat prod...")
        bdcat_prod_version_json = requests.get(
            f"{bdcat_prod_url}/index/_version"
        ).json()
        # extract version from json payload
        bdcat_prod_version = bdcat_prod_version_json['version']

        log.info("checking the gen3 release version on bdcat staging...")
        bdcat_staging_version_json = requests.get(
            f"{bdcat_staging_url}/index/_version"
        ).json()
        bdcat_staging_version = bdcat_staging_version_json['version']

        self.assertGreaterEqual(bdcat_staging_version, bdcat_prod_version)


if __name__ == "__main__":
    unittest.main()
