#!/usr/bin/bash
set -euo pipefail

SRC_ROOT=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
RUN_PATH="/home/$USER/BatiCasa"

"$SRC_ROOT/zigbee2mqtt2web/scripts/install_dep_svcs.sh" BatiCasa

if [ ! -f "$SRC_ROOT/Pipfile" ]; then
  if [[ $(arch) -eq "x86_64" ]]; then
    echo "Automatically selecting x86 Pipfile"
    cp "$SRC_ROOT/Pipfile.x86" "$SRC_ROOT/Pipfile"
  else
    echo -e "\033[0;31m"
    echo "Can't find Pipfile, make sure you select between Pipfile.x86 or Pipfile.arm"
    echo -e "\033[0m"
    exit 1
  fi
fi

echo "systemctl status BatiCasa.service zigbee2mqtt.service mosquitto.service" > "$RUN_PATH/status.sh"
echo "sudo journalctl --follow --unit BatiCasa --unit zigbee2mqtt" > "$RUN_PATH/tail_logs.sh"
echo "sudo systemctl restart BatiCasa.service" > "$RUN_PATH/BatiCasa_restart.sh"
chmod +x "$RUN_PATH/status.sh"
chmod +x "$RUN_PATH/tail_logs.sh"
chmod +x "$RUN_PATH/BatiCasa_restart.sh"

# authbind -> run in port 80 with no root
sudo touch /etc/authbind/byport/80
sudo chmod 777 /etc/authbind/byport/80
sudo touch /etc/authbind/byport/443
sudo chmod 777 /etc/authbind/byport/443

cat "$SRC_ROOT/BatiCasa.service.template" | \
  sed "s|#SRC_ROOT#|$SRC_ROOT|g" | \
  sed "s|#RUN_PATH#|$RUN_PATH|g" | \
  sed "s|#RUN_USER#|$(whoami)|g" | \
  sudo tee >/dev/null /etc/systemd/system/BatiCasa.service

cp "$SRC_ROOT/config.test.json" "$RUN_PATH/BatiCasa.config.json"

pushd "$RUN_PATH"
PIPENV_PIPFILE="$SRC_ROOT/Pipfile" python3 -m pipenv --python $(which python3) install
popd

sudo systemctl stop BatiCasa | true
sudo systemctl daemon-reload
sudo systemctl enable BatiCasa
sudo systemctl start BatiCasa
sudo systemctl status BatiCasa

