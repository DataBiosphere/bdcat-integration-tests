FROM python:3
COPY . /bdcat-integration-tests
RUN pip install virtualenv
CMD ["virtualenv", "-p", "python3.8", "venv"]
CMD [".", "venv/bin/activate"]

#try here

RUN pip install --no-binary pandas pandas

RUN pip install -r bdcat-integration-tests/requirements.txt
CMD ["python", "/bdcat-integration-tests/scripts/run_integration_tests.py"]
