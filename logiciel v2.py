import customtkinter as ctk
from tkinter import filedialog, Scrollbar
import numpy as np
import librosa
import sounddevice as sd
import time
import threading


class TimelineObject:
    def __init__(self, name):
        self.name = name
        self.keyframes = []


class TimelineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Animation avec Audio Sync")
        self.geometry("1100x700")

        self.objects = [
            TimelineObject("Objet 1"),
            TimelineObject("Objet 2"),
            TimelineObject("Objet 3"),
        ]

        self.audio_data = None
        self.sample_rate = 44100
        self.zoom_level = 1.0
        self.pixels_per_second = 100
        self.timelines = []

        self.is_playing = False
        self.play_thread = None
        self.play_start_time = 0

        self.create_widgets()

    def create_widgets(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(top_frame, text="Timeline Animation", font=("Arial", 18)).pack(side="left", padx=10)

        ctk.CTkButton(top_frame, text="Charger MP3", command=self.load_audio).pack(side="right", padx=8)
        ctk.CTkButton(top_frame, text="▶ Play", width=70, command=self.toggle_play).pack(side="right", padx=5)
        ctk.CTkButton(top_frame, text="+ Zoom", width=80, command=lambda: self.change_zoom(1.5)).pack(side="right", padx=3)
        ctk.CTkButton(top_frame, text="- Zoom", width=80, command=lambda: self.change_zoom(0.75)).pack(side="right", padx=3)

        self.timeline_frame = ctk.CTkFrame(self)
        self.timeline_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.scrollbar = Scrollbar(self.timeline_frame, orient="horizontal", command=self.sync_scroll)
        self.scrollbar.pack(side="bottom", fill="x")

        for obj in self.objects:
            canvas = self.create_object_timeline(obj)
            self.timelines.append(canvas)

        self.sound_canvas = self.create_sound_timeline()
        self.timelines.append(self.sound_canvas)

        for c in self.timelines:
            c.config(xscrollcommand=self.scrollbar.set)

    def create_object_timeline(self, obj):
        frame = ctk.CTkFrame(self.timeline_frame, height=40)
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=obj.name, width=100).pack(side="left")

        canvas = ctk.CTkCanvas(frame, bg="#222", height=30, scrollregion=(0, 0, 2000, 30))
        canvas.pack(side="left", fill="x", expand=True, padx=10)
        canvas.bind("<Button-1>", lambda e, o=obj, c=canvas: self.add_keyframe(o, c, e.x))
        return canvas

    def create_sound_timeline(self):
        frame = ctk.CTkFrame(self.timeline_frame, height=100)
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text="Bande Son", width=100).pack(side="left")

        canvas = ctk.CTkCanvas(frame, bg="#111", height=80, scrollregion=(0, 0, 2000, 80))
        canvas.pack(side="left", fill="x", expand=True, padx=10)
        return canvas

    def sync_scroll(self, *args):
        for canvas in self.timelines:
            canvas.xview(*args)

    def add_keyframe(self, obj, canvas, x):
        px = canvas.canvasx(x)
        if px not in obj.keyframes:
            obj.keyframes.append(px)
            obj.keyframes.sort()
        else:
            obj.keyframes.remove(px)
        self.redraw_keyframes(obj, canvas)

    def redraw_keyframes(self, obj, canvas):
        canvas.delete("all")
        for kf in obj.keyframes:
            canvas.create_oval(kf - 5, 10, kf + 5, 20, fill="cyan")

    def load_audio(self):
        filepath = filedialog.askopenfilename(filetypes=[("Fichiers audio", "*.mp3 *.wav *.flac")])
        if not filepath:
            return

        samples, sr = librosa.load(filepath, sr=None, mono=True)
        samples = samples / np.max(np.abs(samples))
        self.audio_data = samples
        self.sample_rate = sr
        self.draw_waveform()

    def draw_waveform(self):
        if self.audio_data is None:
            return

        c = self.sound_canvas
        c.delete("waveform")
        c.delete("cursor")

        duration = len(self.audio_data) / self.sample_rate
        width = int(duration * self.pixels_per_second * self.zoom_level)
        height = 80
        mid_y = height // 2
        c.config(scrollregion=(0, 0, width, height))

        samples_per_pixel = max(1, len(self.audio_data) // width)
        for px in range(width):
            start = px * samples_per_pixel
            end = min(len(self.audio_data), (px + 1) * samples_per_pixel)
            seg = self.audio_data[start:end]
            if len(seg) == 0:
                continue
            vmin = float(np.min(seg))
            vmax = float(np.max(seg))
            y1 = mid_y - int(vmax * 30)
            y2 = mid_y - int(vmin * 30)
            c.create_line(px, y1, px, y2, fill="#00ffff", tags="waveform")

        c.create_line(0, mid_y, width, mid_y, fill="#444", tags="waveform")

        for canvas in self.timelines:
            h = int(canvas["height"])
            canvas.config(scrollregion=(0, 0, width, h))

        # Curseur rouge initial
        c.create_line(0, 0, 0, 80, fill="red", width=2, tags="cursor")

    def change_zoom(self, factor):
        self.zoom_level *= factor
        self.zoom_level = max(0.3, min(self.zoom_level, 10))
        if self.audio_data is not None:
            self.draw_waveform()

    def toggle_play(self):
        if self.audio_data is None:
            return
        if not self.is_playing:
            self.is_playing = True
            self.play_thread = threading.Thread(target=self.play_audio)
            self.play_thread.start()
        else:
            self.is_playing = False
            sd.stop()

    def play_audio(self):
        self.play_start_time = time.time()
        sd.play(self.audio_data, self.sample_rate)
        duration = len(self.audio_data) / self.sample_rate

        width = int(duration * self.pixels_per_second * self.zoom_level)
        scroll_width = width - self.sound_canvas.winfo_width()

        while self.is_playing and sd.get_stream().active:
            elapsed = time.time() - self.play_start_time
            if elapsed > duration:
                break

            # Position du curseur (en pixels)
            x = int(elapsed * self.pixels_per_second * self.zoom_level)

            # Défilement horizontal (simule le mouvement)
            view_frac = x / width
            self.sound_canvas.xview_moveto(max(0, view_frac - 0.05))
            for canvas in self.timelines[:-1]:
                canvas.xview_moveto(max(0, view_frac - 0.05))

            # Déplacement du curseur rouge
            self.sound_canvas.delete("cursor")
            self.sound_canvas.create_line(x, 0, x, 80, fill="red", width=2, tags="cursor")

            time.sleep(0.02)

        self.is_playing = False
        sd.stop()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = TimelineApp()
    app.mainloop()
