.PHONY: devrun
devrun:
	# Run the service corresponding to the active directory
	pipenv run python3 ./$(notdir $(CURDIR)).py

.PHONY: install_svc
install_svc:
	../zigbee2mqtt2web/scripts/install_svc.sh .

rebuild_deps:
	rm -f Pipfile Pipfile.lock
	pipenv --rm || true
	pipenv --python python3
	pipenv install -e "$(shell readlink -f "$(PWD)/../zigbee2mqtt2web/zz2m")"
	pipenv install -e "$(shell readlink -f "$(PWD)/../zigbee2mqtt2web/zzmw_lib")"
	pipenv install flask


