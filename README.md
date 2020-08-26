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
strengthen the stability of interaction between components.  Please email either lblauvel at ucsc.edu or 
bhannafi at ucsc.edu.

