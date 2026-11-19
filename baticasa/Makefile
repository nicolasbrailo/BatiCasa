.PHONY: devrun
devrun:
	# Run the service corresponding to the active directory
	pipenv run python3 ./$(notdir $(CURDIR)).py

.PHONY: install_svc
install_svc:
	../zigbee2mqtt2web/scripts/install_svc.sh .

test:

ZMW_DIR = ../zigbee2mqtt2web

# Same as ZMW's rebuild_ui (common.mk): bundle zmw.js + this app into one file named after its hash, and point the
# html at it and at hashed css links, so browsers refetch after a deploy.
.PHONY: rebuild_ui
rebuild_ui:
	$(MAKE) -C $(ZMW_DIR)/zzmw_lib/www js
	$(ZMW_DIR)/zzmw_lib/www/babel_compile_single.sh ./www/app.js ./www/app.rel.js
	rm -f ./www/app.rel.*.js
	cat $(ZMW_DIR)/zzmw_lib/www/zmw.js ./www/app.rel.js > ./www/app.rel.combined.js
	mv ./www/app.rel.combined.js ./www/app.rel.js
	HASH=$$(md5sum ./www/app.rel.js | cut -d' ' -f1 | head -c8) && \
		cp ./www/app.rel.js "./www/app.rel.$$HASH.js" && \
		sed -i "s|app\.rel[^\"]*\.js|app.rel.$$HASH.js|g" ./www/index.html
	$(ZMW_DIR)/scripts/cache_bust_css.sh ./www $(ZMW_DIR)/zzmw_lib/www

rebuild_deps:
	rm -f Pipfile Pipfile.lock
	pipenv --rm || true
	pipenv --python python3
	pipenv install soco
	pipenv install -e "$(shell readlink -f "$(PWD)/../zigbee2mqtt2web/zzmw_lib")[z2m]"


