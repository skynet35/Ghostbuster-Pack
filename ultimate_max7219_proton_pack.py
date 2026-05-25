import machine
import time
import math
import uasyncio as asyncio
from machine import Pin, I2S, SPI
import neopixel

# Importer tous les modules
from audio_system import ProtonPackAudio, SoundManager
from cyclotron_4x21 import CyclotronManager
from wand_bargraph_max7219 import ProtonWandBargraph, ProtonWandEffects
from wand_effects_bargraph import ProtonWandBargraphEffects
from control_system import ProtonPackControls
from power_management import PowerManagementSystem

class UltimateProtonPackWithMAX7219:
    """Proton Pack ultime avec cyclotron 4x21 LEDs et bargraph MAX7219"""
    
    def __init__(self):
        print("=" * 70)
        print("🚫👻 PROTON PACK ULTIMATE - 4x21 CYCLOTRON + MAX7219 BARGRAPH")
        print("Configuration: 84 LEDs Cyclotron + 28 Segments Bargraph BL28-3005S")
        print("=" * 70)
        
        # Configuration matérielle
        self.setup_hardware()
        
        # Initialiser les systèmes
        self.setup_audio()
        self.setup_cyclotron()
        self.setup_wand_bargraph()
        self.setup_controls()
        self.setup_power_management()
        
        # État global
        self.system_state = {
            'power': False,
            'power_level': 0,
            'cyclotron_rpm': 0,
            'proton_stream': False,
            'stream_intensity': 0.5,
            'overheating': False,
            'venting': False,
            'emergency_mode': False,
            'test_mode': False,
            'calibration_mode': False,
            'wand_active': False,
            'barrel_extended': False,
            'total_leds': 84,
            'bargraph_segments': 28,
            'power_consumption': 0.0
        }
        
        # Timers et performance
        self.last_update = time.ticks_ms()
        self.startup_time = 0
        self.frame_count = 0
        self.last_fps_time = time.ticks_ms()
        
        print("[SYSTEM] Initialisation terminée!")
        print(f"[SYSTEM] Configuration: {self.system_state['total_leds']} LEDs + {self.system_state['bargraph_segments']} segments")
        
    def setup_hardware(self):
        """Configuration matérielle complète"""
        print("[HARDWARE] Configuration du matériel...")
        
        # Configuration des pins optimisée
        self.pin_config = {
            # Cyclotron 4x21 LEDs (84 LEDs total)
            'cyclotron_data': 0,      # GPIO 0 pour les 84 LEDs en série
            
            # Cellule de puissance
            'power_cell': 1,          # 15 LEDs
            
            # MAX7219 Bargraph (BL28-3005S)
            'max7219_spi_sck': 2,     # SPI Clock
            'max7219_spi_mosi': 3,    # SPI MOSI
            'max7219_spi_miso': 4,    # SPI MISO (optionnel)
            'max7219_cs': 5,          # Chip Select
            
            # Audio (MAX98357A)
            'audio_bclk': 6,
            'audio_lrc': 7,
            'audio_din': 8,
            
            # Contrôles
            'main_power': 9,            # Interrupteur principal
            'wand_trigger': 10,         # Gâchette
            'wand_switch': 11,          # Interrupteur baguette
            'venting_button': 12,       # Bouton ventilation
            'mode_switch': 13,          # Sélecteur de mode
            'emergency_stop': 15,       # Arrêt d'urgence
            'test_button': 16,          # Bouton test
            'calibration_button': 17,    # Bouton calibration
            'barrel_extend': 18,        # Déploiement canon
            'barrel_retract': 19,       # Rétraction canon
        }
        
        # Initialiser les LEDs
        self.leds = {}
        self.leds['cyclotron'] = neopixel.NeoPixel(Pin(self.pin_config['cyclotron_data']), 84)
        self.leds['power_cell'] = neopixel.NeoPixel(Pin(self.pin_config['power_cell']), 15)
        
        # Initialiser SPI pour MAX7219
        self.spi = SPI(0, baudrate=10000000, polarity=0, phase=0,
                      sck=Pin(self.pin_config['max7219_spi_sck']),
                      mosi=Pin(self.pin_config['max7219_spi_mosi']))
        
        print("[HARDWARE] Configuration matérielle terminée!")
        
    def setup_audio(self):
        """Configuration du système audio"""
        print("[AUDIO] Configuration audio...")
        
        # Initialiser I2S pour le MAX98357A
        self.i2s = I2S(
            0,
            sck=Pin(self.pin_config['audio_bclk']),
            ws=Pin(self.pin_config['audio_lrc']),
            sd=Pin(self.pin_config['audio_din']),
            mode=I2S.TX,
            bits=16,
            format=I2S.STEREO,
            rate=44100,
            ibuf=20000
        )
        
        self.audio_system = ProtonPackAudio(self.i2s)
        self.sound_manager = SoundManager(self.audio_system)
        
        print("[AUDIO] Système audio configuré!")
        
    def setup_cyclotron(self):
        """Configuration du cyclotron 4x21"""
        print("[CYCLOTRON] Configuration cyclotron 4x21...")
        
        self.cyclotron = CyclotronManager(self.pin_config['cyclotron_data'])
        
        print("[CYCLOTRON] Cyclotron 4x21 configuré!")
        
    def setup_wand_bargraph(self):
        """Configuration du bargraph MAX7219"""
        print("[BARGRAPH] Configuration MAX7219 bargraph...")
        
        # Créer le système de bargraph
        self.wand_bargraph = ProtonWandBargraph(
            self.spi,
            self.pin_config['max7219_cs']
        )
        
        # Créer les effets pour le bargraph
        self.wand_effects = ProtonWandBargraphEffects(self.wand_bargraph)
        
        print("[BARGRAPH] Bargraph BL28-3005S configuré!")
        
    def setup_controls(self):
        """Configuration des contrôles"""
        print("[CONTROLS] Configuration contrôles...")
        
        self.controls = ProtonPackControls()
        
        # Connecter les callbacks
        self.controls.controls['main_power'].add_callback('on', self.on_power_on)
        self.controls.controls['main_power'].add_callback('off', self.on_power_off)
        self.controls.controls['wand_trigger'].add_callback('press', self.on_wand_trigger_press)
        self.controls.controls['wand_trigger'].add_callback('release', self.on_wand_trigger_release)
        self.controls.controls['venting_button'].add_callback('press', self.on_venting_start)
        self.controls.controls['venting_button'].add_callback('release', self.on_venting_stop)
        self.controls.controls['emergency_stop'].add_callback('press', self.on_emergency_stop)
        
        print("[CONTROLS] Contrôles configurés!")
        
    def setup_power_management(self):
        """Configuration de la gestion de puissance"""
        print("[POWER] Configuration gestion de puissance...")
        
        self.power_manager = PowerManagementSystem()
        
        print("[POWER] Gestion de puissance configurée!")
        
    # Méthodes de callback
    def on_power_on(self, control_name):
        """Mise sous tension"""
        print(f"[EVENT] Power ON - Control: {control_name}")
        self.system_state['power'] = True
        self.startup_time = time.ticks_ms()
        
        # Démarrer les séquences
        asyncio.create_task(self.power_on_sequence())
        
    def on_power_off(self, control_name):
        """Mise hors tension"""
        print(f"[EVENT] Power OFF - Control: {control_name}")
        self.system_state['power'] = False
        self.system_state['wand_active'] = False
        self.system_state['proton_stream'] = False
        
        # Arrêter les séquences
        asyncio.create_task(self.power_off_sequence())
        
    def on_wand_trigger_press(self, control_name):
        """Pression sur la gâchette"""
        if self.system_state['power'] and not self.system_state['emergency_mode']:
            print(f"[EVENT] Wand trigger PRESSED - Control: {control_name}")
            self.system_state['wand_active'] = True
            self.system_state['proton_stream'] = True
            self.system_state['stream_intensity'] = 1.0
            
            # Jouer le son et activer les effets
            asyncio.create_task(self.activate_proton_stream())
            
    def on_wand_trigger_release(self, control_name):
        """Relâchement de la gâchette"""
        print(f"[EVENT] Wand trigger RELEASED - Control: {control_name}")
        self.system_state['wand_active'] = False
        self.system_state['proton_stream'] = False
        
        # Arrêter le flux proton
        asyncio.create_task(self.deactivate_proton_stream())
        
    def on_venting_start(self, control_name):
        """Démarrage de la ventilation"""
        if self.system_state['power']:
            print(f"[EVENT] Venting START - Control: {control_name}")
            self.system_state['venting'] = True
            asyncio.create_task(self.start_venting_sequence())
            
    def on_venting_stop(self, control_name):
        """Arrêt de la ventilation"""
        print(f"[EVENT] Venting STOP - Control: {control_name}")
        self.system_state['venting'] = False
        
    def on_emergency_stop(self, control_name):
        """Arrêt d'urgence"""
        print(f"[EVENT] EMERGENCY STOP - Control: {control_name}")
        self.system_state['emergency_mode'] = True
        self.system_state['wand_active'] = False
        self.system_state['proton_stream'] = False
        
        asyncio.create_task(self.emergency_stop_sequence())
        
    # Séquences d'animation avancées
    async def power_on_sequence(self):
        """Séquence de mise sous tension"""
        print("[SEQUENCE] Power ON sequence...")
        
        # Jouer le son de démarrage
        await self.sound_manager.play_sound('startup', priority=10)
        
        # Animation de la cellule de puissance
        for level in range(1, 101, 5):
            self.system_state['power_level'] = level / 100.0
            
            # Mettre à jour la cellule de puissance
            colors = self._generate_power_cell_colors(level)
            for i, color in enumerate(colors):
                if i < self.leds['power_cell'].n:
                    self.leds['power_cell'][i] = color
            self.leds['power_cell'].write()
            
            await asyncio.sleep(0.1)
        
        # Démarrer le cyclotron
        self.cyclotron.start()
        
        # Animation du bargraph
        await self.wand_effects.async_effect('charging', duration=2000)
        
        print("[SEQUENCE] Power ON sequence complete!")
        
    async def power_off_sequence(self):
        """Séquence de mise hors tension"""
        print("[SEQUENCE] Power OFF sequence...")
        
        # Animation du bargraph
        await self.wand_effects.async_effect('shutdown', duration=1500)
        
        # Réduire progressivement le niveau de puissance
        current_level = int(self.system_state['power_level'] * 100)
        for level in range(current_level, -1, -5):
            self.system_state['power_level'] = level / 100.0
            
            # Mettre à jour la cellule de puissance
            colors = self._generate_power_cell_colors(level)
            for i, color in enumerate(colors):
                if i < self.leds['power_cell'].n:
                    self.leds['power_cell'][i] = color
            self.leds['power_cell'].write()
            
            await asyncio.sleep(0.1)
        
        # Arrêter le cyclotron
        self.cyclotron.stop()
        
        # Jouer le son d'arrêt
        await self.sound_manager.play_sound('shutdown', priority=10)
        
        print("[SEQUENCE] Power OFF sequence complete!")
        
    async def activate_proton_stream(self):
        """Activation du flux proton"""
        print("[STREAM] Activating proton stream...")
        
        # Jouer le son du flux
        await self.sound_manager.play_sound('proton_stream_start', priority=8)
        
        # Animation du bargraph
        await self.wand_effects.async_effect('firing', duration=2000)
        
        # Activer le cyclotron en mode tir
        self.cyclotron.set_power_level(90)
        
        # Maintenir le flux avec son en boucle
        await self.sound_manager.play_sound('proton_stream', priority=7, loop=True)
        
    async def deactivate_proton_stream(self):
        """Désactivation du flux proton"""
        print("[STREAM] Deactivating proton stream...")
        
        # Arrêter le son en boucle
        self.sound_manager.stop_sound('proton_stream')
        
        # Animation du bargraph
        self.wand_bargraph.set_power_level(int(self.system_state['power_level'] * 100))
        
        # Jouer le son d'arrêt
        await self.sound_manager.play_sound('proton_stream_stop', priority=8)
        
    async def start_venting_sequence(self):
        """Séquence de ventilation"""
        print("[VENTING] Starting venting sequence...")
        
        # Jouer le son de ventilation
        await self.sound_manager.play_sound('venting', priority=9)
        
        # Animation du bargraph
        await self.wand_effects.async_effect('overload', duration=3000)
        
        # Activer l'effet de surchauffe
        self.system_state['overheating'] = True
        
        # Attendre la fin de la ventilation
        await asyncio.sleep(5)
        
        # Désactiver la surchauffe
        self.system_state['overheating'] = False
        
        print("[VENTING] Venting sequence complete!")
        
    async def emergency_stop_sequence(self):
        """Séquence d'arrêt d'urgence"""
        print("[EMERGENCY] Emergency stop sequence...")
        
        # Arrêter tous les sons
        self.sound_manager.stop_all_sounds()
        
        # Jouer l'alarme d'urgence
        await self.sound_manager.play_sound('overheat', priority=10)
        
        # Animation d'urgence sur le bargraph
        await self.wand_effects.async_effect('error', duration=3000, error_code=2)
        
        # Animation d'urgence sur le cyclotron
        for _ in range(10):
            # Éteindre toutes les LEDs
            self.leds['cyclotron'].fill((0, 0, 0))
            self.leds['cyclotron'].write()
            self.leds['power_cell'].fill((0, 0, 0))
            self.leds['power_cell'].write()
            await asyncio.sleep(0.2)
            
            # Allumer en rouge
            self.leds['cyclotron'].fill((255, 0, 0))
            self.leds['cyclotron'].write()
            self.leds['power_cell'].fill((255, 0, 0))
            self.leds['power_cell'].write()
            await asyncio.sleep(0.2)
        
        # Éteindre complètement
        self.leds['cyclotron'].fill((0, 0, 0))
        self.leds['cyclotron'].write()
        self.leds['power_cell'].fill((0, 0, 0))
        self.leds['power_cell'].write()
        
        print("[EMERGENCY] Emergency stop complete!")
        
    # Méthodes utilitaires
    def _generate_power_cell_colors(self, level):
        """Générer les couleurs pour la cellule de puissance"""
        colors = []
        total_segments = 15
        active_segments = int((level / 100) * total_segments)
        
        for i in range(total_segments):
            if i < active_segments:
                # Couleur selon la position
                if i < total_segments * 0.3:
                    color = (255, 0, 0)        # Rouge
                elif i < total_segments * 0.7:
                    color = (255, 255, 0)    # Jaune
                else:
                    color = (0, 255, 0)      # Vert
                
                # Effet de pulsation pour le dernier segment
                if i == active_segments - 1:
                    brightness = 0.7 + 0.3 * abs(math.sin(time.ticks_ms() * 0.005))
                    color = tuple(int(c * brightness) for c in color)
                
                colors.append(color)
            else:
                colors.append((0, 0, 0))
        
        return colors
    
    def calculate_power_consumption(self):
        """Calculer la consommation électrique"""
        # Estimation basée sur les LEDs actives
        active_cyclotron = 0
        active_power_cell = 0
        active_bargraph = self.wand_bargraph.get_status()['active_segments']
        
        # Compter les LEDs du cyclotron
        for i in range(84):
            if self.leds['cyclotron'][i] != (0, 0, 0):
                active_cyclotron += 1
        
        # Compter les LEDs de la cellule de puissance
        for i in range(15):
            if self.leds['power_cell'][i] != (0, 0, 0):
                active_power_cell += 1
        
        # Estimation: ~60mA par LED WS2812, ~20mA par segment MAX7219
        cyclotron_current = active_cyclotron * 0.060
        power_cell_current = active_power_cell * 0.060
        bargraph_current = active_bargraph * 0.020
        
        total_current = cyclotron_current + power_cell_current + bargraph_current
        self.system_state['power_consumption'] = total_current
        
        return total_current
    
    # Boucle principale
    async def main_loop(self):
        """Boucle principale du système"""
        print("[SYSTEM] Starting main loop...")
        
        while True:
            current_time = time.ticks_ms()
            
            # Mettre a jour les controles (non bloquant)
            self.controls.update_once()
            
            # Si le système est allumé
            if self.system_state['power']:
                # Mettre à jour le cyclotron
                self.cyclotron.update()
                
                # Mettre à jour la cellule de puissance
                colors = self._generate_power_cell_colors(int(self.system_state['power_level'] * 100))
                for i, color in enumerate(colors):
                    if i < self.leds['power_cell'].n:
                        self.leds['power_cell'][i] = color
                self.leds['power_cell'].write()
                
                # Mettre à jour le bargraph selon l'état
                if self.system_state['proton_stream']:
                    self.wand_bargraph.set_power_level(100)
                    self.wand_effects.proton_fire_effect(intensity=1.0, duration=100)
                elif self.system_state['overheating']:
                    self.wand_effects.overheat_effect(severity=1.0)
                else:
                    power_level = int(self.system_state['power_level'] * 100)
                    self.wand_bargraph.set_power_level(power_level)
                    if not self.wand_effects.get_current_effect():
                        self.wand_effects.breathing_effect(speed=1.5, base_level=power_level)
                
                # Calculer la consommation de puissance
                self.calculate_power_consumption()
                
                # Calculer les FPS
                fps = self.calculate_fps()
                if fps:
                    self.system_state['fps'] = fps
                
                # Ajuster la vitesse du cyclotron selon l'activité
                if self.system_state['proton_stream']:
                    self.cyclotron.set_power_level(90)
                elif self.system_state['overheating']:
                    self.cyclotron.set_power_level(100)
                else:
                    power_level = int(self.system_state['power_level'] * 100)
                    self.cyclotron.set_power_level(power_level)
            
            # Petite pause pour ne pas surcharger
            await asyncio.sleep(0.01)  # 10ms = 100 FPS théorique
            
    # Méthodes utilitaires
    def calculate_fps(self):
        """Calculer les FPS réels"""
        self.frame_count += 1
        current_time = time.ticks_ms()
        
        if current_time - self.last_fps_time >= 1000:  # 1 seconde
            fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = current_time
            
            if fps < 25:  # Avertissement si < 25 FPS
                print(f"[PERFORMANCE] FPS faible: {fps}")
            
            return fps
        
        return None
    
    def get_status(self):
        """Obtenir l'état complet du système"""
        return {
            'system_state': self.system_state.copy(),
            'controls': self.controls.get_system_status(),
            'cyclotron': self.cyclotron.get_status(),
            'bargraph': self.wand_bargraph.get_status(),
            'power_consumption': self.system_state['power_consumption'],
            'performance': {
                'fps': getattr(self.system_state, 'fps', 0),
                'total_leds': self.system_state['total_leds'],
                'bargraph_segments': self.system_state['bargraph_segments']
            }
        }
    
    def reset_emergency(self):
        """Réinitialiser le mode d'urgence"""
        self.system_state['emergency_mode'] = False
        self.controls.reset_emergency()
        print("[SYSTEM] Emergency mode reset")

# Programme principal
async def main():
    """Fonction principale"""
    print("=" * 70)
    print("PROTON PACK ULTIMATE - 4x21 CYCLOTRON + MAX7219 BARGRAPH")
    print("Version 4.0 - Système complet avec baguette professionnelle")
    print("=" * 70)
    
    # Créer l'instance du proton pack
    proton_pack = UltimateProtonPackWithMAX7219()
    
    # Démarrer la boucle principale
    try:
        await proton_pack.main_loop()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n[ERROR] Erreur système: {e}")
    finally:
        print("[SYSTEM] Arrêt du système...")
        # Nettoyer et éteindre
        for strip in proton_pack.leds.values():
            strip.fill((0, 0, 0))
            strip.write()
        proton_pack.wand_bargraph.clear_all()
        proton_pack.sound_manager.stop_all_sounds()
        print("[SYSTEM] Système arrêté")

if __name__ == "__main__":
    asyncio.run(main())
