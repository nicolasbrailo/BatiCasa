import json
import logging
import os
import pathlib
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
from zigbee2mqtt2web_extras.reolink_doorbell import ReolinkDoorbell
from zigbee2mqtt2web_extras.scenes import SceneManager
from zigbee2mqtt2web_extras.sensor_history import SensorsHistory
from zigbee2mqtt2web_extras.sonos import Sonos
from zigbee2mqtt2web_extras.spotify import Spotify
from zigbee2mqtt2web import Zigbee2Mqtt2Web

from notifications import NotificationDispatcher

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler)

fh = logging.FileHandler('/home/batman/BatiCasa/current.log', mode='w')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(fh)

log = logging.getLogger(__name__)

MY_LATLON=(51.5464371,0.111148)


### class Cronenberg:
###     def __init__(self, registry):
###         self._managing_light = False
###         self._registry = registry
### 
###     def _tick(self):
###         local_hour = datetime.datetime.now().hour # no tz, just local hour
###         if not light_outside() and local_hour < 23 and local_hour > 12:
###             logger.info("Arbolito on")
###             self._registry.get_thing('IkeaOutlet').set('state', True)
###             self._managing_light = True
### 
###         elif self._managing_light and local_hour == 23:
###             logger.info("Arbolito off")
###             self._managing_light = False
###             self._registry.get_thing('IkeaOutlet').set('state', False)
### 

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
        def comer():
            self.reg.get_thing('CocinaCeiling').set_brightness_pct(60)
            self.reg.get_thing('CocinaCountertop').set_brightness_pct(80)
            self.reg.get_thing('CocinaEntrada').set_brightness_pct(20)
            self.reg.get_thing('CocinaEntradaColor').set_brightness_pct(50)
            self.reg.broadcast_things(['CocinaCeiling', 'CocinaCountertop', 'CocinaEntrada', 'CocinaEntradaColor'])
        scenes.add_scene('Comer', 'Comer', comer)

        if 'spotify' in self._cfg:
            spotify = Spotify(self._cfg['spotify'])
            spotify.add_reauth_paths(self.zmw.webserver)
            self.reg.register(spotify)

        self.sonos = None
        if 'sonos' in self._cfg:
            self.sonos = Sonos(self._cfg['sonos'], self.zmw.webserver)
            self.reg.register(self.sonos)

        self.doorbell = None
        if 'doorbell' in self._cfg:
            self.doorbell = ReolinkDoorbell(self._cfg['doorbell'], self.zmw)

        self.notifications = NotificationDispatcher(self._cfg, self.zmw, self.sonos, self.doorbell)

        self.zmw.start_and_block()
        self.zmw.stop()

    def on_net_discovery(self):
        reg = self.zmw.registry

        reg.register_and_shadow_mqtt_thing(
            MultiMqttThing(reg, 'Comedor', ['ComedorL', 'ComedorR'])
        )
        def boton_comedor_click(action):
            if action == 'on_press':
                reg.get_thing('Comedor').set_brightness_pct(100)
                reg.get_thing('Comedor').set('color_temp', 250)
                reg.get_thing('Snoopy').set_brightness_pct(100)
            if action == 'up_press':
                reg.get_thing('Comedor').set_brightness_pct(60)
                reg.get_thing('Comedor').set('color_temp', 370)
                reg.get_thing('Snoopy').set_brightness_pct(60)
            if action == 'down_press':
                reg.get_thing('Comedor').set_brightness_pct(30)
                reg.get_thing('Comedor').set('color_temp', 454)
                reg.get_thing('Snoopy').set_brightness_pct(30)
            if action == 'off_press':
                reg.get_thing('Comedor').set_brightness_pct(0)
                reg.get_thing('Snoopy').set_brightness_pct(0)
            reg.broadcast_things(['Comedor', 'Snoopy'])
        self.install_cb('BotonComedor', 'action', boton_comedor_click)


        reg.register_and_shadow_mqtt_thing(
            MultiMqttThing(reg, 'CocinaCountertop', ['CocinaCountertop1', 'CocinaCountertop2'])
        )

        def boton_cocina_click(action):
            if action == 'toggle':
                light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 60), ('CocinaCountertop', 80), ('CocinaEntrada', 20), ('CocinaEntradaColor', 60)]);
            if action == 'brightness_up_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 100)]);
            if action == 'brightness_down_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCountertop', 100)]);
            if action == 'arrow_right_click':
                light_group_toggle_brightness_pct(reg, [('CocinaEntrada', 100)]);
            if action == 'arrow_left_click':
                light_group_toggle_brightness_pct(reg, [('CocinaEntradaColor', 100)]);
            if action == 'toggle_hold':
                time.sleep(2)
                reg.get_thing(self._cfg['sonos']['zmw_thing_name']).play_announcement('http://bati.casa/web_assets/winxpshutdown.mp3', timeout_secs=20)
                reg.get_thing('SceneManager').actions['World off'].apply_scene()
        self.install_cb('BotonCocina', 'action', boton_cocina_click)

        def boton_cocina_entrada_click(action):
            if action == 'toggle':
                self.main_door_monitor.trigger_leaving_routine()
                return
            return boton_cocina_click(action)
        self.install_cb('BotonCocinaEntrada', 'action', boton_cocina_entrada_click)

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

        def boton_olma_click(action):
            if action == 'on':
                light_group_toggle_brightness_pct(reg, [('VeladorEmma', 80), ])
            if action == 'off':
                light_group_toggle_brightness_pct(reg, [('VeladorOlivia', 80), ])
        self.install_cb('BotonOlma', 'action', boton_olma_click)

        def boton_batiloft_click(action):
            light_group_toggle_brightness_pct(reg, [('NicoVelador', 40), ('Belador', 60), ])
        self.install_cb('BotonBatiloft', 'action', boton_batiloft_click)

        self.pbMotionActivatedNightLight = MotionActivatedNightLight(reg,
                                                    ['SensorEscaleraPB1', 'SensorEscaleraPB2'],
                                                    'CocinaEntrada', MY_LATLON)
        self.pbMotionActivatedNightLight.configure('off_during_late_night', True)

        self.main_door_monitor = MainDoorMonitor(self.zmw, {
            'contact_sensor_name': 'SensorPuertaEntrada',
            # Works for aqara sensor, never tried with anything else
            'on_contact_action_name': 'contact',
            'lat_lon': MY_LATLON,
            'managed_lamps': [('CocinaCeiling', 40), ('CocinaEntrada', 80),],
        })
        self.register_sensor('SensorPuertaEntrada', ['device_temperature'])

        self.ventana_banio_monitor = MainDoorMonitor(self.zmw, {
            'contact_sensor_name': 'SensorVentanaBanio',
            'on_contact_action_name': 'contact',
            'lat_lon': MY_LATLON,
            'managed_lamps': [],
        })
        self.register_sensor('SensorVentanaBanio', ['device_temperature'])

        self.register_sensor("SensorTHBanio", ['temperature', 'humidity'])
        self.register_sensor("SensorTHCocina", ['temperature', 'humidity'])
        self.register_sensor("SensorTHOlma", ['temperature', 'humidity'])
        self.register_sensor("SensorAQMOlma", ['humidity', 'pm25', 'temperature', 'voc_index'])
        self.register_sensor("SensorAQMTVRoom", ['humidity', 'pm25', 'temperature', 'voc_index'])
        self.register_sensor("SensorAQMCuarto", ['humidity', 'pm25', 'temperature', 'voc_index'])
        self.zmw.registry.get_thing("SensorAQMOlma").is_mqtt_spammy = True
        self.zmw.registry.get_thing("SensorAQMTVRoom").is_mqtt_spammy = True
        self.zmw.registry.get_thing("SensorAQMCuarto").is_mqtt_spammy = True

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
