import numpy as np
import librosa
import matplotlib.pyplot as plt

# Paramètres
audio_file = "Blues.mp3"
pixels = 1500  # largeur écran approx

# Chargement optimisé (mono + float32)
signal, sr = librosa.load(audio_file, sr=None, mono=True, dtype=np.float32)

# Décimation intelligente (min/max)
samples_per_pixel = max(1, len(signal) // pixels)

signal = signal[:samples_per_pixel * pixels]
signal_reshaped = signal.reshape(pixels, samples_per_pixel)

min_vals = signal_reshaped.min(axis=1)
max_vals = signal_reshaped.max(axis=1)

# Axe du temps
times = np.linspace(0, len(signal) / sr, pixels)

# Plot
plt.figure(figsize=(14, 4))
plt.fill_between(times, min_vals, max_vals, color="steelblue")
plt.title("Waveform optimisée (rapide)")
plt.xlabel("Temps (secondes)")
plt.ylabel("Amplitude")
plt.tight_layout()
plt.show()
