from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight, Vec4, Point3, loadPrcFileData

loadPrcFileData("", """
win-size 1280 720
window-title Déplacement de bee.glb avec la souris
""")

class BeeViewer(ShowBase):
    def __init__(self):
        super().__init__()

        # Charger le modèle
        self.model = self.loader.loadModel("Bee.glb")
        if not self.model:
            print("Erreur : impossible de charger bee.glb")
            return

        self.model.reparentTo(self.render)
        self.model.setScale(0.001, 0.001, 0.001)
        self.model.setPos(0, 10, -2)

        # Lumières
        dlight = DirectionalLight("dlight")
        dlight.setColor(Vec4(1, 1, 0.9, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.render.setLight(dlnp)

        alight = AmbientLight("alight")
        alight.setColor(Vec4(0.3, 0.3, 0.4, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        # Caméra
        self.camera.setPos(0, -20, 5)
        self.camera.lookAt(Point3(0, 0, 0))

        # 🔸 Liaison d’un clic de souris
        self.accept("arrow_up", self.on_up_click)     # bouton gauche
        self.accept("arrow_down", self.on_down_click)   # bouton du milieu
        self.accept("arrow_left", self.on_left_click)    # bouton droit
        self.accept("arrow_right", self.on_right_click)    # bouton droit

        # Animation
        self.taskMgr.add(self.rotate_model, "rotationTask")

    def rotate_model(self, task):
        angle = task.time * 30
        self.model.setHpr(angle, 0, 0)
        return task.cont

    # Fonction appelée quand on clique
    def on_left_click(self):
        #print("Clic gauche ! Le modèle avance.")
        x, y, z = self.model.getPos()
        self.model.setPos(x - 1, y, z)  # déplace sur X

    def on_up_click(self):
        #print("Clic milieu ! Le modèle monte.")
        x, y, z = self.model.getPos()
        self.model.setPos(x, y, z + 1)  # déplace sur Z

    def on_right_click(self):
        #print("Clic droit ! Le modèle recule.")
        x, y, z = self.model.getPos()
        self.model.setPos(x + 1, y, z)  # déplace sur X (autre sens)

    def on_down_click(self):
        #print("Clic droit ! Le modèle recule.")
        x, y, z = self.model.getPos()
        self.model.setPos(x, y, z - 1)  # déplace sur X (autre sens)

if __name__ == "__main__":
    app = BeeViewer()
    app.run()
