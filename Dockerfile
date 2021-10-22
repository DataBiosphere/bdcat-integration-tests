FROM ubuntu:18.04

RUN apt-get update && apt-get install -y --no-install-recommends  \
    apt-transport-https \
    build-essential \
    ca-certificates \
    curl \
    firefox \
    git \
    gnupg \
    python3.8-dev \
    software-properties-common \
    virtualenv \
    wget \
&& apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add -

RUN apt-get update && apt-get install -y  \
    google-cloud-sdk \
&& apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.29.1/geckodriver-v0.29.1-linux64.tar.gz -O - | tar -xz --directory=/usr/local/bin \
    && chmod 755 /usr/local/bin/geckodriver

RUN virtualenv -p python3.8 venv

COPY requirements.txt /opt/.

RUN /venv/bin/pip install -r /opt/requirements.txt \
    --no-cache-dir --disable-pip-version-check

# For `make lint` to work without special considerations
RUN ln -s /venv/bin/flake8 /usr/local/bin/flake8
