FROM python:3
COPY . /bdcat-integration-tests
RUN pip install virtualenv
CMD ["virtualenv", "-p", "python3.8", "venv"]
CMD [".", "venv/bin/activate"]

#try here

# nope RUN pip install --no-binary pandas pandas

RUN pip3 install Cython

RUN pip install -r bdcat-integration-tests/requirements.txt --no-use-pep517
CMD ["python", "/bdcat-integration-tests/scripts/run_integration_tests.py"]
