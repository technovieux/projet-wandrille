"""
composition_editor.py
Preuve de concept d'un éditeur de composition en 4 quadrants avec CustomTkinter.

Prérequis:
    pip install customtkinter pillow matplotlib numpy
    pip install pydub     # optionnel pour MP3 (pydub nécessite ffmpeg installé séparément)
"""

import os
import sys
import math
import wave
import random
import bisect
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import time
import threading

# Librosa for optimized audio loading
try:
    import librosa
    LibrosaAvailable = True
except Exception:
    LibrosaAvailable = False

# Optional audio lib for MP3
try:
    from pydub import AudioSegment
    PydubAvailable = True
except Exception:
    PydubAvailable = False

# Audio playback library
try:
    import simpleaudio as sa
    SimpleaudioAvailable = True
except Exception:
    SimpleaudioAvailable = False


# --- Animation mode: True = interpolation, False = téléportation ---
animate = False

WINDOW_SIZE = (1200, 800)

actual_color_theme = "light"

ctk.set_appearance_mode(actual_color_theme)  # Modes: "system" (standard), "dark", "light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"






class Layer:
    def __init__(self, name, x_rel=0.1, y_rel=0.1, w_rel=0.2, h_rel=0.2, color="#ff0000", opacity=100, rotation=0, shape_type="rectangle"):
        """
        Coordinates relative to background image: values between 0 and 1.
        """
        self.name = name
        self.x = x_rel
        self.y = y_rel
        self.w = w_rel
        self.h = h_rel
        self.color = color
        self.opacity = opacity  # 0..100
        self.rotation = rotation  # in degrees
        self.shape_type = shape_type




class Keyframe:
    def __init__(self, time, x, y, w, h, color, opacity, rotation=0, shape_type="rectangle"):
        self.time = time
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.opacity = opacity
        self.rotation = rotation
        self.shape_type = shape_type








class export_Window(ctk.CTkToplevel):
    """Fenêtre de dialogue qui s'ouvre lors de l'action Ctrl+S."""
    def __init__(self, master=None):
        super().__init__(master=master)
        
        # Configuration de la fenêtre Toplevel
        self.title("Options de Sauvegarde")
        self.geometry("300x200")
        # Rendre cette fenêtre modale (bloque les interactions avec la fenêtre principale)
        self.grab_set() 

        # --- Contenu de la Fenêtre ---
        
        ctk.CTkLabel(self, text="Sélectionnez un format :").pack(pady=20, padx=20)
        
        # Menu Déroulant (CTkOptionMenu)
        options = ["Projet (.editor)", "Vidéo (.mp4)", "Image (.png)"]
        self.format_var = ctk.StringVar(value=options[0]) # Valeur par défaut
        
        dropdown = ctk.CTkOptionMenu(
            self, 
            values=options,
            variable=self.format_var,
        )
        dropdown.pack(pady=10)
        
        ctk.CTkButton(self, text="Sauvegarder et Fermer", command=self.close_window).pack(pady=20)

    def option_selected(self, choice):
        """Action lorsque l'option du menu déroulant est sélectionnée."""
        print(f"Format de sauvegarde choisi : {choice}")

    def close_window(self):
        print(f"Format de sauvegarde choisi : {self.format_var.get()}")

        """Ferme la fenêtre de dialogue et libère la fenêtre principale."""
        # Libérer le focus de la fenêtre principale
        self.grab_release()
        self.destroy()








class CompositionApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.root.title("Composition Editor")
        
        self.bg_image = None
        self.bg_orig_size = (1280, 720)
        
        self.layers = []
        self.keyframes = []  # Liste de liste : une liste de keyframes par layer
        self.selected_index = None
        self.selected_keyframes = set()  # Set des tuples (layer_idx, kf_idx) sélectionnés
        
        self.scene_keyframes = []  # Liste des keyframes de scène

        # Track last selected object for deletion
        self.last_selected_type = None  # 'layer' or 'keyframe'
        self.last_selected_object = None  # layer_idx or (layer_idx, kf_idx)
        
        # Variables de lecture
        self.playback_time = 0.0
        self.is_playing = False
        self.playback_job = None
        
        # Variables de drag & drop des keyframes
        self._keyframe_drag = {
            'dragging': False,
            'start_x': 0,
            'start_time': 0.0,
            'selected': set()
        }
        
        self.setup_ui()
        self.prompt_load_background()
        self.create_sample_layers()

    # --- Manipulation souris sur le rendu ---
    def _init_render_interaction(self):
        self._drag_mode = None  # 'move', 'resize', 'rotate', None
        self._drag_start = None
        self._drag_layer_idx = None
        self._drag_orig = None
        self._resize_corner = None
        self.render_canvas.bind('<Button-1>', self._on_render_mouse_down)
        self.render_canvas.bind('<B1-Motion>', self._on_render_mouse_drag)
        self.render_canvas.bind('<ButtonRelease-1>', self._on_render_mouse_up)

    def _get_handle_under_mouse(self, x, y):
        idx = self.selected_index
        if idx is None:
            return None, None
        bx, by, draw_w, draw_h, _ = self._render_geometry()
        state = self._compute_layer_state_at_time(idx, self.get_playback_time())
        w = state['w'] * draw_w
        h = state['h'] * draw_h
        angle = state.get('rotation', 0)
        cx = bx + state['x'] * draw_w + w/2
        cy = by + state['y'] * draw_h + h/2
        from math import cos, sin, radians, hypot
        rot = radians(angle)
        cos_a = cos(rot)
        sin_a = sin(rot)
        # Corners
        corners = [
            ('nw', (-w/2, -h/2)),
            ('ne', (w/2, -h/2)),
            ('se', (w/2, h/2)),
            ('sw', (-w/2, h/2))
        ]
        handle_size = 12
        for name, (px, py) in corners:
            rx = px * cos_a - py * sin_a + cx
            ry = px * sin_a + py * cos_a + cy
            if abs(x - rx) <= handle_size and abs(y - ry) <= handle_size:
                return 'resize', name
        # Rotation handle
        rot_px, rot_py = 0, -h/2 - 30
        rot_x = rot_px * cos_a - rot_py * sin_a + cx
        rot_y = rot_px * sin_a + rot_py * cos_a + cy
        if hypot(x - rot_x, y - rot_y) <= 16:
            return 'rotate', None
        return None, None

    def _on_render_mouse_down(self, event):
        # Sélectionne d'abord la forme cliquée (même si une autre est sélectionnée)
        x, y = event.x, event.y
        bx, by, draw_w, draw_h, scale = self._render_geometry()
        found = None
        for idx in range(len(self.layers)-1, -1, -1):
            # Utiliser l'état direct si pas en lecture, sinon keyframe/interpolé
            if not self.is_playing and idx == self.selected_index:
                L = self.layers[idx]
                state = {
                    'x': L.x, 'y': L.y, 'w': L.w, 'h': L.h,
                    'color': L.color, 'opacity': L.opacity,
                    'rotation': getattr(L, 'rotation', 0)
                }
            else:
                state = self._compute_layer_state_at_time(idx, self.get_playback_time())
            w = state['w'] * draw_w
            h = state['h'] * draw_h
            angle = state.get('rotation', 0)
            cx = bx + state['x'] * draw_w + w/2
            cy = by + state['y'] * draw_h + h/2
            from math import cos, sin, radians
            rot = radians(angle)
            cos_a = cos(rot)
            sin_a = sin(rot)
            points = [
                (-w/2, -h/2),
                (w/2, -h/2),
                (w/2, h/2),
                (-w/2, h/2)
            ]
            abs_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a + cx
                ry = px * sin_a + py * cos_a + cy
                abs_points.append((rx, ry))
            if self._point_in_polygon(x, y, abs_points):
                found = idx
                break
        if found is not None:
            self.select_layer(found)
            idx = found
        else:
            idx = self.selected_index
        if idx is None:
            return
        mode, corner = self._get_handle_under_mouse(x, y)
        if mode == 'resize':
            self._drag_mode = 'resize'
            self._resize_corner = corner
            self._drag_start = (x, y)
            self._drag_layer_idx = idx
            L = self.layers[idx]
            self._drag_orig = (L.x, L.y, L.w, L.h)
            return
        elif mode == 'rotate':
            self._drag_mode = 'rotate'
            self._drag_start = (x, y)
            self._drag_layer_idx = idx
            L = self.layers[idx]
            bx, by, draw_w, draw_h, _ = self._render_geometry()
            w = L.w * draw_w
            h = L.h * draw_h
            self._drag_center = (bx + L.x * draw_w + w/2, by + L.y * draw_h + h/2)
            self._drag_orig_angle = getattr(L, 'rotation', 0)
            return
        # Sinon, test forme (drag move)
        c = self.render_canvas
        items = c.find_overlapping(x-2, y-2, x+2, y+2)
        for item in items:
            tags = c.gettags(item)
            if f"layer_{idx}" in tags:
                self._drag_mode = 'move'
                self._drag_start = (x, y)
                self._drag_layer_idx = idx
                L = self.layers[idx]
                self._drag_orig = (L.x, L.y)
                return

    def _on_render_mouse_drag(self, event):
        if self._drag_mode == 'move' and self._drag_layer_idx is not None:
            idx = self._drag_layer_idx
            L = self.layers[idx]
            bx, by, draw_w, draw_h, _ = self._render_geometry()
            dx = (event.x - self._drag_start[0]) / draw_w
            dy = (event.y - self._drag_start[1]) / draw_h
            L.x = min(max(self._drag_orig[0] + dx, 0), 1-L.w)
            L.y = min(max(self._drag_orig[1] + dy, 0), 1-L.h)
            self.update_properties_panel()
            self.redraw_render()
        elif self._drag_mode == 'resize' and self._drag_layer_idx is not None:
            idx = self._drag_layer_idx
            L = self.layers[idx]
            bx, by, draw_w, draw_h, _ = self._render_geometry()
            x0, y0, w0, h0 = self._drag_orig
            dx = (event.x - self._drag_start[0]) / draw_w
            dy = (event.y - self._drag_start[1]) / draw_h
            # Selon le coin, ajuster x/y/w/h
            if self._resize_corner == 'nw':
                new_x = x0 + dx
                new_y = y0 + dy
                new_w = w0 - dx
                new_h = h0 - dy
            elif self._resize_corner == 'ne':
                new_x = x0
                new_y = y0 + dy
                new_w = w0 + dx
                new_h = h0 - dy
            elif self._resize_corner == 'se':
                new_x = x0
                new_y = y0
                new_w = w0 + dx
                new_h = h0 + dy
            elif self._resize_corner == 'sw':
                new_x = x0 + dx
                new_y = y0
                new_w = w0 - dx
                new_h = h0 + dy
            # Contraintes min/max
            min_size = 0.01
            L.x = min(max(new_x, 0), 1-min_size)
            L.y = min(max(new_y, 0), 1-min_size)
            L.w = max(min(new_w, 1-L.x), min_size)
            L.h = max(min(new_h, 1-L.y), min_size)
            self.update_properties_panel()
            self.redraw_render()
        elif self._drag_mode == 'rotate' and self._drag_layer_idx is not None:
            idx = self._drag_layer_idx
            L = self.layers[idx]
            cx, cy = self._drag_center
            from math import atan2, degrees
            angle0 = self._drag_orig_angle
            x0, y0 = self._drag_start
            a0 = atan2(y0 - cy, x0 - cx)
            a1 = atan2(event.y - cy, event.x - cx)
            delta = degrees(a1 - a0)
            L.rotation = angle0 + delta
            self.update_properties_panel()
            self.redraw_render()

    def _on_render_mouse_up(self, event):
        self._drag_mode = None
        self._drag_layer_idx = None
        self._drag_start = None
        self._drag_orig = None
        self._resize_corner = None
        self._drag_center = None
        self._drag_orig_angle = None
    # --- Gestion des poignées de manipulation sur le rendu ---
    def _draw_layer_handles(self, idx, state, bx, by, draw_w, draw_h):
        """Dessine les poignées de redimensionnement et de rotation pour le layer sélectionné."""
        if idx != self.selected_index:
            return
        c = self.render_canvas
        x = bx + state['x'] * draw_w
        y = by + state['y'] * draw_h
        w = state['w'] * draw_w
        h = state['h'] * draw_h
        angle = state.get('rotation', 0)
        cx = x + w/2
        cy = y + h/2
        from math import cos, sin, radians
        rot = radians(angle)
        cos_a = cos(rot)
        sin_a = sin(rot)
        # Coins pour les poignées
        corners = [
            (-w/2, -h/2),  # nw
            (w/2, -h/2),   # ne
            (w/2, h/2),    # se
            (-w/2, h/2)    # sw
        ]
        handle_size = 8
        for i, (px, py) in enumerate(corners):
            rx = px * cos_a - py * sin_a + cx
            ry = px * sin_a + py * cos_a + cy
            c.create_rectangle(
                rx-handle_size, ry-handle_size, rx+handle_size, ry+handle_size,
                fill="#FF5555", outline="#1F6AA5", width=1, tags="handle_corner"
            )
        # Poignée de rotation (au-dessus du centre haut)
        rot_px, rot_py = 0, -h/2 - 30
        rot_x = rot_px * cos_a - rot_py * sin_a + cx
        rot_y = rot_px * sin_a + rot_py * cos_a + cy
        c.create_oval(
            rot_x-6, rot_y-6, rot_x+6, rot_y+6,
            fill="#00FF00", outline="#1F6AA5", width=2, tags="handle_rotate"
        )
    def __init__(self, root):
        self.root = root
        self.root.title("Composition Editor - Proof of Concept")
        self.root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.root.iconbitmap(False, 'icone.png')  # You can set a custom icon here if desired

        # store layers
        self.layers = []
        self.selected_index = None
        # selection state (ensure attributes exist for older code paths)
        self.selected_keyframes = set()
        self.last_selected_type = None
        self.last_selected_object = None

        # Variables de lecture
        self.playback_time = 0.0
        self.is_playing = False
        self.playback_job = None

        # Variables de drag & drop des keyframes
        self._keyframe_drag = {
            'dragging': False,
            'start_x': 0,
            'start_time': 0.0,
            'selected': set()
        }

        # background image (PIL)
        self.bg_image = None
        self.bg_orig_size = (1, 1)  # real image origin size
        self.bg_tk = None

        # audio data
        self.audio_waveform = None
        self.audio_duration = 0.0
        self.audio_filename = None

        # keyframes
        self.keyframes = [[] for _ in range(len(self.layers))]  # keyframes par layer

        # scene keyframes (timeline markers for scene changes)
        self.scene_keyframes = []
        # scene names: dictionary mapping scene number to its name
        self.scene_names = {}

        # Build UI (paned windows)
        self.build_panes()
        # build application menu (File / Export)
        self.build_menu()
        # Fill default sample layers
        self.create_sample_layers()
        # Ask user to load background image
        self.root.after(50, self.prompt_load_background)  # schedule after startup
        # Setup sash initial positions after window is mapped
        self.root.after(100, self.set_initial_sash_positions)



    def build_panes(self):
        # top-level horizontal paned window (left / right)
        self.pw_lr = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.pw_lr.pack(fill=tk.BOTH, expand=1)

        # left and right frames to be split vertically
        self.left_frame = tk.Frame(self.pw_lr)
        self.right_frame = tk.Frame(self.pw_lr)
        self.pw_lr.add(self.left_frame)
        self.pw_lr.add(self.right_frame)

        # left is split vertically top/bottom
        self.pw_left_tb = tk.PanedWindow(self.left_frame, orient=tk.VERTICAL)
        self.pw_left_tb.pack(fill=tk.BOTH, expand=1)
        # right is split vertically top/bottom
        self.pw_right_tb = tk.PanedWindow(self.right_frame, orient=tk.VERTICAL)
        self.pw_right_tb.pack(fill=tk.BOTH, expand=1)

        # Create CTk frames inside each pane
        # Top-left: Layers list
        self.top_left_ctk = ctk.CTkFrame(self.pw_left_tb)
        self.pw_left_tb.add(self.top_left_ctk)

        # Bottom-left: Properties
        self.bottom_left_ctk = ctk.CTkFrame(self.pw_left_tb)
        self.pw_left_tb.add(self.bottom_left_ctk)

        # Top-right: Render canvas
        self.top_right_ctk = ctk.CTkFrame(self.pw_right_tb)
        self.pw_right_tb.add(self.top_right_ctk)

        # Bottom-right: Timeline
        self.bottom_right_ctk = ctk.CTkFrame(self.pw_right_tb)
        self.pw_right_tb.add(self.bottom_right_ctk)

        # Build content of each quadrant
        self.build_layers_list(self.top_left_ctk)
        self.build_properties_panel(self.bottom_left_ctk)
        self.build_render_view(self.top_right_ctk)
        self.build_timeline(self.bottom_right_ctk)

    def set_initial_sash_positions(self):
        # Set initial sash positions to make right panels wider and top/bottom proportions reasonable
        # Note: coordinates are absolute pixels; compute from current window geometry
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            # place vertical sash (left/right) at 40% -> left narrower, right wider
            print(w, h)
            print(w*5, h)
            self.pw_lr.sash_place(0, 500, 0)
            # left vertical split: top/bottom - top smaller
            self.pw_left_tb.sash_place(0, 0, 500)
            # right vertical split: top bigger for render
            self.pw_right_tb.sash_place(0, 0, 500)
        except Exception as e:
            print("Could not set initial sash positions:", e)






    # -------------------------
    # Top-left: Layers list
    # -------------------------
    def build_layers_list(self, parent):
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(parent, text="Layers / Objects", anchor="w")
        header.grid(row=0, column=0, sticky="w", padx=8, pady=0)

        # Scrollable frame
        self.layers_scroll = ctk.CTkScrollableFrame(parent, label_text="")
        self.layers_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,6))


        self.layers_btn_frame = ctk.CTkFrame(parent, bg_color="transparent", fg_color="transparent")
        self.layers_btn_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))

        self.layers_btn_frame.grid_columnconfigure(0, weight=1)
        self.layers_btn_frame.grid_columnconfigure(1, weight=1)

        add_layer_btn = ctk.CTkButton(self.layers_btn_frame, text="+ Add Layer", command=self.add_layer_dialog)
        add_layer_btn.grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        add_audio_btn = ctk.CTkButton(self.layers_btn_frame, text="+ Add Audio file", command=self.add_audio)
        add_audio_btn.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        self.render_layers_list()

    def render_layers_list(self):
        # clear
        for widget in self.layers_scroll.winfo_children():
            widget.destroy()

        self._layer_drag_data = {'drag_idx': None, 'drag_widget': None}

        def on_drag_start(event, drag_idx):
            self._layer_drag_data['drag_idx'] = drag_idx
            self._layer_drag_data['drag_widget'] = event.widget.master
            event.widget.master.configure(fg_color="#444444")

        def on_drag_motion(event):
            widget = self._layer_drag_data.get('drag_widget')
            if widget:
                widget.place_configure(y=event.y_root)
        for idx, layer in enumerate(self.layers):
            fr = ctk.CTkFrame(self.layers_scroll, corner_radius=6)
            fr.pack(fill="x", pady=6, padx=6)
            # Truncate display name to 6 characters; show full name on hover
            display_name = layer.name if len(layer.name) <= 6 else (layer.name[:6] + '…')
            lbl = ctk.CTkLabel(fr, text=display_name, anchor="w")
            lbl.pack(side="left", expand=True, padx=8, pady=6)
            # show full name on mouse over
            try:
                lbl.bind('<Enter>', lambda e, n=layer.name: self._show_overlay(n, e.x_root+12, e.y_root+12))
                lbl.bind('<Leave>', lambda e: self._hide_overlay())
            except Exception:
                pass
            select_btn = ctk.CTkButton(fr, text="Select", width=70, command=lambda i=idx: self.select_layer(i))
            select_btn.pack(side="right", padx=4)
            # Boutons monter/descendre
            def move_layer_up(i=idx):
                if i > 0:
                    self.layers[i-1], self.layers[i] = self.layers[i], self.layers[i-1]
                    self.keyframes[i-1], self.keyframes[i] = self.keyframes[i], self.keyframes[i-1]
                    # Met à jour l'index sélectionné si besoin
                    if self.selected_index == i:
                        self.selected_index = i-1
                    elif self.selected_index == i-1:
                        self.selected_index = i
                    self.render_layers_list()
                    self.redraw_render()
                    self.redraw_timeline()
            def move_layer_down(i=idx):
                if i < len(self.layers)-1:
                    self.layers[i+1], self.layers[i] = self.layers[i], self.layers[i+1]
                    self.keyframes[i+1], self.keyframes[i] = self.keyframes[i], self.keyframes[i+1]
                    # Met à jour l'index sélectionné si besoin
                    if self.selected_index == i:
                        self.selected_index = i+1
                    elif self.selected_index == i+1:
                        self.selected_index = i
                    self.render_layers_list()
                    self.redraw_render()
                    self.redraw_timeline()
            up_btn = ctk.CTkButton(fr, text="▲", width=24, command=move_layer_up)
            up_btn.pack(side="left", padx=2)
            down_btn = ctk.CTkButton(fr, text="▼", width=24, command=move_layer_down)
            down_btn.pack(side="left", padx=2)
            select_btn.pack(side="right", padx=6, pady=6)
            dup_btn = ctk.CTkButton(fr, text="Dup", width=40, command=lambda i=idx: self._duplicate_layer(i))
            dup_btn.pack(side="right", padx=4)
            del_btn = ctk.CTkButton(fr, text="Del", width=50, fg_color="transparent",
                                     command=lambda i=idx: self.delete_layer(i))
            del_btn.pack(side="right", padx=6, pady=6)

    def add_layer_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Ajouter une forme")
        dialog.geometry("300x200")
        dialog.grab_set()
    
        ctk.CTkLabel(dialog, text="Type de forme :").pack(pady=20)
    
        shape_var = ctk.StringVar(value="rectangle")
    
        ctk.CTkRadioButton(dialog, text="Rectangle", variable=shape_var, 
                           value="rectangle").pack(pady=5)
        ctk.CTkRadioButton(dialog, text="Cercle", variable=shape_var, 
                       value="circle").pack(pady=5)
    
        def create_shape():
            shape_type = shape_var.get()
            name = f"{'Cercle' if shape_type == 'circle' else 'Rectangle'} {len(self.layers)+1}"
            new = Layer(
                name=name,
                x_rel=0.3,
                y_rel=0.3,
                w_rel=0.2,
                h_rel=0.2,
                color="#%02x%02x%02x" % (random.randint(50,255), 
                                         random.randint(50,255), 
                                         random.randint(50,255)),
                opacity=100,
                shape_type=shape_type
            )
            self.layers.append(new)
            self.keyframes.append([])
            self.render_layers_list()
            self.select_layer(len(self.layers)-1)
            self.redraw_render()
            dialog.destroy()
    
        ctk.CTkButton(dialog, text="Créer", command=create_shape).pack(pady=20)

    def delete_layer(self, idx):
        if 0 <= idx < len(self.layers):
            del self.layers[idx]
            if self.selected_index == idx:
                self.selected_index = None
            elif self.selected_index and self.selected_index > idx:
                self.selected_index -= 1
            self.render_layers_list()
            self.update_properties_panel()
            self.redraw_render()
            self.redraw_timeline()

    def select_layer(self, idx):
        self.selected_index = idx
        # Track last selected object type and index
        if idx is not None:
            self.last_selected_type = 'layer'
            self.last_selected_object = idx
        self.update_properties_panel()
        self.redraw_render()
        # highlight selection visually by redrawing; timeline update
        self.redraw_timeline()





    # -------------------------
    # Bottom-left: Properties
    # -------------------------
    def build_properties_panel(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        #parent.grid_rowconfigure(0, weight=0)
        lbl = ctk.CTkLabel(parent, text="Properties", anchor="w")
        lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=0)

        self.props_frame = ctk.CTkFrame(parent)
        self.props_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,6))
        self.props_frame.grid_columnconfigure(1, weight=1)

        # Position X %
        ctk.CTkLabel(self.props_frame, text="Position X (%)", anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.posx_slider = ctk.CTkSlider(self.props_frame, from_=0, to=100, command=self.on_prop_change)
        self.posx_slider.grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        # Position Y
        ctk.CTkLabel(self.props_frame, text="Position Y (%)", anchor="w").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.posy_slider = ctk.CTkSlider(self.props_frame, from_=0, to=100, command=self.on_prop_change)
        self.posy_slider.grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        # Width
        ctk.CTkLabel(self.props_frame, text="Width (%)", anchor="w").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.w_slider = ctk.CTkSlider(self.props_frame, from_=1, to=100, command=self.on_prop_change)
        self.w_slider.grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        # Height
        ctk.CTkLabel(self.props_frame, text="Height (%)", anchor="w").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.h_slider = ctk.CTkSlider(self.props_frame, from_=1, to=100, command=self.on_prop_change)
        self.h_slider.grid(row=3, column=1, sticky="ew", padx=6, pady=4)


        # Opacity
        ctk.CTkLabel(self.props_frame, text="Opacity (%)", anchor="w").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self.op_slider = ctk.CTkSlider(self.props_frame, from_=0, to=100, command=self.on_prop_change)
        self.op_slider.grid(row=4, column=1, sticky="ew", padx=6, pady=4)

        # Rotation
        ctk.CTkLabel(self.props_frame, text="Rotation (°)", anchor="w").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        self.rotation_slider = ctk.CTkSlider(self.props_frame, from_=-180, to=180, command=self.on_prop_change)
        self.rotation_slider.grid(row=5, column=1, sticky="ew", padx=6, pady=4)

        # Color picker
        ctk.CTkLabel(self.props_frame, text="Color", anchor="w").grid(row=6, column=0, sticky="w", padx=6, pady=4)
        self.color_preview = ctk.CTkButton(self.props_frame, text="", width=80, command=self.pick_color)
        self.color_preview.grid(row=6, column=1, sticky="w", padx=6, pady=4)

        # Buttons for convenience
        btn_frame = ctk.CTkFrame(self.props_frame, fg_color="transparent", bg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=10, padx=6)
        ctk.CTkButton(btn_frame, text="Center Selected", command=self.center_selected).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Reset Size", command=self.reset_size_selected).pack(side="left", padx=6)

        # Ajoute un bouton dans la timeline pour ajouter une keyframe au layer sélectionné
        self.add_kf_btn = ctk.CTkButton(parent, text="Ajouter Keyframe", command=self.add_selected_keyframe)
        self.add_kf_btn.grid(row=8, column=0, padx=8, pady=(0,8))

        self.update_properties_panel()

    def update_properties_panel(self):
        # update values to selected layer or disable if none
        if self.selected_index is None or not (0 <= self.selected_index < len(self.layers)):
            # disable controls
            for w in (self.posx_slider, self.posy_slider, self.w_slider, self.h_slider, self.op_slider, self.rotation_slider, self.color_preview):
                w.configure(state="disabled")
            return
        layer = self.layers[self.selected_index]
        for w in (self.posx_slider, self.posy_slider, self.w_slider, self.h_slider, self.op_slider, self.rotation_slider, self.color_preview):
            w.configure(state="normal")
        # set values (percents)
        self.posx_slider.set(layer.x * 100)
        self.posy_slider.set(layer.y * 100)
        self.w_slider.set(layer.w * 100)
        self.h_slider.set(layer.h * 100)
        self.op_slider.set(layer.opacity)
        self.rotation_slider.set(getattr(layer, 'rotation', 0))
        # color preview background via configure
        try:
            self.color_preview.configure(fg_color=layer.color)
        except Exception:
            pass

    def on_prop_change(self, *_):
        if self.selected_index is None or not (0 <= self.selected_index < len(self.layers)):
            return
        layer = self.layers[self.selected_index]
        layer.x = float(self.posx_slider.get()) / 100.0
        layer.y = float(self.posy_slider.get()) / 100.0
        layer.w = float(self.w_slider.get()) / 100.0
        layer.h = float(self.h_slider.get()) / 100.0
        layer.opacity = int(self.op_slider.get())
        layer.rotation = float(self.rotation_slider.get())
        # immediate update
        self.redraw_render()
        self.redraw_timeline()

    def pick_color(self):
        if self.selected_index is None:
            return
        res = colorchooser.askcolor(title="Choose layer color")
        if res and res[1]:
            self.layers[self.selected_index].color = res[1]
            self.color_preview.configure(fg_color=res[1])
            self.redraw_render()
            self.redraw_timeline()

    def center_selected(self):
        if self.selected_index is None:
            return
        layer = self.layers[self.selected_index]
        layer.x = 0.5 - layer.w / 2
        layer.y = 0.5 - layer.h / 2
        self.update_properties_panel()
        self.redraw_render()
        self.redraw_timeline()

    def reset_size_selected(self):
        if self.selected_index is None:
            return
        layer = self.layers[self.selected_index]
        layer.w = 0.2
        layer.h = 0.15
        self.update_properties_panel()
        self.redraw_render()
        self.redraw_timeline()







    # -------------------------
    # Top-right: Render view
    # -------------------------
    def build_render_view(self, parent):
        # header and canvas
        header = ctk.CTkLabel(parent, text="Render / Composition View", anchor="w")
        header.pack(fill="x", padx=8, pady=(0,0))
        # canvas container to allow background centering
        self.render_container = tk.Frame(parent)
        self.render_container.pack(fill="both", expand=True, padx=8, pady=(0,8))
        # use normal tkinter Canvas for fine control
        self.render_canvas = tk.Canvas(self.render_container, bg="#111111", highlightthickness=0)
        self.render_canvas.pack(fill="both", expand=True)
        self.render_canvas.bind("<Configure>", lambda e: self.on_render_resize(e.width, e.height))
        # allow selecting layers by clicking on canvas (hit test)
        self.render_canvas.bind("<Button-1>", self.on_render_click)

        # Ajoute la gestion de la souris pour manipuler les formes
        self._init_render_interaction()

    def on_render_click(self, event):

        # Sélectionne le layer cliqué (supporte la rotation)
        x = event.x
        y = event.y
        bx, by, draw_w, draw_h, scale = self._render_geometry()
        print("[DEBUG] Parcours de sélection (du dessus vers le dessous) :")
        for i in range(len(self.layers)-1, -1, -1):
            print(f"  idx={i} name={self.layers[i].name}")
        found = None
        for idx in range(len(self.layers)-1, -1, -1):

            # Utiliser l'état direct si pas en lecture, sinon keyframe/interpolé
            if not self.is_playing and idx == self.selected_index:
                L = self.layers[idx]
                state = {
                    'x': L.x, 'y': L.y, 'w': L.w, 'h': L.h,
                    'color': L.color, 'opacity': L.opacity,
                    'rotation': getattr(L, 'rotation', 0)
                }
            else:
                state = self._compute_layer_state_at_time(idx, self.get_playback_time())
            # Calcul des coordonnées absolues et rotation
            w = state['w'] * draw_w
            h = state['h'] * draw_h
            angle = state.get('rotation', 0)
            cx = bx + state['x'] * draw_w + w/2
            cy = by + state['y'] * draw_h + h/2
            from math import cos, sin, radians
            rot = radians(angle)
            cos_a = cos(rot)
            sin_a = sin(rot)
            # Points du rectangle
            points = [
                (-w/2, -h/2),
                (w/2, -h/2),
                (w/2, h/2),
                (-w/2, h/2)
            ]
            abs_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a + cx
                ry = px * sin_a + py * cos_a + cy
                abs_points.append((rx, ry))
            # Test si le point (x, y) est dans le polygone
            if self._point_in_polygon(x, y, abs_points):
                found = idx
                break
        if found is not None:
            print(f"[DEBUG] Layer sélectionné : idx={found} name={self.layers[found].name}")
            self.select_layer(found)

    def _point_in_polygon(self, x, y, poly):
        # Ray casting algorithm for convex polygon
        n = len(poly)
        inside = False
        px, py = poly[-1]
        for qx, qy in poly:
            if ((qy > y) != (py > y)) and (x < (px - qx) * (y - qy) / (py - qy + 1e-12) + qx):
                inside = not inside
            px, py = qx, qy
        return inside

    def prompt_load_background(self):
        messagebox.showinfo("Background image", "Veuillez sélectionner une image de fond pour la composition (PNG/JPG)...")
        f = filedialog.askopenfilename(title="Select background image",
                                       filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")])
        if not f:
            # if user cancels, create an empty placeholder image
            self.bg_image = Image.new("RGBA", (1280, 720), (30,30,30))
            self.bg_orig_size = self.bg_image.size
        else:
            try:
                im = Image.open(f).convert("RGBA")
                self.bg_image = im
                self.bg_orig_size = im.size
            except Exception as e:
                messagebox.showwarning("Erreur", f"Impossible d'ouvrir l'image: {e}")
                self.bg_image = Image.new("RGBA", (1280, 720), (30,30,30))
                self.bg_orig_size = self.bg_image.size
        self.redraw_render()

    def _render_geometry(self):
        # Compute how background is fitted (contain) into canvas
        cw = max(1, self.render_canvas.winfo_width())
        ch = max(1, self.render_canvas.winfo_height())
        if not self.bg_image:
            return 0,0,0,0,1.0
        bw, bh = self.bg_orig_size
        scale = min(cw / bw, ch / bh)
        draw_w = int(bw * scale)
        draw_h = int(bh * scale)
        offset_x = int((cw - draw_w) / 2)
        offset_y = int((ch - draw_h) / 2)
        return offset_x, offset_y, draw_w, draw_h, scale

    def on_render_resize(self, width, height):
        # Called when render canvas is resized
        self.redraw_render()

    def redraw_render(self):
        c = self.render_canvas
        c.delete("all")
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        if not self.bg_image:
            c.create_text(cw/2, ch/2, text="No background", fill="white")
            return

        bx, by, draw_w, draw_h, scale = self._render_geometry()
    
        try:
            bg_resized = self.bg_image.resize((draw_w, draw_h), Image.LANCZOS)
            self.bg_tk = ImageTk.PhotoImage(bg_resized)
            c.create_image(bx, by, anchor="nw", image=self.bg_tk, tags="bg")
        except Exception as e:
            print("Error resizing background:", e)

        playback_time = self.get_playback_time()
    
        for real_idx in range(len(self.layers)):
            L = self.layers[real_idx]
            if (not self.is_playing) and (real_idx == self.selected_index) and (getattr(self, '_drag_mode', None) is not None):
                state = {
                    'x': L.x, 'y': L.y, 'w': L.w, 'h': L.h,
                    'color': L.color, 'opacity': L.opacity,
                    'rotation': getattr(L, 'rotation', 0),
                    'shape_type': getattr(L, 'shape_type', 'rectangle')
                }
            else:
                state = self._compute_layer_state_at_time(real_idx, playback_time)
        
            x = bx + state['x'] * draw_w
            y = by + state['y'] * draw_h
            w = state['w'] * draw_w
            h = state['h'] * draw_h
            angle = state.get('rotation', 0)
            shape_type = state.get('shape_type', 'rectangle')
        
            # Préparer la couleur avec opacité
            color = state['color']
            opacity = state.get('opacity', 100)
        
            # Convertir l'opacité en stipple uniquement pour affichage
            stipple = "gray50" if opacity < 100 else ""
        
            # Dessiner selon le type de forme
            if shape_type == "circle":
                # Pour un cercle, utiliser create_oval
                cx = x + w/2
                cy = y + h/2
                # Utiliser le plus petit des deux pour un cercle parfait
                radius = min(w, h) / 2
            
                c.create_oval(
                    cx - radius, cy - radius,
                    cx + radius, cy + radius,
                    fill=color,
                    outline="",  # Pas de bordure par défaut
                    stipple=stipple,
                    tags=f"layer_{real_idx}"
                )
            
            else:  # rectangle
                cx = x + w/2
                cy = y + h/2
            
                points = [
                    (-w/2, -h/2),
                    (w/2, -h/2),
                    (w/2, h/2),
                    (-w/2, h/2)
                ]
            
                from math import cos, sin, radians
                rot = radians(angle)
                cos_a = cos(rot)
                sin_a = sin(rot)
                rotated_points = []
                for px, py in points:
                    rx = px * cos_a - py * sin_a + cx
                    ry = px * sin_a + py * cos_a + cy
                    rotated_points.extend([rx, ry])
            
                c.create_polygon(
                    rotated_points,
                    fill=color,
                    outline="",  # Pas de bordure par défaut
                    stipple=stipple,
                    tags=f"layer_{real_idx}"
                )
        
        # Dessiner la bordure en pointillés UNIQUEMENT si sélectionné
            if real_idx == self.selected_index:
                cx = x + w/2
                cy = y + h/2
                from math import cos, sin, radians
                rot = radians(angle)
                cos_a = cos(rot)
                sin_a = sin(rot)
            
                points = [
                    (-w/2, -h/2),
                    (w/2, -h/2),
                    (w/2, h/2),
                    (-w/2, h/2)
                ]
            
                rotated_points = []
                for px, py in points:
                    rx = px * cos_a - py * sin_a + cx
                    ry = px * sin_a + py * cos_a + cy
                    rotated_points.extend([rx, ry])
            
                c.create_polygon(
                    rotated_points,
                    fill="",
                    outline="#1F6AA5",
                    width=1,
                    dash=(4, 4),  # Pointillés
                    tags="selection_border"
                )
            
                # Dessiner les poignées
                self._draw_layer_handles(real_idx, state, bx, by, draw_w, draw_h)






    # -------------------------
    # Bottom-right: Timeline
    # ------------------------
    def build_timeline(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8,4))
        lab = ctk.CTkLabel(header, text="Timeline", anchor="w")
        lab.pack(side="left", padx=(0,8))
        #audio_btn = ctk.CTkButton(header, text="Ajouter Bande Son", command=self.add_audio)
        #audio_btn.pack(side="left", padx=6)

        self.setup_playback()
        self.play_btn = ctk.CTkButton(header, text="▶ Play", command=self.toggle_playback)
        self.play_btn.pack(side="left", padx=6)

        # Button to add a scene keyframe on the scene timeline
        self.add_scene_btn = ctk.CTkButton(header, text="+ Add Scene", command=self.add_scene_keyframe)
        self.add_scene_btn.pack(side="left", padx=6)

        self.stop_btn = ctk.CTkButton(header, text="■ Stop", command=self.stop_playback)
        self.stop_btn.forget()  # hide initially

        # timecode label
        self.timecode_var = tk.StringVar(value="00:00:00.000")
        timecode_lbl = ctk.CTkLabel(header, textvariable=self.timecode_var, anchor="e")
        timecode_lbl.pack(fill="x", padx=8, pady=6, side="right")


        # timeline canvas with horizontal scrollbar
        self.timeline_canvas = tk.Canvas(parent, height=250, bg="#222222", highlightthickness=0)
        self.h_scroll = tk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.timeline_canvas.xview)
        self.v_scroll = tk.Scrollbar(parent, orient=tk.VERTICAL, command=self.timeline_canvas.yview)
        self.timeline_canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.v_scroll.pack(fill="y", side="right", pady=(0,8))
        self.timeline_canvas.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self.h_scroll.pack(fill="x", padx=8, pady=(0,8))
        
        # Ajoute les événements souris pour la timeline
        self.timeline_canvas.bind('<Button-1>', self._timeline_mouse_down)
        self.timeline_canvas.bind('<B1-Motion>', self._timeline_mouse_drag)
        self.timeline_canvas.bind('<ButtonRelease-1>', self._timeline_mouse_up)
        # show overlay when hovering keyframes
        try:
            self.timeline_canvas.bind('<Motion>', self._timeline_mouse_motion)
            self.timeline_canvas.bind('<Leave>', lambda e: self._hide_overlay())
        except Exception:
            pass
        # Right-click or double-click to seek instantly (pause at that point)
        self.timeline_canvas.bind('<Button-3>', self._timeline_seek)
        self.timeline_canvas.bind('<Double-1>', self._timeline_seek)
        # Delete key to remove last selected object (layer or keyframe)
        try:
            # bind to root so it works even if timeline canvas doesn't have focus
            self.root.bind('<Delete>', self._delete_last_selected_object)
            # duplicate last selected object with Ctrl+D
            self.root.bind('<Control-d>', self._duplicate_last_selected_object)
        except Exception:
            pass

        # bind resize
        self.timeline_canvas.bind("<Configure>", lambda e: self.redraw_timeline())

    def add_keyframe(self, layer_idx, time):
        L = self.layers[layer_idx]
        kf = Keyframe(
            time,
            L.x, L.y, L.w, L.h,
            L.color, L.opacity,
            getattr(L, 'rotation', 0),
            getattr(L, 'shape_type', 'rectangle')
        )
        self.keyframes[layer_idx].append(kf)
        self.keyframes[layer_idx].sort(key=lambda k: k.time)
        self.redraw_timeline()
        self.redraw_render()

    def add_selected_keyframe(self):
        if self.selected_index is not None:
            time = self.get_playback_time()
            self.add_keyframe(self.selected_index, time)

    def add_scene_keyframe(self):
        """Ajoute un keyframe de scène à l'instant courant de lecture.
        Affiche une fenêtre de dialogue pour nommer la scène.
        """
        t = self.get_playback_time()
        # Prévenir les doublons au même moment (avec une tolérance de 1e-6 secondes)
        if any(abs(t - s) < 1e-6 for s in self.scene_keyframes):
            return
        
        # La nouvelle scène commence à ce keyframe; son numéro est déterminé à l'export
        # Pour l'instant, on stocke l'index du keyframe dans scene_keyframes
        keyframe_idx = len(self.scene_keyframes)
        
        # Afficher une fenêtre de dialogue pour nommer la scène
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Nommer la scène")
        dialog.geometry("300x120")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Nom de la scène:").pack(pady=10, padx=20)
        
        name_entry = ctk.CTkEntry(dialog, placeholder_text="Entrez le nom de la scène")
        name_entry.pack(pady=5, padx=20, fill="x")
        
        def confirm_scene():
            scene_name = name_entry.get().strip() or f"Scene{keyframe_idx + 1}"
            # Ajouter le keyframe de scène
            self.scene_keyframes.append(float(t))
            self.scene_keyframes.sort()
            # Stocker le nom de la scène avec l'index de son keyframe
            self.scene_names[keyframe_idx] = scene_name
            self.redraw_timeline()
            dialog.destroy()
        
        ctk.CTkButton(dialog, text="Valider", command=confirm_scene).pack(pady=10)

    def redraw_timeline(self):
        try:
            c = self.timeline_canvas
            c.delete("all")
            width = max(300000, self.timeline_canvas.winfo_width())
            #height = self.timeline_canvas.winfo_height()
            height = max(1000, self.timeline_canvas.winfo_height())

            # configure scrollregion
            c.configure(scrollregion=(0,0,width, height))
            # draw a time ruler at top

            total_seconds = max(10.0, self.audio_duration, 7200.0)
            pixels_per_second = width / total_seconds

            # draw grid ticks every second and label every 5 seconds
            for s in range(0, int(math.ceil(total_seconds))+1):
                x = s * pixels_per_second
                c.create_line(x, 0, x, 12, fill="#555")
                
                if s % 5 == 0:
                    c.create_line(x, 0, x, 15, fill="#555", width=3)
                    tlabel = self._format_timecode(s)[:8]
                    c.create_text(x-20.5, 14, anchor="nw", text=tlabel, fill="#aaa", font=("TkDefaultFont", 8))

            # draw tracks: one per layer, and one audio track at bottom
            track_h = 28
            padding = 8
            y = 30



            c.create_rectangle(0, y, width, y + track_h, fill="#0777a4", outline="#2b2b2b")
            # Dessiner les keyframes de scène
            c.create_text(12, y+6, anchor="nw", text="Scenes", fill="white", font=("TkDefaultFont",9))
            if self.scene_keyframes:
                for sk in self.scene_keyframes:
                    x_sk = sk * pixels_per_second
                    # diamond marker (losange)
                    size = 6
                    c.create_polygon(x_sk, y + track_h//2 - size, x_sk + size, y + track_h//2, x_sk, y + track_h//2 + size, x_sk - size, y + track_h//2, fill="#fff", outline="#000")
            y += track_h + padding



            for idx, L in enumerate(self.layers):
                c.create_rectangle(0, y, width, y + track_h, fill="#1e1e1e", outline="#2b2b2b")
                # Dessiner les keyframes pour ce layer
                c.create_text(12, y+6, anchor="nw", text=L.name, fill="white", font=("TkDefaultFont",9))
                if idx < len(self.keyframes):
                    for kf in self.keyframes[idx]:
                        x_kf = kf.time * pixels_per_second
                        c.create_oval(x_kf-6, y+track_h//2-6, x_kf+6, y+track_h//2+6, fill=kf.color, outline="#000000", width=2)
                y += track_h + padding

            # audio track
            audio_track_y = y
            c.create_rectangle(0, audio_track_y, width, audio_track_y + 80, fill="#111111", outline="#2b2b2b")
            c.create_text(6, audio_track_y+4, anchor="nw", text="Audio", fill="white")
            # draw waveform if exists
            if self.audio_waveform is not None and len(self.audio_waveform) > 0:
                wf = self.audio_waveform  # numpy array scaled -1..1
                # map waveform samples across width using same coordinate system as timeline
                samples = wf
                
                # Limit display resolution to avoid performance issues
                max_display_points = 4096
                actual_points = min(len(samples), max_display_points)
                
                # Downsample if needed
                if len(samples) > actual_points:
                    # Group samples and average for simpler visualization
                    samples_per_group = len(samples) // actual_points
                    trimmed_len = actual_points * samples_per_group
                    samples_ds = samples[:trimmed_len].reshape(actual_points, samples_per_group).mean(axis=1)
                else:
                    samples_ds = samples
                
                mid_y = audio_track_y + 40
                amp_h = 34
                
                # Calculate x spacing using the same pixels_per_second as the timeline
                # Each display point represents (audio_duration / actual_points) seconds
                pixels_per_display_point = (self.audio_duration * pixels_per_second) / actual_points if actual_points > 0 else 1
                
                points = []
                for i, v in enumerate(samples_ds):
                    x = i * pixels_per_display_point
                    y_p = mid_y - v * amp_h
                    points.append((x, y_p))
                # draw top half
                poly_top = []
                for x,y_p in points:
                    poly_top.append(x)
                    poly_top.append(y_p)
                # bottom half mirror to create filled polygon
                poly = poly_top + [width-1, mid_y, 0, mid_y]
                try:
                    c.create_polygon(poly, fill="#4caf50", outline="#2e7d32")
                except Exception:
                    # fallback: draw line
                    for i in range(len(points)-1):
                        c.create_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1], fill="#4caf50")

            # After redrawing the timeline contents, create/update the playback cursor
            # via the dedicated helper so we can refresh it independently.
            try:
                self.draw_playback_cursor()
            except Exception:
                # fallback: set timecode
                try:
                    playback_time = self.get_playback_time()
                    self.timecode_var.set(self._format_timecode(playback_time))
                except Exception:
                    pass
        except Exception as e:
            print(f"[ERROR] redraw_timeline crashed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    # -------------------------
    # Menu & Export utilities
    # -------------------------
    def build_menu(self):
        try:
            menubar = tk.Menu(self.root)

            #menus prinscipaux
            file_menu = tk.Menu(menubar, tearoff=0)
            edit_menu = tk.Menu(menubar, tearoff=0)
            objects_menu = tk.Menu(menubar, tearoff=0)
            preferences_menu = tk.Menu(menubar, tearoff=0)

            #sous menus
            file_export_menu = tk.Menu(file_menu, tearoff=0)
            objects_add_menu = tk.Menu(objects_menu, tearoff=0)
            preferences_color_menu = tk.Menu(preferences_menu, tearoff=0)

            menubar.add_cascade(label="Fichier", menu=file_menu)
            menubar.add_cascade(label="Édition", menu=edit_menu)
            menubar.add_cascade(label="Objets", menu=objects_menu)
            menubar.add_cascade(label="Preferences", menu=preferences_menu)

            #fichier menu
            file_menu.add_command(label="Nouveau", accelerator="Ctrl+N")
            file_menu.add_command(label="Ouvrir", accelerator="Ctrl+O")
            file_menu.add_command(label="Sauvegarder", accelerator="Ctrl+S")
            file_menu.add_cascade(label="Exporter", menu=file_export_menu, accelerator="Ctrl+E")
            file_menu.add_separator()
            file_menu.add_command(label="Quitter", accelerator="Ctrl+Q", command=self.root.quit)

            file_export_menu.add_command(label="Images", command=self.export_images_and_close)
            file_export_menu.add_command(label="PDF", command=self.export_images_and_close)

            #edition menu
            edit_menu.add_command(label="supprimer", accelerator="Del", command=self._delete_last_selected_object)
            #edit_menu.add_command(label="dupliquer", accelerator="Ctrl+D")
            edit_menu.add_separator()
            edit_menu.add_command(label="ajouter keyframe", accelerator="Ctrl+I", command=self.add_selected_keyframe)

            #objects menu
            objects_menu.add_cascade(label="Ajouter", menu=objects_add_menu)
            objects_add_menu.add_command(label="Rectangle", command=self.add_layer_dialog)
            objects_add_menu.add_command(label="Cercle", command=self.add_layer_dialog)
            objects_add_menu.add_command(label="Image", command=self.add_layer_dialog)
            objects_add_menu.add_command(label="Texte", command=self.add_layer_dialog)

            objects_menu.add_command(label="Renommer", accelerator="Ctrl+R")


            #preferences menu
            preferences_menu.add_command(label="swap theme", command=self.menu_cmd().swap_theme)
            preferences_menu.add_cascade(label="change color", menu=preferences_color_menu)

            preferences_color_menu.add_command(label="bleu")
            preferences_color_menu.add_command(label="bleu foncé")
            preferences_color_menu.add_command(label="vert")
            
            self.root.config(menu=menubar)
        except Exception:
            pass


    class menu_cmd:
        def swap_theme(self):
            if ctk.get_appearance_mode() == "Dark":
                ctk.set_appearance_mode("Light")
            else:
                ctk.set_appearance_mode("Dark")

        def change_color(self, color):
            if color == "dark-blue":
                ctk.set_default_color_theme("dark-blue")
            elif color == "green":
                ctk.set_default_color_theme("green")
            else:   
                ctk.set_default_color_theme("blue")


    def _compute_layer_state_at_time(self, idx, time):
        from __main__ import animate
        L = self.layers[idx]
        state = {
            'x': L.x, 'y': L.y, 'w': L.w, 'h': L.h, 
            'color': L.color, 'opacity': L.opacity, 
            'rotation': getattr(L, 'rotation', 0),
            'shape_type': getattr(L, 'shape_type', 'rectangle')
        }
    
        if idx < len(self.keyframes):
            kfs = self.keyframes[idx]
            if kfs:
                kf_prev = max((kf for kf in kfs if kf.time <= time), 
                             key=lambda k: k.time, default=None)
                kf_next = min((kf for kf in kfs if kf.time > time), 
                             key=lambda k: k.time, default=None)
            
                if animate and kf_prev and kf_next:
                    t0, t1 = kf_prev.time, kf_next.time
                    alpha = (time - t0) / (t1 - t0) if t1 > t0 else 0
                    state['x'] = kf_prev.x + (kf_next.x - kf_prev.x) * alpha
                    state['y'] = kf_prev.y + (kf_next.y - kf_prev.y) * alpha
                    state['w'] = kf_prev.w + (kf_next.w - kf_prev.w) * alpha
                    state['h'] = kf_prev.h + (kf_next.h - kf_prev.h) * alpha
                
                    def interp_color(c1, c2, a):
                        c1 = c1.lstrip('#'); c2 = c2.lstrip('#')
                        r1,g1,b1 = int(c1[0:2],16),int(c1[2:4],16),int(c1[4:6],16)
                        r2,g2,b2 = int(c2[0:2],16),int(c2[2:4],16),int(c2[4:6],16)
                        r = int(r1 + (r2-r1)*a)
                        g = int(g1 + (g2-g1)*a)
                        b = int(b1 + (b2-b1)*a)
                        return f'#{r:02x}{g:02x}{b:02x}'
                
                    state['color'] = interp_color(kf_prev.color, kf_next.color, alpha)
                    state['opacity'] = int(kf_prev.opacity + (kf_next.opacity - kf_prev.opacity) * alpha)
                    state['rotation'] = getattr(kf_prev, 'rotation', 0) + \
                                      (getattr(kf_next, 'rotation', 0) - getattr(kf_prev, 'rotation', 0)) * alpha
                    state['shape_type'] = getattr(kf_prev, 'shape_type', 'rectangle')
                
                elif kf_prev:
                    state.update({
                        'x': kf_prev.x, 'y': kf_prev.y, 'w': kf_prev.w, 'h': kf_prev.h,
                        'color': kf_prev.color, 'opacity': kf_prev.opacity,
                        'rotation': getattr(kf_prev, 'rotation', 0),
                        'shape_type': getattr(kf_prev, 'shape_type', 'rectangle')
                    })
                elif kf_next:
                    state.update({
                        'x': kf_next.x, 'y': kf_next.y, 'w': kf_next.w, 'h': kf_next.h,
                        'color': kf_next.color, 'opacity': kf_next.opacity,
                        'rotation': getattr(kf_next, 'rotation', 0),
                        'shape_type': getattr(kf_next, 'shape_type', 'rectangle')
                    })
    
        return state


    def export_images(self):
        folder = filedialog.askdirectory(title="Choisir le dossier de destination")
        if not folder:
            return
        try:
            self.export_keyframes_to_images(folder)
        except Exception as e:
            messagebox.showerror("Export error", f"Erreur lors de l'export: {e}")


    def export_images_and_close(self):
        folder = filedialog.askdirectory(title="Choisir le dossier de destination")
        if not folder:
            return
        try:
            self.export_keyframes_to_images(folder)
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Export error", f"Erreur lors de l'export: {e}")


    def export_keyframes_to_images(self, folder):
        times = set()
        for kfs in self.keyframes:
            for k in kfs:
                times.add(float(k.time))
        times = sorted(times)
        if not times:
            raise Exception("Aucune keyframe à exporter")

        if self.bg_image:
            bw, bh = self.bg_orig_size
            bg_base = self.bg_image.copy().convert('RGBA')
        else:
            bw, bh = 1280, 720
            bg_base = Image.new('RGBA', (bw, bh), (30,30,30))

        from PIL import Image, ImageDraw
        import bisect
        from collections import defaultdict

        # Determine scene number for each time based on scene_keyframes
        scene_counters = defaultdict(int)
        pil_images = []

        for t in times:
            # scene number starts at 1; each scene keyframe increments it for times >= keyframe
            if self.scene_keyframes:
                scene_idx = bisect.bisect_right(self.scene_keyframes, t)
            else:
                scene_idx = 0

            # Get the scene name: find which keyframe initiated this scene
            scene_name = f"Scene{scene_idx}"
            if self.scene_keyframes:
                # Find the keyframe that started this scene
                kf_pos = bisect.bisect_right(self.scene_keyframes, t) - 1
                if kf_pos >= 0:
                    scene_name = self.scene_names.get(kf_pos, f"Scene{scene_idx}")
            
            scene_counters[scene_idx] += 1
            y_idx = scene_counters[scene_idx]

            img = bg_base.copy()
            draw = ImageDraw.Draw(img)
        
            for idx in range(len(self.layers)):
                state = self._compute_layer_state_at_time(idx, t)
                x_px = int(state['x'] * bw)
                y_px = int(state['y'] * bh)
                w_px = max(1, int(state['w'] * bw))
                h_px = max(1, int(state['h'] * bh))
                shape_type = state.get('shape_type', 'rectangle')
            
                try:
                    if shape_type == "circle":
                        # Dessiner un cercle plein
                        cx = x_px + w_px//2
                        cy = y_px + h_px//2
                        radius = min(w_px, h_px) // 2
                        draw.ellipse(
                            [cx - radius, cy - radius, cx + radius, cy + radius],
                            fill=state['color']
                        )
                    else:
                        # Dessiner un rectangle plein
                        draw.rectangle(
                            [x_px, y_px, x_px + w_px, y_px + h_px],
                            fill=state['color']
                        )
                except Exception as e:
                    print(f"Erreur lors du dessin: {e}")
        
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            print(f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}")
            
            filename = os.path.join(folder, f"scene{scene_idx}-{scene_name}-{h:02d}_{m:02d}_{s:02d}_{ms:03d}.png")
            img.save(filename)
            try:
                pil_images.append(img.convert('RGB'))
            except Exception:
                pil_images.append(img)




        # Also create a combined PDF of all images (multipage)
        if pil_images:
            pdf_path = os.path.join(folder, "scenes_export.pdf")
            try:
                first = pil_images[0]
                rest = pil_images[1:]
                first.save(pdf_path, save_all=True, append_images=rest)
            except Exception as e:
                print("Impossible de créer le PDF combiné:", e)




    def add_audio(self):
        f = filedialog.askopenfilename(title="Select audio file", filetypes=[("Audio files","*.wav *.mp3 *.flac *.ogg"), ("All files","*.*")])
        if not f:
            return
        self.audio_filename = f
        # try WAV first using wave
        try:
            ext = os.path.splitext(f)[1].lower()
            if ext == ".wav":
                wf, sr = self._load_wav_file(f)
            elif ext in (".mp3", ".flac", ".ogg") and PydubAvailable:
                wf, sr = self._load_audio_with_pydub(f)
            else:
                # fallback: if pydub not available and not WAV -> mock
                raise Exception("MP3/other format requires pydub installed; creating mock waveform.")
            # normalize to -1..1
            try:
                wf = np.array(wf, dtype=np.float32)
                maxv = np.abs(wf).max()
                if maxv > 0:
                    wf = wf / maxv
                else:
                    wf = wf * 0  # all zeros
                
                # for stereo, average channels
                if wf.ndim == 2 and wf.shape[1] > 1:
                    wf = wf.mean(axis=1)
                
                self.audio_waveform = wf
                self.audio_duration = len(wf) / float(sr)
            except Exception as norm_e:
                print(f"[ERROR] Failed to normalize waveform: {norm_e}")
                raise
        except Exception as e:
            print("Audio import fallback:", e)
            # create mock waveform (sine envelope)
            sr = 44100
            dur = 12.0
            t = np.linspace(0, dur, int(sr*dur))
            wf = 0.6 * np.sin(2 * math.pi * 2 * t) * np.exp(-t/10.0)
            self.audio_waveform = wf
            self.audio_duration = dur
            self.audio_filename = None

        try:
            self.redraw_timeline()
        except Exception as e:
            print(f"[ERROR] redraw_timeline failed: {e}")
            import traceback
            traceback.print_exc()

    def _load_wav_file(self, path):
        with wave.open(path, "rb") as wf:
            nchan = wf.getnchannels()
            sr = wf.getframerate()
            nframes = wf.getnframes()
            data = wf.readframes(nframes)
            # convert bytes to numpy
            sample_width = wf.getsampwidth()
            if sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                dtype = np.int16
            arr = np.frombuffer(data, dtype=dtype)
            if nchan > 1:
                arr = arr.reshape(-1, nchan)
            return arr, sr

    def _load_audio_with_pydub(self, path):
        seg = AudioSegment.from_file(path)
        sr = seg.frame_rate
        samples = np.array(seg.get_array_of_samples())
        if seg.channels > 1:
            samples = samples.reshape((-1, seg.channels))
        return samples, sr

    def _format_timecode(self, seconds):
        # seconds -> HH:MM:SS.mmm
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    
    def setup_playback(self):
        # Use a high-resolution clock to track playback time precisely.
        self.is_playing = False
        self.playback_time = 0.0
        self.playback_job = None
        # Reference perf_counter start time when playback begins
        self._playback_start_perf = None
        # Counter to reduce full render frequency (helps keep cursor smooth)
        self._playback_frame_count = 0
    
    def toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text="▶ Play")
    
            if self.playback_time > 0.0:
                self.stop_btn.pack(side="left", padx=6)
                self.stop_btn.configure(text="reset")
    
            else:
                self.stop_btn.forget()

            if self.playback_job:
                self.root.after_cancel(self.playback_job)
                self.playback_job = None
        else:
            # Start playback and record precise start time so playback_time
            # is derived from real elapsed time (perf_counter) instead of
            # incremental steps which drift when rendering is slow.
            self.is_playing = True
            self.play_btn.configure(text="❚❚ Pause")
            self.stop_btn.pack(side="left", padx=6)
            self.stop_btn.configure(text="■ Stop")
            # anchor playback so current playback_time is preserved
            try:
                self._playback_start_perf = time.perf_counter() - float(self.playback_time)
            except Exception:
                self._playback_start_perf = time.perf_counter()
            # start loop
            self.playback_loop()
    
    def playback_loop(self):
        try:
            if not self.is_playing:
                return
            # Compute precise playback time from perf_counter.
            try:
                now = time.perf_counter()
                if self._playback_start_perf is None:
                    # fallback if not set
                    self._playback_start_perf = now - float(self.playback_time)
                self.playback_time = now - self._playback_start_perf
            except Exception:
                # fallback to previous incremental method
                self.playback_time += 0.04

            # Stop audio when duration is reached, but keep cursor moving
            if self.playback_time > self.audio_duration and self.audio_duration > 0:
                # Audio has ended, stop audio playback but keep cursor moving
                try:
                    self.stop_audio()
                except Exception:
                    pass

            # Draw only the timeline playback cursor each tick to keep it smooth.
            try:
                self._playback_frame_count = getattr(self, '_playback_frame_count', 0) + 1
            except Exception:
                self._playback_frame_count = 0

            # Update timeline cursor (fast)
            try:
                self.draw_playback_cursor()
            except Exception:
                try:
                    self.redraw_timeline()
                except Exception:
                    pass

            # Occasionally do a full render/redraw (to keep visuals updated)
            try:
                if self._playback_frame_count % 8 == 0:
                    # full render less frequently
                    self.redraw_timeline()
                    self.redraw_render()
            except Exception:
                pass

            # Schedule next tick. Playback time remains accurate because it's based on perf_counter.
            if self.is_playing:
                self.playback_job = self.root.after(40, self.playback_loop)
        except Exception as e:
            print(f"[ERROR] playback_loop crashed: {e}")
            import traceback
            traceback.print_exc()
            self.is_playing = False
            try:
                self.play_btn.configure(text="▶ Play")
            except Exception:
                pass
    
    def _time_to_timeline_x(self, time):
        # Convertit un temps en position x dans la timeline
        width = max(300000, self.timeline_canvas.winfo_width())
        # Use same logic as redraw_timeline for consistency
        total_seconds = max(10.0, self.audio_duration, 7200.0)
        return time * (width / total_seconds)

    def _timeline_x_to_time(self, x):
        # Convertit une position x de la timeline en temps
        width = max(300000, self.timeline_canvas.winfo_width())
        # Use same logic as redraw_timeline to ensure consistency
        total_seconds = max(10.0, self.audio_duration, 7200.0)
        return x * (total_seconds / width)

    def get_playback_time(self):
        return self.playback_time
        
    def _timeline_mouse_down(self, event):
        # Cherche une keyframe sous la souris
        clicked = None
        best_distance = float('inf')
        for layer_idx, keyframes in enumerate(self.keyframes):
            for kf_idx, kf in enumerate(keyframes):
                x = self._time_to_timeline_x(kf.time)
                dist = abs(x - event.x)
                if dist < 10 and dist < best_distance:  # 10 pixels de marge
                    clicked = (layer_idx, kf_idx)
                    best_distance = dist
                    break

        # Gestion de la sélection (Ctrl pour multi-sélection)
        if event.state & 0x4:  # Ctrl pressed
            if clicked:
                if clicked in self.selected_keyframes:
                    self.selected_keyframes.remove(clicked)
                else:
                    self.selected_keyframes.add(clicked)
        else:
            # Sinon, nouvelle sélection contenant uniquement l'élément cliqué
            if clicked:
                self.selected_keyframes = {clicked}
            else:
                self.selected_keyframes.clear()

        # Track last clicked keyframe for delete operations
        if clicked:
            self.last_selected_type = 'keyframe'
            self.last_selected_object = clicked

        # Si une keyframe est cliquée, commence le drag
        if clicked:
            # store direct references to selected keyframe objects and their original times
            selected_kfs = []
            for (li, ki) in list(self.selected_keyframes):
                try:
                    kf_obj = self.keyframes[li][ki]
                    selected_kfs.append({'layer': li, 'index': ki, 'kf': kf_obj, 'orig_time': float(kf_obj.time)})
                except Exception:
                    # skip invalid references
                    continue

            self._keyframe_drag = {
                'dragging': True,
                'start_x': event.x,
                'start_time': self._timeline_x_to_time(event.x),
                'selected_kfs': selected_kfs
            }
        else:
            # nothing to drag
            self._keyframe_drag = {'dragging': False, 'start_x': 0, 'start_time': 0.0, 'selected_kfs': []}
        
        self.redraw_timeline()

    def _timeline_mouse_drag(self, event):
        if not self._keyframe_drag.get('dragging'):
            return

        # Calcule le delta de temps basé sur la position de la souris
        current_time = self._timeline_x_to_time(event.x)
        start_time = self._keyframe_drag.get('start_time', 0.0)
        delta = current_time - start_time

        # Applique le déplacement relatif sur les objets keyframe stockés
        for entry in self._keyframe_drag.get('selected_kfs', []):
            kf_obj = entry.get('kf')
            orig = entry.get('orig_time', 0.0)
            if kf_obj is None:
                continue
            kf_obj.time = max(0.0, orig + delta)

        # Trie les keyframes par temps
        for layer_keyframes in self.keyframes:
            layer_keyframes.sort(key=lambda k: k.time)

        self.redraw_timeline()
        self.redraw_render()

    def _timeline_mouse_up(self, event):
        if self._keyframe_drag.get('dragging'):
            self._keyframe_drag['dragging'] = False
            # clear temporary drag list
            self._keyframe_drag['selected_kfs'] = []
            # Les keyframes sont déjà à leur nouvelle position
            self.redraw_timeline()
            self.redraw_render()

    def _timeline_seek(self, event):
        """Seek instantly to mouse x on timeline and pause playback so the user can resume from there."""
        try:
            # Convert window coordinates to canvas coordinates considering scroll
            c = self.timeline_canvas
            # canvasx converts from window x-coordinate to canvas x-coordinate
            canvas_x = c.canvasx(event.x)
            t = max(0.0, self._timeline_x_to_time(canvas_x))
        except Exception as e:
            print(f"Seek error: {e}")
            return
        # set playback time and pause
        self.playback_time = t
        self.is_playing = False
        if getattr(self, 'playback_job', None):
            try:
                self.root.after_cancel(self.playback_job)
            except Exception:
                pass
            self.playback_job = None
        # update play/stop UI
        try:
            self.play_btn.configure(text="▶ Play")
        except Exception:
            pass
        try:
            self.stop_btn.forget()
        except Exception:
            pass
        # update timecode and views
        try:
            self.timecode_var.set(self._format_timecode(self.playback_time))
        except Exception:
            pass
        self.redraw_timeline()
        self.redraw_render()

    # -------------------------
    # Overlay / tooltip helpers
    # -------------------------
    def _show_overlay(self, text, x_root, y_root):
        """Show a small tooltip-like overlay at absolute root coords."""
        try:
            if getattr(self, '_overlay_win', None) is None:
                self._overlay_win = tk.Toplevel(self.root)
                self._overlay_win.wm_overrideredirect(True)
                self._overlay_label = tk.Label(self._overlay_win, text=text, justify='left', bg='#222', fg='white', bd=1, padx=6, pady=4, font=(None, 9))
                self._overlay_label.pack()
                try:
                    self._overlay_win.wm_attributes('-topmost', True)
                except Exception:
                    pass
            else:
                try:
                    self._overlay_label.configure(text=text)
                except Exception:
                    pass
            # position
            try:
                self._overlay_win.geometry(f"+{x_root}+{y_root}")
                self._overlay_win.deiconify()
            except Exception:
                pass
        except Exception:
            pass

    def _hide_overlay(self):
        try:
            if getattr(self, '_overlay_win', None) is not None:
                try:
                    self._overlay_win.withdraw()
                except Exception:
                    try:
                        self._overlay_win.destroy()
                    except Exception:
                        pass
        except Exception:
            pass

    def _timeline_mouse_motion(self, event):
        """On mouse move over timeline: show overlay when hovering a keyframe."""
        try:
            # find nearest keyframe within threshold
            nearest = None
            best_dist = 9999
            for layer_idx, keyframes in enumerate(self.keyframes):
                for kf_idx, kf in enumerate(keyframes):
                    x = self._time_to_timeline_x(kf.time)
                    dist = abs(x - event.x)
                    if dist < 10 and dist < best_dist:
                        nearest = (layer_idx, kf_idx, kf)
                        best_dist = dist
            if nearest is None:
                self._hide_overlay()
                return

            li, ki, kf = nearest
            # gather properties
            try:
                L = self.layers[li]
                name = getattr(L, 'name', f'Layer {li}')
            except Exception:
                name = f'Layer {li}'
            txt = (
                f"{name}\n"
                f"time: {kf.time:.3f}s\n"
                f"x: {kf.x:.3f}, y: {kf.y:.3f}\n"
                f"w: {kf.w:.3f}, h: {kf.h:.3f}\n"
                f"color: {kf.color}, opacity: {kf.opacity}\n"
                f"rotation: {getattr(kf, 'rotation', 0):.1f}°"
            )
            # show overlay near pointer
            self._show_overlay(txt, event.x_root + 12, event.y_root + 12)
        except Exception:
            try:
                self._hide_overlay()
            except Exception:
                pass

    def draw_playback_cursor(self):
        """Draw or update the red playback cursor on the timeline canvas only.

        This avoids full timeline redraws every tick and keeps the cursor smooth.
        The cursor is drawn in canvas virtual coordinates so it scrolls correctly.
        """
        try:
            c = self.timeline_canvas
            # compute mapping same as redraw_timeline
            width = max(300000, c.winfo_width())
            # Use same logic as redraw_timeline for consistency
            total_seconds = max(10.0, self.audio_duration, 7200.0)
            pixels_per_second = width / total_seconds
            # scrollregion height for cursor
            scrollregion = c.cget('scrollregion')
            if scrollregion:
                sr_parts = scrollregion.split()
                height = float(sr_parts[3]) if len(sr_parts) > 3 else max(1000, c.winfo_height())
            else:
                height = max(1000, c.winfo_height())
            
            cursor_x = float(self.get_playback_time()) * pixels_per_second

            # Try to find an existing cursor by tag first
            try:
                ids = c.find_withtag('playback_cursor')
            except Exception:
                ids = []

            if ids:
                item = ids[0]
                try:
                    c.coords(item, cursor_x, 0, cursor_x, height)
                    self._cursor_item = item
                except Exception:
                    try:
                        c.delete(item)
                    except Exception:
                        pass
                    try:
                        self._cursor_item = c.create_line(cursor_x, 0, cursor_x, height, fill="red", width=2, tags='playback_cursor')
                    except Exception:
                        self._cursor_item = None
            else:
                try:
                    self._cursor_item = c.create_line(cursor_x, 0, cursor_x, height, fill="red", width=2, tags='playback_cursor')
                except Exception:
                    self._cursor_item = None

            # Ensure cursor is on top of timeline items and visible
            try:
                if getattr(self, '_cursor_item', None) is not None:
                    c.tag_raise(self._cursor_item)
                    c.update_idletasks()
            except Exception:
                pass

            # update timecode label
            try:
                self.timecode_var.set(self._format_timecode(self.playback_time))
            except Exception:
                pass
        except Exception:
            pass

    def _delete_last_selected_object(self, event=None):
        """Delete the last selected object (layer or keyframe) when user presses Delete."""
        if not hasattr(self, 'last_selected_type') or not hasattr(self, 'last_selected_object'):
            return
            
        if self.last_selected_type == 'keyframe':
            self._delete_keyframe(self.last_selected_object)
        elif self.last_selected_type == 'layer':
            self._delete_layer(self.last_selected_object)
            
    def _delete_keyframe(self, target_tuple):
        """Helper to delete a keyframe and update related state."""
        if not target_tuple or target_tuple not in self.selected_keyframes:
            return
            
        layer_idx, kf_idx = target_tuple
        if not (0 <= layer_idx < len(self.keyframes)):
            # remove from selection and exit
            self.selected_keyframes.discard(target_tuple)
            if self.last_selected_object == target_tuple:
                self.last_selected_object = None
                self.last_selected_type = None
            return
            
        if not (0 <= kf_idx < len(self.keyframes[layer_idx])):
            # possibly indexes shifted
            self.selected_keyframes.discard(target_tuple)
            if self.last_selected_object == target_tuple:
                self.last_selected_object = None
                self.last_selected_type = None
            return
                
        # Validation passed, delete keyframe
        self.keyframes[layer_idx].pop(kf_idx)
        
        # rebuild selected_keyframes to account for index shifts in same layer
        new_sel = set()
        for (li, ki) in list(self.selected_keyframes):
            if li != layer_idx:
                new_sel.add((li, ki))
            else:
                if ki == kf_idx:
                    continue  # removed keyframe
                elif ki > kf_idx:
                    new_sel.add((li, ki-1))  # shift down for keyframes after
                else:
                    new_sel.add((li, ki))  # keep as is for keyframes before
        self.selected_keyframes = new_sel
        
        # update last selected reference
        if self.last_selected_object == target_tuple:
            self.last_selected_object = next(iter(self.selected_keyframes), None)
            if not self.last_selected_object:
                self.last_selected_type = None
                
        # update UI
        self.redraw_timeline()
        self.redraw_render()
        try:
            self.update_properties_panel()
        except Exception:
            pass
        
    def _delete_layer(self, layer_idx):
        """Helper to delete a layer and update related state."""
        if not isinstance(layer_idx, int) or not (0 <= layer_idx < len(self.layers)):
            return
            
        # First, remove any keyframes that reference this layer
        new_selected = set()
        for li, ki in list(self.selected_keyframes):
            if li == layer_idx:
                continue  # skip keyframes from deleted layer
            elif li > layer_idx:
                # adjust indices for layers above the deleted one
                new_selected.add((li-1, ki))
            else:
                new_selected.add((li, ki))
        self.selected_keyframes = new_selected
        
        # Remove layer and its keyframes
        self.layers.pop(layer_idx)
        self.keyframes.pop(layer_idx)
        
        # Clear selection state
        if self.selected_index == layer_idx:
            self.selected_index = None
        elif self.selected_index is not None and self.selected_index > layer_idx:
            self.selected_index -= 1
        
        # Clear last selected if it was this layer
        if self.last_selected_type == 'layer' and self.last_selected_object == layer_idx:
            self.last_selected_type = None
            self.last_selected_object = None
        
        # Update UI
        self.render_layers_list()
        self.update_properties_panel()
        self.redraw_render()
        self.redraw_timeline()

    def _duplicate_last_selected_object(self, event=None):
        """Duplicate the last selected object (layer or keyframe).

        If a layer was last selected, duplicate the layer and all its keyframes.
        If a keyframe was last selected, duplicate only that keyframe (inserted just after).
        """
        if not hasattr(self, 'last_selected_type') or not hasattr(self, 'last_selected_object'):
            return

        if self.last_selected_type == 'layer':
            try:
                self._duplicate_layer(self.last_selected_object)
            except Exception:
                return
        elif self.last_selected_type == 'keyframe':
            try:
                self._duplicate_keyframe(self.last_selected_object)
            except Exception:
                return

    def _duplicate_layer(self, layer_idx):
        """Duplicate a layer and all its keyframes, inserting the copy after the original.

        The new layer will be selected and UI updated.
        """
        if not (isinstance(layer_idx, int) and 0 <= layer_idx < len(self.layers)):
            return

        orig = self.layers[layer_idx]
        # Create a copy of the layer (new object)
        # Make a unique name for the duplicated layer (avoid exact name collisions)
        base = f"{orig.name} (copy)"
        new_name = base
        existing = {L.name for L in self.layers}
        counter = 2
        while new_name in existing:
            new_name = f"{orig.name} (copy {counter})"
            counter += 1
        new_layer = Layer(new_name, x_rel=orig.x, y_rel=orig.y, w_rel=orig.w, h_rel=orig.h,
                          color=orig.color, opacity=orig.opacity, rotation=getattr(orig, 'rotation', 0))

        insert_idx = layer_idx + 1
        self.layers.insert(insert_idx, new_layer)

        # Duplicate keyframes for this layer
        orig_kfs = self.keyframes[layer_idx]
        new_kfs = []
        for kf in orig_kfs:
            new_kfs.append(Keyframe(kf.time, kf.x, kf.y, kf.w, kf.h, kf.color, kf.opacity, getattr(kf, 'rotation', 0)))
        self.keyframes.insert(insert_idx, new_kfs)

        # Adjust selected_keyframes indices (shift layers after insert_idx)
        new_sel = set()
        for li, ki in self.selected_keyframes:
            if li >= insert_idx:
                new_sel.add((li + 1, ki))
            else:
                new_sel.add((li, ki))
        self.selected_keyframes = new_sel

        # Select the new layer (use select_layer to update UI consistently)
        print(f"Duplicated layer {layer_idx} -> new at {insert_idx}")
        self.render_layers_list()
        try:
            # ensure widgets created
            self.root.update_idletasks()
        except Exception:
            pass

        # Use select_layer which sets last_selected and updates panels
        try:
            self.select_layer(insert_idx)
        except Exception:
            # fallback: directly set selection state
            self.selected_index = insert_idx
            self.last_selected_type = 'layer'
            self.last_selected_object = insert_idx

        # Try to scroll to the new item if scrollable
        try:
            # CTkScrollableFrame contains an internal canvas named _canvas
            if hasattr(self.layers_scroll, '_canvas'):
                canvas = getattr(self.layers_scroll, '_canvas')
                canvas.yview_moveto(1.0)  # scroll to bottom where new item is likely placed
        except Exception:
            pass

        self.redraw_render()
        self.redraw_timeline()

        # Try a safer scroll to the duplicated item's approximate position
        try:
            if hasattr(self.layers_scroll, '_canvas'):
                canvas = getattr(self.layers_scroll, '_canvas')
            elif hasattr(self.layers_scroll, 'canvas'):
                canvas = getattr(self.layers_scroll, 'canvas')
            else:
                canvas = None
            if canvas is not None:
                # compute fraction to scroll: position of insert_idx within total layers
                total = max(1, len(self.layers))
                frac = min(1.0, insert_idx / total)
                canvas.yview_moveto(frac)
        except Exception:
            pass

    def _duplicate_keyframe(self, kf_tuple):
        """Duplicate a single keyframe in its layer.

        The duplicate will be inserted just after the original (time + small offset if needed).
        """
        if not kf_tuple:
            return
        if kf_tuple not in self.selected_keyframes:
            # allow duplicating a single provided tuple even if not in selected set
            pass

        try:
            li, ki = kf_tuple
        except Exception:
            return

        if not (0 <= li < len(self.keyframes)):
            return
        if not (0 <= ki < len(self.keyframes[li])):
            return

        orig = self.keyframes[li][ki]
        # create duplicate; prefer a tiny time offset to avoid exact overlap
        offset = 0.1
        new_time = orig.time + offset

        new_kf = Keyframe(new_time, orig.x, orig.y, orig.w, orig.h, orig.color, orig.opacity, getattr(orig, 'rotation', 0))

        insert_pos = ki + 1
        self.keyframes[li].insert(insert_pos, new_kf)

        # Shift selected_keyframes indices for same layer where needed
        new_sel = set()
        for (lidx, kidx) in self.selected_keyframes:
            if lidx != li:
                new_sel.add((lidx, kidx))
            else:
                if kidx >= insert_pos:
                    new_sel.add((lidx, kidx + 1))
                else:
                    new_sel.add((lidx, kidx))

        # Select the new duplicated keyframe
        new_sel.add((li, insert_pos))
        self.selected_keyframes = new_sel
        self.last_selected_type = 'keyframe'
        self.last_selected_object = (li, insert_pos)

        # Refresh UI
        self.redraw_timeline()
        self.redraw_render()
        try:
            self.update_properties_panel()
        except Exception:
            pass

    def stop_playback(self):
        self.is_playing = False
        self.playback_time = 0.0
        self.play_btn.configure(text="▶ Play")
        self.stop_btn.forget()
        if self.playback_job:
            self.root.after_cancel(self.playback_job)
            self.playback_job = None
        self.redraw_timeline()
        self.redraw_render()






    # -------------------------
    # Sample content
    # -------------------------
    def create_sample_layers(self):
        self.layers.append(Layer("Background placeholder", x_rel=0.05, y_rel=0.05, w_rel=0.9, h_rel=0.9, color="#4444aa", opacity=100, rotation=0))
        self.keyframes.append([])
        self.layers.append(Layer("Foreground 1", x_rel=0.2, y_rel=0.25, w_rel=0.25, h_rel=0.18, color="#ff5555", opacity=100, rotation=0))
        self.keyframes.append([])
        self.layers.append(Layer("Logo", x_rel=0.65, y_rel=0.2, w_rel=0.18, h_rel=0.18, color="#55ff88", opacity=100, rotation=0))
        self.keyframes.append([])
        self.render_layers_list()





    # -------------------------
    # Generic
    # -------------------------
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = ctk.CTk()
    app = CompositionApp(root)
    app.run()
