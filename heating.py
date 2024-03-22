from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import logging
import os
import pathlib
import sys

sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))

from zigbee2mqtt2web import Zigbee2MqttAction, Zigbee2MqttActionValue
from zigbee2mqtt2web_extras.phony import PhonyZMWThing

from schedule import Schedule

log = logging.getLogger(__name__)

def _hack(thing):
    # Hack a thing so that its type is not that of a normal thing (ie not a light or a switch)
    # Removes all methods that can be 'understood' as a light or switch
    # This is useful to stop having a boiler in the normal list of things, and also to skip
    # it from the scene manager (eg when 'turning world off')
    # Note this will not stop anyone from changing the thing's state via mqtt directly
    thing.thing_type = 'boiler'

    if 'state' not in thing.actions:
        raise RuntimeError(f'Thing {thing.name} has no action "state", required for boiler control')
    if thing.actions['state'].value.meta['type'] != 'binary':
        raise RuntimeError(f"Thing {thing.name} action 'state' isn't binary, can't use it for a boiler")

    off_val = thing.actions['state'].value.meta['value_off']
    on_val = thing.actions['state'].value.meta['value_on']
    curr_val = thing.get('state')
    rm_actions = ['state', 'brightness', 'effect', 'transition']
    for act in rm_actions:
        if act in thing.actions:
            del thing.actions[act]

    class BoilerState(Zigbee2MqttActionValue):
        def __init__(self):
            self.state = curr_val

        def getter(self):
            return self.state

        def setter(self, val):
            if val == True or val == 1:
                val = on_val
            if val == False or val == 0:
                val = off_val
            self.state = val

    class BoilerStateAction(Zigbee2MqttAction):
        def accepts_value(self, key, val):
            # ZMW will use "accepts_value" to determine if a key matches a thing. Since we hijacked
            # the 'state' key, we need to accept either boiler_state or state.
            return key == 'state' or key == 'boiler_state'

    state_mgr = BoilerState()
    thing.actions['boiler_state'] = BoilerStateAction(
        name='state',
        description='Switch boiler on or off',
        can_set=True,
        can_get=True,
        value=Zigbee2MqttActionValue(
            thing_name=thing.name,
            meta={
                'type': 'user_defined',
                'on_set': state_mgr.setter,
                'on_get': state_mgr.getter},
        ))


def _set_poweron_behaviour(zmw, thing):
    if 'power_on_behavior' not in thing.actions:
        log.info("Boiler %s doesn't support power_on_behavior, not setting", thing.name)
        return

    if thing.get('power_on_behavior') in ['previous', 'off']:
        #log.debug("Boiler %s already has power_on_behavior=%s, not setting", thing.name, thing.get('power_on_behavior'))
        return

    for val in ['previous', 'off']:
        if val in thing.actions['power_on_behavior'].value.meta['values']:
            thing.set('power_on_behavior', val)
            log.info("Set boiler %s power_on_behavior to '%s'", thing.name, val)
            zmw.registry.broadcast_thing(thing)
            return

    opts = ", ".join(thing.actions['power_on_behavior'].value.meta['values'])
    log.error("Can't set boiler %s power_on_behavior, don't know what option to choose. Options: %s", thing.name, opts)


class Heating(PhonyZMWThing):
    def _print_stat_change(self, old, new):
        log.info("%s %s", old, new)

    def __init__(self, zmw):
        super().__init__(
            name="Heating",
            description="Heating controller",
            thing_type="heating",
        )

        self.schedule = Schedule(self._print_stat_change)

        self.actions = {}
        class _GetSchedule:
            def __init__(self, sched):
                self.schedule = sched
            def get(self):
                return self.schedule.as_table()
        self.actions['schedule'] = Zigbee2MqttAction(
            name='schedule',
            description='Get the schedule for the next 24 hours',
            can_set=False,
            can_get=True,
            value=_GetSchedule(self.schedule))
        class _Boost:
            def __init__(self, sched):
                self.schedule = sched
            def set(self):
                self.schedule.boost()
        self.actions['boost'] = Zigbee2MqttAction(
            name='boost',
            description='Boost heating for a number of hours',
            can_set=True,
            can_get=False,
            value=_Boost(self.schedule))

        self.zmw = zmw
        self.log_file = '/home/batman/BatiCasa/heating.log'
        #self.boiler_name = 'Boiler'
        self.boiler_name = 'Batioficina'
        self.boiler = None

        log_file = logging.FileHandler(self.log_file, mode='w')
        log_file.setLevel(logging.DEBUG)
        log_file.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        log.addHandler(log_file)
        log.info("BatiCasa heating manager starting...")

        self.zmw.webserver.add_url_rule('/heating/log', self._www_log)
        self.zmw.webserver.add_url_rule('/heating/on_forever', self._www_on_forever)
        self.zmw.webserver.add_url_rule('/heating/force_off', self._www_force_off)
        self.zmw.registry.on_mqtt_network_discovered(self._on_mqtt_net_discovery_cb)

        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

    def get_json_state(self):
        return {"schedule": self.schedule.as_table()}

    def _on_mqtt_net_discovery_cb(self):
        if self.boiler is not None:
            try:
                self.zmw.registry.get_thing(self.boiler_name)
                log.debug("MQTT network published update, boiler didn't change")
                return
            except KeyError:
                self.boiler = None
                log.error("MQTT network published update, boiler named %s is now gone", self.boiler_name)
                return

        try:
            boiler = self.zmw.registry.get_thing(self.boiler_name)
            log.debug("MQTT network discovered, found boiler %s...", self.boiler_name)
        except KeyError:
            log.error("MQTT network discovered, but there is no known boiler named %s", self.boiler_name)
            return

        # Delay processing until after network settles and we get boiler state/info
        self.zmw.registry._mqtt.update_thing_state(self.boiler_name)

        def _on_boiler_discovered():
            _hack(boiler)
            _set_poweron_behaviour(self.zmw, boiler)
            log.info("BatiCasa heating manager started. Heating state %s link %s PowerOn %s",
                      boiler.get('boiler_state'),
                      boiler.get('linkquality'),
                      boiler.get('power_on_behavior'))
            # Assign boiler only after all hacks applied - doing it before may break, as the thing won't have
            # the expected API
            self.boiler = boiler
            self.zmw.registry.register(self)
        self._scheduler.add_job(func=_on_boiler_discovered, trigger="date", run_date=datetime.now() + timedelta(seconds=3))

    def _www_log(self):
        try:
            with open(self.log_file, 'r') as fp:
                return '<pre>' + fp.read()
        except Exception as ex:
            return f"Can't get heating logs: {ex}", 500

    def _www_on_forever(self):
        if self.boiler is None:
            return "Boiler not ready"
        self.boiler.set('boiler_state', True)
        self.zmw.registry.broadcast_thing(self.boiler)
        return self._www_log()

    def _www_force_off(self):
        if self.boiler is None:
            return "Boiler not ready"
        self.boiler.set('boiler_state', False)
        self.zmw.registry.broadcast_thing(self.boiler)
        return self._www_log()

