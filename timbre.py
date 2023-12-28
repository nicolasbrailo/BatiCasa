from zigbee2mqtt2web_extras.reolink_doorbell import ReolinkDoorbell

import logging
log = logging.getLogger(__name__)

class Timbre(ReolinkDoorbell):
    def __init__(self, cfg, zmw, sonos_name):
        super().__init__(cfg, zmw)
        self._sonos_name = sonos_name

    def on_doorbell_button_pressed(self):
        log.info("Doorbell says someone pressed the visitor button")
        sonos = self._zmw.registry.get_thing(self._sonos_name)
        sonos.play_announcement('http://192.168.1.20/web_assets/knockknock.mp3', timeout_secs=20)

    def on_motion_detected(self, motion_level):
        log.info("Doorbell says someone is at the door")
        #sonos = self._zmw.registry.get_thing(self._sonos_name)
        #sonos.tts_announce('es', 'Hay alguien en la puerta')

    def on_motion_cleared(self):
        log.info("Doorbell says no motion is detected")

