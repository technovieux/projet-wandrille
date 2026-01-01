import customtkinter as ctk
import math

class DraggableRectangle:
    def __init__(self, canvas, x1, y1, x2, y2, **kwargs):
        self.canvas = canvas
        self.rotation_angle = 0  # Angle de rotation en degrés
        self.handle_size = 8  # Taille des poignées
        
        # Calcul du centre
        self.center_x = (x1 + x2) / 2
        self.center_y = (y1 + y2) / 2
        
        # Dimensions originales (non rotatées)
        self.width = abs(x2 - x1)
        self.height = abs(y2 - y1)
        
        # Points du rectangle non rotaté
        self.original_points = [
            [-self.width/2, -self.height/2],  # Coin supérieur gauche
            [self.width/2, -self.height/2],   # Coin supérieur droit
            [self.width/2, self.height/2],    # Coin inférieur droit
            [-self.width/2, self.height/2]    # Coin inférieur gauche
        ]
        
        # Couleurs par défaut
        self.fill_color = kwargs.get('fill', '#3B8ED0')
        self.outline_color = kwargs.get('outline', '#1F6AA5')
        self.handle_color = kwargs.get('handle_color', '#FF5555')
        self.rotate_handle_color = kwargs.get('rotate_handle_color', '#00FF00')
        
        # Création du rectangle principal
        self.rect = self.canvas.create_polygon(
            self.get_rotated_points(),
            fill=self.fill_color,
            outline=self.outline_color,
            width=2,
            tags="draggable"
        )
        
        # Création des poignées
        self.handles = {}
        self.rotate_handle = None
        self.create_handles()
        
        # Événements
        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_release)
        
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.resizing = False
        self.rotating = False
        self.resize_corner = None
    
    def rotate_point(self, point, angle_degrees):
        """Fait tourner un point autour du centre"""
        angle_rad = math.radians(angle_degrees)
        x, y = point
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Rotation
        new_x = x * cos_a - y * sin_a
        new_y = x * sin_a + y * cos_a
        
        # Translation vers la position du centre
        return new_x + self.center_x, new_y + self.center_y
    
    def get_rotated_points(self):
        """Retourne les points du rectangle après rotation"""
        points = []
        for point in self.original_points:
            rotated_point = self.rotate_point(point, self.rotation_angle)
            points.extend(rotated_point)
        return points
    
    def get_handle_positions(self):
        """Retourne les positions des poignées après rotation"""
        handle_offsets = {
            'nw': [-self.width/2, -self.height/2],  # Coin nord-ouest
            'ne': [self.width/2, -self.height/2],   # Coin nord-est
            'sw': [-self.width/2, self.height/2],   # Coin sud-ouest
            'se': [self.width/2, self.height/2],    # Coin sud-est
            'rotate': [0, -self.height/2 - 30]      # Poignée de rotation
        }
        
        positions = {}
        for corner, offset in handle_offsets.items():
            positions[corner] = self.rotate_point(offset, self.rotation_angle)
        
        return positions
    
    def create_handles(self):
        """Crée les poignées de redimensionnement (coins) et de rotation"""
        handle_positions = self.get_handle_positions()
        
        # Poignées de redimensionnement (coins)
        corners = ['nw', 'ne', 'sw', 'se']
        for corner in corners:
            x, y = handle_positions[corner]
            
            handle = self.canvas.create_rectangle(
                x - self.handle_size, y - self.handle_size,
                x + self.handle_size, y + self.handle_size,
                fill=self.handle_color,
                outline=self.outline_color,
                width=1,
                tags=f"handle_{corner}",
                state='hidden'
            )
            
            self.handles[corner] = handle
        
        # Poignée de rotation
        rot_x, rot_y = handle_positions['rotate']
        self.rotate_handle = self.canvas.create_oval(
            rot_x - 6, rot_y - 6,
            rot_x + 6, rot_y + 6,
            fill=self.rotate_handle_color,
            outline=self.outline_color,
            width=2,
            tags="handle_rotate",
            state='hidden'
        )
        self.handles['rotate'] = self.rotate_handle
        
        # Événements pour toutes les poignées
        for corner, handle in self.handles.items():
            self.canvas.tag_bind(handle, "<ButtonPress-1>", 
                               lambda e, c=corner: self.on_handle_press(e, c))
            self.canvas.tag_bind(handle, "<B1-Motion>", self.on_handle_drag)
            self.canvas.tag_bind(handle, "<ButtonRelease-1>", self.on_handle_release)
    
    def update_handles(self):
        """Met à jour la position de toutes les poignées"""
        handle_positions = self.get_handle_positions()
        
        for corner, handle in self.handles.items():
            if corner == 'rotate':
                x, y = handle_positions[corner]
                self.canvas.coords(handle,
                                 x - 6, y - 6,
                                 x + 6, y + 6)
            else:
                x, y = handle_positions[corner]
                self.canvas.coords(handle,
                                 x - self.handle_size, y - self.handle_size,
                                 x + self.handle_size, y + self.handle_size)
    
    def show_handles(self):
        """Affiche toutes les poignées"""
        for handle in self.handles.values():
            self.canvas.itemconfig(handle, state='normal')
    
    def hide_handles(self):
        """Cache toutes les poignées"""
        for handle in self.handles.values():
            self.canvas.itemconfig(handle, state='hidden')
    
    def on_press(self, event):
        """Début du déplacement"""
        current_item = self.canvas.find_withtag("current")
        if current_item and any(current_item[0] == handle for handle in self.handles.values()):
            return
            
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["item"] = self.rect
        
        self.show_handles()
        self.canvas.itemconfig(self.rect, fill='#2A6FA0')
    
    def on_drag(self, event):
        """Déplacement du rectangle"""
        if not self.resizing and not self.rotating and self.drag_data["item"] is not None:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            
            # Mettre à jour le centre
            self.center_x += dx
            self.center_y += dy
            
            # Mettre à jour le rectangle
            self.canvas.coords(self.rect, self.get_rotated_points())
            
            # Mettre à jour les poignées
            self.update_handles()
            
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_release(self, event):
        """Fin du déplacement"""
        self.drag_data["item"] = None
        self.canvas.itemconfig(self.rect, fill=self.fill_color)
    
    def on_handle_press(self, event, handle_type):
        """Début d'interaction avec une poignée"""
        if handle_type == 'rotate':
            self.rotating = True
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        else:
            self.resizing = True
            self.resize_corner = handle_type
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_handle_drag(self, event):
        """Interaction avec les poignées"""
        if self.rotating:
            self.handle_rotate(event)
        elif self.resizing:
            self.handle_resize(event)
    
    def handle_rotate(self, event):
        """Rotation du rectangle"""
        # Calcul de l'angle entre le centre et la position de la souris
        dx = event.x - self.center_x
        dy = event.y - self.center_y
        new_angle = math.degrees(math.atan2(dy, dx)) + 90  # +90 pour aligner avec la poignée
        
        # Mettre à jour l'angle
        self.rotation_angle = new_angle
        
        # Mettre à jour le rectangle
        self.canvas.coords(self.rect, self.get_rotated_points())
        
        # Mettre à jour les poignées
        self.update_handles()
    
    def handle_resize(self, event):
        """Redimensionnement du rectangle par les coins - CENTRE FIXE"""
        if not self.resizing or not self.resize_corner:
            return
            
        # Calcul du déplacement dans le système local (rotaté)
        angle_rad = math.radians(-self.rotation_angle)
        dx_world = event.x - self.drag_data["x"]
        dy_world = event.y - self.drag_data["y"]
        
        # Conversion en coordonnées locales
        dx_local = dx_world * math.cos(angle_rad) - dy_world * math.sin(angle_rad)
        dy_local = dx_world * math.sin(angle_rad) + dy_world * math.cos(angle_rad)
        
        # Sauvegarde des anciennes dimensions
        old_width = self.width
        old_height = self.height
        
        # Ajustement des dimensions selon le coin
        if 'n' in self.resize_corner:
            self.height = max(20, self.height - dy_local)
        if 's' in self.resize_corner:
            self.height = max(20, self.height + dy_local)
        if 'w' in self.resize_corner:
            self.width = max(20, self.width - dx_local)
        if 'e' in self.resize_corner:
            self.width = max(20, self.width + dx_local)
        
        # Calcul du déplacement du centre pour le garder fixe
        # Le centre se déplace de la moitié du changement de dimension
        delta_width = self.width - old_width
        delta_height = self.height - old_height
        
        # Conversion du déplacement du centre en coordonnées mondiales
        center_dx_local = delta_width / 2
        center_dy_local = delta_height / 2
        
        center_dx_world = center_dx_local * math.cos(math.radians(self.rotation_angle)) - center_dy_local * math.sin(math.radians(self.rotation_angle))
        center_dy_world = center_dx_local * math.sin(math.radians(self.rotation_angle)) + center_dy_local * math.cos(math.radians(self.rotation_angle))
        
        # Ajustement du centre pour compenser le redimensionnement
        # (cette partie est commentée pour garder le centre fixe)
        # self.center_x += center_dx_world
        # self.center_y += center_dy_world
        
        # Mettre à jour les points originaux
        self.original_points = [
            [-self.width/2, -self.height/2],
            [self.width/2, -self.height/2],
            [self.width/2, self.height/2],
            [-self.width/2, self.height/2]
        ]
        
        # Mettre à jour l'affichage
        self.canvas.coords(self.rect, self.get_rotated_points())
        self.update_handles()
        
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
    
    def on_handle_release(self, event):
        """Fin d'interaction avec les poignées"""
        self.resizing = False
        self.rotating = False
        self.resize_corner = None

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Rectangle avec Poignées aux Coins - Centre Fixe")
        self.geometry("1000x700")
        
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
        
        # Cadre de contrôle
        self.control_frame = ctk.CTkFrame(self.main_frame)
        self.control_frame.pack(fill="x", padx=5, pady=5)
        
        # Boutons
        self.add_btn = ctk.CTkButton(
            self.control_frame,
            text="Ajouter Rectangle",
            command=self.add_rectangle
        )
        self.add_btn.pack(side="left", padx=5, pady=5)
        
        self.clear_btn = ctk.CTkButton(
            self.control_frame,
            text="Tout Effacer",
            command=self.clear_canvas,
            fg_color="#D35B5B",
            hover_color="#B24949"
        )
        self.clear_btn.pack(side="left", padx=5, pady=5)
        
        self.rotate_btn = ctk.CTkButton(
            self.control_frame,
            text="Rotation +15°",
            command=self.rotate_selected,
            fg_color="#2FA572",
            hover_color="#268A5D"
        )
        self.rotate_btn.pack(side="left", padx=5, pady=5)
        
        # Informations
        self.info_label = ctk.CTkLabel(
            self.control_frame,
            text="💡 Cliquez: Déplacer • Coins: Redimensionner (centre fixe) • Cercle vert: Rotation",
            text_color="gray"
        )
        self.info_label.pack(side="left", padx=20, pady=5)
        
        # Liste pour stocker les rectangles
        self.rectangles = []
        self.selected_rectangle = None
        
        # Ajouter un rectangle par défaut
        self.add_rectangle()
        
        # Événements du canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)
    
    def on_canvas_click(self, event):
        """Gère les clics sur le canvas"""
        # Désélectionner tout
        if self.selected_rectangle:
            self.selected_rectangle.hide_handles()
            self.selected_rectangle.canvas.itemconfig(self.selected_rectangle.rect, 
                                                    fill=self.selected_rectangle.fill_color)
            self.selected_rectangle = None
        
        # Vérifier si on clique sur un rectangle
        items = self.canvas.find_overlapping(event.x-1, event.y-1, event.x+1, event.y+1)
        for item in items:
            for rect in self.rectangles:
                if item == rect.rect:
                    self.selected_rectangle = rect
                    rect.show_handles()
                    rect.canvas.itemconfig(rect.rect, fill='#2A6FA0')
                    return
    
    def rotate_selected(self):
        """Rotation de 15° du rectangle sélectionné"""
        if self.selected_rectangle:
            self.selected_rectangle.rotation_angle += 15
            self.selected_rectangle.canvas.coords(
                self.selected_rectangle.rect, 
                self.selected_rectangle.get_rotated_points()
            )
            self.selected_rectangle.update_handles()
    
    def add_rectangle(self):
        """Ajoute un nouveau rectangle au canvas"""
        import random
        x1 = random.randint(100, 500)
        y1 = random.randint(100, 400)
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
    
    def clear_canvas(self):
        """Efface tous les rectangles"""
        for rect in self.rectangles:
            self.canvas.delete(rect.rect)
            for handle in rect.handles.values():
                self.canvas.delete(handle)
        self.rectangles.clear()
        self.selected_rectangle = None

if __name__ == "__main__":
    app = App()
    app.mainloop()