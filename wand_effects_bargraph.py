import math
import time
import uasyncio as asyncio
import urandom

class ProtonWandBargraphEffects:
    """Effets visuels avancés pour bargraph BL28-3005S avec MAX7219"""
    
    def __init__(self, bargraph):
        self.bargraph = bargraph
        self.current_effect = None
        self.effect_params = {}
        self.animation_timer = 0
        
        # Palettes de couleurs simulées (intensité)
        self.color_palettes = {
            'proton_blue': {
                'low': 4,      # Faible intensité
                'medium': 8,   # Moyenne intensité
                'high': 12,    # Haute intensité
                'maximum': 15  # Maximum
            },
            'warning_orange': {
                'low': 6,
                'medium': 9,
                'high': 12,
                'maximum': 15
            },
            'danger_red': {
                'low': 8,
                'medium': 11,
                'high': 13,
                'maximum': 15
            },
            'white_hot': {
                'low': 10,
                'medium': 12,
                'high': 14,
                'maximum': 15
            }
        }
        
        # Configuration des effets
        self.effect_configs = {
            'idle_breath': {
                'speed': 2.0,           # Cycles par seconde
                'intensity_range': [4, 8],  # Intensité min/max
                'direction': 'up'       # Sens de la respiration
            },
            'charging_wave': {
                'speed': 3.0,
                'wave_width': 5,        # Largeur de l'onde en segments
                'trail_length': 3        # Longueur de la traînée
            },
            'firing_pulse': {
                'pulse_frequency': 8,   # Hz
                'pulse_intensity': 15,  # Maximum
                'sustain_time': 0.3     # Secondes
            },
            'overheat_flash': {
                'flash_rate': 10,       # Hz
                'flash_intensity': 15,  # Maximum
                'emergency_pattern': True
            },
            'error_strobe': {
                'strobe_rate': 15,      # Hz
                'pattern_type': 'alternating',  # Type de pattern
                'emergency_color': 'danger_red'
            }
        }
        
    # Effets de base
    def proton_charge_effect(self, charge_level, speed=1.0):
        """Effet de charge proton - montée progressive"""
        segments = int((charge_level / 100) * 28)  # 28 segments total
        
        # Effacer d'abord
        self.bargraph.display.clear()
        
        # Effet d'onde montante
        wave_position = int((time.ticks_ms() / (1000 / speed)) % (segments + 5))
        
        for i in range(segments):
            # Calculer la distance de l'onde
            distance_from_wave = abs(i - wave_position)
            
            if distance_from_wave < 3:
                # Intensité selon la position dans l'onde
                intensity = self.color_palettes['proton_blue']['maximum'] - (distance_from_wave * 3)
                intensity = max(self.color_palettes['proton_blue']['low'], intensity)
                
                self.bargraph.display.set_intensity(intensity)
                self.bargraph.display.set_segment(i, True)
            else:
                # Intensité de base pour les segments actifs
                base_intensity = self.color_palettes['proton_blue']['medium']
                self.bargraph.display.set_intensity(base_intensity)
                self.bargraph.display.set_segment(i, True)
                
    def proton_fire_effect(self, intensity=1.0, duration=2000):
        """Effet de tir proton - pulsation rapide"""
        start_time = time.ticks_ms()
        
        while time.ticks_ms() - start_time < duration:
            progress = (time.ticks_ms() - start_time) / duration
            
            # Effet de pulsation
            pulse_phase = (time.ticks_ms() / 100) % (2 * math.pi)
            pulse_intensity = 0.7 + 0.3 * math.sin(pulse_phase * 8)  # 8 Hz
            
            # Nombre de segments actifs selon l'intensité
            active_segments = int(intensity * 28 * pulse_intensity)
            active_segments = max(1, min(28, active_segments))
            
            # Effacer
            self.bargraph.display.clear()
            
            # Allumer les segments avec intensité variable
            self.bargraph.display.set_intensity(int(pulse_intensity * 15))
            
            for i in range(active_segments):
                self.bargraph.display.set_segment(i, True)
                
            time.sleep_ms(20)  # 50 FPS
            
    def warning_effect(self, severity=0.5):
        """Effet d'avertissement - orange clignotant"""
        flash_rate = 5  # 5 Hz
        flash_state = int((time.ticks_ms() / (1000 / flash_rate)) % 2)
        
        if flash_state:
            # Flash brillant
            self.bargraph.display.set_intensity(self.color_palettes['warning_orange']['maximum'])
            
            # Allumer les segments selon la gravité
            warning_segments = int(severity * 28)
            for i in range(warning_segments):
                self.bargraph.display.set_segment(i, True)
        else:
            # Flash plus faible
            self.bargraph.display.set_intensity(self.color_palettes['warning_orange']['low'])
            
            # Moitié des segments seulement
            dim_segments = int(severity * 14)
            for i in range(dim_segments):
                self.bargraph.display.set_segment(i, True)
                
    def overheat_effect(self, severity=1.0):
        """Effet de surchauffe - rouge d'urgence"""
        flash_rate = 10 + int(severity * 5)  # Plus rapide avec la gravité
        flash_state = int((time.ticks_ms() / (1000 / flash_rate)) % 2)
        
        self.bargraph.display.clear()
        
        if flash_state:
            # Flash rouge intense
            self.bargraph.display.set_intensity(self.color_palettes['danger_red']['maximum'])
            
            # Tous les segments en mode alarme
            for i in range(28):
                self.bargraph.display.set_segment(i, True)
        else:
            # Flash intermédiaire
            self.bargraph.display.set_intensity(self.color_palettes['danger_red']['medium'])
            
            # Pattern d'urgence (alternance rapide)
            for i in range(0, 28, 2):
                self.bargraph.display.set_segment(i, True)
                
    def error_strobe_effect(self, error_type=1):
        """Effet stroboscopique pour les erreurs"""
        strobe_rate = 15  # 15 Hz
        strobe_phase = int((time.ticks_ms() / (1000 / strobe_rate)) % 4)
        
        self.bargraph.display.clear()
        
        if error_type == 1:  # Erreur système
            # Pattern alterné rapide
            if strobe_phase % 2 == 0:
                # Segments pairs
                self.bargraph.display.set_intensity(self.color_palettes['danger_red']['high'])
                for i in range(0, 28, 2):
                    self.bargraph.display.set_segment(i, True)
            else:
                # Segments impairs
                self.bargraph.display.set_intensity(self.color_palettes['danger_red']['high'])
                for i in range(1, 28, 2):
                    self.bargraph.display.set_segment(i, True)
                    
        elif error_type == 2:  # Erreur critique
            # Pattern en V
            if strobe_phase < 2:
                # Moitié gauche
                self.bargraph.display.set_intensity(self.color_palettes['danger_red']['maximum'])
                for i in range(0, 14):
                    self.bargraph.display.set_segment(i, True)
            else:
                # Moitié droite
                self.bargraph.display.set_intensity(self.color_palettes['danger_red']['maximum'])
                for i in range(14, 28):
                    self.bargraph.display.set_segment(i, True)
                    
    # Effets avancés
    def wave_propagation_effect(self, speed=2.0, direction='up'):
        """Effet d'onde se propageant le long du bargraph"""
        wave_position = (time.ticks_ms() / (1000 / speed)) % (28 + 5)
        
        self.bargraph.display.clear()
        
        for i in range(28):
            # Calculer la distance de l'onde
            if direction == 'up':
                distance = abs(i - wave_position)
            else:  # down
                distance = abs((27 - i) - wave_position)
                
            if distance < 3:
                # Intensité selon la distance
                intensity = self.color_palettes['proton_blue']['maximum'] - (distance * 3)
                intensity = max(self.color_palettes['proton_blue']['low'], intensity)
                
                self.bargraph.display.set_intensity(intensity)
                self.bargraph.display.set_segment(i, True)
                
    def breathing_effect(self, speed=1.5, base_level=30):
        """Effet de respiration - montée/descente douce"""
        breath_phase = (time.ticks_ms() / (1000 / speed)) % (2 * math.pi)
        breath_intensity = 0.5 + 0.5 * math.sin(breath_phase)
        
        # Nombre de segments actifs
        active_segments = int(base_level + (breath_intensity * (100 - base_level)))
        active_segments = int((active_segments / 100) * 28)
        
        # Intensité variable
        current_intensity = self.color_palettes['proton_blue']['low'] + int(breath_intensity * 8)
        
        self.bargraph.display.clear()
        self.bargraph.display.set_intensity(current_intensity)
        
        for i in range(active_segments):
            self.bargraph.display.set_segment(i, True)
            
    def energy_pulse_effect(self, frequency=4, intensity_decay=0.95):
        """Effet d'impulsion d'énergie - pulsations rapides"""
        pulse_phase = (time.ticks_ms() / 1000) % (1 / frequency)
        pulse_intensity = math.sin(pulse_phase * 2 * math.pi * frequency)
        
        if pulse_intensity > 0:
            # Phase active de l'impulsion
            segments_to_light = int(pulse_intensity * 28)
            
            self.bargraph.display.clear()
            self.bargraph.display.set_intensity(int(pulse_intensity * 15))
            
            for i in range(segments_to_light):
                self.bargraph.display.set_segment(i, True)
        else:
            # Phase inactive - faible lueur
            self.bargraph.display.clear()
            self.bargraph.display.set_intensity(2)  # Très faible
            
            # Quelques segments de veille
            for i in range(0, 28, 7):
                self.bargraph.display.set_segment(i, True)
                
    def charging_sequence_effect(self, duration=3000):
        """Séquence complète de charge"""
        steps = int(duration / 50)  # 50ms par étape
        
        for step in range(steps):
            progress = step / steps
            
            # Effet de montée progressive
            current_level = int(progress * 28)
            
            # Effacer
            self.bargraph.display.clear()
            
            # Intensité croissante
            intensity = self.color_palettes['proton_blue']['low'] + int(progress * 8)
            self.bargraph.display.set_intensity(intensity)
            
            # Allumer progressivement
            for i in range(current_level):
                # Effet de vague interne
                wave_offset = int((step / 10) % 3)
                if (i + wave_offset) % 3 == 0:
                    # Accentuer certains segments
                    self.bargraph.display.set_intensity(min(15, intensity + 2))
                else:
                    self.bargraph.display.set_intensity(intensity)
                    
                self.bargraph.display.set_segment(i, True)
                
            time.sleep_ms(50)
            
        # Final - tous les segments à maximum
        self.bargraph.display.clear()
        self.bargraph.display.set_intensity(self.color_palettes['proton_blue']['maximum'])
        
        for i in range(28):
            self.bargraph.display.set_segment(i, True)
            
    def firing_sequence_effect(self, power_level=100, duration=2000):
        """Séquence complète de tir"""
        start_time = time.ticks_ms()
        original_level = self.bargraph.power_level
        
        while time.ticks_ms() - start_time < duration:
            progress = (time.ticks_ms() - start_time) / duration
            
            if progress < 0.3:
                # Phase de montée
                current_power = original_level + (power_level - original_level) * (progress / 0.3)
            elif progress < 0.7:
                # Phase de sustentation
                current_power = power_level
            else:
                # Phase de descente
                current_power = power_level - (power_level - original_level) * ((progress - 0.7) / 0.3)
                
            # Afficher le niveau actuel avec effet de pulsation
            active_segments = int((current_power / 100) * 28)
            
            # Pulsation rapide pendant le tir
            pulse = 0.8 + 0.2 * math.sin((time.ticks_ms() / 50) * 8)
            
            self.bargraph.display.clear()
            self.bargraph.display.set_intensity(int(pulse * 15))
            
            for i in range(active_segments):
                self.bargraph.display.set_segment(i, True)
                
            time.sleep_ms(20)  # 50 FPS
            
        # Retour au niveau original
        self.bargraph.set_power_level(original_level)
        
    def overload_sequence_effect(self, severity=1.0, duration=3000):
        """Séquence de surcharge/overload"""
        start_time = time.ticks_ms()
        
        while time.ticks_ms() - start_time < duration:
            progress = (time.ticks_ms() - start_time) / duration
            
            # Augmenter la fréquence de flash avec le temps
            current_flash_rate = 8 + int(progress * 10)
            
            flash_state = int((time.ticks_ms() / (1000 / current_flash_rate)) % 2)
            
            self.bargraph.display.clear()
            
            if flash_state:
                # Flash rouge intense
                self.bargraph.display.set_intensity(self.color_palettes['danger_red']['maximum'])
                
                # Pattern d'urgence qui change
                if int((time.ticks_ms() / 500) % 3) == 0:
                    # Tous les segments
                    for i in range(28):
                        self.bargraph.display.set_segment(i, True)
                elif int((time.ticks_ms() / 500) % 3) == 1:
                    # Moitié supérieure
                    for i in range(14, 28):
                        self.bargraph.display.set_segment(i, True)
                else:
                    # Moitié inférieure
                    for i in range(14):
                        self.bargraph.display.set_segment(i, True)
            else:
                # Flash plus faible ou éteint
                if progress > 0.7:  # Phase finale
                    # Clignotement très rapide
                    micro_flash = int((time.ticks_ms() / 100) % 2)
                    if micro_flash:
                        self.bargraph.display.set_intensity(self.color_palettes['danger_red']['high'])
                        for i in range(0, 28, 3):
                            self.bargraph.display.set_segment(i, True)
                            
            time.sleep_ms(50)
            
    def shutdown_sequence_effect(self, duration=1500):
        """Séquence d'arrêt"""
        steps = int(duration / 30)  # ~33 FPS
        
        for step in range(steps):
            progress = step / steps
            
            # Effet de descente avec traînée
            current_level = int((1 - progress) * 28)
            
            # Intensité décroissante
            intensity = int((1 - progress) * 12) + 2  # Minimum de 2
            
            self.bargraph.display.clear()
            self.bargraph.display.set_intensity(intensity)
            
            # Allumer avec traînée
            for i in range(current_level):
                # Traînée sur les derniers segments
                if i >= current_level - 3:
                    trail_intensity = (current_level - i) / 3
                    self.bargraph.display.set_intensity(int(intensity * trail_intensity))
                    
                self.bargraph.display.set_segment(i, True)
                
            time.sleep_ms(30)
            
        # Éteindre complètement
        self.bargraph.display.clear()
        
    def error_pattern_effect(self, error_code=1, duration=2000):
        """Pattern d'erreur spécifique"""
        patterns = {
            1: {'type': 'alternating', 'intensity': 12},      # Erreur système
            2: {'type': 'v_pattern', 'intensity': 15},       # Erreur critique
            3: {'type': 'random', 'intensity': 10},          # Erreur aléatoire
            4: {'type': 'bottom_half', 'intensity': 13}     # Erreur matérielle
        }
        
        if error_code not in patterns:
            error_code = 1
            
        pattern = patterns[error_code]
        start_time = time.ticks_ms()
        
        while time.ticks_ms() - start_time < duration:
            strobe_phase = int((time.ticks_ms() / 200) % 4)
            
            self.bargraph.display.clear()
            self.bargraph.display.set_intensity(pattern['intensity'])
            
            if pattern['type'] == 'alternating':
                if strobe_phase % 2 == 0:
                    for i in range(0, 28, 2):
                        self.bargraph.display.set_segment(i, True)
                else:
                    for i in range(1, 28, 2):
                        self.bargraph.display.set_segment(i, True)
                        
            elif pattern['type'] == 'v_pattern':
                if strobe_phase < 2:
                    # Côtés
                    for i in [0, 27, 1, 26, 2, 25, 3, 24]:
                        self.bargraph.display.set_segment(i, True)
                else:
                    # Centre
                    for i in range(10, 18):
                        self.bargraph.display.set_segment(i, True)
                        
            elif pattern['type'] == 'random':
                # Segments aléatoires
                for _ in range(8):
                    random_segment = urandom.getrandbits(5) % 28
                    self.bargraph.display.set_segment(random_segment, True)
                    
            elif pattern['type'] == 'bottom_half':
                # Moitié inférieure
                for i in range(14):
                    self.bargraph.display.set_segment(i, True)
                    
            time.sleep_ms(100)
            
    def get_current_effect(self):
        """Obtient l'effet actuellement actif"""
        return self.current_effect
        
    def stop_current_effect(self):
        """Arrête l'effet actuel"""
        self.current_effect = None
        self.bargraph.display.clear()
        
    def run_continuous_effect(self, effect_name, **kwargs):
        """Exécute un effet en continu"""
        self.current_effect = effect_name
        
        effects = {
            'breathing': self.breathing_effect,
            'wave': self.wave_propagation_effect,
            'energy_pulse': self.energy_pulse_effect,
            'warning': self.warning_effect,
            'overheat': self.overheat_effect
        }
        
        if effect_name in effects:
            while self.current_effect == effect_name:
                effects[effect_name](**kwargs)
                time.sleep_ms(20)  # 50 FPS
                
    async def async_effect(self, effect_name, duration=None, **kwargs):
        """Version asynchrone des effets"""
        self.current_effect = effect_name
        
        effects = {
            'charging': self.charging_sequence_effect,
            'firing': self.firing_sequence_effect,
            'overload': self.overload_sequence_effect,
            'shutdown': self.shutdown_sequence_effect,
            'error': self.error_pattern_effect
        }
        
        if effect_name in effects:
            if duration:
                # Effet avec durée
                effects[effect_name](duration=duration, **kwargs)
            else:
                # Effet jusqu'à interruption
                effects[effect_name](**kwargs)
                
        self.current_effect = None