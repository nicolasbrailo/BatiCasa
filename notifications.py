from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import os
import pathlib
import sys

sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))
from zigbee2mqtt2web_extras.utils.telegram import TelegramLongpollBot
from zigbee2mqtt2web_extras.utils.whatsapp import WhatsApp
from zigbee2mqtt2web.mqtt_proxy import MqttProxy

import logging
log = logging.getLogger(__name__)

from datetime import datetime, time


class BatiCasaTelegramBot(TelegramLongpollBot):
    def __init__(self, zmw, tok, poll_interval_secs):
        def _bcast_telegram_cmd(bot, msg):
            zmw.announce_system_event({
                'event': 'on_telegram_bot_recv_remote_cmd',
                'cmd': msg['cmd'],
                'args': msg['cmd_args'],
                'msg': msg,
            })

        cmds = [
            ('say', 'Make Speaker announcement', _bcast_telegram_cmd),
            ('snap', 'Share doorbell snapshot', _bcast_telegram_cmd),
            ('stfu_door_motion', 'Pause door motion notifications for the next half hour', _bcast_telegram_cmd),
            ('stfu', 'Pause a notification type for the next N minutes (eg: /stfu on_main_door_open 90)', _bcast_telegram_cmd),
        ]
        super().__init__(tok, poll_interval_secs=poll_interval_secs, bot_name='BatiCasa Bot', bot_descr='BatiCasa control over Telegram', cmds=cmds)

    def on_bot_connected(self, bot):
        log.info('Connected to Telegram bot %s', bot.bot_info['first_name'])

    def on_bot_received_message(self, msg):
        log.info('Telegram bot %s received a message: %s', bot.bot_info['first_name'], msg)


class NotificationDispatcher:
    def __init__(self, cfg, zmw, sonos, doorbell):
        self._mqtt = MqttProxy(cfg, cfg['mqtt_topic_zmw'])
        self._mqtt.on_message = self._on_message
        self._mqtt.start()

        self._sonos = sonos
        self._doorbell = doorbell
        self._files_cache = cfg['telegram']['files_cache']

        self._paused_notifications = set()
        self._pausable_notifications = set({'door_motion', 'window_open', 'door_open'})
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

        self.telegram = None
        if 'telegram' in cfg:
            self._baticasa_chat_id = cfg['telegram']['bcast_chat_id']
            self.telegram = BatiCasaTelegramBot(zmw, cfg['telegram']['tok'], cfg['telegram']['poll_secs'])
        self.wa = None
        if 'whatsapp' in cfg:
            self.wa = WhatsApp(cfg['whatsapp'], test_mode=False)

    def _should_skip_push_notify(self):
        current_time = datetime.now().time()
        start_time = time(22, 0)  # 10 pm
        end_time = time(6, 0)     # 6 am
        if start_time <= current_time or current_time <= end_time:
            return True
        return False

    def _on_message(self, _topic, msg):
        if 'event' not in msg:
            return

        # Doorbell events
        if msg['event'] == 'on_doorbell_button_pressed':
            self._sonos.play_announcement('http://192.168.1.20/web_assets/knockknock.mp3')
        elif msg['event'] == 'on_doorbell_cam_motion_detected':
            if 'door_motion' in self._paused_notifications:
                log.info('door_motion event triggered, but notifications are paused')
                return
            if self.telegram is not None:
                self.telegram.send_photo(
                        self._baticasa_chat_id, msg['snap'], "Motion detected!",
                        disable_notifications=self._should_skip_push_notify())
            if self.wa is not None:
                self.wa.send_photo(msg['snap'], "Motion detected!")
        elif msg['event'] == 'on_doorbell_cam_motion_cleared':
            pass
        elif msg['event'] == 'on_doorbell_cam_motion_timeout':
            pass

        # Contact sensor events
        elif msg['event'] == 'on_main_door_open' and msg['thing_name'] == 'SensorPuertaEntrada':
            log.info('door_open event triggered')
            if msg['user_requested_mute_announcement'] or 'door_open' in self._paused_notifications:
                log.info('door_open event triggered, but notifications are paused')
                return
            self._sonos.play_announcement('http://bati.casa/web_assets/win95.mp3')
        elif msg['event'] == 'on_main_door_open' and msg['thing_name'] == 'SensorVentanaBanio':
            if 'window_open' in self._paused_notifications:
                log.info('window_open event triggered, but notifications are paused')
                return
            self._sonos.tts_announce('es', 'Ventana abierta')
            if self.telegram is not None:
                self.telegram.send_message(self._baticasa_chat_id, f'Event triggered: Ventana frente abierta')
        elif msg['event'] == 'on_main_door_closed':
            pass

        # Telegram message handling
        elif msg['event'] == 'on_telegram_bot_recv_remote_cmd':
            self._on_telegram_cmd(msg)

    def _on_telegram_cmd(self, msg):
        log.info('Received Telegram command %s: %s', msg['cmd'], msg)
        if msg['cmd'] == 'say':
            tts = ' '.join(msg['args'])
            self._sonos.tts_announce('es', tts)
            self.telegram.send_message(self._baticasa_chat_id, f"OK {msg['msg']['from']['first_name']}, announcing '{tts}'")
        elif msg['cmd'] == 'snap':
            fpath = os.path.join(pathlib.Path(self._files_cache).resolve(), f'doorbell.jpg')
            self._doorbell.get_snapshot(fpath)
            self.telegram.send_photo(self._baticasa_chat_id, fpath, f"Ok {msg['msg']['from']['first_name']}, here's a snap of the door cam",
                                     disable_notifications=self._should_skip_push_notify())
        elif msg['cmd'] == 'stfu_door_motion':
            self.pause_notification('door_motion', 30 * 60)
        elif msg['cmd'] == 'stfu':
            if len(msg['args']) != 2 or not msg['args'][1].isdigit():
                self.telegram.send_message(msg['msg']['chat']['id'], f"Invalid command args {msg['cmd']} {msg['args']}")
                return
            if msg['args'][0] not in self._pausable_notifications:
                self.telegram.send_message(msg['msg']['chat']['id'], f"Invalid event {msg['args'][0]} ({self._pausable_notifications})")
                return
            self.pause_notification(msg['args'][0], int(msg['args'][1]) * 60)


    def pause_notification(self, event, timeout_secs):
        log.info("Notifications for %s paused for %s seconds", event, timeout_secs)
        timeout_secs = int(timeout_secs)
        def reenable_notifs():
            self._paused_notifications.remove(event)
            log.info("Notifications for %s unpaused", event)
            self.telegram.send_message(self._baticasa_chat_id, f"Notifications for {event} are now unpaused")
        self.telegram.send_message(self._baticasa_chat_id, f"Notifications for {event} are paused for {timeout_secs/60} minutes")
        self._paused_notifications.add(event)
        self._scheduler.add_job(
            func=reenable_notifs,
            trigger="date",
            run_date=(datetime.datetime.now() + datetime.timedelta(seconds=timeout_secs)))

