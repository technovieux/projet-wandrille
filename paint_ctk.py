import customtkinter as ctk
from tkinter import filedialog, colorchooser, messagebox
from PIL import Image, ImageDraw, ImageTk

ctk.set_appearance_mode("system")  # "light", "dark" ou "system"
ctk.set_default_color_theme("blue")


class PaintApp:
    def __init__(self, root, image_path=None, width=900, height=600, bg="white"):
        self.root = root
        self.bg = bg
        self.width = width
        self.height = height
        self.root.title("🎨 Mini Paint (CTk)")

        # ---- IMAGE DE BASE ----
        if image_path:
            try:
                self.image = Image.open(image_path).convert("RGB")
                self.image = self.image.resize((self.width, self.height))
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d’ouvrir l’image : {e}")
                self.image = Image.new("RGB", (self.width, self.height), self.bg)
        else:
            self.image = Image.new("RGB", (self.width, self.height), self.bg)

        self.draw = ImageDraw.Draw(self.image)
        self.canvas_image = ImageTk.PhotoImage(self.image)

        # ---- CANVAS ----
        self.canvas = ctk.CTkCanvas(self.root, width=self.width, height=self.height, bg=self.bg, highlightthickness=0)
        self.canvas.create_image(0, 0, anchor="nw", image=self.canvas_image)
        self.canvas.grid(row=0, column=0, columnspan=9, padx=10, pady=10)

        # ---- ÉTATS ----
        self.color = "#000000"
        self.brush_size = 5
        self.eraser_on = False
        self.old_x = None
        self.old_y = None
        self.undo_stack = []
        self.redo_stack = []
        self.save_undo_state()

        # ---- BARRE D’OUTILS ----
        toolbar = ctk.CTkFrame(self.root)
        toolbar.grid(row=1, column=0, columnspan=9, pady=5)

        ctk.CTkButton(toolbar, text="🎨 Couleur", command=self.choose_color, width=120).grid(row=0, column=0, padx=5)
        ctk.CTkButton(toolbar, text="🧽 Gomme", command=self.toggle_eraser, width=120).grid(row=0, column=1, padx=5)
        ctk.CTkButton(toolbar, text="🧹 Effacer tout", command=self.clear, width=120).grid(row=0, column=2, padx=5)
        ctk.CTkButton(toolbar, text="💾 Sauvegarder", command=self.save, width=120).grid(row=0, column=3, padx=5)
        ctk.CTkButton(toolbar, text="⟲ Undo", command=self.undo, width=80).grid(row=0, column=4, padx=5)
        ctk.CTkButton(toolbar, text="⟳ Redo", command=self.redo, width=80).grid(row=0, column=5, padx=5)

        ctk.CTkLabel(toolbar, text="Taille du pinceau").grid(row=0, column=6, padx=5)
        self.size_slider = ctk.CTkSlider(toolbar, from_=1, to=50, number_of_steps=49, command=self.change_size, width=150)
        self.size_slider.set(self.brush_size)
        self.size_slider.grid(row=0, column=7, padx=5)

        # ---- BIND SOURIS ----
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_paint)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    # ------------------- OUTILS -------------------
    def choose_color(self):
        color_code = colorchooser.askcolor(title="Choisir une couleur")
        if color_code and color_code[1]:
            self.color = color_code[1]
            self.eraser_on = False

    def toggle_eraser(self):
        self.eraser_on = not self.eraser_on
        messagebox.showinfo("Gomme", "Mode gomme activé" if self.eraser_on else "Mode pinceau activé")

    def change_size(self, val):
        self.brush_size = int(float(val))

    def clear(self):
        self.save_undo_state()
        self.draw.rectangle([0, 0, self.width, self.height], fill=self.bg)
        self.update_canvas()

    def save(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            try:
                self.image.save(file_path, "PNG")
                messagebox.showinfo("Sauvegarde", f"Sauvegardé : {file_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de sauver l'image:\n{e}")

    # ------------------- DESSIN -------------------
    def on_button_press(self, event):
        self.old_x, self.old_y = event.x, event.y
        self.save_undo_state()
        self._draw_line(event.x, event.y, event.x, event.y)

    def on_paint(self, event):
        if self.old_x and self.old_y:
            self._draw_line(self.old_x, self.old_y, event.x, event.y)
            self.old_x, self.old_y = event.x, event.y

    def on_button_release(self, event):
        self.old_x, self.old_y = None, None
        self.update_canvas()

    def _draw_line(self, x1, y1, x2, y2):
        color = self.bg if self.eraser_on else self.color
        size = self.brush_size
        self.draw.line((x1, y1, x2, y2), fill=color, width=size)
        if size > 1:
            r = size // 2
            self.draw.ellipse((x2 - r, y2 - r, x2 + r, y2 + r), fill=color)
        self.update_canvas(live=True)

    # ------------------- UNDO / REDO -------------------
    def save_undo_state(self):
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.image = self.undo_stack[-1].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
        else:
            messagebox.showinfo("Undo", "Aucune action à annuler.")

    def redo(self):
        if self.redo_stack:
            self.image = self.redo_stack.pop()
            self.undo_stack.append(self.image.copy())
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
        else:
            messagebox.showinfo("Redo", "Aucune action à rétablir.")

    # ------------------- CANVAS -------------------
    def update_canvas(self, live=False):
        self.canvas_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.canvas_image)
        if not live:
            self.root.update_idletasks()


# ------------------- PAGE D’ACCUEIL -------------------
class StartPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Paint 🎨 - Accueil")
        self.root.geometry("500x350")

        frame = ctk.CTkFrame(root, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(frame, text="Bienvenue dans Mini Paint 🎨", font=("Arial", 22, "bold")).pack(pady=25)

        ctk.CTkButton(frame, text="🖼️ Ouvrir une image existante", width=250,
                      height=40, command=self.open_image).pack(pady=10)
        ctk.CTkButton(frame, text="📄 Nouveau dessin (fond blanc)", width=250,
                      height=40, command=self.new_drawing).pack(pady=10)
        ctk.CTkButton(frame, text="❌ Quitter", fg_color="red", hover_color="#aa0000",
                      width=200, height=35, command=root.destroy).pack(pady=30)

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path:
            self.launch_paint(image_path=path)

    def new_drawing(self):
        self.launch_paint()

    def launch_paint(self, image_path=None):
        for widget in self.root.winfo_children():
            widget.destroy()
        PaintApp(self.root, image_path=image_path)


# ------------------- MAIN -------------------
if __name__ == "__main__":
    root = ctk.CTk()
    StartPage(root)
    root.mainloop()
