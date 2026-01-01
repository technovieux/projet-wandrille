import customtkinter as ctk

class TopLevelWindow(ctk.CTkToplevel):
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


class ShortcutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Application Principale")
        self.geometry("500x350")

        self.label = ctk.CTkLabel(self, text="Appuyez sur Ctrl + S pour ouvrir la fenêtre de sauvegarde.", font=("Arial", 16))
        self.label.pack(pady=50)

        # Une référence à la fenêtre Toplevel pour éviter d'en ouvrir plusieurs
        self.toplevel_window = None

        # 1. Binder la séquence de touches Ctrl+S
        self.bind('<Control-s>', self.open_save_dialog)
        
        # IMPORTANT pour les utilisateurs Mac (Commande + S)
        self.bind('<Command-s>', self.open_save_dialog) 


    def open_save_dialog(self, event):
        """
        Gère l'ouverture de la fenêtre de dialogue de sauvegarde.
        """
        # Vérifier si une fenêtre Toplevel est déjà ouverte
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            # Créer et ouvrir la nouvelle fenêtre
            self.toplevel_window = TopLevelWindow(self) 
            # Déplacer le focus sur la nouvelle fenêtre
            self.toplevel_window.focus()
        else:
            # Si elle est déjà ouverte, la mettre juste en avant
            self.toplevel_window.focus()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = ShortcutApp()
    app.mainloop()