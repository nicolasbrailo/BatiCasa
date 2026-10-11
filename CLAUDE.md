# baticasa

My home automation. Three layers, each its own repo (the two below are git submodules):

- `baticasa/`: house-specific logic ("if buttonX is pressed, turn on lightY", scenes, schedules). A ZMW-style
  service (`baticasa.py`, subclasses `zzmw_lib`'s `ButtonActionService`).
- `zigbee2mqtt2web/` (ZMW): generic(ish) reusable services, e.g. `zmw_lights`. See its `CLAUDE.md`.
- `matter2mqtt/`: jailed Matter/Thread -> MQTT bridge. See its `CLAUDE.md`.

Devices come from zigbee2mqtt (Zigbee) and matter2mqtt (Matter). Both speak the same MQTT dialect, so ZMW
services and baticasa don't care which network a device lives on. House-specific code belongs in `baticasa/`,
not in ZMW.

## Environment

- This dir is an sshfs mount of the runtime host `bati.casa` (`/home/batman/src/BatiCasa`). If files vanish,
  the mount dropped: ask the user to remount; don't recreate anything.
- The dev machine has no runtime deps: don't run tests, UI builds or import checks here.
- Services run on bati.casa (`make devrun`, `make install_svc`, managed via systemd).
