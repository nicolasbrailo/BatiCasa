""" Doorbell/ONVIF-camera service """

import sys
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import request as FlaskRequest

sys.path.append('/home/batman/src/BatiCasa/reolink_aio')

from reolink_aio.api import Host as ReolinkDoorbell
from reolink_aio.helpers import parse_reolink_onvif_event

logging.getLogger("reolink_aio.api").setLevel(logging.ERROR)
logging.getLogger("reolink_aio.helpers").setLevel(logging.ERROR)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)

log = logging.getLogger(__name__)


# Watchdog for cam subscription
_CAM_SUBSCRIPTION_CHECK_INTERVAL_SECS=60


def _register_webhook_url(cfg, zmw, cb):
    # Ensure cfg has required keys
    cfg['webhook_base_path']
    if not 'webhook_service' in cfg or len(cfg['webhook_service']) == 0:
        raise KeyError("webhook_service must be configured to a server accesible by the camera")

    # Create a webhook endpoint in the zmw web server
    if len(cfg['webhook_base_path']) > 0 and cfg['webhook_base_path'][0] == '/':
        webhook_path = f"{cfg['webhook_base_path']}{cfg['host']}"
    else:
        webhook_path = f"/{cfg['webhook_base_path']}{cfg['host']}"

    if cfg['webhook_service'][-1] == '/':
        webhook_url = f"{cfg['webhook_service']}{webhook_path}"
    else:
        webhook_url = f"{cfg['webhook_service']}/{webhook_path}"

    zmw.webserver.add_url_rule(webhook_path, cb, methods=['GET', 'POST'])
    log.info("Registered webhook %s for camera %s...", webhook_url, cfg['host'])
    return webhook_url


async def _connect_to_cam(cfg, webhook_url):
    log.info("Connecting to doorbell at %s...", cfg['host'])
    cam = ReolinkDoorbell(cfg['host'], cfg['user'], cfg['pass'], use_https=True)

    # Fetch all cam state
    await cam.get_host_data()
    await cam.get_states()
    cam.construct_capabilities()

    # Cleanup old subscriptions, if there were any
    await cam.unsubscribe()
    await cam.subscribe(webhook_url)

    log.info("Connected to doorbell %s %s model %s - firmware %s",
        cfg['host'],
        cam.camera_name(0),
        cam.camera_model(0),
        cam.camera_sw_version(0))

    if not cam.is_doorbell(0):
        log.error("Something is wrong, %s reports it isn't a doorbell!", cfg['host'])

    return cam



class Timbre:
    """ Subscribe to ONVIF notifications from a Reolink cam """

    def __init__(self, cfg, zmw, sonos_name):
        """ Logs in and subscribes to camera events """
        # __del__ will run if the ctor fails, so mark "we've been here" somehow
        self._cam = None

        webhook_url = _register_webhook_url(cfg, zmw, self._on_cam_webhook)
        cam = asyncio.run(_connect_to_cam(cfg, webhook_url))
        self._cam_host = cfg['host']

        self._scheduler = BackgroundScheduler()
        self._cam_subscription_watchdog = self._scheduler.add_job(
            func=self._check_cam_subscription,
            trigger="interval",
            seconds=_CAM_SUBSCRIPTION_CHECK_INTERVAL_SECS)

        # Object should be fully constructed now
        self._sonos_name = sonos_name
        self._zmw = zmw
        self._cam = cam
        self._scheduler.start()

    def __del__(self):
        self.deinit()

    def deinit(self):
        """ Logs out and tries to cleanup subscriptions to events in the camera """
        if self._cam is None:
            # Constructor failed
            return

        async def _async_deinit():
            await self._cam.unsubscribe()
            await self._cam.logout()
            log.info("Disconnecting from doorbell at %s...", self._cam_host)
        self._cam_subscription_watchdog.remove()
        asyncio.run(_async_deinit())

    def _check_cam_subscription(self):
        t = self._cam.renewtimer()
        if (t <= 100):
            log.debug("Subscription to cam %s has %s seconds remaining, renewing",
                      self._cam_host, t)
            asyncio.run(self._cam.renew())

    def _on_cam_webhook(self):
        msg = parse_reolink_onvif_event(FlaskRequest.data)
        log.info("Received event from camera %s: %s", self._cam_host, str(msg))

        # msg should look something like this:
        # {0: {'Motion': False, 'MotionAlarm': False, 'Visitor': False},
        # 'VideoSourceToken': {'FaceDetect': False, 'PeopleDetect': False,
        #                      'VehicleDetect': False, 'DogCatDetect': False}}

        if msg[0]['Visitor']:
            sonos = self._zmw.registry.get_thing(self._sonos_name)
            sonos.play_announcement('http://192.168.1.20/web_assets/knockknock.mp3', timeout_secs=20)
        if msg[0]['Motion']:
            sonos.tts_announce('es', 'Hay alguien en la puerta')

        return '', 200
