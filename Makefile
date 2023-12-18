.PHONY: run testrun install install_service restart_and_tail_logs tail_logs install_system_deps

run:
	/usr/bin/authbind --deep python3 -m pipenv run python ./main.py | tee run.log

testrun:
	python3 -m pipenv run python ./main.py TESTRUN | tee run.log

shell:
	python3 -m pipenv run python

restart_and_tail_logs:
	sudo systemctl restart BatiCasa.service && journalctl -fu BatiCasa

tail_logs:
	journalctl -fu BatiCasa

tail_logs_with_zigbee2mqtt:
	journalctl -f -u BatiCasa -u zigbee2mqtt

restart_and_tail_logs_with_zigbee2mqtt:
	sudo systemctl restart BatiCasa.service && journalctl -fu BatiCasa -u zigbee2mqtt

Pipfile:
	echo 'You need to `cp Pipfile.arm Pipfile` or `cp Pipfile.x86 Pipfile` first'
	false

install: Pipfile
	python3 -m pipenv --python $(shell which python3 )
	python3 -m pipenv install requests

install_system_deps:
	make -C zigbee2mqtt2web install_system_deps
