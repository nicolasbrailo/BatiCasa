import sys
import os
import pathlib
sys.path.append(os.path.join(pathlib.Path(__file__).parent.resolve(), "zigbee2mqtt2web"))

from zigbee2mqtt2web_extras.utils.telegram import TelegramLongpollBot

import logging
log = logging.getLogger(__name__)

class BatiCasaTelegramBot(TelegramLongpollBot):
    def __init__(self, tok, poll_interval_secs, baticasa_chat_id, files_cache, sonos, doorbell):
        self._sonos = sonos
        self._doorbell = doorbell
        self._baticasa_chat_id = baticasa_chat_id
        self._files_cache = files_cache
        super().__init__(tok, poll_interval_secs=poll_interval_secs, cmds=[
            ('hola', 'Say hello', self._say_hi),
            ('announce', 'Make announcement', self._say_something),
            ('snap', 'Share doorbell snapshot', self._send_snap)
        ])

    def on_bot_connected(self, bot):
        log.info('Connected to Telegram bot %s', bot.bot_info['first_name'])
        bot.set_bot_name('BatiCasa Bot')
        bot.set_bot_description('BatiCasa control over Telegram')

    def on_bot_received_message(self, msg):
        log.info('Telegram bot %s received a message: %s', bot.bot_info['first_name'], msg)

    def _say_hi(self, bot, msg):
        log.info('Telegram bot %s saying hello', bot.bot_info['first_name'])
        if self._sonos is None:
            bot.send_message(self._baticasa_chat_id,
                             f"Sorry {msg['from']['first_name']}, no announcements configured")
            return

        bot.send_message(self._baticasa_chat_id,
                         f"Ok {msg['from']['first_name']}, I'll send announcement: hola mundo")
        self._sonos.tts_announce('es', 'Hola mundo')

    def _say_something(self, bot, msg):
        announce = ' '.join(msg['cmd_args'])
        log.info('Telegram bot %s requesting announcement %s', bot.bot_info['first_name'], announce)
        if self._sonos is None:
            bot.send_message(self._baticasa_chat_id,
                             f"Sorry {msg['from']['first_name']}, no announcements configured")
            return
        bot.send_message(self._baticasa_chat_id,
                         f"Ok {msg['from']['first_name']}, I'll send announcement: {announce}")
        self._sonos.tts_announce('es', announce)

    def _send_snap(self, bot, msg):
        log.info('Telegram bot %s requesting doorbell snap', bot.bot_info['first_name'])
        if self._doorbell is None:
            bot.send_message(self._baticasa_chat_id,
                             f"Sorry {msg['from']['first_name']}, no doorbell cam configured")
            return
        fpath = os.path.join(pathlib.Path(self._files_cache).resolve(), f'doorbell.jpg')
        self._doorbell.get_snapshot(fpath)
        log.info('Telegram bot %s saved doorbell snap to %s', bot.bot_info['first_name'], fpath)
        bot.send_photo(self._baticasa_chat_id,
                       fpath,
                       f"Ok {msg['from']['first_name']}, here's a snap of the door cam")

