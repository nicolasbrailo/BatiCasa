.PHONY: run install install_service restart_and_tail_logs tail_logs

run:
	/usr/bin/authbind --deep python3 -m pipenv run python ./main.py | tee run.log

shell:
	python3 -m pipenv run python

restart_and_tail_logs:
	sudo systemctl restart BatiCasa.service && journalctl -fu BatiCasa

tail_logs:
	journalctl -fu BatiCasa

tail_logs_with_zigbee2mqtt:
	journalctl -f -u BatiCasa -u zigbee2mqtt

install:
	python3 -m pipenv install requests
	# If Redis is missing, it's because it tends to fail when installing spotipy. Try this:
	# python3 -m pipenv --upgrade install spotipy

MKFILE_PATH=$(abspath $(lastword $(MAKEFILE_LIST)))
SRC_DIR=$(patsubst %/,%,$(dir $(MKFILE_PATH)))

install_service:
	@# authbind -> run in port 80 with no root
	sudo touch /etc/authbind/byport/80
	sudo chmod 777 /etc/authbind/byport/80
	cat ./zigbee2mqtt2web/scripts/zigbee2mqtt2web.service.template | \
		sed "s|#INSTALL_DIR#|$(SRC_DIR)|g" | \
		sed "s|Zigbee2Mqtt2Web|BatiCasa|g" | \
		sudo tee >/dev/null /etc/systemd/system/BatiCasa.service
	sudo systemctl stop BatiCasa | true
	sudo systemctl daemon-reload
	sudo systemctl enable BatiCasa
	sudo systemctl start BatiCasa
	sudo systemctl status BatiCasa
