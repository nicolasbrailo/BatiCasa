import reolinkapi
class Cam:
    def __init__(self, cfg):
        self._ip = cfg['ip']
        self._user = cfg['user']
        self._pass = cfg['pass']
        self.cam = reolinkapi.Camera(self._ip, self._user, self._pass)
        self.name = self.cam.get_information()[0]['value']['DevInfo']['name']
CFG = {
        'ip': '192.168.1.30',
        'user': 'admin',
        'pass': 'qwepoi',
        }
cam = Cam(CFG)
print(cam)
exit(0)


import sys
sys.path.append("./zigbee2mqtt2web")

import logging
import os
import json
import sys
import time
import datetime

from zigbee2mqtt2web_extras.utils.whatsapp import WhatsApp
from zigbee2mqtt2web_extras.security_cam import SecurityCam
from zigbee2mqtt2web_extras.utils.ftpd import Ftpd

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
#print(wa.text('HOLA'))
#imgid = wa.upload_image('/home/pi/n.jpg')
#print(imgid)
#print(wa.send_image(imgid))
#print(wa.message_from_params_template(imgid))
#print(wa.message_from_template('hello_world'))

#ftpd = Ftpd(CFG['security_cam']['ftp'])
#print("START")
#ftpd.start()
#print("SLEEP")
#time.sleep(30)
#print("STOP")
#ftpd.stop()

cam_manager = SecurityCam(CFG['security_cam'], wa)
cam_manager.start()

while True:
    time.sleep(1)
