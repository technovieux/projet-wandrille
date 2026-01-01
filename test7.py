import pygame

pygame.mixer.init()

fichier = "Blues.mp3"   # recommandé : OGG
start_time = 10.0       # secondes

pygame.mixer.music.load(fichier)
pygame.mixer.music.play(start=start_time)

print("Lecture depuis", start_time, "secondes (p = pause, r = reprendre, q = quitter)")

while True:
    cmd = input("> ").lower()

    if cmd == "p":
        pygame.mixer.music.pause()

    elif cmd == "r":
        pygame.mixer.music.unpause()

    elif cmd == "q":
        pygame.mixer.music.stop()
        break
