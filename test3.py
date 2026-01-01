import customtkinter as ctk

class DraggableRectangle:
    def __init__(self, canvas, x1, y1, x2, y2, **kwargs):
        self.canvas = canvas
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        
        # Couleurs par défaut
        self.fill_color = kwargs.get('fill', '#3B8ED0')
        self.outline_color = kwargs.get('outline', '#1F6AA5')
        self.handle_color = kwargs.get('handle_color', '#FF0000')
        
        # Création du rectangle principal
        self.rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=self.fill_color,
            outline=self.outline_color,
            width=2,
            tags="draggable"
        )
        
        # Création des poignées de redimensionnement
        self.handles = []
        self.create_handles()
        
        # Événements
        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_release)
        
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.resizing = False
        self.resize_corner = None
    
    def create_handles(self):
        """Crée les poignées de redimensionnement aux coins"""
        handles_positions = [
            (self.x1, self.y1, "nw"),  # Coin nord-ouest
            (self.x2, self.y1, "ne"),  # Coin nord-est
            (self.x1, self.y2, "sw"),  # Coin sud-ouest
            (self.x2, self.y2, "se")   # Coin sud-est
        ]
        
        for x, y, corner in handles_positions:
            handle = self.canvas.create_rectangle(
                x-4, y-4, x+4, y+4,
                fill=self.handle_color,
                outline=self.outline_color,
                width=1,
                tags=f"handle_{corner}"
            )
            self.handles.append(handle)
            
            # Événements pour les poignées
            self.canvas.tag_bind(handle, "<ButtonPress-1>", 
                               lambda e, c=corner: self.on_resize_press(e, c))
            self.canvas.tag_bind(handle, "<B1-Motion>", self.on_resize_drag)
            self.canvas.tag_bind(handle, "<ButtonRelease-1>", self.on_resize_release)
    
    def update_handles(self):
        """Met à jour la position des poignées"""
        handles_positions = [
            (self.x1, self.y1, "nw"),
            (self.x2, self.y1, "ne"),
            (self.x1, self.y2, "sw"),
            (self.x2, self.y2, "se")
        ]
        
        for i, (x, y, corner) in enumerate(handles_positions):
            print(f"Updating handle {i} to position ({x}, {y})")
            if i == 0:
                self.canvas.coords(self.handles[i], x, y, x, y+15)
            if i == 1:
                self.canvas.coords(self.handles[i], x, y, x+15, y+15)


            else:
                self.canvas.coords(self.handles[i], x, y, x+10, y+4)
    
    def on_press(self, event):
        """Début du déplacement"""
        # Vérifier si on clique sur une poignée (alors c'est un redimensionnement)
        if self.canvas.find_withtag("current") in self.handles:
            return
            
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["item"] = self.rect
        
        # Changer la couleur pour indiquer la sélection
        self.canvas.itemconfig(self.rect, fill='#2A6FA0')
    
    def on_drag(self, event):
        """Déplacement du rectangle - Désactive le déplacement vers le haut"""
        if not self.resizing and self.drag_data["item"] is not None:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            # Empêche le déplacement vers le haut (dy négatif)
            if dy != 0:
                dy = 0

            self.x1 += dx
            self.y1 += dy
            self.x2 += dx
            self.y2 += dy
            self.canvas.coords(self.rect, self.x1, self.y1, self.x2, self.y2)
            self.update_handles()
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_release(self, event):
        """Fin du déplacement"""
        self.drag_data["item"] = None
        # Restaurer la couleur originale
        self.canvas.itemconfig(self.rect, fill=self.fill_color)
    
    def on_resize_press(self, event, corner):
        """Début du redimensionnement"""
        self.resizing = True
        self.resize_corner = corner
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
    
    def on_resize_drag(self, event):
        """Redimensionnement en temps réel"""
        if self.resizing and self.resize_corner:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            # Bloque l'étirement en hauteur (ignore dy)
            # Ajuster uniquement la largeur
            if "w" in self.resize_corner:
                self.x1 += dx
            if "e" in self.resize_corner:
                self.x2 += dx
            # Assurer une taille minimale
            min_size = 10
            if abs(self.x2 - self.x1) < min_size:
                if "e" in self.resize_corner:
                    self.x2 = self.x1 + min_size
                else:
                    self.x1 = self.x2 - min_size
            # Mettre à jour le rectangle
            self.canvas.coords(self.rect, self.x1, self.y1, self.x2, self.y2)
            self.update_handles()
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_resize_release(self, event):
        """Fin du redimensionnement"""
        self.resizing = False
        self.resize_corner = None



class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Rectangle Déplaçable et Redimensionnable - CORRIGÉ")
        self.geometry("800x600")
        
        # Configuration du thème
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Cadre principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Canvas pour dessiner
        self.canvas = ctk.CTkCanvas(
            self.main_frame, 
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        

        
        # Liste pour stocker les rectangles
        self.rectangles = []
        
        # Ajouter un rectangle par défaut
        self.add_rectangle()
    
    def add_rectangle(self):
        """Ajoute un nouveau rectangle au canvas"""
        import random
        x1 = random.randint(50, 400)
        y1 = random.randint(50, 300)
        x2 = x1 + random.randint(80, 200)
        y2 = y1 + random.randint(60, 150)
        
        colors = ["#3B8ED0", "#2FA572", "#D35B5B", "#E6B229", "#9B59B6"]
        color = random.choice(colors)
        
        rectangle = DraggableRectangle(
            self.canvas, x1, y1, x2, y2,
            fill=color,
            outline="#1F6AA5"
        )
        self.rectangles.append(rectangle)
    
    

if __name__ == "__main__":
    app = App()
    app.mainloop()