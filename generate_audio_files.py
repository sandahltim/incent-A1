#!/usr/bin/env python3
"""
generate_audio_files.py
Professional Audio File Generator for Vegas Casino Application
Creates all missing audio files using numpy and scipy for audio synthesis
"""

import os
import json
import numpy as np
from scipy.io.wavfile import write
from scipy import signal
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CasinoAudioGenerator:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.audio_dir = Path(__file__).parent / "static" / "audio"
        self.manifest_path = self.audio_dir / "audio-manifest.json"
        
        # Ensure audio directory exists
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Load manifest
        self.manifest = self.load_manifest()
    
    def load_manifest(self):
        """Load the audio manifest file"""
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return None
    
    def generate_sine_wave(self, frequency, duration, volume=0.3, envelope='adsr', modulation=None):
        """Generate a sine wave with optional envelope and modulation"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Apply modulation if specified
        if modulation:
            mod_signal = np.sin(2 * np.pi * modulation['frequency'] * t)
            frequency = frequency + modulation['depth'] * mod_signal
        
        # Generate sine wave
        wave = np.sin(2 * np.pi * frequency * t)
        
        # Apply envelope
        if envelope == 'adsr':
            wave = self.apply_adsr(wave, attack=0.01, decay=0.1, sustain=0.7, release=0.3)
        elif envelope == 'exponential':
            wave = wave * np.exp(-t * 5)
        
        return wave * volume
    
    def generate_noise(self, duration, noise_type='white', volume=0.2):
        """Generate different types of noise"""
        samples = int(self.sample_rate * duration)
        
        if noise_type == 'white':
            noise = np.random.normal(0, 1, samples)
        elif noise_type == 'pink':
            # Generate pink noise using Voss-McCartney algorithm
            noise = self.generate_pink_noise(samples)
        elif noise_type == 'brown':
            # Brown noise (red noise)
            white = np.random.normal(0, 1, samples)
            noise = np.cumsum(white)
            noise = noise / np.max(np.abs(noise))  # Normalize
        else:
            noise = np.random.normal(0, 1, samples)
        
        return noise * volume
    
    def generate_pink_noise(self, samples):
        """Generate pink noise using the Voss-McCartney algorithm"""
        # Number of random sources
        num_sources = 12
        
        # Create array to hold the pink noise
        pink = np.zeros(samples)
        
        # Random sources
        sources = np.random.randn(num_sources, samples)
        
        # Generate pink noise
        for i in range(num_sources):
            # Each source is updated at a different rate
            update_rate = 2 ** i
            for j in range(0, samples, update_rate):
                end_idx = min(j + update_rate, samples)
                pink[j:end_idx] += sources[i, j]
        
        # Normalize
        pink = pink / np.max(np.abs(pink))
        return pink
    
    def apply_adsr(self, wave, attack=0.01, decay=0.1, sustain=0.7, release=0.3):
        """Apply ADSR envelope to a wave"""
        length = len(wave)
        envelope = np.ones(length)
        
        # Attack
        attack_samples = int(attack * length)
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay
        decay_samples = int(decay * length)
        if decay_samples > 0:
            decay_end = attack_samples + decay_samples
            if decay_end < length:
                envelope[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)
        
        # Release
        release_samples = int(release * length)
        if release_samples > 0:
            release_start = length - release_samples
            if release_start > 0:
                envelope[release_start:] = np.linspace(sustain, 0, release_samples)
        
        return wave * envelope
    
    def generate_ui_sounds(self):
        """Generate UI interaction sounds"""
        sounds = {
            'ui-hover.mp3': self.generate_sine_wave(800, 0.1, 0.2, 'exponential'),
            'ui-disabled.mp3': self.generate_sine_wave(200, 0.15, 0.2, 'exponential'),
            'modal-open.mp3': self.generate_chord([440, 554, 659], 0.3, 0.3),
            'modal-close.mp3': self.generate_chord([659, 554, 440], 0.2, 0.25),
            'tab-switch.mp3': self.generate_sine_wave(523, 0.15, 0.25, 'adsr')
        }
        return sounds
    
    def generate_slot_sounds(self):
        """Generate slot machine sounds"""
        sounds = {
            'slot-lever-pull.mp3': self.generate_mechanical_sound(0.8),
            'slot-reel-start.mp3': self.generate_sine_wave(110, 0.5, 0.4, modulation={'frequency': 2, 'depth': 10}),
            'slot-reel-stop-1.mp3': self.generate_mechanical_click(0.3),
            'slot-reel-stop-2.mp3': self.generate_mechanical_click(0.3),
            'slot-reel-stop-3.mp3': self.generate_mechanical_click(0.3),
            'slot-near-miss.mp3': self.generate_tension_sound(0.5)
        }
        return sounds
    
    def generate_scratch_sounds(self):
        """Generate scratch card sounds"""
        sounds = {
            'scratch-start.mp3': self.generate_noise(0.2, 'pink', 0.3),
            'scratch-loop.mp3': self.generate_noise(0.5, 'pink', 0.2),
            'scratch-reveal.mp3': self.generate_sine_wave(880, 0.4, 0.4, 'adsr'),
            'scratch-complete.mp3': self.generate_win_sound('small')
        }
        return sounds
    
    def generate_roulette_sounds(self):
        """Generate roulette sounds"""
        sounds = {
            'roulette-spin.mp3': self.generate_noise(2.0, 'brown', 0.15),
            'roulette-ball-roll.mp3': self.generate_sine_wave(400, 1.0, 0.3, modulation={'frequency': 8, 'depth': 50}),
            'roulette-ball-bounce.mp3': self.generate_bounce_sound(0.8),
            'roulette-ball-drop.mp3': self.generate_sine_wave(200, 0.4, 0.4, 'adsr'),
            'roulette-click.mp3': self.generate_sine_wave(800, 0.1, 0.2, 'exponential')
        }
        return sounds
    
    def generate_wheel_sounds(self):
        """Generate wheel of fortune sounds"""
        sounds = {
            'wheel-start.mp3': self.generate_sine_wave(150, 0.5, 0.4, 'adsr'),
            'wheel-spin.mp3': self.generate_noise(1.0, 'pink', 0.15),
            'wheel-tick.mp3': self.generate_sine_wave(600, 0.05, 0.3, 'exponential'),
            'wheel-slowdown.mp3': self.generate_slowdown_sound(2.0),
            'wheel-stop.mp3': self.generate_sine_wave(300, 0.5, 0.5, 'adsr')
        }
        return sounds
    
    def generate_dice_sounds(self):
        """Generate dice sounds"""
        sounds = {
            'dice-shake.mp3': self.generate_dice_shake(0.8),
            'dice-throw.mp3': self.generate_noise(0.4, 'pink', 0.25),
            'dice-roll-1.mp3': self.generate_dice_roll(0.6),
            'dice-roll-2.mp3': self.generate_dice_roll(0.7),
            'dice-land.mp3': self.generate_sine_wave(300, 0.2, 0.3, 'exponential'),
            'dice-settle.mp3': self.generate_sine_wave(200, 0.3, 0.25, 'adsr')
        }
        return sounds
    
    def generate_win_sounds(self):
        """Generate progressive win sounds"""
        sounds = {
            'win-tiny.mp3': self.generate_win_sound('tiny'),
            'win-small.mp3': self.generate_win_sound('small'),
            'win-medium.mp3': self.generate_win_sound('medium'),
            'win-big.mp3': self.generate_win_sound('big'),
            'win-huge.mp3': self.generate_win_sound('huge'),
            'win-mega.mp3': self.generate_win_sound('mega')
        }
        return sounds
    
    def generate_coin_sounds(self):
        """Generate coin and money sounds"""
        sounds = {
            'coin-single.mp3': self.generate_coin_drop(0.2),
            'coin-shower.mp3': self.generate_coin_shower(1.5),
            'coin-cascade.mp3': self.generate_coin_cascade(2.5),
            'cash-register.mp3': self.generate_sine_wave(523, 0.6, 0.4, 'adsr')
        }
        return sounds
    
    def generate_celebration_sounds(self):
        """Generate celebration sounds"""
        sounds = {
            'fanfare-1.mp3': self.generate_fanfare(1.0, 'short'),
            'fanfare-2.mp3': self.generate_fanfare(1.5, 'medium'),
            'fanfare-3.mp3': self.generate_fanfare(2.0, 'long'),
            'applause.mp3': self.generate_applause(3.0),
            'cheer.mp3': self.generate_noise(2.5, 'white', 0.25),
            'airhorn.mp3': self.generate_sine_wave(200, 1.0, 0.4, 'adsr')
        }
        return sounds
    
    def generate_ambient_sounds(self):
        """Generate ambient casino sounds"""
        sounds = {
            'casino-ambient-1.mp3': self.generate_noise(5.0, 'pink', 0.1),
            'casino-ambient-2.mp3': self.generate_noise(5.0, 'brown', 0.1),
            'slot-machines-bg.mp3': self.generate_ambient_slots(5.0),
            'crowd-murmur.mp3': self.generate_noise(5.0, 'brown', 0.05)
        }
        return sounds
    
    def generate_notification_sounds(self):
        """Generate notification sounds"""
        sounds = {
            'notification-success.mp3': self.generate_sine_wave(660, 0.4, 0.4, 'adsr'),
            'notification-error.mp3': self.generate_sine_wave(220, 0.3, 0.3, 'adsr'),
            'notification-warning.mp3': self.generate_sine_wave(440, 0.35, 0.35, modulation={'frequency': 3, 'depth': 20}),
            'notification-info.mp3': self.generate_sine_wave(523, 0.25, 0.3, 'adsr')
        }
        return sounds
    
    def generate_transition_sounds(self):
        """Generate transition sounds"""
        sounds = {
            'swoosh-in.mp3': self.generate_swoosh(0.3, 'in'),
            'swoosh-out.mp3': self.generate_swoosh(0.3, 'out'),
            'slide-in.mp3': self.generate_sine_wave(330, 0.4, 0.3, 'adsr'),
            'slide-out.mp3': self.generate_sine_wave(220, 0.4, 0.3, 'adsr'),
            'fade-transition.mp3': self.generate_sine_wave(440, 0.5, 0.25, 'adsr')
        }
        return sounds
    
    # Helper methods for complex sounds
    def generate_chord(self, frequencies, duration, volume):
        """Generate a chord from multiple frequencies"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        chord = np.zeros_like(t)
        
        for freq in frequencies:
            chord += np.sin(2 * np.pi * freq * t)
        
        chord = chord / len(frequencies)  # Normalize
        chord = self.apply_adsr(chord)
        return chord * volume
    
    def generate_mechanical_sound(self, duration):
        """Generate mechanical lever pull sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sound = np.zeros_like(t)
        
        # Initial click
        click_duration = 0.1
        click_samples = int(click_duration * self.sample_rate)
        click_env = np.exp(-np.linspace(0, 10, click_samples))
        click_noise = np.random.normal(0, 1, click_samples) * click_env * 0.3
        click_tone = np.sin(2 * np.pi * 150 * np.linspace(0, click_duration, click_samples)) * click_env * 0.2
        sound[:click_samples] = click_noise + click_tone
        
        # Spring sound
        if duration > 0.1:
            spring_start = int(0.1 * self.sample_rate)
            spring_end = int(0.6 * self.sample_rate) if duration > 0.6 else len(sound)
            spring_t = t[spring_start:spring_end] - 0.1
            spring_freq = 80 + 40 * np.sin(2 * np.pi * 3 * spring_t)
            spring_env = np.exp(-spring_t * 3)
            spring_sound = np.sin(2 * np.pi * spring_freq * spring_t) * spring_env * 0.25
            sound[spring_start:spring_end] = spring_sound
        
        return sound
    
    def generate_mechanical_click(self, duration):
        """Generate mechanical click sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        envelope = np.exp(-t * 12)
        
        noise = np.random.normal(0, 1, len(t)) * envelope * 0.3
        tone1 = np.sin(2 * np.pi * 200 * t) * envelope * 0.15
        tone2 = np.sin(2 * np.pi * 400 * t) * envelope * 0.1
        
        return noise + tone1 + tone2
    
    def generate_tension_sound(self, duration):
        """Generate near-miss tension sound"""
        return self.generate_sine_wave(220, duration, 0.3, modulation={'frequency': 0.5, 'depth': 20})
    
    def generate_bounce_sound(self, duration):
        """Generate ball bouncing sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sound = np.zeros_like(t)
        
        # Create multiple bounces with decreasing amplitude
        bounce_times = np.array([0.0, 0.15, 0.28, 0.38, 0.46, 0.52, 0.57, 0.61])
        bounce_times = bounce_times[bounce_times < duration]
        
        for i, bounce_time in enumerate(bounce_times):
            bounce_idx = int(bounce_time * self.sample_rate)
            bounce_duration = min(0.1, duration - bounce_time)
            bounce_samples = int(bounce_duration * self.sample_rate)
            
            if bounce_idx + bounce_samples <= len(sound):
                amplitude = 0.4 * np.exp(-i * 0.5)  # Decreasing amplitude
                bounce_t = np.linspace(0, bounce_duration, bounce_samples)
                bounce_env = np.exp(-bounce_t * 15)
                bounce_freq = 300 + np.random.normal(0, 50)
                bounce = np.sin(2 * np.pi * bounce_freq * bounce_t) * bounce_env * amplitude
                sound[bounce_idx:bounce_idx + bounce_samples] += bounce
        
        return sound
    
    def generate_slowdown_sound(self, duration):
        """Generate wheel slowing down sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Frequency decreases over time
        freq_start = 20
        freq_end = 5
        frequency = freq_start * np.exp(-t / (duration / 3))
        
        # Generate the sound
        phase = 2 * np.pi * np.cumsum(frequency) / self.sample_rate
        sound = np.sin(phase) * 0.15
        
        return sound
    
    def generate_dice_shake(self, duration):
        """Generate dice shaking sound"""
        return self.generate_noise(duration, 'white', 0.2)
    
    def generate_dice_roll(self, duration):
        """Generate dice rolling sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sound = np.zeros_like(t)
        
        # Random impacts for dice bouncing
        for i in range(len(t)):
            if np.random.random() < (8 * (1 - t[i] / duration) / self.sample_rate) * 100:
                impact_duration = min(0.05, duration - t[i])
                impact_samples = int(impact_duration * self.sample_rate)
                
                if i + impact_samples <= len(sound):
                    impact_t = np.linspace(0, impact_duration, impact_samples)
                    impact_env = np.exp(-impact_t * 20)
                    impact_freq = 300 + np.random.normal(0, 200)
                    impact = np.sin(2 * np.pi * impact_freq * impact_t) * impact_env * 0.4
                    sound[i:i + impact_samples] += impact
        
        # General rolling sound
        roll_env = 1 - (t / duration) ** 2
        roll_noise = np.random.normal(0, 1, len(t)) * roll_env * 0.1
        sound += roll_noise
        
        return sound
    
    def generate_win_sound(self, tier):
        """Generate win sounds of different tiers"""
        durations = {'tiny': 0.3, 'small': 0.5, 'medium': 0.8, 'big': 1.2, 'huge': 1.5, 'mega': 2.0}
        duration = durations.get(tier, 0.5)
        
        # Arpeggio notes (C major)
        notes = [261.63, 329.63, 392.00, 523.25, 659.25]
        note_duration = duration / len(notes)
        
        sound = np.array([])
        
        for i, freq in enumerate(notes):
            t = np.linspace(0, note_duration, int(self.sample_rate * note_duration), False)
            note = np.sin(2 * np.pi * freq * t)
            note = self.apply_adsr(note, attack=0.1, decay=0.1, sustain=0.8, release=0.1)
            
            # Add harmonics for richer sound
            if tier in ['big', 'huge', 'mega']:
                note += 0.3 * np.sin(2 * np.pi * freq * 2 * t)  # Octave
                note += 0.2 * np.sin(2 * np.pi * freq * 1.5 * t)  # Fifth
            
            sound = np.concatenate([sound, note * 0.4])
        
        return sound
    
    def generate_coin_drop(self, duration):
        """Generate single coin drop sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        envelope = np.exp(-t * 8)
        
        # Metallic frequencies
        freq = 800 + 400 * np.exp(-t * 20)
        sound = np.sin(2 * np.pi * freq * t) * envelope * 0.4
        
        # Add metallic ring
        sound += np.sin(2 * np.pi * (freq * 1.5) * t) * envelope * 0.2
        
        return sound
    
    def generate_coin_shower(self, duration):
        """Generate multiple coins falling"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sound = np.zeros_like(t)
        
        # Random coin drops throughout duration
        for i in range(len(t)):
            if np.random.random() < (30 / self.sample_rate):
                coin_duration = min(0.2, duration - t[i])
                coin_samples = int(coin_duration * self.sample_rate)
                
                if i + coin_samples <= len(sound):
                    coin_t = np.linspace(0, coin_duration, coin_samples)
                    freq = 600 + np.random.normal(0, 200)
                    coin_env = np.exp(-coin_t * 10)
                    coin = np.sin(2 * np.pi * freq * coin_t) * coin_env * 0.2
                    sound[i:i + coin_samples] += coin
        
        return sound
    
    def generate_coin_cascade(self, duration):
        """Generate massive coin waterfall"""
        return self.generate_coin_shower(duration) * 2  # Louder and denser
    
    def generate_fanfare(self, duration, style):
        """Generate fanfare sounds"""
        if style == 'short':
            return self.generate_chord([523, 659, 784], duration, 0.4)
        elif style == 'medium':
            return self.generate_chord([440, 523, 659, 784], duration, 0.4)
        else:  # long
            return self.generate_chord([349, 440, 523, 659, 784], duration, 0.5)
    
    def generate_applause(self, duration):
        """Generate applause sound"""
        return self.generate_noise(duration, 'pink', 0.2)
    
    def generate_ambient_slots(self, duration):
        """Generate ambient slot machine sounds"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        sound = self.generate_noise(duration, 'pink', 0.05)
        
        # Add occasional slot machine sounds
        for i in range(0, len(t), int(self.sample_rate * 0.5)):
            if np.random.random() < 0.3 and i < len(sound) - 1000:
                slot_freq = 50 + np.random.normal(0, 10)
                slot_duration = min(0.3, (len(sound) - i) / self.sample_rate)
                slot_samples = int(slot_duration * self.sample_rate)
                slot_t = np.linspace(0, slot_duration, slot_samples)
                slot_sound = np.sin(2 * np.pi * slot_freq * slot_t) * 0.02
                sound[i:i + slot_samples] += slot_sound
        
        return sound
    
    def generate_swoosh(self, duration, direction):
        """Generate swoosh sound"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        if direction == 'in':
            freq = 200 + 800 * (t / duration)  # Rising frequency
        else:
            freq = 1000 - 800 * (t / duration)  # Falling frequency
        
        # Generate swept sine
        phase = 2 * np.pi * np.cumsum(freq) / self.sample_rate
        sound = np.sin(phase) * 0.15
        
        # Apply envelope
        envelope = np.sin(np.pi * t / duration)  # Bell curve
        sound *= envelope
        
        return sound
    
    def save_audio(self, sound, filename):
        """Save audio to file"""
        # Convert to 16-bit integers
        if np.max(np.abs(sound)) > 0:
            sound = sound / np.max(np.abs(sound))  # Normalize
        
        sound_int = (sound * 32767).astype(np.int16)
        
        # Convert to stereo
        stereo_sound = np.column_stack((sound_int, sound_int))
        
        filepath = self.audio_dir / filename
        write(str(filepath), self.sample_rate, stereo_sound)
        logger.info(f"Generated: {filename}")
    
    def generate_all_missing_sounds(self):
        """Generate all missing sound files"""
        if not self.manifest:
            logger.error("No manifest loaded, cannot generate sounds")
            return
        
        # Get all sound generators
        generators = {
            **self.generate_ui_sounds(),
            **self.generate_slot_sounds(),
            **self.generate_scratch_sounds(),
            **self.generate_roulette_sounds(),
            **self.generate_wheel_sounds(),
            **self.generate_dice_sounds(),
            **self.generate_win_sounds(),
            **self.generate_coin_sounds(),
            **self.generate_celebration_sounds(),
            **self.generate_ambient_sounds(),
            **self.generate_notification_sounds(),
            **self.generate_transition_sounds()
        }
        
        # Check which files are missing and generate them
        categories = self.manifest['audio_manifest']['categories']
        generated_count = 0
        
        for category_name, category in categories.items():
            for sound in category['sounds']:
                filename = sound['file']
                filepath = self.audio_dir / filename
                
                # Skip if file already exists (unless force flag is set)
                if filepath.exists() and not getattr(self, 'force_regenerate', False):
                    logger.info(f"Skipping existing file: {filename}")
                    continue
                
                # Generate and save the sound
                if filename in generators:
                    try:
                        audio_data = generators[filename]
                        self.save_audio(audio_data, filename)
                        generated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate {filename}: {e}")
                else:
                    logger.warning(f"No generator found for: {filename}")
        
        logger.info(f"Successfully generated {generated_count} audio files")
        return generated_count

def main():
    parser = argparse.ArgumentParser(description='Generate casino audio files')
    parser.add_argument('--force', action='store_true', 
                       help='Force regeneration of existing files')
    parser.add_argument('--list', action='store_true',
                       help='List all audio files that would be generated')
    
    args = parser.parse_args()
    
    generator = CasinoAudioGenerator()
    
    if args.force:
        generator.force_regenerate = True
    
    if args.list:
        # List all files from manifest
        if generator.manifest:
            categories = generator.manifest['audio_manifest']['categories']
            print("\nAudio files to be generated:")
            for category_name, category in categories.items():
                print(f"\n{category_name.upper()}: {category['description']}")
                for sound in category['sounds']:
                    status = "EXISTS" if (generator.audio_dir / sound['file']).exists() else "MISSING"
                    print(f"  - {sound['file']} ({status})")
        return
    
    # Generate all missing sounds
    try:
        count = generator.generate_all_missing_sounds()
        print(f"\n✅ Audio generation complete! Generated {count} files.")
        print(f"Audio files saved to: {generator.audio_dir}")
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())