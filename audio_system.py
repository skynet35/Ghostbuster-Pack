import uasyncio as asyncio
import struct
import time
import math
import urandom

class ProtonPackAudio:
    def __init__(self, i2s_instance):
        self.audio = i2s_instance
        self.sounds = {}
        self.current_sound = None
        self.volume = 0.7
        
        # Fréquences authentiques des sons
        self.sound_frequencies = {
            'startup': [440, 554, 659, 880],  # Do#, Fa, Mi, La
            'shutdown': [880, 659, 554, 440],
            'proton_stream': [1000, 1200, 800, 1500],
            'venting': [200, 150, 100, 50],
            'overheat': [300, 250, 200, 150],
            'cyclotron': [60, 120, 180, 240],
            'wand_activate': [1500, 1800, 2200],
            'error': [400, 300, 200, 100]
        }
        
    def generate_sine_wave(self, frequency, duration, amplitude=0.5, sample_rate=44100):
        """Génère une onde sinusoïdale"""
        samples = int(duration * sample_rate)
        wave = bytearray()
        
        for i in range(samples):
            value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            # Convertir en format I2S (16-bit, little-endian, signed)
            wave.extend(struct.pack('<hh', value, value))
        
        return bytes(wave)
    
    def generate_noise(self, duration, amplitude=0.3, sample_rate=44100):
        """Génère du bruit blanc pour effets spéciaux"""
        samples = int(duration * sample_rate)
        noise = bytearray()
        
        for i in range(samples):
            value = int(amplitude * 32767 * (urandom.getrandbits(16) - 32768) / 32768)
            noise.extend(struct.pack('<hh', value, value))
        
        return bytes(noise)
    
    def generate_proton_stream(self, duration=2.0):
        """Génère le son du flux proton authentique"""
        samples = int(duration * 44100)
        stream = bytearray()
        
        for i in range(samples):
            # Mélange de plusieurs fréquences pour créer le son caractéristique
            t = i / 44100
            
            # Fréquence principale variable
            freq1 = 1000 + 200 * math.sin(2 * math.pi * 3 * t)
            freq2 = 1200 + 150 * math.sin(2 * math.pi * 5 * t)
            freq3 = 800 + 100 * math.sin(2 * math.pi * 7 * t)
            
            # Génération des ondes
            value1 = 0.4 * math.sin(2 * math.pi * freq1 * t)
            value2 = 0.3 * math.sin(2 * math.pi * freq2 * t)
            value3 = 0.2 * math.sin(2 * math.pi * freq3 * t)
            
            # Ajout de bruit pour rendre plus réaliste
            noise = 0.1 * (urandom.getrandbits(16) - 32768) / 32768
            
            # Combinaison des valeurs
            final_value = int((value1 + value2 + value3 + noise) * 32767 * self.volume)
            
            # Limiter les valeurs
            final_value = max(-32768, min(32767, final_value))
            
            stream.extend(struct.pack('<hh', final_value, final_value))
        
        return bytes(stream)
    
    def generate_startup_sound(self):
        """Son de démarrage progressif"""
        duration = 3.0
        samples = int(duration * 44100)
        startup = bytearray()
        
        for i in range(samples):
            t = i / 44100
            
            # Progression ascendante d'accords
            if t < 0.75:
                freq = 440 * (1 + t * 0.5)
            elif t < 1.5:
                freq = 554 * (1 + (t - 0.75) * 0.3)
            elif t < 2.25:
                freq = 659 * (1 + (t - 1.5) * 0.2)
            else:
                freq = 880
            
            # Enveloppe d'amplitude
            if t < 2.5:
                amplitude = self.volume * (t / 2.5)
            else:
                amplitude = self.volume * (1 - (t - 2.5) / 0.5)
            
            value = int(amplitude * 32767 * math.sin(2 * math.pi * freq * t))
            startup.extend(struct.pack('<hh', value, value))
        
        return bytes(startup)
    
    def generate_cyclotron_sound(self, speed=1.0):
        """Son du cyclotron avec rotation"""
        duration = 4.0
        samples = int(duration * 44100)
        cyclotron = bytearray()
        
        for i in range(samples):
            t = i / 44100
            
            # Fréquence de base qui augmente avec la vitesse
            base_freq = 60 * speed
            
            # Effet de rotation avec harmoniques
            rotation = math.sin(2 * math.pi * 0.5 * t * speed)
            freq1 = base_freq * (1 + 0.2 * rotation)
            freq2 = base_freq * 2 * (1 + 0.15 * rotation)
            freq3 = base_freq * 3 * (1 + 0.1 * rotation)
            
            # Génération des ondes
            value1 = 0.5 * math.sin(2 * math.pi * freq1 * t)
            value2 = 0.3 * math.sin(2 * math.pi * freq2 * t)
            value3 = 0.2 * math.sin(2 * math.pi * freq3 * t)
            
            final_value = int((value1 + value2 + value3) * 32767 * self.volume * 0.6)
            cyclotron.extend(struct.pack('<hh', final_value, final_value))
        
        return bytes(cyclotron)
    
    def generate_venting_sound(self):
        """Son de ventilation (venting)"""
        duration = 5.0
        samples = int(duration * 44100)
        venting = bytearray()
        
        for i in range(samples):
            t = i / 44100
            
            # Descente de fréquence progressive
            start_freq = 400
            end_freq = 50
            freq = start_freq - (start_freq - end_freq) * (t / duration)
            
            # Bruit de soufflement avec modulation
            noise = (urandom.getrandbits(16) - 32768) / 32768
            modulation = 0.5 + 0.5 * math.sin(2 * math.pi * 2 * t)
            
            value = int(noise * 32767 * self.volume * modulation * (1 - t / duration))
            venting.extend(struct.pack('<hh', value, value))
        
        return bytes(venting)
    
    def generate_overheat_warning(self):
        """Avertissement de surchauffe"""
        duration = 2.0
        samples = int(duration * 44100)
        warning = bytearray()
        
        for i in range(samples):
            t = i / 44100
            
            # Bips d'alarme alternés
            if int(t * 4) % 2 == 0:
                freq = 800
            else:
                freq = 600
            
            # Modulation pour créer un son d'alarme
            amplitude = self.volume * (0.5 + 0.5 * math.sin(2 * math.pi * 8 * t))
            value = int(amplitude * 32767 * math.sin(2 * math.pi * freq * t))
            warning.extend(struct.pack('<hh', value, value))
        
        return bytes(warning)
    
    async def play_sound_async(self, sound_name, loop=False):
        """Jouer un son de manière asynchrone"""
        try:
            # Générer le son approprié
            if sound_name == 'startup':
                audio_data = self.generate_startup_sound()
            elif sound_name == 'proton_stream':
                audio_data = self.generate_proton_stream()
            elif sound_name == 'cyclotron':
                audio_data = self.generate_cyclotron_sound()
            elif sound_name == 'venting':
                audio_data = self.generate_venting_sound()
            elif sound_name == 'overheat':
                audio_data = self.generate_overheat_warning()
            else:
                # Son par défaut
                audio_data = self.generate_sine_wave(440, 1.0)
            
            # Jouer le son
            if loop:
                while True:
                    self.audio.write(audio_data)
                    await asyncio.sleep(0.01)
            else:
                self.audio.write(audio_data)
                
        except Exception as e:
            print(f"Erreur audio: {e}")
    
    def set_volume(self, volume):
        """Régler le volume (0.0 à 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
    
    def stop_all_sounds(self):
        """Arrêter tous les sons"""
        # Jouer un silence
        silence = bytes(2000)
        self.audio.write(silence)

class SoundManager:
    def __init__(self, audio_system):
        self.audio = audio_system
        self.active_tasks = {}
        self.sound_queue = []
        
    async def play_sound(self, sound_name, priority=1, loop=False):
        """Gestionnaire de sons avec priorité"""
        # Arrêter les sons de plus faible priorité
        for task_name in list(self.active_tasks.keys()):
            if self.active_tasks[task_name]['priority'] < priority:
                self.stop_sound(task_name)
        
        # Démarrer le nouveau son
        task = asyncio.create_task(
            self.audio.play_sound_async(sound_name, loop)
        )
        
        self.active_tasks[sound_name] = {
            'task': task,
            'priority': priority,
            'loop': loop
        }
    
    def stop_sound(self, sound_name):
        """Arrêter un son spécifique"""
        if sound_name in self.active_tasks:
            self.active_tasks[sound_name]['task'].cancel()
            del self.active_tasks[sound_name]
    
    def stop_all_sounds(self):
        """Arrêter tous les sons"""
        for task_info in self.active_tasks.values():
            task_info['task'].cancel()
        self.active_tasks.clear()
        self.audio.stop_all_sounds()
    
    async def background_loop(self):
        """Boucle de fond pour gérer les sons"""
        while True:
            # Jouer le son du cyclotron en continu si nécessaire
            if 'cyclotron' not in self.active_tasks:
                await self.play_sound('cyclotron', priority=0, loop=True)
            
            await asyncio.sleep(1.0)