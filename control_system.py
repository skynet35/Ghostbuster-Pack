import machine
import time
import uasyncio as asyncio
from machine import Pin

class ButtonHandler:
    def __init__(self, pin, name, pull=Pin.PULL_UP, debounce_time=50):
        self.pin = Pin(pin, Pin.IN, pull)
        self.name = name
        self.debounce_time = debounce_time
        self.last_state = self.pin.value()
        self.last_debounce_time = 0
        self.state = 'released'
        self.callbacks = {
            'press': [],
            'release': [],
            'long_press': [],
            'double_click': []
        }
        self.long_press_time = 1000  # ms
        self.double_click_time = 300  # ms
        self.last_click_time = 0
        self.click_count = 0
        self.long_press_triggered = False
        
    def add_callback(self, event, callback):
        """Ajouter un callback pour un événement"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def remove_callback(self, event, callback):
        """Retirer un callback"""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)
    
    def trigger_callbacks(self, event):
        """Déclencher tous les callbacks d'un événement"""
        for callback in self.callbacks[event]:
            try:
                callback(self.name)
            except Exception as e:
                print(f"Erreur callback {event}: {e}")
    
    def update(self):
        """Mettre à jour l'état du bouton avec anti-rebond"""
        current_time = time.ticks_ms()
        current_state = self.pin.value()
        
        # Détection du changement d'état
        if current_state != self.last_state:
            self.last_debounce_time = current_time
            self.last_state = current_state
        
        # Vérification du temps d'anti-rebond
        if current_time - self.last_debounce_time > self.debounce_time:
            # Détection de l'état stable
            if current_state == 0 and self.state == 'released':  # Bouton pressé
                self.state = 'pressed'
                self.trigger_callbacks('press')
                self.click_count += 1
                
                # Détection du double-clic
                if current_time - self.last_click_time < self.double_click_time:
                    self.trigger_callbacks('double_click')
                    self.click_count = 0
                
                self.last_click_time = current_time
                self.long_press_triggered = False
                
            elif current_state == 1 and self.state == 'pressed':  # Bouton relâché
                self.state = 'released'
                self.trigger_callbacks('release')
            
            # Détection de l'appui long
            if self.state == 'pressed' and not self.long_press_triggered:
                if current_time - self.last_click_time > self.long_press_time:
                    self.trigger_callbacks('long_press')
                    self.long_press_triggered = True
    
    def is_pressed(self):
        """Vérifier si le bouton est pressé"""
        return self.state == 'pressed'
    
    def is_released(self):
        """Vérifier si le bouton est relâché"""
        return self.state == 'released'

class SwitchHandler:
    def __init__(self, pin, name, pull=Pin.PULL_UP):
        self.pin = Pin(pin, Pin.IN, pull)
        self.name = name
        self.state = self.pin.value()
        self.last_state = self.state
        self.callbacks = {
            'on': [],
            'off': [],
            'toggle': []
        }
    
    def add_callback(self, event, callback):
        """Ajouter un callback"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def update(self):
        """Mettre à jour l'état de l'interrupteur"""
        current_state = self.pin.value()
        
        if current_state != self.last_state:
            self.last_state = current_state
            time.sleep(50)  # Petit délai pour la stabilité
            
            if current_state == 0:  # Interrupteur ON
                self.state = 'on'
                for callback in self.callbacks['on']:
                    callback(self.name)
            else:  # Interrupteur OFF
                self.state = 'off'
                for callback in self.callbacks['off']:
                    callback(self.name)
            
            # Callback de basculement
            for callback in self.callbacks['toggle']:
                callback(self.name, self.state)
    
    def is_on(self):
        """Vérifier si l'interrupteur est ON"""
        return self.state == 'on'
    
    def is_off(self):
        """Vérifier si l'interrupteur est OFF"""
        return self.state == 'off'

class ProtonPackControls:
    def __init__(self):
        # Configuration des boutons selon le schéma authentique
        intensity_dial_pin = 26
        self.controls = {
            'main_power': SwitchHandler(9, 'Main Power'),
            'wand_trigger': ButtonHandler(10, 'Wand Trigger'),
            'wand_switch': SwitchHandler(11, 'Wand Switch'),
            'venting_button': ButtonHandler(12, 'Venting Button'),
            'mode_switch': SwitchHandler(13, 'Mode Switch'),
            'intensity_dial': Pin(intensity_dial_pin, Pin.IN),
            'emergency_stop': ButtonHandler(15, 'Emergency Stop'),
            'test_button': ButtonHandler(16, 'Test Button'),
            'calibration_button': ButtonHandler(17, 'Calibration Button')
        }
        self._intensity_adc = None
        try:
            self._intensity_adc = machine.ADC(intensity_dial_pin)
        except Exception:
            self._intensity_adc = None
        
        # État du système
        self.system_state = {
            'power': False,
            'wand_active': False,
            'venting': False,
            'emergency_mode': False,
            'test_mode': False,
            'calibration_mode': False,
            'intensity_level': 0
        }
        
        # Historique des actions
        self.action_log = []
        self.max_log_size = 100
        
        # Configuration des callbacks
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Configurer tous les callbacks pour les contrôles"""
        # Interrupteur principal
        self.controls['main_power'].add_callback('on', self.power_on)
        self.controls['main_power'].add_callback('off', self.power_off)
        
        # Gâchette de la baguette
        self.controls['wand_trigger'].add_callback('press', self.wand_trigger_press)
        self.controls['wand_trigger'].add_callback('release', self.wand_trigger_release)
        self.controls['wand_trigger'].add_callback('long_press', self.wand_overload)
        
        # Interrupteur de la baguette
        self.controls['wand_switch'].add_callback('on', self.wand_switch_on)
        self.controls['wand_switch'].add_callback('off', self.wand_switch_off)
        
        # Bouton de ventilation
        self.controls['venting_button'].add_callback('press', self.start_venting)
        self.controls['venting_button'].add_callback('release', self.stop_venting)
        
        # Bouton d'arrêt d'urgence
        self.controls['emergency_stop'].add_callback('press', self.emergency_stop)
        
        # Bouton de test
        self.controls['test_button'].add_callback('press', self.toggle_test_mode)
        
        # Bouton de calibration
        self.controls['calibration_button'].add_callback('press', self.start_calibration)
        self.controls['calibration_button'].add_callback('long_press', self.full_calibration)
        
        # Interrupteur de mode
        self.controls['mode_switch'].add_callback('toggle', self.mode_switch_changed)
    
    def log_action(self, action, details=None):
        """Enregistrer une action dans l'historique"""
        timestamp = time.ticks_ms()
        log_entry = {
            'timestamp': timestamp,
            'action': action,
            'details': details,
            'state': self.system_state.copy()
        }
        
        self.action_log.append(log_entry)
        
        # Limiter la taille du journal
        if len(self.action_log) > self.max_log_size:
            self.action_log.pop(0)
        
        print(f"[CONTROLS] {action}: {details}")
    
    # Méthodes de callback
    def power_on(self, control_name):
        """Mise sous tension du système"""
        if not self.system_state['power']:
            self.system_state['power'] = True
            self.log_action('POWER_ON', f'Control: {control_name}')
            # Déclencher la séquence de démarrage
            
    def power_off(self, control_name):
        """Mise hors tension du système"""
        if self.system_state['power']:
            self.system_state['power'] = False
            self.system_state['wand_active'] = False
            self.system_state['venting'] = False
            self.log_action('POWER_OFF', f'Control: {control_name}')
            # Déclencher la séquence d'arrêt
            
    def wand_trigger_press(self, control_name):
        """Pression sur la gâchette"""
        if self.system_state['power'] and not self.system_state['emergency_mode']:
            self.system_state['wand_active'] = True
            self.log_action('WAND_TRIGGER_PRESS', f'Control: {control_name}')
            # Activer le flux proton
            
    def wand_trigger_release(self, control_name):
        """Relâchement de la gâchette"""
        if self.system_state['wand_active']:
            self.system_state['wand_active'] = False
            self.log_action('WAND_TRIGGER_RELEASE', f'Control: {control_name}')
            # Désactiver le flux proton
            
    def wand_overload(self, control_name):
        """Surcharge de la baguette (appui long)"""
        if self.system_state['wand_active']:
            self.log_action('WAND_OVERLOAD', f'Control: {control_name}')
            # Déclencher l'effet de surcharge
            
    def wand_switch_on(self, control_name):
        """Activation de l'interrupteur de baguette"""
        self.log_action('WAND_SWITCH_ON', f'Control: {control_name}')
        # Préparer la baguette
        
    def wand_switch_off(self, control_name):
        """Désactivation de l'interrupteur de baguette"""
        self.log_action('WAND_SWITCH_OFF', f'Control: {control_name}')
        # Sécuriser la baguette
        
    def start_venting(self, control_name):
        """Démarrer la ventilation"""
        if self.system_state['power'] and not self.system_state['venting']:
            self.system_state['venting'] = True
            self.log_action('VENTING_START', f'Control: {control_name}')
            # Déclencher la séquence de ventilation
            
    def stop_venting(self, control_name):
        """Arrêter la ventilation"""
        if self.system_state['venting']:
            self.system_state['venting'] = False
            self.log_action('VENTING_STOP', f'Control: {control_name}')
            # Arrêter la ventilation
            
    def emergency_stop(self, control_name):
        """Arrêt d'urgence"""
        self.system_state['emergency_mode'] = True
        self.system_state['wand_active'] = False
        self.log_action('EMERGENCY_STOP', f'Control: {control_name}')
        # Déclencher l'arrêt d'urgence
        
    def toggle_test_mode(self, control_name):
        """Basculer le mode test"""
        self.system_state['test_mode'] = not self.system_state['test_mode']
        self.log_action('TEST_MODE_TOGGLE', f'Control: {control_name}, State: {self.system_state["test_mode"]}')
        # Activer/désactiver le mode test
        
    def start_calibration(self, control_name):
        """Démarrer la calibration"""
        if not self.system_state['calibration_mode']:
            self.system_state['calibration_mode'] = True
            self.log_action('CALIBRATION_START', f'Control: {control_name}')
            # Démarrer la procédure de calibration
            
    def full_calibration(self, control_name):
        """Calibration complète (appui long)"""
        self.log_action('FULL_CALIBRATION', f'Control: {control_name}')
        # Déclencher la calibration complète du système
        
    def mode_switch_changed(self, control_name, new_state):
        """Changement de position de l'interrupteur de mode"""
        self.log_action('MODE_SWITCH_CHANGED', f'Control: {control_name}, State: {new_state}')
        # Ajuster les paramètres selon le mode
        
    def read_intensity_dial(self):
        """Lire la position du potentiomètre d'intensité"""
        if self._intensity_adc is None:
            return self.system_state['intensity_level']
        try:
            value = self._intensity_adc.read_u16()
            self.system_state['intensity_level'] = value / 65535.0
        except Exception:
            self.system_state['intensity_level'] = 0
        return self.system_state['intensity_level']
    
    def get_system_status(self):
        """Obtenir l'état complet du système"""
        return {
            'state': self.system_state.copy(),
            'controls': {
                name: {
                    'type': 'switch' if isinstance(control, SwitchHandler) else 'button',
                    'state': control.state if hasattr(control, 'state') else 'unknown'
                }
                for name, control in self.controls.items()
                if hasattr(control, 'state')
            },
            'last_actions': self.action_log[-10:]  # 10 dernières actions
        }
    
    def reset_emergency(self):
        """Réinitialiser le mode d'urgence"""
        self.system_state['emergency_mode'] = False
        self.log_action('EMERGENCY_RESET')

    def update_once(self):
        """Mettre a jour les controles une seule fois (non bloquant)."""
        # Mettre à jour tous les contrôles
        for control_name, control in self.controls.items():
            if hasattr(control, 'update'):
                control.update()

        # Lire le potentiomètre d'intensité
        self.read_intensity_dial()
    
    async def update_loop(self):
        """Boucle de mise à jour principale"""
        while True:
            self.update_once()
            # Petite pause pour ne pas surcharger
            await asyncio.sleep(0.01)  # 10ms

# Configuration des pins pour différents types de boutons
class AuthenticControls:
    """Configuration des contrôles authentiques du Proton Pack"""
    
    # Pins GPIO du Raspberry Pi Pico
    PIN_CONFIG = {
        'main_power_switch': 9,      # Interrupteur principal (ON/OFF)
        'wand_trigger': 10,          # Gâchette de la baguette
        'wand_power_switch': 11,     # Interrupteur de puissance de la baguette
        'venting_button': 12,        # Bouton de ventilation
        'mode_selector': 13,         # Sélecteur de mode (positions multiples)
        'intensity_knob': 26,
        'emergency_stop': 15,        # Bouton d'arrêt d'urgence (rouge)
        'test_button': 16,           # Bouton de test
        'calibration_button': 17,    # Bouton de calibration
        'barrel_extend': 18,         # Déploiement du canon
        'barrel_retract': 19,        # Rétraction du canon
        'status_leds': {              # LEDs de statut
            'power': 20,
            'ready': 21,
            'warning': 22,
            'error': 26
        }
    }
    
    @classmethod
    def get_pin_config(cls):
        """Obtenir la configuration des pins"""
        return cls.PIN_CONFIG
    
    @classmethod
    def create_authentic_controls(cls):
        """Créer une instance avec la configuration authentique"""
        config = cls.get_pin_config()
        controls = ProtonPackControls()
        
        # Personnaliser la configuration pour correspondre à l'authentique
        for name, pin in config.items():
            if name != 'status_leds':
                print(f"Authentic control: {name} on pin {pin}")
        
        return controls
