import os
from datetime import datetime
from flask import send_from_directory

def _format_file_size(sz):
    if sz < 1024:
        return f"{sz} bytes"
    elif sz < 1024 * 1024:
        return f"{sz / 1024:.2f} KB"
    else:
        return f"{sz / (1024 * 1024):.2f} MB"

def _get_month_name(month_number):
    month_names = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]
    # Adjust month_number to match the index of month_names
    index = month_number - 1
    return month_names[index] if 1 <= month_number <= 12 else f"Month {month_number}?"


def _parse_and_format_filename(filename):
    try:
        datetime_str = filename.split('.')[0]
        date = datetime_str.split('_')[0]
        hour = datetime_str.split('_')[1]
        month = int(datetime_str[4:6])
        day = int(datetime_str[6:8])
        hr = int(hour[0:2])
        minute = int(hour[2:4])
        return f'{_get_month_name(month)} - {day:02} - {hr:02}:{minute:02}'
    except:
        return filename


class Nvr:
    def __init__(self, nvr_path, webserver):
        self._nvr_path = nvr_path
        self._cams = []
        self._cam_files = {}

        webserver.add_url_rule('/nvr/ls', self._list_cams)
        webserver.add_url_rule('/nvr/<cam>/files', self._list_cam_recs)
        webserver.add_url_rule('/nvr/<cam>/get_recording/<file>', self._get_recording)

    def _list_cams(self):
        txt = ""
        for entry in os.listdir(self._nvr_path):
            full_path = os.path.join(self._nvr_path, entry)
            if os.path.isdir(full_path):
                cam = entry
                txt += f'<li><a href="/nvr/{cam}/files">{cam}</a></li>'
        return txt

    def _list_cam_recs(self, cam):
        path = os.path.join(self._nvr_path, cam)
        if not os.path.exists(path) or not os.path.isdir(path):
            return f"Unknown cam {cam}", 404

        recs = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                recs.append(filename)
        recs.sort(reverse=True)

        txt = ""
        for rec in recs:
            filepath = os.path.join(path, rec)
            file_size = os.path.getsize(filepath)
            txt += f'<li><a href="/nvr/{cam}/get_recording/{rec}">{_parse_and_format_filename(rec)} - {_format_file_size(file_size)}</a></li>'
        return txt

    def _get_recording(self, cam, file):
        path = os.path.join(self._nvr_path, cam)
        if not os.path.exists(path) or not os.path.isdir(path):
            return f"Can't get recording for unknown cam {cam}", 404

        fpath = os.path.join(path, file)
        if not os.path.exists(fpath) or not os.path.isfile(fpath):
            return f"Can't get unknown recording {file} for unknown cam {cam}", 404

        return send_from_directory(path, file)

