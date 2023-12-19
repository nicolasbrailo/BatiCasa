import json
import logging
import os
import pathlib
import sys
import sys
import time

sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))

from zigbee2mqtt2web_extras.light_helpers import any_light_on_in_the_house
from zigbee2mqtt2web_extras.light_helpers import light_group_toggle_brightness_pct
from zigbee2mqtt2web_extras.main_door_monitor import MainDoorMonitor
from zigbee2mqtt2web_extras.monkeypatching import add_all_known_monkeypatches
from zigbee2mqtt2web_extras.motion_sensors import MotionActivatedNightLight
from zigbee2mqtt2web_extras.motion_sensors import MultiMotionSensor
from zigbee2mqtt2web_extras.multi_mqtt_thing import MultiMqttThing
from zigbee2mqtt2web_extras.scenes import SceneManager
from zigbee2mqtt2web_extras.sensor_history import SensorsHistory
from zigbee2mqtt2web_extras.sonos import Sonos
from zigbee2mqtt2web_extras.spotify import Spotify
from zigbee2mqtt2web import Zigbee2Mqtt2Web

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler)

import logging
logger = logging.getLogger(__name__)

class App:
    def __init__(self, cfg):
        self._cfg = cfg
        self.first_discovery_done = False

        retention_rows = cfg['sensor_db_retention_rows'] if 'sensor_db_retention_rows' in cfg else None
        retention_days = cfg['sensor_db_retention_days'] if 'sensor_db_retention_days' in cfg else None
        self.sensors = SensorsHistory(cfg['sensor_db_path'], retention_rows, retention_days)

        self.zmw = Zigbee2Mqtt2Web(cfg)
        self.zmw.registry.on_mqtt_network_discovered(self.on_net_discovery)
        add_all_known_monkeypatches(self.zmw)
        self.reg = self.zmw.registry

        scenes = SceneManager(self.zmw.registry)
        def skip_next_chime():
            self.main_door_monitor.skip_next_door_open_chime()
        scenes.add_scene('Skip next door open chime', 'Skip next door open chime', skip_next_chime)

        if 'spotify' in self._cfg:
            spotify = Spotify(self._cfg['spotify'])
            spotify.add_reauth_paths(self.zmw.webserver)
            self.reg.register(spotify)

        if 'sonos' in self._cfg:
            self.reg.register(Sonos(self._cfg['sonos'], self.zmw.webserver))

        self.zmw.start_and_block()
        self.zmw.stop()

    def on_net_discovery(self):
        reg = self.zmw.registry

        reg.register_and_shadow_mqtt_thing(
            MultiMqttThing(reg, 'Comedor', ['ComedorL', 'ComedorR'])
        )
        def boton_comedor_click(action):
            if action == 'toggle':
                light_group_toggle_brightness_pct(reg, [('Comedor', 100), ]);
            if action == 'brightness_up_click':
                reg.get_thing('Comedor').set_brightness_pct(100)
                reg.broadcast_thing('Comedor')
            if action == 'brightness_down_click':
                reg.get_thing('Comedor').set_brightness_pct(0)
                reg.broadcast_thing('Comedor')
        self.install_cb('BotonComedor', 'action', boton_comedor_click)

        def boton_cocina_click(action):
            if action == 'toggle':
                light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 60), ('CocinaCountertop', 60), ('CocinaEntrada', 20)]);
            if action == 'brightness_up_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 100)]);
            if action == 'brightness_down_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCountertop', 100)]);
            if action == 'toggle_hold':
                time.sleep(2)
                reg.get_thing(self._cfg['sonos']['zmw_thing_name']).play_announcement('http://192.168.1.20/web_assets/winxpshutdown.mp3', timeout_secs=20)
                reg.get_thing('SceneManager').actions['World off'].apply_scene()
        self.install_cb('BotonCocina', 'action', boton_cocina_click)

        def boton_belador_click(action):
            if action != 'press':
                return
            if any_light_on_in_the_house(reg):
                time.sleep(2)
                reg.get_thing('SceneManager').actions['World off'].apply_scene()
            else:
                lamp = reg.get_thing('Belador')
                lamp.set_brightness_pct(10)
                reg.broadcast_thing(lamp)
        self.install_cb('BotonBelador', 'action', boton_belador_click)

        self.main_door_monitor = MainDoorMonitor(self.zmw, {
            'contact_sensor_name': 'SensorPuertaEntrada',
            # Works for aqara sensor, never tried with anything else
            'on_contact_action_name': 'contact',
            'sonos_name': self._cfg['sonos']['zmw_thing_name'],
            'lat_lon': (51.5464371,0.111148),
            #'chime_url': 'http://bati.casa/web_assets/win95.mp3', # XXX TODO
            'chime_url': 'http://192.168.1.20/web_assets/win95.mp3',
            'managed_lamps': [('CocinaCeiling', 40), ('CocinaEntrada', 80),],
        })
        self.register_sensor('SensorPuertaEntrada', ['device_temperature'])

        self.register_sensor("SensorTHBanio", ['temperature', 'humidity'])
        self.register_sensor("SensorTHCocina", ['temperature', 'humidity'])
        self.register_sensor("SensorTHEntrada", ['temperature', 'humidity'])
        self.register_sensor("SensorAQMOlma", ['humidity', 'pm25', 'temperature', 'voc_index'])
        self.register_sensor("SensorAQMTVRoom", ['humidity', 'pm25', 'temperature', 'voc_index'])
        #self.register_sensor("SensorAQMCuarto", ['humidity', 'pm25', 'temperature', 'voc_index'])

        if self.first_discovery_done:
            return

        self.sensors.register_to_webserver(self.zmw.webserver)
        self.first_discovery_done = True


    def register_sensor(self, thing_name, supported_metrics):
        self.sensors.register_sensor(
                self.zmw.registry.get_thing(thing_name),
                supported_metrics
        )

    def install_cb(self, thing, changed_prop, cb):
        self.zmw.registry.get_thing(thing).actions[changed_prop].value.on_change_from_mqtt = cb


with open('BatiCasa.config.json', 'r') as fp:
    CFG = json.loads(fp.read())
App(CFG)
