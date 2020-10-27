FROM python:3.8-slim
COPY . /bdcat-integration-tests
RUN pip install virtualenv
CMD ["virtualenv", "-p", "python3.8", "venv"]
CMD [".", "venv/bin/activate"]
RUN pip install -r bdcat-integration-tests/requirements.txt --use-feature=2020-resolver
CMD ["python", "/bdcat-integration-tests/scripts/run_integration_tests.py"]
