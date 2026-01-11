import os
import pathlib

from apscheduler.triggers.cron import CronTrigger

from zzmw_lib.service_runner import service_runner
from zzmw_lib.logs import build_logger
from zz2m.button_action_service import ButtonActionService
from zz2m.light_helpers import (
    any_light_on,
    light_group_toggle_brightness_pct,
    toggle_ensure_color,
    turn_all_lights_off
)

log = build_logger("Baticasa")

class Baticasa(ButtonActionService):
    def __init__(self, cfg, www, sched):
        www_path = os.path.join(pathlib.Path(__file__).parent.resolve(), 'www')
        super().__init__(cfg, www, www_path, sched, svc_deps=["ZmwSonosCtrl", "ZmwSpotify", "ZmwSpeakerAnnounce"])
        self._cocina_btn_heladera_action_idx = 0
        self.boton_olivia_click_num = 0
        self.boton_olivia_click_off_num = 0
        self.boton_emma_click_num = 0
        self.boton_emma_click_off_num = 0

        www.serve_url('/arbolito_on', self._arbolito_on)
        www.serve_url('/arbolito_off', self._arbolito_off)

        sched.add_job(
            self._arbolito_on,
            CronTrigger(hour=16, minute=0)
        )
        sched.add_job(
            self._arbolito_off,
            CronTrigger(hour=22, minute=0)
        )

    # Don't support any messages, ignore all replies
    def on_service_received_message(self, subtopic, payload):
        pass
    def on_dep_published_message(self, svc_name, subtopic, payload):
        pass

    def _arbolito_on(self):
        log.info("Arbolito ON")
        self._z2m.get_thing('TVRoomArbolito').set('state', True)
        self._z2m.broadcast_thing('TVRoomArbolito')
        return "ON"
    def _arbolito_off(self):
        log.info("Arbolito OFF")
        self._z2m.get_thing('TVRoomArbolito').set('state', False)
        self._z2m.broadcast_thing('TVRoomArbolito')
        return "OFF"

    def _scene_TVRoomTele_Night(self):
        self._z2m.get_thing('CocinaCeiling').turn_off()
        self._z2m.get_thing('CocinaCountertop').turn_off()
        self._z2m.get_thing('CocinaFloorlamp').turn_off()
        self._z2m.get_thing('CocinaSink').turn_off()
        self._z2m.get_thing('EntradaCeiling').turn_off()
        self._z2m.get_thing('EntradaColor').turn_off()
        self._z2m.get_thing('TVRoomFloorlampLeft').set_brightness_pct(30)
        self._z2m.get_thing('TVRoomFloorlampLeft').set('color_temp', 454)
        self._z2m.get_thing('TVRoomFloorlampRight').set_brightness_pct(30)
        self._z2m.get_thing('TVRoomFloorlampRight').set('color_temp', 454)
        self._z2m.get_thing('TVRoomSnoopy').set_brightness_pct(30)
        self._z2m.get_thing('EmmaVelador').set_brightness_pct(25)
        self._z2m.get_thing('EmmaVelador').actions['color_rgb'].set_value('F07529')
        self._z2m.get_thing('OliviaVelador').set_brightness_pct(25)
        self._z2m.get_thing('OliviaVelador').actions['color_rgb'].set_value('F07529')
        self._z2m.broadcast_things([
            'CocinaCeiling', 'CocinaCountertop', 'CocinaFloorlamp', 'CocinaSink',
            'EntradaCeiling', 'EntradaColor',
            'TVRoomFloorlampLeft', 'TVRoomFloorlampRight', 'TVRoomSnoopy',
            'EmmaVelador', 'OliviaVelador',
        ])

    def _scene_TVRoomPlay(self):
        self._z2m.get_thing('TVRoomFloorlampLeft').set_brightness_pct(5)
        self._z2m.get_thing('TVRoomFloorlampLeft').set('color_temp', 454)
        self._z2m.get_thing('TVRoomFloorlampRight').set_brightness_pct(5)
        self._z2m.get_thing('TVRoomFloorlampRight').set('color_temp', 454)
        self._z2m.get_thing('TVRoomSnoopy').set_brightness_pct(30)
        self._z2m.broadcast_things([
            'TVRoomFloorlampLeft', 'TVRoomFloorlampRight', 'TVRoomSnoopy',
        ])

    def _scene_CocinaComer(self):
        self._z2m.get_thing('CocinaCeiling').set_brightness_pct(80)
        self._z2m.get_thing('CocinaSink').set_brightness_pct(90)
        self._z2m.get_thing('CocinaCountertop').set_brightness_pct(90)
        self._z2m.get_thing('EntradaCeiling').set_brightness_pct(50)
        self._z2m.get_thing('EntradaColor').set_brightness_pct(100)
        self._z2m.get_thing('CocinaFloorlamp').set_brightness_pct(30)
        self._z2m.broadcast_things([
            'CocinaCeiling', 'CocinaSink', 'CocinaCountertop',
            'EntradaCeiling', 'EntradaColor', 'CocinaFloorlamp'
        ])

    def _scene_CocinaGezellig(self):
        self._z2m.get_thing('CocinaCeiling').set_brightness_pct(25)
        self._z2m.get_thing('CocinaSink').set_brightness_pct(70)
        self._z2m.get_thing('CocinaCountertop').set_brightness_pct(70)
        self._z2m.get_thing('EntradaCeiling').set_brightness_pct(10)
        self._z2m.get_thing('EntradaColor').set_brightness_pct(100)
        self._z2m.get_thing('CocinaFloorlamp').set_brightness_pct(10)
        self._z2m.broadcast_things([
            'CocinaCeiling', 'CocinaSink', 'CocinaCountertop',
            'EntradaCeiling', 'EntradaColor', 'CocinaFloorlamp'
        ])

    def _scene_OliviaA_Dormir(self):
        self._z2m.get_thing('OliviaVelador').set_brightness_pct(15)
        self._z2m.get_thing('OliviaSonoslamp').turn_off()
        self._z2m.get_thing('OliviaFloorlamp').turn_off()

    def _scene_WorldOff(self):
        turn_all_lights_off(self._z2m, transition_secs=3)

    def _z2m_cb_BatiOficinaBtn_action(self, action):  # pylint: disable=invalid-name
        lamp = self._z2m.get_thing('BatiOficinaColor')
        lamp.set('transition', 1)
        if action == 'on':
            toggle_ensure_color(lamp, 'FFA9A9')
        if action == 'off':
            toggle_ensure_color(lamp, 'FFEA79')
        self._z2m.broadcast_thing(lamp)

    def _z2m_cb_BaticuartoBeladorBtn_action(self, action):  # pylint: disable=invalid-name
        lamp = self._z2m.get_thing('BaticuartoBelador')
        lamp.set('transition', 1)
        if action == 'on':
            toggle_ensure_color(lamp, 'FFA9A9')
        if action == 'off':
            toggle_ensure_color(lamp, 'FFEA79')

        lamp2 = self._z2m.get_thing('BaticuartoNicoVelador')
        lamp2.set('transition', 1)
        lamp2.set('state', lamp.is_light_on())
        lamp.set_brightness_pct(60 if lamp.is_light_on() else 0)
        self._z2m.broadcast_things([lamp, lamp2])

    def _z2m_cb_BaticuartoWorldOffBtn_action(self, _action):  # pylint: disable=invalid-name
        turn_all_lights_off(self._z2m, transition_secs=3)

    def _z2m_cb_EmmaBtn_action(self, action):  # pylint: disable=invalid-name
        if action == 'on':
            lamp = self._z2m.get_thing('EmmaVelador')
            self.boton_emma_click_num += 1
            if self.boton_emma_click_num == 1:
                lamp.set_brightness_pct(100)
                lamp.actions['color_rgb'].set_value('DEDED6')
            elif self.boton_emma_click_num == 2:
                lamp.set_brightness_pct(10)
                lamp.actions['color_rgb'].set_value('F07529')
            else:
                self.boton_emma_click_num = 0
                # Set color to step zero, otherwise on switch-on it will start white and fade to orange
                lamp.actions['color_rgb'].set_value('DEDED6')
                lamp.turn_off()
            lamp.set('transition', 2)
            self._z2m.broadcast_thing(lamp)

        if action == 'off':
            lamp1 = self._z2m.get_thing('EmmaFloorlampColor')
            lamp2 = self._z2m.get_thing('EmmaTriangleLamp')
            self.boton_emma_click_off_num += 1
            if self.boton_emma_click_off_num == 1:
                lamp1.set_brightness_pct(50)
                lamp2.set_brightness_pct(50)
            elif self.boton_emma_click_off_num == 2:
                lamp1.set_brightness_pct(100)
                lamp2.set_brightness_pct(100)
            else:
                self.boton_emma_click_off_num = 0
                lamp1.turn_off()
                lamp2.turn_off()
            lamp1.set('transition', 2)
            lamp2.set('transition', 2)
            self._z2m.broadcast_things([lamp1, lamp2])

    def _z2m_cb_OliviaBtn_action(self, action):  # pylint: disable=invalid-name
        if action == 'on':
            lamp = self._z2m.get_thing('OliviaVelador')
            self.boton_olivia_click_num += 1
            if self.boton_olivia_click_num == 1:
                lamp.set_brightness_pct(100)
                lamp.actions['color_rgb'].set_value('DEDED6')
            elif self.boton_olivia_click_num == 2:
                lamp.set_brightness_pct(10)
                lamp.actions['color_rgb'].set_value('F07529')
            else:
                self.boton_olivia_click_num = 0
                # Set color to step zero, otherwise on switch-on it will start white and fade to orange
                lamp.actions['color_rgb'].set_value('DEDED6')
                lamp.turn_off()
            lamp.set('transition', 2)
            self._z2m.broadcast_thing(lamp)

        if action == 'off':
            lamp1 = self._z2m.get_thing('OliviaFloorlamp')
            lamp2 = self._z2m.get_thing('OliviaSonoslamp')
            self.boton_olivia_click_off_num += 1
            if self.boton_olivia_click_off_num == 1:
                lamp1.set_brightness_pct(50)
                lamp2.set_brightness_pct(50)
            elif self.boton_olivia_click_off_num == 2:
                lamp1.set_brightness_pct(100)
                lamp2.set_brightness_pct(100)
            else:
                self.boton_olivia_click_off_num = 0
                lamp1.turn_off()
                lamp2.turn_off()
            lamp1.set('transition', 2)
            lamp2.set('transition', 2)
            self._z2m.broadcast_things([lamp1, lamp2])

    def _z2m_cb_TVRoomBtn_action(self, action):  # pylint: disable=invalid-name
        if action == 'on_press':
            self._z2m.get_thing('TVRoomFloorlampLeft').set_brightness_pct(100)
            self._z2m.get_thing('TVRoomFloorlampLeft').set('color_temp', 250)
            self._z2m.get_thing('TVRoomFloorlampRight').set_brightness_pct(100)
            self._z2m.get_thing('TVRoomFloorlampRight').set('color_temp', 250)
            self._z2m.get_thing('TVRoomSnoopy').set_brightness_pct(100)
        if action == 'up_press':
            self._z2m.get_thing('TVRoomFloorlampLeft').set_brightness_pct(60)
            self._z2m.get_thing('TVRoomFloorlampLeft').set('color_temp', 370)
            self._z2m.get_thing('TVRoomFloorlampRight').set_brightness_pct(60)
            self._z2m.get_thing('TVRoomFloorlampRight').set('color_temp', 370)
            self._z2m.get_thing('TVRoomSnoopy').set_brightness_pct(60)
        if action == 'down_press':
            self._z2m.get_thing('TVRoomFloorlampLeft').set_brightness_pct(30)
            self._z2m.get_thing('TVRoomFloorlampLeft').set('color_temp', 454)
            self._z2m.get_thing('TVRoomFloorlampRight').set_brightness_pct(30)
            self._z2m.get_thing('TVRoomFloorlampRight').set('color_temp', 454)
            self._z2m.get_thing('TVRoomSnoopy').set_brightness_pct(30)
        if action == 'off_press':
            self._z2m.get_thing('TVRoomFloorlampLeft').turn_off()
            self._z2m.get_thing('TVRoomFloorlampRight').turn_off()
            self._z2m.get_thing('TVRoomSnoopy').turn_off()
        self._z2m.broadcast_things(['TVRoomFloorlampLeft', 'TVRoomFloorlampRight', 'TVRoomSnoopy'])

    def _z2m_cb_CocinaMediaCtrlBtn_action(self, action):  # pylint: disable=invalid-name
        if action == 'toggle':
            log.info("Rquest Spotify Hijack")
            self.message_svc("ZmwSonosCtrl", "spotify_hijack_or_toggle_play", {
                "BatiDiscos": {"vol": 60},
                "BatiPatio": {"vol": 17},
                "Baticocina": {"vol": 14},
            })
        if action == 'brightness_up_click':
            log.info("Request Sonos Volume up")
            self.message_svc("ZmwSonosCtrl", "volume_up", {})
        if action == 'brightness_down_click':
            log.info("Request Sonos Volume down")
            self.message_svc("ZmwSonosCtrl", "volume_down", {})
        if action == 'arrow_right_click':
            log.info("Request Spotify next track")
            self.message_svc("ZmwSonosCtrl", "next_track", {})
        if action == 'arrow_left_click':
            log.info("Request Spotify prev track")
            self.message_svc("ZmwSonosCtrl", "prev_track", {})

    def _z2m_cb_CocinaBtnHeladera_action(self, action):  # pylint: disable=invalid-name
        if action == 'toggle':
            kitchen_lights = [
                'CocinaCeiling', 'CocinaSink', 'CocinaCountertop',
                'CocinaFloorlamp', 'EntradaCeiling', 'EntradaColor'
            ]
            group_on = any_light_on(self._z2m, kitchen_lights)
            if not group_on:
                self._cocina_btn_heladera_action_idx = 1
            else:
                self._cocina_btn_heladera_action_idx += 1
            if self._cocina_btn_heladera_action_idx == 1:
                self._z2m.get_thing('CocinaCeiling').set_brightness_pct(20)
                self._z2m.get_thing('CocinaSink').set_brightness_pct(50)
                self._z2m.get_thing('CocinaCountertop').set_brightness_pct(50)
                self._z2m.get_thing('EntradaCeiling').set_brightness_pct(15)
                self._z2m.get_thing('EntradaColor').set_brightness_pct(60)
                self._z2m.get_thing('CocinaFloorlamp').set_brightness_pct(10)
                self._z2m.broadcast_things([
                    'CocinaCeiling', 'CocinaSink', 'CocinaCountertop',
                    'EntradaCeiling', 'EntradaColor', 'CocinaFloorlamp'
                ])
            elif self._cocina_btn_heladera_action_idx == 2:
                self._z2m.get_thing('CocinaCeiling').set_brightness_pct(70)
                self._z2m.get_thing('CocinaSink').set_brightness_pct(80)
                self._z2m.get_thing('CocinaCountertop').set_brightness_pct(80)
                self._z2m.get_thing('EntradaCeiling').set_brightness_pct(50)
                self._z2m.get_thing('EntradaColor').set_brightness_pct(100)
                self._z2m.get_thing('CocinaFloorlamp').set_brightness_pct(30)
                self._z2m.broadcast_things([
                    'CocinaCeiling', 'CocinaSink', 'CocinaCountertop',
                    'EntradaCeiling', 'EntradaColor', 'CocinaFloorlamp'
                ])
            else:
                light_group_toggle_brightness_pct(
                    self._z2m,
                    [
                        ('CocinaCeiling', 90),
                        ('CocinaSink', 90),
                        ('CocinaCountertop', 90),
                        ('EntradaCeiling', 75),
                        ('EntradaColor', 100),
                        ('CocinaFloorlamp', 40)
                    ]
                )
        if action == 'brightness_up_click':
            light_group_toggle_brightness_pct(self._z2m, [('CocinaCeiling', 100)])
        if action == 'brightness_down_click':
            light_group_toggle_brightness_pct(self._z2m, [('CocinaSink', 100), ('CocinaCountertop', 100)])
        if action == 'arrow_right_click':
            light_group_toggle_brightness_pct(self._z2m, [('EntradaCeiling', 100)])
        if action == 'arrow_left_click':
            light_group_toggle_brightness_pct(self._z2m, [('EntradaColor', 100)])


service_runner(Baticasa)
