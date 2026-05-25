import math
import time
import neopixel
from machine import Pin
import uasyncio as asyncio
import urandom

class AdvancedCyclotron4x21:
    """Système cyclotron pour 4 anneaux de 21 LEDs (84 LEDs total)"""
    
    def __init__(self, data_pin):
        # Configuration des 84 LEDs en série (4 anneaux de 21)
        self.num_rings = 4
        self.leds_per_ring = 21
        self.total_leds = self.num_rings * self.leds_per_ring
        
        # Initialisation de la bande LED
        self.led_strip = neopixel.NeoPixel(Pin(data_pin), self.total_leds)
        
        # État du système
        self.rotation_speed = 1.0
        self.current_position = 0.0
        self.mode = 'idle'  # idle, startup, active, overheat, shutdown
        self.intensity = 1.0
        self.target_rpm = 60
        self.current_rpm = 0
        
        # Timing
        self.last_update = time.ticks_ms()
        self.update_interval = 20  # ms (50 FPS)
        
        # Effets spéciaux
        self.sparks = []  # Étincelles
        self.trail_positions = []  # Traînées
        self.expansion_effect = False
        
        # Couleurs authentiques
        self.colors = {
            'deep_red': (255, 0, 0),
            'red_orange': (255, 50, 0),
            'orange': (255, 165, 0),
            'yellow_orange': (255, 200, 0),
            'yellow': (255, 255, 0),
            'white': (255, 255, 255),
            'hot_white': (255, 240, 200),
            'blue': (0, 100, 255),
            'purple': (128, 0, 128)
        }
        
        # Configuration par mode
        self.mode_configs = {
            'idle': {
                'base_colors': [self.colors['deep_red'], self.colors['red_orange']],
                'pulse_speed': 0.5,
                'rotation_speed': 0.3,
                'brightness': 0.4,
                'sparkle_rate': 0.02
            },
            'startup': {
                'base_colors': [self.colors['red_orange'], self.colors['orange']],
                'pulse_speed': 1.0,
                'rotation_speed': 0.8,
                'brightness': 0.7,
                'sparkle_rate': 0.05
            },
            'active': {
                'base_colors': [self.colors['orange'], self.colors['yellow_orange']],
                'pulse_speed': 2.0,
                'rotation_speed': 2.0,
                'brightness': 1.0,
                'sparkle_rate': 0.08
            },
            'overheat': {
                'base_colors': [self.colors['yellow'], self.colors['white']],
                'pulse_speed': 4.0,
                'rotation_speed': 3.5,
                'brightness': 1.2,
                'sparkle_rate': 0.15,
                'flash': True
            },
            'shutdown': {
                'base_colors': [self.colors['red_orange'], self.colors['deep_red']],
                'pulse_speed': 0.3,
                'rotation_speed': 0.2,
                'brightness': 0.2,
                'sparkle_rate': 0.01
            }
        }
        
        # Animation state
        self.animation_phase = 0
        self.subpixel_offset = 0.0
        
    def set_mode(self, mode):
        """Changer le mode du cyclotron"""
        if mode in self.mode_configs:
            old_mode = self.mode
            self.mode = mode
            
            # Déclencher des effets spéciaux lors du changement
            if old_mode != mode:
                if mode == 'overheat':
                    self.trigger_overheat_effect()
                elif mode == 'active' and old_mode == 'startup':
                    self.trigger_expansion_effect()
    
    def set_rpm(self, rpm):
        """Définir la vitesse en RPM"""
        self.target_rpm = max(0, min(300, rpm))
        self.rotation_speed = rpm / 60.0  # Convertir en tours par seconde
    
    def calculate_led_position(self, ring_index, led_index):
        """Calculer la position absolue d'une LED dans la bande"""
        return ring_index * self.leds_per_ring + led_index
    
    def get_ring_leds(self, ring_index):
        """Obtenir toutes les LEDs d'un anneau spécifique"""
        start = ring_index * self.leds_per_ring
        end = start + self.leds_per_ring
        return list(range(start, end))
    
    def create_sparkle_effect(self, config):
        """Créer des étincelles aléatoires"""
        current_time = time.ticks_ms()
        
        # Ajouter de nouvelles étincelles
        if urandom.getrandbits(16) < int(config['sparkle_rate'] * 65535):
            ring = urandom.getrandbits(2)  # 0-3
            led = urandom.getrandbits(5)   # 0-20
            if led < self.leds_per_ring:
                self.sparks.append({
                    'ring': ring,
                    'led': led,
                    'intensity': 0.8 + urandom.random() * 0.2,
                    'life': 1.0,
                    'max_life': 0.3 + urandom.random() * 0.4,
                    'color': self.colors['white'] if urandom.random() < 0.5 else self.colors['hot_white']
                })
        
        # Mettre à jour les étincelles existantes
        for spark in self.sparks[:]:
            spark['life'] -= 0.03
            if spark['life'] <= 0:
                self.sparks.remove(spark)
    
    def create_trail_effect(self, config):
        """Créer des traînées lumineuses"""
        # Ajouter la position actuelle à la traînée
        for ring in range(self.num_rings):
            self.trail_positions.append({
                'ring': ring,
                'position': self.current_position,
                'intensity': 0.6,
                'age': 0
            })
        
        # Limiter la longueur et vieillir les traînées
        max_trails = 8
        if len(self.trail_positions) > max_trails:
            self.trail_positions = self.trail_positions[-max_trails:]
        
        # Vieillir les traînées
        for trail in self.trail_positions:
            trail['age'] += 1
            trail['intensity'] *= 0.85  # Dégradation exponentielle
    
    def calculate_rotation_color(self, led_position, base_colors, intensity, pulse_value):
        """Calculer la couleur selon la position de rotation"""
        # Position relative par rapport à la rotation
        relative_pos = (led_position - self.current_position) % self.leds_per_ring
        
        # Normaliser la position (0-1)
        normalized_pos = relative_pos / self.leds_per_ring
        
        # Créer un gradient circulaire
        if normalized_pos < 0.5:
            # Première moitié: premier vers second
            ratio = normalized_pos * 2
            r = int(base_colors[0][0] * (1 - ratio) + base_colors[1][0] * ratio)
            g = int(base_colors[0][1] * (1 - ratio) + base_colors[1][1] * ratio)
            b = int(base_colors[0][2] * (1 - ratio) + base_colors[1][2] * ratio)
        else:
            # Deuxième moitié: second vers premier
            ratio = (normalized_pos - 0.5) * 2
            r = int(base_colors[1][0] * (1 - ratio) + base_colors[0][0] * ratio)
            g = int(base_colors[1][1] * (1 - ratio) + base_colors[1][1] * ratio)
            b = int(base_colors[1][2] * (1 - ratio) + base_colors[0][2] * ratio)
        
        # Appliquer l'intensité et la pulsation
        brightness = intensity * (0.6 + 0.4 * pulse_value)
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    
    def apply_sparkle_overlay(self, base_color, ring, led):
        """Appliquer les étincelles par-dessus la couleur de base"""
        for spark in self.sparks:
            if spark['ring'] == ring and spark['led'] == led:
                # Mélanger la couleur de l'étincelle
                spark_intensity = spark['intensity'] * (spark['life'] / spark['max_life'])
                r = int(base_color[0] * (1 - spark_intensity) + spark['color'][0] * spark_intensity)
                g = int(base_color[1] * (1 - spark_intensity) + spark['color'][1] * spark_intensity)
                b = int(base_color[2] * (1 - spark_intensity) + spark['color'][2] * spark_intensity)
                return (r, g, b)
        return base_color
    
    def apply_trail_overlay(self, base_color, ring, led_position):
        """Appliquer les effets de traînée"""
        for trail in self.trail_positions:
            if trail['ring'] == ring:
                # Calculer la distance avec la traînée
                distance = abs(led_position - trail['position']) % self.leds_per_ring
                if distance < 3:  # Portée de la traînée
                    trail_intensity = trail['intensity'] * (1 - distance / 3)
                    # Ajouter un effet de "glow"
                    r = min(255, int(base_color[0] + trail_intensity * 100))
                    g = min(255, int(base_color[1] + trail_intensity * 50))
                    b = min(255, int(base_color[2] + trail_intensity * 25))
                    return (r, g, b)
        return base_color
    
    def trigger_expansion_effect(self):
        """Déclencher un effet d'expansion depuis le centre"""
        # Cet effet sera utilisé lors de la transition startup→active
        self.expansion_effect = True
        self.expansion_start_time = time.ticks_ms()
    
    def apply_expansion_effect(self, base_color, ring, led_position):
        """Appliquer l'effet d'expansion"""
        if not self.expansion_effect:
            return base_color
        
        elapsed = time.ticks_ms() - self.expansion_start_time
        if elapsed > 2000:  # 2 secondes d'effet
            self.expansion_effect = False
            return base_color
        
        # Calculer la distance depuis le centre
        center_pos = self.leds_per_ring // 2
        distance = abs(led_position - center_pos)
        
        # L'onde d'expansion
        expansion_radius = (elapsed / 2000) * (self.leds_per_ring // 2)
        wave_intensity = max(0, 1 - abs(distance - expansion_radius) / 3)
        
        if wave_intensity > 0:
            # Amplifier la couleur
            r = min(255, int(base_color[0] * (1 + wave_intensity * 0.5)))
            g = min(255, int(base_color[1] * (1 + wave_intensity * 0.3)))
            b = min(255, int(base_color[2] * (1 + wave_intensity * 0.2)))
            return (r, g, b)
        
        return base_color
    
    def trigger_overheat_effect(self):
        """Déclencher l'effet de surchauffe"""
        # Flash rapide et couleurs intenses
        self.overheat_flash = True
        self.overheat_start_time = time.ticks_ms()
    
    def apply_overheat_effect(self, base_color, ring, led_position):
        """Appliquer les effets de surchauffe"""
        if not hasattr(self, 'overheat_flash') or not self.overheat_flash:
            return base_color
        
        elapsed = time.ticks_ms() - self.overheat_start_time
        if elapsed > 3000:  # 3 secondes d'effet
            self.overheat_flash = False
            return base_color
        
        # Flash rapide
        flash_rate = 15 + (elapsed / 100)  # Augmente avec le temps
        if int(elapsed * flash_rate * 0.001) % 2:
            # Couleur de surchauffe intense
            r = min(255, base_color[0] + 100)
            g = min(255, base_color[1] + 50)
            b = min(255, base_color[2] + 25)
            return (r, g, b)
        
        return base_color
    
    def update_rpm_simulation(self):
        """Simuler l'accélération/décélération réaliste"""
        # Accélération progressive vers la cible
        rpm_diff = self.target_rpm - self.current_rpm
        if abs(rpm_diff) > 1:
            self.current_rpm += rpm_diff * 0.1  # Facteur d'accélération
        else:
            self.current_rpm = self.target_rpm
        
        # Ajuster la vitesse de rotation
        self.rotation_speed = self.current_rpm / 60.0
    
    def render_all_rings(self, config):
        """Rendu complet de tous les anneaux"""
        # Calculer la valeur de pulsation
        pulse_phase = time.ticks_ms() * 0.001 * config['pulse_speed']
        pulse_value = 0.5 + 0.5 * math.sin(pulse_phase)
        
        # Parcourir tous les anneaux et LEDs
        for ring in range(self.num_rings):
            for led in range(self.leds_per_ring):
                # Position absolue dans la bande
                absolute_pos = self.calculate_led_position(ring, led)
                
                # Calculer la couleur de base selon la rotation
                base_color = self.calculate_rotation_color(
                    led, config['base_colors'], 
                    config['brightness'], pulse_value
                )
                
                # Appliquer les effets spéciaux
                final_color = base_color
                final_color = self.apply_sparkle_overlay(final_color, ring, led)
                final_color = self.apply_trail_overlay(final_color, ring, led)
                final_color = self.apply_expansion_effect(final_color, ring, led)
                final_color = self.apply_overheat_effect(final_color, ring, led)
                
                # Effet de profondeur (anneaux extérieurs plus brillants)
                depth_factor = 0.8 + (ring / self.num_rings) * 0.4
                final_color = (
                    int(final_color[0] * depth_factor),
                    int(final_color[1] * depth_factor),
                    int(final_color[2] * depth_factor)
                )
                
                # Appliquer à la LED
                self.led_strip[absolute_pos] = final_color
    
    def update(self):
        """Mise à jour principale du cyclotron"""
        current_time = time.ticks_ms()
        
        # Vérifier le timing
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Mettre à jour la simulation RPM
        self.update_rpm_simulation()
        
        # Obtenir la configuration du mode actuel
        config = self.mode_configs[self.mode]
        
        # Mettre à jour la position de rotation (avec sub-pixel precision)
        self.current_position += self.rotation_speed * 0.1
        self.current_position %= self.leds_per_ring
        
        # Créer les effets spéciaux
        self.create_sparkle_effect(config)
        self.create_trail_effect(config)
        
        # Rendu complet
        self.render_all_rings(config)
        
        # Écrire les données aux LEDs
        self.led_strip.write()
    
    def startup_sequence(self):
        """Séquence de démarrage complète"""
        print("[CYCLOTRON] Démarrage en cours...")
        
        # Phase 1: Allumage progressif des anneaux
        for phase in range(100):
            progress = phase / 100
            
            # Allumer progressivement chaque anneau
            for ring in range(self.num_rings):
                ring_start = int(ring * self.leds_per_ring * progress)
                ring_end = int((ring + 1) * self.leds_per_ring * progress)
                
                for led in range(self.leds_per_ring):
                    absolute_pos = self.calculate_led_position(ring, led)
                    
                    if led < ring_start % self.leds_per_ring or led > ring_end % self.leds_per_ring:
                        self.led_strip[absolute_pos] = (0, 0, 0)
                    else:
                        # Couleur selon le progrès
                        intensity = 0.3 + progress * 0.7
                        color = self.colors['red_orange']
                        self.led_strip[absolute_pos] = (
                            int(color[0] * intensity),
                            int(color[1] * intensity),
                            int(color[2] * intensity)
                        )
            
            self.led_strip.write()
            time.sleep(0.03)  # 30ms entre frames
        
        # Phase 2: Accélération jusqu'à 60 RPM
        self.set_mode('startup')
        for rpm in range(0, 61, 5):
            self.set_rpm(rpm)
            time.sleep(0.2)
        
        print("[CYCLOTRON] Démarrage terminé!")
    
    def shutdown_sequence(self):
        """Séquence d'arrêt"""
        print("[CYCLOTRON] Arrêt en cours...")
        
        # Décélération
        current_rpm = int(self.current_rpm)
        for rpm in range(current_rpm, -1, -10):
            self.set_rpm(rpm)
            time.sleep(0.3)
        
        # Extinction progressive
        for intensity in range(100, -1, -5):
            brightness = intensity / 100
            
            for i in range(self.total_leds):
                current_color = self.led_strip[i]
                self.led_strip[i] = (
                    int(current_color[0] * brightness),
                    int(current_color[1] * brightness),
                    int(current_color[2] * brightness)
                )
            
            self.led_strip.write()
            time.sleep(0.05)
        
        print("[CYCLOTRON] Arrêt terminé!")
    
    def power_on_animation(self):
        """Animation d'allumage cinématographique"""
        # Effet d'expansion depuis le centre
        center_led = self.leds_per_ring // 2
        
        for wave in range(self.leds_per_ring // 2 + 1):
            for ring in range(self.num_rings):
                for led in range(self.leds_per_ring):
                    distance = abs(led - center_led)
                    
                    if distance <= wave:
                        # Intensité selon la distance
                        intensity = 1.0 - (distance / (self.leds_per_ring // 2))
                        color = self.colors['hot_white']
                        
                        absolute_pos = self.calculate_led_position(ring, led)
                        self.led_strip[absolute_pos] = (
                            int(color[0] * intensity),
                            int(color[1] * intensity),
                            int(color[2] * intensity)
                        )
            
            self.led_strip.write()
            time.sleep(0.05)
    
    def get_status(self):
        """Obtenir l'état du cyclotron"""
        return {
            'mode': self.mode,
            'current_rpm': self.current_rpm,
            'target_rpm': self.target_rpm,
            'rotation_speed': self.rotation_speed,
            'intensity': self.intensity,
            'active_effects': {
                'sparks': len(self.sparks),
                'trails': len(self.trail_positions),
                'expansion': hasattr(self, 'expansion_effect') and self.expansion_effect,
                'overheat': hasattr(self, 'overheat_flash') and self.overheat_flash
            }
        }

# Classe principale pour gérer le cyclotron dans le système complet
class CyclotronManager:
    def __init__(self, data_pin):
        self.cyclotron = AdvancedCyclotron4x21(data_pin)
        self.is_running = False
        
    def start(self):
        """Démarrer le cyclotron"""
        if not self.is_running:
            self.is_running = True
            self.cyclotron.power_on_animation()
            self.cyclotron.startup_sequence()
            self.cyclotron.set_mode('active')
    
    def stop(self):
        """Arrêter le cyclotron"""
        if self.is_running:
            self.cyclotron.shutdown_sequence()
            self.is_running = False
    
    def set_power_level(self, level):
        """Ajuster le niveau de puissance (0-100)"""
        rpm = 60 + (level / 100) * 240  # 60-300 RPM
        self.cyclotron.set_rpm(rpm)
        
        # Ajuster l'intensité lumineuse
        self.cyclotron.intensity = 0.4 + (level / 100) * 0.6
    
    def trigger_fire_effect(self):
        """Déclencher l'effet de tir"""
        # Accélération rapide
        original_rpm = self.cyclotron.current_rpm
        self.cyclotron.set_rpm(250)
        
        # Effet d'expansion
        self.cyclotron.trigger_expansion_effect()
        
        # Retour à la vitesse normale après 2 secondes
        time.sleep(2)
        self.cyclotron.set_rpm(original_rpm)
    
    def update(self):
        """Mise à jour du cyclotron (à appeler dans la boucle principale)"""
        if self.is_running:
            self.cyclotron.update()
    
    def get_status(self):
        """Obtenir l'état complet"""
        return self.cyclotron.get_status()