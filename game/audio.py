import numpy as np
import pygame

def make_sine_sound(freq=440, duration=0.12, volume=0.2, sample_rate=44100):
    """Generate a pygame Sound with a sine wave tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = 0.5 * np.sin(2 * np.pi * freq * t)
    # Apply quick envelope
    env = np.ones_like(wave)
    env[:int(0.01 * sample_rate)] = np.linspace(0, 1, int(0.01 * sample_rate))
    env[-int(0.03 * sample_rate):] = np.linspace(1, 0, int(0.03 * sample_rate))
    wave = wave * env
    wave = (wave * (2**15 - 1)).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)

def make_bass_loop(sample_rate=44100):
    """Create a looping ambient bass pad (short looping clip)."""
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # layered low-frequency sine waves and subtle noise
    wave = 0.3 * np.sin(2 * np.pi * 55 * t) + 0.15 * np.sin(2 * np.pi * 110 * t * (1 + 0.02*np.sin(2*np.pi*0.2*t)))
    # gentle amplitude LFO
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * t)
    wave = wave * lfo
    wave = (wave * (2**15 - 1) * 0.6).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)
