import datetime
import json
import logging
import os
import pathlib
import sys
import sys
import time

sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))

from zigbee2mqtt2web import Zigbee2Mqtt2Web
from zigbee2mqtt2web_extras.utils.geo_helper import light_outside
from zigbee2mqtt2web_extras.light_helpers import any_light_on_in_the_house
from zigbee2mqtt2web_extras.light_helpers import light_group_toggle_brightness_pct
from zigbee2mqtt2web_extras.monkeypatching import add_all_known_monkeypatches
from zigbee2mqtt2web_extras.motion_sensors import MotionActivatedNightLight
from zigbee2mqtt2web_extras.motion_sensors import MultiMotionSensor
from zigbee2mqtt2web_extras.multi_mqtt_thing import MultiMqttThing
from zigbee2mqtt2web_extras.scenes import SceneManager
from zigbee2mqtt2web_extras.sensor_history import SensorsHistory
from zigbee2mqtt2web_extras.sonos import Sonos
from zigbee2mqtt2web_extras.spotify import Spotify

from apscheduler.schedulers.background import BackgroundScheduler

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler)

import logging
logger = logging.getLogger(__name__)

# TODO: Make sensor history safe to thing re-registration
# TODO: UI for unknown/broken/hidden/button things
# TODO: On new network announcement, try to merge old state

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
### class LeavingRoutine:
###     def __init__(self, sonos_name, world):
###         self.world = world
###         self.sonos_name = sonos_name
###         self._bg = None
###         self._skip_chime_bg = None
###         self.timeout_secs = 60 * 4
###         self.managed_things = [('ComedorII', 100), ('EscaleraPBLight', 50)]
###         # If True, plays a ringtone when the door-open event is triggered
###         self.play_door_open_chime = True
### 
### 
###     def trigger_leaving_routine(self):
###         logger.info("Leaving home scene on")
###         if self._bg is not None:
###             self._bg.remove()
### 
###         self._bg = self._scheduler.add_job(func=self._timeout,
###                                trigger="interval", seconds=self.timeout_secs)
### 
### 
###     def _timeout(self):
###         logger.info("Leaving timeout: shutdown all managed lights")
###         for t,_pct in self.managed_things:
###             self.world.get_thing(t).turn_off()
###         self.world.broadcast_things([x for x,_ in self.managed_things])
###         self._bg.remove()
### 
### 
class App:
    def __init__(self, cfg):
        self._cfg = cfg
        self.first_discovery_done = False
        self.zmw = Zigbee2Mqtt2Web(cfg)
        self.zmw.registry.on_mqtt_network_discovered(self.on_net_discovery)
        add_all_known_monkeypatches(self.zmw)
        retention_rows = cfg['sensor_db_retention_rows'] if 'sensor_db_retention_rows' in cfg else None
        retention_days = cfg['sensor_db_retention_days'] if 'sensor_db_retention_days' in cfg else None
        self.sensors = SensorsHistory(cfg['sensor_db_path'], retention_rows, retention_days)
###         self.cron = Cronenberg(self.zmw.registry)
###         self.leaving_routine = LeavingRoutine(self._cfg['sonos']['zmw_thing_name'], self.zmw.registry)

        if 'spotify' in self._cfg:
            spotify = Spotify(self._cfg['spotify'])
            spotify.add_reauth_paths(self.zmw.webserver)
            self.zmw.registry.register(spotify)

        if 'sonos' in self._cfg:
            self.zmw.registry.register(Sonos(self._cfg['sonos'], self.zmw.webserver))

    def run_blocking(self):
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

        reg.get_thing('BotonComedor').actions['action'].value.on_change_from_mqtt = boton_comedor_click

        def on_report_sensor_puerta_entrada(has_contact):
            if has_contact:
                logger.info('Puerta de entrada cerrada')
            else:
                if not light_outside(MY_LATLON):
                    logger.info('Puerta de entrada abierta, trigger leaving routine')
                    self.leaving_routine.trigger_leaving_routine()
                else:
                    logger.info('Puerta de entrada abierta')
                self.leaving_routine.door_open_announce_and_block()
        registry.get_thing('SensorPuertaEntrada')\
            .actions['contact'].value.on_change_from_mqtt = on_report_sensor_puerta_entrada


        self.register_custom_behaviour(self.zmw.registry)
        self.register_sensors()

        if self.first_discovery_done:
            return

        self.sensors.register_to_webserver(self.zmw.webserver)
        self.register_custom_things()
        self.register_scenes()
        self.first_discovery_done = True

    def register_custom_behaviour(self, registry):
        return
###         #######################################################################
###         def boton_comedor_pressed(action):
###             transition = 3
###             if action == 'on_press':
###                 registry.get_thing('Snoopy').set_brightness_pct(80)
###                 registry.get_thing('Comedor').set_brightness_pct(100)
###                 registry.get_thing('Comedor').set('color_rgb', 'FFF')
###             elif action == 'up_press':
###                 registry.get_thing('Snoopy').set_brightness_pct(40)
###                 registry.get_thing('Comedor').set_brightness_pct(80)
###                 registry.get_thing('Comedor').set('color_rgb', 'FFA600')
###             elif action == 'down_press':
###                 registry.get_thing('Snoopy').set_brightness_pct(5)
###                 registry.get_thing('Comedor').set_brightness_pct(15)
###                 registry.get_thing('Comedor').set('color_rgb', 'FF6400')
###             elif action == 'off_press' or action[-5:] == '_hold':
###                 registry.get_thing('Snoopy').turn_off()
###                 registry.get_thing('Comedor').turn_off()
###                 transition = 0
###             else:
###                 # Return early on unknown action, to avoid a spurious bcast
###                 return
### 
###             registry.get_thing('Comedor').set('transition', transition)
###             registry.get_thing('Snoopy').set('transition', transition)
###             registry.broadcast_things(['Snoopy', 'Comedor'])
### 
###         registry.get_thing('BotonComedor')\
###             .actions['action'].value.on_change_from_mqtt = boton_comedor_pressed
###         #######################################################################
###         def batipieza_boton_pressed(action):
###             if action == 'on':
###                 light_group_toggle_brightness_pct(registry, [
###                         ('Belador', 30),
###                         ('NicoVelador', 25),
###                     ]);
###             if action == 'off':
###                 lamp = registry.get_thing('EscaleraP1')
###                 lamp.set_brightness_pct(25)
###                 registry.broadcast_thing(lamp)
### 
###         registry.get_thing('BatipiezaBoton')\
###             .actions['action'].value.on_change_from_mqtt = batipieza_boton_pressed
###         #######################################################################
### 
###         registry.get_thing('BeladorBoton')\
###             .actions['action'].value.on_change_from_mqtt = belador_boton_pressed
###         #######################################################################
###         def boton_cocina_pressed(action):
###             if action == 'on':
###                 light_group_toggle_brightness_pct(registry, [
###                         ('CocinaCeiling', 100),
###                     ]);
###             if action == 'off':
###                 light_group_toggle_brightness_pct(registry, [
###                         ('CocinaCountertop', 100),
###                     ]);
### 
###         registry.get_thing('BotonCocina')\
###             .actions['action'].value.on_change_from_mqtt = boton_cocina_pressed
###         #######################################################################
###         def boton_entrada_pressed(action):
###             if action == 'toggle':
###                 self.leaving_routine.trigger_leaving_routine()
###             if action == 'brightness_up_click':
###                 registry.get_thing('SceneManager').actions['Comedor tarde'].apply_scene()
###             if action == 'brightness_down_click':
###                 registry.get_thing('SceneManager').actions['World off'].apply_scene(all_except=['ComedorII'])
###             if action == 'toggle_hold':
###                 registry.get_thing('SceneManager').actions['World off'].apply_scene()
### 
###         registry.get_thing('BotonEntrada')\
###             .actions['action'].value.on_change_from_mqtt = boton_entrada_pressed
###         #######################################################################
###         #######################################################################
###         self.foo = MotionActivatedNightLight(registry, ['SensorEscaleraPB1', 'SensorEscaleraPB2'], 'EscaleraPBLight', MY_LATLON)
###         self.bar = MotionActivatedNightLight(registry, ['SensorEscaleraP1P2'], 'EscaleraP1', MY_LATLON)
###         self.bar.configure('off_during_late_night', True)
### 
### 
    def register_custom_things(self):
        return
### 
###         self.zmw.registry.register_and_shadow_mqtt_thing(
###             MultiMqttThing(self.zmw.registry, 'CocinaCountertop', ['CocinaCountertop1', 'CocinaCountertop2'])
###         )
### 
    def register_sensors(self):
        register = lambda sensor_name, metrics: \
            self.sensors.register_sensor(
                    self.zmw.registry.get_thing(sensor_name),
                    metrics
            )

        register('SensorPuertaEntrada', ['temperature'])
###         register('SensorHTOlma', ['temperature', 'humidity'])
###         register('SensorHTBatipieza', ['temperature', 'humidity'])
### 
    def register_scenes(self):
        scenes = SceneManager(self.zmw.registry)
### 
###         def comedor_dia():
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'FFFFFF')
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(100)
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(100)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.broadcast_things(['Comedor', 'Snoopy'])
###         scenes.add_scene('Comedor dia', 'Luces altas, comedor', comedor_dia)
### 
###         def comedor_tarde():
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'FF8820')
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(60)
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(60)
###             self.zmw.registry.get_thing('EscaleraP1').set_brightness_pct(15)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.get_thing('EscaleraP1').set('transition', 3)
###             self.zmw.registry.broadcast_things(['Comedor', 'Snoopy', 'EscaleraP1'])
###         scenes.add_scene('Comedor tarde', 'Comedor, luces medias', comedor_tarde)
### 
###         def dormir():
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'C20')
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(5)
###             self.zmw.registry.get_thing('EscaleraP1').turn_off()
###             self.zmw.registry.get_thing('CocinaCountertop').turn_off()
###             self.zmw.registry.get_thing('CocinaCeiling').turn_off()
###             self.zmw.registry.get_thing('OficinaVelador').turn_off()
###             self.zmw.registry.get_thing('Oficina').turn_off()
###             self.zmw.registry.get_thing('ComedorII').turn_off()
###             self.zmw.registry.get_thing('NicoVelador').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Belador').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.get_thing('EscaleraP1').set('transition', 3)
###             self.zmw.registry.broadcast_things([
###                 'Comedor', 'Snoopy', 'EscaleraP1', 'CocinaCountertop', 'CocinaCeiling',
###                 'OficinaVelador', 'Oficina', 'ComedorII', 'NicoVelador', 'Belador'])
###         scenes.add_scene('Dormir', 'Luces bajas en toda la casa', dormir)
### 
###         self.zmw.registry.register(scenes)
### 

cfg_file = './config.test.json' if len(sys.argv) > 1 else 'BatiCasa.config.json'
with open(cfg_file, 'r') as fp:
    CFG = json.loads(fp.read())
app = App(CFG)
app.run_blocking()

