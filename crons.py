from apscheduler.schedulers.background import BackgroundScheduler
from zigbee2mqtt2web_extras.light_helpers import which_lights_are_on_in_the_house

from datetime import datetime, timedelta

import logging
log = logging.getLogger(__name__)


class Cronenberg:
    def __init__(self, zmw):
        self._zmw = zmw
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

        self._scheduler.add_job(self._check_lights, trigger='cron', day_of_week='mon-fri', hour=9)
        # TEST: self._scheduler.add_job(self._check_lights, 'date', run_date=datetime.now() + timedelta(seconds=30))

    def _check_lights(self):
        lights = which_lights_are_on_in_the_house(self._zmw.registry)
        if len(lights) == 0:
            return
        log.info("Lights are on at 9am, someone probably forgot them")
        for name in lights:
            self._zmw.registry.get_thing(name).turn_off()
        self._zmw.registry.broadcast_things(lights)

        self._zmw.announce_system_event({
            'event': 'on_forgot_lights_on_morning',
            'light_names': lights,
        })

