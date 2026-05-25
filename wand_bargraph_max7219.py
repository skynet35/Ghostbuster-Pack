import machine
import time
import math
from machine import Pin, SPI
import uasyncio as asyncio
import urandom

class MAX7219Bargraph:
    """Système MAX7219 pour bargraph BL28-3005S (28 segments)"""
    
    # Registres MAX7219
    REG_DECODE_MODE = 0x09
    REG_INTENSITY = 0x0A
    REG_SCAN_LIMIT = 0x0B
    REG_SHUTDOWN = 0x0C
    REG_DISPLAY_TEST = 0x0F
    
    def __init__(self, spi, cs_pin, num_digits=4):
        """
        Initialise le MAX7219
        
        Args:
            spi: Objet SPI configuré
            cs_pin: Pin de chip select
            num_digits: Nombre de digits (4 pour 28 segments)
        """
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT)
        self.num_digits = num_digits
        self.buffer = [0] * num_digits  # Buffer pour l'affichage
        
        # Configuration initiale
        self.init_display()
        
    def init_display(self):
        """Initialise l'affichage MAX7219"""
        # Mode normal (pas test)
        self.write_register(self.REG_DISPLAY_TEST, 0x00)
        
        # Mode décodeur OFF (nous contrôlons directement les segments)
        self.write_register(self.REG_DECODE_MODE, 0x00)
        
        # Limite de scan (tous les digits)
        self.write_register(self.REG_SCAN_LIMIT, self.num_digits - 1)
        
        # Intensité moyenne
        self.write_register(self.REG_INTENSITY, 0x08)
        
        # Mode normal (pas shutdown)
        self.write_register(self.REG_SHUTDOWN, 0x01)
        
        # Effacer l'affichage
        self.clear()
        
    def write_register(self, register, data):
        """Écrit un registre MAX7219"""
        self.cs.value(0)  # CS actif
        self.spi.write(bytes([register, data]))
        self.cs.value(1)  # CS inactif
        time.sleep_us(2)  # Petit délai
        
    def write_digit(self, digit, value):
        """Écrit un digit spécifique"""
        if 0 <= digit < self.num_digits:
            self.buffer[digit] = value
            self.write_register(digit + 1, value)
            
    def clear(self):
        """Efface tous les digits"""
        for i in range(self.num_digits):
            self.write_digit(i, 0x00)
            
    def set_intensity(self, level):
        """Règle l'intensité (0-15)"""
        level = max(0, min(15, level))
        self.write_register(self.REG_INTENSITY, level)
        
    def set_segment(self, segment, state):
        """Allume/éteint un segment spécifique"""
        digit = segment // 8  # Quel digit (0-3)
        bit = segment % 8   # Quel bit dans le digit (0-7)
        
        if 0 <= digit < self.num_digits and 0 <= bit < 8:
            if state:
                self.buffer[digit] |= (1 << bit)
            else:
                self.buffer[digit] &= ~(1 << bit)
            
            self.write_digit(digit, self.buffer[digit])
            
    def set_segments(self, segments):
        """Définit plusieurs segments à la fois"""
        for segment, state in enumerate(segments):
            if segment < self.num_digits * 8:
                self.set_segment(segment, state)
                
    def get_segment_state(self, segment):
        """Obtient l'état d'un segment"""
        digit = segment // 8
        bit = segment % 8
        
        if 0 <= digit < self.num_digits and 0 <= bit < 8:
            return (self.buffer[digit] >> bit) & 1
        return 0

class ProtonWandBargraph:
    """Baguette Proton avec bargraph BL28-3005S"""
    
    def __init__(self, spi, cs_pin):
        self.display = MAX7219Bargraph(spi, cs_pin, num_digits=4)
        self.num_segments = 28  # 4 digits × 7 segments
        
        # État de la baguette
        self.power_level = 0  # 0-100
        self.is_firing = False
        self.overheating = False
        self.charge_level = 0  # 0-100
        
        # Animation state
        self.animation_phase = 0
        self.last_update = time.ticks_ms()
        
        # Couleurs simulées (intensité)
        self.intensity_levels = {
            'off': 0,
            'dim': 4,
            'normal': 8,
            'bright': 12,
            'maximum': 15
        }
        
        # Configuration des effets
        self.effect_speed = 50  # ms entre mises à jour
        
    def set_power_level(self, level):
        """Définit le niveau de puissance (0-100)"""
        self.power_level = max(0, min(100, level))
        self.update_display()
        
    def set_firing(self, firing):
        """Active/désactive le tir"""
        self.is_firing = firing
        self.update_display()
        
    def set_overheating(self, overheating):
        """Définit l'état de surchauffe"""
        self.overheating = overheating
        self.update_display()
        
    def set_charge_level(self, level):
        """Définit le niveau de charge (0-100)"""
        self.charge_level = max(0, min(100, level))
        self.update_display()
        
    def clear_all(self):
        """Éteint tous les segments"""
        self.display.clear()
        
    def update_display(self):
        """Met à jour l'affichage selon l'état"""
        if self.overheating:
            self.show_overheat_pattern()
        elif self.is_firing:
            self.show_firing_pattern()
        else:
            self.show_power_pattern()
            
    def show_power_pattern(self):
        """Affiche le niveau de puissance"""
        # Calculer combien de segments allumer
        active_segments = int((self.power_level / 100) * self.num_segments)
        
        # Effacer d'abord
        self.display.clear()
        
        # Allumer les segments de bas en haut
        for i in range(active_segments):
            # Intensité selon la position (plus brillant en haut)
            position_intensity = (i / self.num_segments)
            intensity = self.intensity_levels['dim'] + int(position_intensity * 8)
            
            self.display.set_intensity(intensity)
            self.display.set_segment(i, True)
            
    def show_firing_pattern(self):
        """Affiche le pattern de tir"""
        self.display.clear()
        
        # Pattern de tir: vague montante
        firing_segments = int((self.power_level / 100) * self.num_segments)
        
        # Effet de vague
        wave_position = int((time.ticks_ms() / 100) % (firing_segments + 5))
        
        for i in range(self.num_segments):
            if i < firing_segments:
                # Calculer l'intensité selon la position dans la vague
                distance_from_wave = abs(i - wave_position)
                if distance_from_wave < 3:
                    intensity = self.intensity_levels['maximum'] - distance_from_wave * 2
                    self.display.set_intensity(max(0, intensity))
                    self.display.set_segment(i, True)
                else:
                    # Base intensity for active segments
                    base_intensity = self.intensity_levels['bright']
                    self.display.set_intensity(base_intensity)
                    self.display.set_segment(i, True)
                    
    def show_overheat_pattern(self):
        """Affiche le pattern de surchauffe"""
        self.display.clear()
        
        # Pattern clignotant rouge/orange
        flash_rate = 10  # Hz
        flash_state = int((time.ticks_ms() / (1000 / flash_rate)) % 2)
        
        if flash_state:
            # Flash brillant
            self.display.set_intensity(self.intensity_levels['maximum'])
            # Allumer tous les segments pour l'alarme
            for i in range(self.num_segments):
                self.display.set_segment(i, True)
        else:
            # Flash plus faible
            self.display.set_intensity(self.intensity_levels['normal'])
            # Allumer seulement les segments de puissance
            power_segments = int((self.power_level / 100) * self.num_segments)
            for i in range(power_segments):
                self.display.set_segment(i, True)
                
    def show_charging_animation(self, duration=2000):
        """Animation de charge"""
        steps = int(duration / 50)  # 50ms par étape
        
        for step in range(steps):
            progress = step / steps
            
            # Effacer
            self.display.clear()
            
            # Allumer progressivement les segments
            active_segments = int(progress * self.num_segments)
            
            for i in range(active_segments):
                # Intensité croissante
                intensity = self.intensity_levels['dim'] + int((i / self.num_segments) * 8)
                self.display.set_intensity(intensity)
                self.display.set_segment(i, True)
                
            time.sleep_ms(50)
            
        # Maintenir au maximum
        self.display.set_intensity(self.intensity_levels['maximum'])
        for i in range(self.num_segments):
            self.display.set_segment(i, True)
            
    def show_firing_animation(self, duration=1000):
        """Animation de tir"""
        steps = int(duration / 20)  # 20ms par étape
        
        original_power = self.power_level
        
        for step in range(steps):
            progress = step / steps
            
            # Effet de montée puis descente
            if progress < 0.5:
                # Phase de montée
                current_power = original_power + (100 - original_power) * (progress * 2)
            else:
                # Phase de descente
                current_power = 100 - (100 - original_power) * ((progress - 0.5) * 2)
                
            # Afficher le niveau actuel
            self.display.clear()
            active_segments = int((current_power / 100) * self.num_segments)
            
            # Intensité maximum pendant le tir
            self.display.set_intensity(self.intensity_levels['maximum'])
            
            for i in range(active_segments):
                self.display.set_segment(i, True)
                
            time.sleep_ms(20)
            
        # Retour au niveau original
        self.power_level = original_power
        self.update_display()
        
    def show_idle_animation(self):
        """Animation idle - respiration"""
        current_time = time.ticks_ms()
        
        if current_time - self.last_update < self.effect_speed:
            return
            
        self.last_update = current_time
        
        # Effet de respiration
        breath_phase = (current_time / 1000) % (2 * math.pi)
        breath_intensity = 0.5 + 0.5 * math.sin(breath_phase)
        
        # Afficher le niveau avec variation
        self.display.clear()
        active_segments = int((self.power_level / 100) * self.num_segments)
        
        # Intensité variable
        current_intensity = self.intensity_levels['dim'] + int(breath_intensity * 6)
        self.display.set_intensity(current_intensity)
        
        for i in range(active_segments):
            self.display.set_segment(i, True)
            
    def show_error_pattern(self, error_code=1):
        """Affiche un pattern d'erreur"""
        self.display.clear()
        
        # Pattern différent selon le code d'erreur
        if error_code == 1:  # Erreur système
            # Clignotement rapide des segments pairs
            if int((time.ticks_ms() / 200) % 2):
                for i in range(0, self.num_segments, 2):
                    self.display.set_segment(i, True)
        elif error_code == 2:  # Erreur de surchauffe
            # Clignotement alterné
            flash = int((time.ticks_ms() / 300) % 2)
            start = 0 if flash else self.num_segments // 2
            end = self.num_segments // 2 if flash else self.num_segments
            
            for i in range(start, end):
                self.display.set_segment(i, True)
                
        self.display.set_intensity(self.intensity_levels['bright'])
        
    def set_brightness(self, brightness):
        """Règle la luminosité globale (0-15)"""
        self.display.set_intensity(brightness)
        
    def get_status(self):
        """Obtient l'état de la baguette"""
        return {
            'power_level': self.power_level,
            'is_firing': self.is_firing,
            'overheating': self.overheating,
            'charge_level': self.charge_level,
            'active_segments': sum(self.display.get_segment_state(i) for i in range(self.num_segments))
        }

class ProtonWandEffects:
    """Effets spéciaux pour la baguette Proton"""
    
    def __init__(self, bargraph):
        self.bargraph = bargraph
        self.effects = {}
        self.current_effect = None
        
    def start_charging_sequence(self):
        """Démarre la séquence de charge"""
        self.current_effect = 'charging'
        
        # Animation progressive
        for level in range(0, 101, 5):
            self.bargraph.set_power_level(level)
            time.sleep_ms(50)
            
        self.current_effect = None
        
    def start_firing_sequence(self, duration=2000):
        """Démarre la séquence de tir"""
        self.current_effect = 'firing'
        
        # Animation de tir
        self.bargraph.show_firing_animation(duration)
        
        self.current_effect = None
        
    def start_overheat_sequence(self):
        """Démarre la séquence de surchauffe"""
        self.current_effect = 'overheat'
        
        original_state = self.bargraph.overheating
        self.bargraph.set_overheating(True)
        
        # Maintenir l'état de surchauffe pendant 3 secondes
        time.sleep_ms(3000)
        
        self.bargraph.set_overheating(original_state)
        self.current_effect = None
        
    def start_error_sequence(self, error_code=1):
        """Affiche une séquence d'erreur"""
        self.current_effect = 'error'
        
        # Afficher le pattern d'erreur
        for _ in range(10):  # 10 cycles
            self.bargraph.show_error_pattern(error_code)
            time.sleep_ms(300)
            self.bargraph.clear_all()
            time.sleep_ms(300)
            
        self.current_effect = None
        
    def start_idle_animation(self):
        """Démarre l'animation idle"""
        self.current_effect = 'idle'
        
        # Animation de respiration pendant 5 secondes
        start_time = time.ticks_ms()
        while time.ticks_ms() - start_time < 5000:
            self.bargraph.show_idle_animation()
            time.sleep_ms(50)
            
        self.current_effect = None
        
    def get_current_effect(self):
        """Obtient l'effet actuel"""
        return self.current_effect

# Configuration SPI pour le MAX7219
class SPIConfig:
    """Configuration SPI pour MAX7219"""
    
    @staticmethod
    def create_spi(baudrate=10000000, polarity=0, phase=0):
        """Crée une configuration SPI pour MAX7219"""
        # Configuration standard pour MAX7219
        spi = SPI(0, baudrate=baudrate, polarity=polarity, phase=phase, 
                  sck=Pin(2), mosi=Pin(3), miso=Pin(4))  # Pins à ajuster
        return spi
    
    @staticmethod
    def create_proton_wand_config():
        """Configuration recommandée pour la baguette Proton"""
        return {
            'spi': SPIConfig.create_spi(baudrate=10000000),
            'cs_pin': 5,  # Chip select pin
            'num_segments': 28,
            'update_rate': 50  # ms
        }
