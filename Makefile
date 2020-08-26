include common.mk
MODULES=scripts test

lint:
	flake8 --ignore=E501,E722 $(MODULES)

refresh_requirements:
	echo -n '' >| requirements.txt
	$(MAKE) requirements.txt

requirements.txt:
	virtualenv -p $(shell which python3) tmp-venv
	./tmp-venv/bin/pip install -r requirements.txt.in
	echo "# You should not edit this file directly.  Instead, you should edit requirements.txt.in." >| $@
	./tmp-venv/bin/pip freeze > requirements.txt
	rm -rf tmp-venv

.PHONY: lint refresh_requirements requirements.txt
