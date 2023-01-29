import sys
sys.path.append("./zigbee2mqtt2web")

import logging
import json
import sys
import time
import datetime

from zigbee2mqtt2web_extras.utils.whatsapp import WhatsApp
from zigbee2mqtt2web_extras.security_cam import SecurityCam

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler)

with open('config.json', 'r') as fp:
    CFG = json.loads(fp.read())

wa = WhatsApp(CFG['whatsapp'])
print(wa.text('HOLA'))
imgid = wa.upload_image('/home/pi/n.jpg')
print(imgid)
print(wa.send_image(imgid))
print(wa.message_from_params_template(imgid))
print(wa.message_from_template('hello_world'))
#ftp = SecurityCam(CFG['security_cam'], wa)
#ftp.blocking_run()
