import customtkinter as ctk


keyframes = []
keyframes_time = []


class TimelineObject:
    def __init__(self, name):
        self.name = name
        self.keyframes = []

class TimelineApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Timeline Animation")
        self.geometry("900x600")
        self.objects = [TimelineObject("Objet 1"), TimelineObject("Objet 2"), TimelineObject("Objet 3")]
        self.create_widgets()

    def create_widgets(self):
        # Première ligne : Liste des objets à gauche, plan final à droite
       
       
        # Colonne liste des objets
        obj_list_frame = ctk.CTkScrollableFrame(self, label_text="objets", width=100, height=150)
        obj_list_frame.pack(side="left", fill="y", padx=5)
        for obj in self.objects:
            ctk.CTkLabel(obj_list_frame, text=obj.name).pack(anchor="w", padx=10)

        add_object_btn = ctk.CTkButton(obj_list_frame, text="+ Ajouter Objet")
        add_object_btn.pack(pady=10)
        

        top_frame = ctk.CTkFrame(self, height=300)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Plan final
        #plan_frame = ctk.CTkFrame(top_frame, width=600, height=300)
        #plan_frame.pack(side="left", fill="both", padx=5)
        #ctk.CTkLabel(plan_frame, text="Plan Final", font=("Arial", 16)).pack(pady=5)

        # Ajout d'un carré blanc dans plan_frame
        square = ctk.CTkCanvas(top_frame, width=100, height=100, bg="white", highlightthickness=0)
        square.place(x=20, y=40)
        square.create_rectangle(0, 0, 50, 50, fill="white", outline="")

        # Deuxième ligne : Timeline
        timeline_frame = ctk.CTkScrollableFrame(self, label_text="CTkScrollableFrame")
        timeline_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Timeline pour chaque objet
        for obj in self.objects + [TimelineObject("Bande Son")]:
            print(obj.name)
            obj_timeline = ctk.CTkFrame(timeline_frame, height=40)
            obj_timeline.pack(fill="x", pady=5)
            ctk.CTkLabel(obj_timeline, text=obj.name, width=100).pack(side="left")
            timeline_canvas = ctk.CTkCanvas(obj_timeline, width=1000, height=30, bg="#222")
            timeline_canvas.pack(side="left", padx=10)

            #clique pour ajouter les keyframes
            timeline_canvas.bind("<Button-1>", lambda e, o=obj, c=timeline_canvas: self.keyframe(o, c, e.x))

    def keyframe(self, obj, canvas, x):

        # Ajoute un point (keyframe) sur la timeline
        if x not in obj.keyframes:
            obj.keyframes.append(x)
            keyframes.append(x)
            print(x)
            obj.keyframes.sort()
            print(obj.keyframes)
        
            canvas.create_oval(x-5, 10, x+5, 20, fill="cyan")
        else:
            obj.keyframes.remove(x)
            keyframes.remove(x)
            print("removed", x)
            canvas.delete("all")
            for kf in obj.keyframes:
                canvas.create_oval(kf-5, 10, kf+5, 20, fill="cyan")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = TimelineApp()
    app.mainloop()