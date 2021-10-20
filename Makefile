include common.mk
MODULES=scripts test

lint:
	flake8 --ignore=E501,E722,E402,F401 $(MODULES)

requirements:
	echo -n '' >| requirements.txt
	virtualenv -p $(shell which python3) tmp-venv
	./tmp-venv/bin/pip install -r requirements.txt.in
	echo "# You should not edit this file directly.  Instead, you should edit requirements.txt.in." >| requirements.txt
	./tmp-venv/bin/pip freeze | sed -e 's/\<pkg-resources==0.0.0\>//g' >> requirements.txt
	rm -rf tmp-venv

.PHONY: lint requirements
