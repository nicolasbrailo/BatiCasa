from zigbee2mqtt2web_extras.reolink_doorbell import ReolinkDoorbell
from zigbee2mqtt2web_extras.utils.whatsapp import WhatsApp

import logging
log = logging.getLogger(__name__)

class Timbre(ReolinkDoorbell):
    def __init__(self, cfg, zmw, sonos_name, wa_cfg=None):
        super().__init__(cfg, zmw)
        self._sonos_name = sonos_name
        if wa_cfg is not None:
            self._wa = WhatsApp(wa_cfg, test_mode=False)

        self._snap_path_on_movement = None
        if 'snap_path_on_movement' in cfg:
            self._snap_path_on_movement = cfg['snap_path_on_movement']

    def on_doorbell_button_pressed(self):
        log.info("Doorbell says someone pressed the visitor button")
        sonos = self._zmw.registry.get_thing(self._sonos_name)
        sonos.play_announcement('http://192.168.1.20/web_assets/knockknock.mp3', timeout_secs=20)

    def on_motion_detected(self, motion_level):
        log.info("Doorbell says someone is at the door")

        #sonos = self._zmw.registry.get_thing(self._sonos_name)
        #sonos.tts_announce('es', 'Hay alguien en la puerta')

        if self._snap_path_on_movement is not None:
            try:
                self.get_snapshot(self._snap_path_on_movement)
            except:
                log.error("Failed to save doorbell snapshot", exc_info=True)
                return

        imgid = None
        try:
            imgid = self._wa.upload_image(self._snap_path_on_movement)
            log.error("Uploaded %s to WA", self._snap_path_on_movement)
        except:
            log.error("Failed WA image upload", exc_info=True)
            return

        if imgid is not None:
            try:
                res = self._wa.template_message_with_image("sample_purchase_feedback", imgid, "Motion detected!")
                log.info("Sent motion detect messages to WA: %s", str(res))
            except:
                log.error("Failed WA image send", exc_info=True)

    def on_motion_cleared(self):
        log.info("Doorbell says no motion is detected")

