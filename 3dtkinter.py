import customtkinter as ctk
import pyglet
from pyglet.gl import *
import trimesh
import numpy as np

class App3D(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("3D Model Viewer")
        self.geometry("1000x600")
        
        # Configuration du grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Panneau gauche avec les boutons
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Boutons flèches
        self.btn_up = ctk.CTkButton(self.left_panel, text="↑", command=lambda: self.move_model("up"))
        self.btn_up.pack(pady=5)
        
        self.btn_down = ctk.CTkButton(self.left_panel, text="↓", command=lambda: self.move_model("down"))
        self.btn_down.pack(pady=5)
        
        self.btn_left = ctk.CTkButton(self.left_panel, text="←", command=lambda: self.move_model("left"))
        self.btn_left.pack(pady=5)
        
        self.btn_right = ctk.CTkButton(self.left_panel, text="→", command=lambda: self.move_model("right"))
        self.btn_right.pack(pady=5)
        
        # Panneau droit pour le modèle 3D
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Chargement du modèle 3D
        try:
            self.model = trimesh.load('Bee.glb')
            self.position = [0, 0, 0]
        except Exception as e:
            print(f"Erreur lors du chargement du modèle: {e}")
            
    def move_model(self, direction):
        step = 0.1
        if direction == "up":
            self.position[1] += step
        elif direction == "down":
            self.position[1] -= step
        elif direction == "left":
            self.position[0] -= step
        elif direction == "right":
            self.position[0] += step
        
        # Mettre à jour la position du modèle
        self.update_model_position()
        
    def update_model_position(self):
        self.model.apply_translation(self.position)
        pass

if __name__ == "__main__":
    app = App3D()
    app.mainloop()