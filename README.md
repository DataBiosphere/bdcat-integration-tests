# Biodata Catalyst Integration Testing

Dedicated to integration testing between components for the Biodata Catalyst grant.

### How to Trigger Integration Tests Externally

You will need two tokens:

1. A trigger token for the repository.

1. A personal gitlab API key.

**Note: It's recommended that you create a new github account to act as a test bot to own both tokens rather than using 
personal accounts.

To create these two tokens, have your github testing account click the github sign-in button (do not register by 
email) here: https://biodata-integration-tests.net 

It will say that you are blocked.  Email either lblauvel at ucsc.edu or bhannafi at ucsc.edu to be unblocked 
and added to the integration testing repo.  Please include what team you're with and which external repos will be 
running the triggered tests.  Once the account is added, mint the two tokens needed:

1. Make a personal access token (GITLAB_READ_TOKEN): https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html#creating-a-personal-access-token

1. Make a project trigger token (GITLAB_TRIGGER_TOKEN): https://docs.gitlab.com/ee/ci/triggers/#adding-a-new-trigger

The following is just an example of how to run the repo.  Please use best practice and don't declare env vars in plain 
text as is done below (i.e. use base64 encoding and fetch from a secret or a secret file; don't allow tokens to be 
captured by stdout or your history (stdin)):

```
# download the repo and setup dependencies
git clone https://github.com/DataBiosphere/bdcat-integration-tests.git && cd bdcat-integration-tests
virtualenv -p python3.7 venv && . venv/bin/activate && pip install -r requirements.txt

# declare the tokens
export GITLAB_READ_TOKEN=somethingsomething
export GITLAB_TRIGGER_TOKEN=somethingsomething

python scripts/run_integration_tests.py
```

# Adding Tests
Simply submit a PR and flag for review.

# Feedback
We welcome feedback and suggestions from any Biodata Catalyst team on useful tests that would help to 
strengthen the stability of interaction between components.  Please email lblauvel at ucsc.edu.

# Current State of Testing

| From / To     | Terra                    | Gen3                     | Dockstore                | Seven Bridges            | PIC-SURE                 | HeLx |
| ------------- |:------------------------:|:------------------------:|:------------------------:|:------------------------:|:------------------------:| ----:|
| Terra         | :heavy_multiplication_x: | :white_check_mark:       | :white_check_mark:       | :heavy_multiplication_x: | Future                   |      |
| Gen3          | TBD                      | :heavy_multiplication_x: | TBD?                     | TBD?                     |                          |      |
| Dockstore     |                          |                          | :heavy_multiplication_x: |                          |                          |      |
| Seven Bridges | :heavy_multiplication_x: | :white_check_mark:       | TBD?                     | :heavy_multiplication_x: | Future                   |      |
| PIC-SURE      |                          | TBD?                     |                          |                          | :heavy_multiplication_x: |      |
| HeLx          | TBD?                     | TBD?                     |                          | TBD?                     |                          | :heavy_multiplication_x: |

 - :white_check_mark: : Implemented (probably not comprehensively; additional testing suggestions are very welcome)
 - :heavy_multiplication_x: : Not Applicable
 - TBD : To Be Done
 - Future : Tests will be needed, but the features have not been built yet


Current tests (all are run in each component's Staging environment):

API Test 1:
 - Create Terra workspace
 - Import static PFB from Gen3 into workspace
 - Check for success of PFB import into Terra workspace
 - Delete workspace

API Test 2:
 - Import from Dockstore workflow to Terra workspace
 - Check presence of Dockstore workflow in Terra workspace
 - Delete Dockstore workflow from terra workspace

API Test 3:
 - Run DRS URI in md5sum workflow in Terra
 - Check workflow run success
 
 Currently tested endpoints are:

 - https://firecloud-orchestration.dsde-alpha.broadinstitute.org/status
 - https://firecloud-orchestration.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/importPFB
 - https://firecloud-orchestration.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/importPFB/{job_id}
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/submissions
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/methodconfigs
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/methodconfigs?allRepos=true
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/methodconfigs/{billing_project}/{workflow}
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}/submissions/{submission_id}
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces
 - https://rawls.dsde-alpha.broadinstitute.org/api/workspaces/{billing_project}/{workspace}
 - https://staging.gen3.biodatacatalyst.nhlbi.nih.gov/user/data/download/{guid}
