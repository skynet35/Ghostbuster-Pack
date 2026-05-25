import machine
import time
from machine import Pin, ADC
import uasyncio as asyncio

class PowerManagementSystem:
    """Système de gestion de puissance pour 84 LEDs"""
    
    def __init__(self):
        # Configuration de la consommation
        self.max_current = 5.0  # 5A max (convertisseur buck)
        self.led_current_per_pixel = 0.060  # 60mA par LED à pleine puissance
        self.total_leds = 84  # 4 anneaux x 21 LEDs
        
        # Surveillance de la puissance
        self.current_consumption = 0.0
        self.voltage_input = 5.0
        self.temperature = 25.0
        
        # État du système
        self.power_budget_status = 'NORMAL'  # NORMAL, WARNING, CRITICAL
        self.brightness_limit = 1.0  # Limite de luminosité (0-1)
        self.emergency_shutdown = False
        
        # Historique pour le suivi
        self.consumption_history = []
        self.max_history_size = 100
        
        # Capteurs (à connecter si disponibles)
        self.current_sensor = None  # ADC(Pin(29)) par exemple
        self.temp_sensor = None      # ADC(Pin(28)) par exemple
        
        # Configuration des alertes
        self.warning_threshold = 4.0   # 4A
        self.critical_threshold = 4.5  # 4.5A
        self.temp_threshold = 70.0     # 70°C
        
    def set_current_sensor(self, pin):
        """Configurer le capteur de courant"""
        self.current_sensor = ADC(Pin(pin))
        
    def set_temperature_sensor(self, pin):
        """Configurer le capteur de température"""
        self.temp_sensor = ADC(Pin(pin))
    
    def calculate_led_consumption(self, num_active_leds, brightness_level, color=(255, 255, 255)):
        """Calculer la consommation estimée des LEDs"""
        # Facteur selon la couleur (RVB)
        color_factor = (color[0] + color[1] + color[2]) / (3 * 255)
        
        # Consommation estimée
        estimated_current = num_active_leds * self.led_current_per_pixel * brightness_level * color_factor
        
        return estimated_current
    
    def apply_brightness_limit(self, color, limit_factor):
        """Appliquer la limite de luminosité à une couleur"""
        r = int(color[0] * limit_factor)
        g = int(color[1] * limit_factor)
        b = int(color[2] * limit_factor)
        
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    
    def adaptive_brightness_control(self, desired_brightness, num_active_leds):
        """Contrôle adaptatif de la luminosité"""
        # Calculer la consommation projetée
        projected_current = self.calculate_led_consumption(num_active_leds, desired_brightness)
        
        # Ajuster selon la consommation actuelle
        if self.current_consumption > self.critical_threshold:
            # Mode critique: réduire fortement
            self.brightness_limit = 0.3
            self.power_budget_status = 'CRITICAL'
            print("[POWER] Mode CRITIQUE - Luminosité réduite à 30%")
            
        elif self.current_consumption > self.warning_threshold:
            # Mode avertissement: réduire modérément
            self.brightness_limit = 0.6
            self.power_budget_status = 'WARNING'
            print("[POWER] Mode WARNING - Luminosité réduite à 60%")
            
        else:
            # Mode normal: autoriser la luminosité désirée
            self.brightness_limit = min(1.0, desired_brightness)
            self.power_budget_status = 'NORMAL'
        
        # Vérifier la consommation projetée
        if projected_current > self.warning_threshold:
            # Réduire la luminosité pour rester dans les limites
            safe_brightness = self.warning_threshold / projected_current
            self.brightness_limit = min(self.brightness_limit, safe_brightness)
        
        return self.brightness_limit
    
    def monitor_power_consumption(self):
        """Surveiller la consommation en temps réel"""
        if self.current_sensor:
            # Lire le capteur de courant (valeur brute)
            raw_value = self.current_sensor.read_u16()
            
            # Convertir en ampères (à calibrer selon votre capteur)
            # Ceci est un exemple, ajustez selon votre capteur spécifique
            self.current_consumption = (raw_value / 65535) * 5.0  # 5A max
        else:
            # Estimation basée sur l'état des LEDs
            self.current_consumption = self.estimate_consumption_from_state()
        
        # Ajouter à l'historique
        self.consumption_history.append({
            'timestamp': time.ticks_ms(),
            'current': self.current_consumption,
            'status': self.power_budget_status
        })
        
        # Limiter la taille de l'historique
        if len(self.consumption_history) > self.max_history_size:
            self.consumption_history.pop(0)
        
        return self.current_consumption
    
    def estimate_consumption_from_state(self):
        """Estimer la consommation depuis l'état du système"""
        # À implémenter selon votre système
        # Cette méthode doit être appelée avec les données d'état réelles
        return 2.5  # Valeur par défaut
    
    def check_thermal_limits(self):
        """Vérifier les limites thermiques"""
        if self.temp_sensor:
            # Lire la température (à calibrer)
            raw_temp = self.temp_sensor.read_u16()
            self.temperature = (raw_temp / 65535) * 100  # Exemple de conversion
        
        if self.temperature > self.temp_threshold:
            print(f"[POWER] Température élevée: {self.temperature:.1f}°C")
            return False
        
        return True
    
    def get_power_budget_info(self):
        """Obtenir les informations sur le budget de puissance"""
        available_power = self.max_current - self.current_consumption
        utilization_percent = (self.current_consumption / self.max_current) * 100
        
        return {
            'current_consumption': self.current_consumption,
            'max_current': self.max_current,
            'available_current': available_power,
            'utilization_percent': utilization_percent,
            'brightness_limit': self.brightness_limit,
            'status': self.power_budget_status,
            'temperature': self.temperature,
            'emergency_shutdown': self.emergency_shutdown
        }
    
    def emergency_power_cut(self):
        """Coupure d'urgence de la puissance"""
        print("[POWER] COUPURE D'URGENCE!")
        self.emergency_shutdown = True
        self.brightness_limit = 0.1  # 10% seulement
        self.power_budget_status = 'EMERGENCY'
        
        # Retourner une couleur d'urgence (rouge clignotant)
        return (255, 0, 0)
    
    def reset_emergency(self):
        """Réinitialiser l'état d'urgence"""
        self.emergency_shutdown = False
        self.brightness_limit = 1.0
        self.power_budget_status = 'NORMAL'
        print("[POWER] État d'urgence réinitialisé")
    
    def get_efficiency_report(self):
        """Obtenir un rapport d'efficacité énergétique"""
        if not self.consumption_history:
            return None
        
        # Calculer les moyennes
        avg_current = sum(entry['current'] for entry in self.consumption_history) / len(self.consumption_history)
        max_current = max(entry['current'] for entry in self.consumption_history)
        min_current = min(entry['current'] for entry in self.consumption_history)
        
        # Calculer le temps en mode critique
        critical_time = sum(1 for entry in self.consumption_history if entry['status'] == 'CRITICAL')
        critical_percent = (critical_time / len(self.consumption_history)) * 100
        
        return {
            'average_current': avg_current,
            'max_current': max_current,
            'min_current': min_current,
            'critical_time_percent': critical_percent,
            'efficiency_score': max(0, 100 - critical_percent)
        }

class PowerOptimizedCyclotron:
    """Cyclotron avec gestion intelligente de la puissance"""
    
    def __init__(self, data_pin, power_manager):
        self.power_manager = power_manager
        self.led_strip = neopixel.NeoPixel(Pin(data_pin), 84)  # 4x21 LEDs
        
        # État des LEDs
        self.led_states = [(0, 0, 0)] * 84
        self.desired_brightness = 1.0
        
    def set_led_color(self, index, color):
        """Définir la couleur d'une LED avec gestion de puissance"""
        if 0 <= index < 84:
            self.led_states[index] = color
            self.update_led(index)
    
    def update_led(self, index):
        """Mettre à jour une LED avec limitation de puissance"""
        original_color = self.led_states[index]
        
        # Compter les LEDs actives
        active_leds = sum(1 for color in self.led_states if color != (0, 0, 0))
        
        # Obtenir la limite de luminosité adaptative
        brightness_limit = self.power_manager.adaptive_brightness_control(
            self.desired_brightness, active_leds
        )
        
        # Appliquer la limite
        limited_color = self.power_manager.apply_brightness_limit(original_color, brightness_limit)
        
        # Définir la couleur finale
        self.led_strip[index] = limited_color
    
    def update_all_leds(self):
        """Mettre à jour toutes les LEDs avec gestion de puissance"""
        # Compter les LEDs actives
        active_leds = sum(1 for color in self.led_states if color != (0, 0, 0))
        
        # Obtenir la limite de luminosité
        brightness_limit = self.power_manager.adaptive_brightness_control(
            self.desired_brightness, active_leds
        )
        
        # Appliquer la limite à toutes les LEDs
        for i in range(84):
            if self.led_states[i] != (0, 0, 0):
                limited_color = self.power_manager.apply_brightness_limit(
                    self.led_states[i], brightness_limit
                )
                self.led_strip[i] = limited_color
        
        # Écrire les données
        self.led_strip.write()
        
        # Surveiller la consommation
        self.power_manager.monitor_power_consumption()
    
    def emergency_shutdown(self):
        """Arrêt d'urgence"""
        emergency_color = self.power_manager.emergency_power_cut()
        
        # Clignotement rouge d'urgence
        for _ in range(10):
            self.led_strip.fill(emergency_color)
            self.led_strip.write()
            time.sleep(0.2)
            
            self.led_strip.fill((0, 0, 0))
            self.led_strip.write()
            time.sleep(0.2)
    
    def get_power_status(self):
        """Obtenir l'état de la puissance"""
        return self.power_manager.get_power_budget_info()
    
    def set_desired_brightness(self, brightness):
        """Définir la luminosité désirée"""
        self.desired_brightness = max(0.0, min(1.0, brightness))
    
    def reset_power_system(self):
        """Réinitialiser le système de puissance"""
        self.power_manager.reset_emergency()
        self.desired_brightness = 1.0