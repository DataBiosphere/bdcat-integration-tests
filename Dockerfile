FROM python:3.8
COPY . /bdcat-integration-tests
RUN pip install virtualenv
CMD ["virtualenv", "-p", "python3.8", "venv"]
CMD [".", "venv/bin/activate"]
RUN pip install -r bdcat-integration-tests/requirements.txt
CMD ["python", "/bdcat-integration-tests/scripts/run_integration_tests.py"]
