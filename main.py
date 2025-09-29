import json
import logging
import os
import pathlib
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from flask import send_from_directory

sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))

from zigbee2mqtt2web_extras.heating import Heating
from zigbee2mqtt2web_extras.light_helpers import any_light_on
from zigbee2mqtt2web_extras.light_helpers import any_light_on_in_the_house
from zigbee2mqtt2web_extras.light_helpers import light_group_toggle_brightness_pct
from zigbee2mqtt2web_extras.main_door_monitor import MainDoorMonitor
from zigbee2mqtt2web_extras.monkeypatching import add_all_known_monkeypatches
from zigbee2mqtt2web_extras.motion_sensors import MotionActivatedNightLight
from zigbee2mqtt2web_extras.motion_sensors import MultiMotionSensor
from zigbee2mqtt2web_extras.multi_mqtt_thing import MultiMqttThing
from zigbee2mqtt2web_extras.reolink_cam import ReolinkDoorbell, Nvr
from zigbee2mqtt2web_extras.scenes import SceneManager
from zigbee2mqtt2web_extras.sensor_history import SensorsHistory
from zigbee2mqtt2web_extras.sonos import Sonos
from zigbee2mqtt2web_extras.spotify import Spotify
from zigbee2mqtt2web import Zigbee2Mqtt2Web

from notifications import NotificationDispatcher
from crons import Cronenberg

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler)

#fh = logging.FileHandler('/home/batman/BatiCasa/current.log', mode='w')
fh = TimedRotatingFileHandler('/home/batman/BatiCasa/current.log', when='midnight', backupCount=3)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(fh)

log = logging.getLogger(__name__)

MY_LATLON=(51.5464371,0.111148)


from zigbee2mqtt2web_extras.phony import PhonyZMWThing
class UIUserDefinedButtons(PhonyZMWThing):
    def __init__(self, button_map):
        self.name = "UIUserButtons"
        self.description = "UI User defined buttons"
        self.thing_type = "UI User defined buttons"
        self._add_action("get", "Get user defined buttons", getter=self._get_udb)
        self._button_map = button_map
        for k,v in button_map.items():
            self._add_action(k, v)

    def _get_udb(self):
        return self._button_map


class App:
    def __init__(self, cfg):
        self._cfg = cfg
        self.first_discovery_done = False

        retention_rows = cfg['sensor_db_retention_rows'] if 'sensor_db_retention_rows' in cfg else None
        retention_days = cfg['sensor_db_retention_days'] if 'sensor_db_retention_days' in cfg else None
        self.sensors = SensorsHistory(cfg['sensor_db_path'], retention_rows, retention_days)

        self.zmw = Zigbee2Mqtt2Web(cfg, self.on_net_discovery)

        self.heating = None
        if 'heating' in cfg:
            self.heating = Heating(cfg['heating'], self.zmw)

        self.zmw.webserver.add_url_rule('/svcs', self._baticasa_svc_idx)
        self.crons = Cronenberg(self.zmw, MY_LATLON)

        add_all_known_monkeypatches(self.zmw)
        self.reg = self.zmw.registry

        self.reg.register(UIUserDefinedButtons({
                '/svcs': 'Services',
                #'/nvr/ls': 'Cams',
                '/www/heating.html': 'Heating',
                '/nvr/10.0.0.20/gallery/2/days': 'Cams',
            }))

        scenes = SceneManager(self.zmw.registry)
        def skip_next_chime():
            self.main_door_monitor.skip_next_door_open_chime()
        scenes.add_scene('Skip door chime', 'Skip door chime', skip_next_chime)
        def comer():
            self.reg.get_thing('CocinaCeiling').set_brightness_pct(70)
            self.reg.get_thing('CocinaCountertop').set_brightness_pct(80)
            self.reg.get_thing('CocinaEntrada').set_brightness_pct(50)
            self.reg.get_thing('EntradaColor').set_brightness_pct(90)
            self.reg.get_thing('CocinaSofa').set_brightness_pct(30)
            self.reg.broadcast_things(['CocinaCeiling', 'CocinaCountertop', 'CocinaEntrada', 'EntradaColor', 'CocinaSofa'])
        scenes.add_scene('Comer', 'Comer', comer)
        def gezellig():
            self.reg.get_thing('CocinaCountertop').set_brightness_pct(50)
            self.reg.get_thing('CocinaCeiling').set_brightness_pct(20)
            self.reg.get_thing('CocinaEntrada').set_brightness_pct(15)
            self.reg.get_thing('EntradaColor').set_brightness_pct(90)
            self.reg.get_thing('CocinaSofa').set_brightness_pct(10)
            self.reg.broadcast_things(['CocinaCeiling', 'CocinaCountertop', 'CocinaEntrada', 'EntradaColor', 'CocinaSofa'])
        scenes.add_scene('Gezellig', 'Gezellig', gezellig)
        def predormir():
            self.reg.get_thing('CocinaCountertop').set_brightness_pct(0)
            self.reg.get_thing('CocinaCeiling').set_brightness_pct(0)
            self.reg.get_thing('CocinaEntrada').set_brightness_pct(0)
            self.reg.get_thing('EntradaColor').set_brightness_pct(0)
            self.reg.get_thing('CocinaSofa').set_brightness_pct(0)
            self.reg.get_thing('Comedor').set_brightness_pct(5)
            self.reg.get_thing('Comedor').set('color_temp', 454)
            self.reg.get_thing('Snoopy').set_brightness_pct(30)
            self.reg.get_thing('VeladorEmma').set_brightness_pct(25)
            self.reg.get_thing('VeladorOlivia').set_brightness_pct(25)
            self.reg.get_thing('Belador').set_brightness_pct(25)
            self.reg.get_thing('NicoVelador').set_brightness_pct(25)
            self.reg.broadcast_things(['CocinaCeiling', 'CocinaCountertop', 'CocinaEntrada', 'EntradaColor',
                                       'CocinaSofa', 'Comedor', 'Snoopy', 'VeladorEmma', 'VeladorOlivia', 'NicoVelador', 'Belador'])
        scenes.add_scene('a dormir', 'a dormir', predormir)

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
            self.nvr = Nvr(self._cfg['doorbell']['rec_path'])
            self.zmw.webserver.add_url_rule('/nvr/ls', self.nvr._list_cams)
            self.zmw.webserver.add_url_rule('/nvr/<cam>/gallery', self.nvr._list_cam_recs_as_gallery)
            self.zmw.webserver.add_url_rule('/nvr/<cam>/gallery/<days>/days', self.nvr._list_cam_recs_as_gallery_days)
            self.zmw.webserver.add_url_rule('/nvr/<cam>/files', self.nvr._list_cam_recs)
            self.zmw.webserver.add_url_rule('/nvr/<cam>/get_recording/<file>', self.nvr._get_recording)

        self.notifications = NotificationDispatcher(self._cfg, self.zmw, self.sonos, self.doorbell)

        self.boton_cocina_click_state = 0
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
                if not self.crons.redshifting:
                    reg.get_thing('Comedor').set('color_temp', 250)
                reg.get_thing('Snoopy').set_brightness_pct(100)
            if action == 'up_press':
                reg.get_thing('Comedor').set_brightness_pct(60)
                if not self.crons.redshifting:
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

        self.boton_cocina_click_state = 0
        def boton_cocina_click(action):
            self.main_door_monitor.stop_leaving_routine_if_active()
            if action == 'toggle':
                global boton_cocina_click
                group_on = any_light_on(reg, ['CocinaCeiling', 'CocinaCountertop', 'CocinaEntrada', 'EntradaColor', 'CocinaSofa'])
                if not group_on:
                    self.boton_cocina_click_state = 0
                if self.boton_cocina_click_state == 0:
                    reg.get_thing('SceneManager').actions['Gezellig'].apply_scene()
                    self.boton_cocina_click_state = 1
                elif self.boton_cocina_click_state == 1:
                    reg.get_thing('SceneManager').actions['Comer'].apply_scene()
                    self.boton_cocina_click_state = 2
                else:
                    light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 60), ('CocinaCountertop', 80), ('CocinaEntrada', 20), ('EntradaColor', 60), ('CocinaSofa', 20)]);
            if action == 'brightness_up_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCeiling', 100)]);
            if action == 'brightness_down_click':
                light_group_toggle_brightness_pct(reg, [('CocinaCountertop', 100)]);
            if action == 'arrow_right_click':
                light_group_toggle_brightness_pct(reg, [('CocinaEntrada', 100)]);
            if action == 'arrow_left_click':
                light_group_toggle_brightness_pct(reg, [('EntradaColor', 100)]);
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

        self.boton_olivia_click_num = 0
        self.boton_olivia_click_off_num = 0
        def boton_olivia_click(action):
            if action == 'on':
                lamp = reg.get_thing('VeladorOlivia')
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
                    lamp.set_brightness_pct(0)
                lamp.set('transition', 2)
                reg.broadcast_thing(lamp)
                lamp.set('transition', 0)

            if action == 'off':
                lamp = reg.get_thing('OliviaFloorlamp')
                self.boton_olivia_click_off_num += 1
                if self.boton_olivia_click_off_num == 1:
                    lamp.set_brightness_pct(50)
                elif self.boton_olivia_click_off_num == 2:
                    lamp.set_brightness_pct(100)
                else:
                    self.boton_olivia_click_off_num = 0
                    lamp.set_brightness_pct(0)
                lamp.set('transition', 2)
                reg.broadcast_thing(lamp)
                lamp.set('transition', 0)
        self.install_cb('BotonOlivia', 'action', boton_olivia_click)

        self.boton_emma_click_num = 0
        self.boton_emma_click_off_num = 0
        def boton_emma_click(action):
            if action == 'on':
                lamp = reg.get_thing('VeladorEmma')
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
                    lamp.set_brightness_pct(0)
                lamp.set('transition', 2)
                reg.broadcast_thing(lamp)
                lamp.set('transition', 0)

            if action == 'off':
                lamp = reg.get_thing('EmmaFloorlamp')
                lamp2 = reg.get_thing('EmmaTriangleLamp')
                self.boton_emma_click_off_num += 1
                if self.boton_emma_click_off_num == 1:
                    lamp.set_brightness_pct(50)
                    lamp2.set_brightness_pct(50)
                elif self.boton_emma_click_off_num == 2:
                    lamp.set_brightness_pct(100)
                    lamp2.set_brightness_pct(100)
                else:
                    self.boton_emma_click_off_num = 0
                    lamp.set_brightness_pct(0)
                    lamp2.set_brightness_pct(0)
                lamp.set('transition', 2)
                lamp2.set('transition', 2)
                reg.broadcast_thing(lamp)
                reg.broadcast_thing(lamp2)
                lamp.set('transition', 0)
                lamp2.set('transition', 0)
        self.install_cb('BotonEmma', 'action', boton_emma_click)

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
        self.zmw.registry.get_thing("SensorTHBanio").is_mqtt_spammy = True
        self.zmw.registry.get_thing("SensorTHCocina").is_mqtt_spammy = True
        self.zmw.registry.get_thing("SensorTHOlma").is_mqtt_spammy = True

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

    def _baticasa_svc_idx(self):
        return send_from_directory(self._cfg["www_extra_local_path"], "svcs.html")


with open('BatiCasa.config.json', 'r') as fp:
    CFG = json.loads(fp.read())
App(CFG)
