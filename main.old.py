MY_LATLON=(51.5464371,0.111148)

### class Cronenberg:
###     def __init__(self, registry):
###         self._managing_light = False
###         self._registry = registry
### 
###     def _tick(self):
###         local_hour = datetime.datetime.now().hour # no tz, just local hour
###         if not light_outside() and local_hour < 23 and local_hour > 12:
###             logger.info("Arbolito on")
###             self._registry.get_thing('IkeaOutlet').set('state', True)
###             self._managing_light = True
### 
###         elif self._managing_light and local_hour == 23:
###             logger.info("Arbolito off")
###             self._managing_light = False
###             self._registry.get_thing('IkeaOutlet').set('state', False)
### 
class App:
    def register_custom_behaviour(self, registry):
###         self.foo = MotionActivatedNightLight(registry, ['SensorEscaleraPB1', 'SensorEscaleraPB2'], 'EscaleraPBLight', MY_LATLON)
###         self.bar = MotionActivatedNightLight(registry, ['SensorEscaleraP1P2'], 'EscaleraP1', MY_LATLON)
###         self.bar.configure('off_during_late_night', True)
### 
### 
    def register_scenes(self):
        scenes = SceneManager(self.zmw.registry)
### 
###         def comedor_dia():
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'FFFFFF')
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(100)
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(100)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.broadcast_things(['Comedor', 'Snoopy'])
###         scenes.add_scene('Comedor dia', 'Luces altas, comedor', comedor_dia)
### 
###         def comedor_tarde():
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'FF8820')
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(60)
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(60)
###             self.zmw.registry.get_thing('EscaleraP1').set_brightness_pct(15)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.get_thing('EscaleraP1').set('transition', 3)
###             self.zmw.registry.broadcast_things(['Comedor', 'Snoopy', 'EscaleraP1'])
###         scenes.add_scene('Comedor tarde', 'Comedor, luces medias', comedor_tarde)
### 
###         def dormir():
###             self.zmw.registry.get_thing('Comedor').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Comedor').set('color_rgb', 'C20')
###             self.zmw.registry.get_thing('Snoopy').set_brightness_pct(5)
###             self.zmw.registry.get_thing('EscaleraP1').turn_off()
###             self.zmw.registry.get_thing('CocinaCountertop').turn_off()
###             self.zmw.registry.get_thing('CocinaCeiling').turn_off()
###             self.zmw.registry.get_thing('OficinaVelador').turn_off()
###             self.zmw.registry.get_thing('Oficina').turn_off()
###             self.zmw.registry.get_thing('ComedorII').turn_off()
###             self.zmw.registry.get_thing('NicoVelador').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Belador').set_brightness_pct(5)
###             self.zmw.registry.get_thing('Comedor').set('transition', 3)
###             self.zmw.registry.get_thing('Snoopy').set('transition', 3)
###             self.zmw.registry.get_thing('EscaleraP1').set('transition', 3)
###             self.zmw.registry.broadcast_things([
###                 'Comedor', 'Snoopy', 'EscaleraP1', 'CocinaCountertop', 'CocinaCeiling',
###                 'OficinaVelador', 'Oficina', 'ComedorII', 'NicoVelador', 'Belador'])
###         scenes.add_scene('Dormir', 'Luces bajas en toda la casa', dormir)
### 
###         self.zmw.registry.register(scenes)
### 
