# Biodata Catalyst Integration Testing

This supports integration testing between components for the biodata catalyst grant.

Server hosted tests here: https://biodata-integration-tests.net/

Initial testing to create end-to-end tests representing the user process of uploading, investigating, running, and analyzing results on the Biodata Catalyst platform.

A secure, credentialed account will supply data to upload to gen3 using their API, login to and import the data into terra using the results from the gen3 API to feed into the terra API, run a series of workflows, and analyze the results as an initial proof of concept integration test.

This should alert teams immediately when a component breaks compatibility with another component.

We are looking for feedback from the teams of the different Biodata Catalyst components on what tests would be useful to help strengthen the stability of interaction between components.
