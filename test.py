import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

placeholder = """Entrez du texte ici..."""

class rename_window(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fenêtre simple")
        self.geometry("350x150")

        # Champ de texte
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder)
        self.entry.pack(pady=20, padx=20, fill="x")

        # Frame pour aligner les boutons côte à côte
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        # Boutons
        cancel_btn = ctk.CTkButton(btn_frame, text="Annuler", fg_color="#444", command=self.on_cancel)
        cancel_btn.pack(side="left", padx=10)

        validate_btn = ctk.CTkButton(btn_frame, text="Valider", command=self.on_validate)
        validate_btn.pack(side="left", padx=10)

    def on_cancel(self):
        self.entry.delete(0, "end")
        self.quit()

    def on_validate(self):
        print("Vous avez entré :", self.entry.get())
        self.quit()

if __name__ == "__main__":
    app = rename_window()
    app.mainloop()
