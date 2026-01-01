from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

# === CHOIX DE L’ORIENTATION ===
orientation = input("Orientation du PDF (portrait/paysage) ? ").strip().lower()

if orientation == "paysage":
    page_size = landscape(A4)
else:
    page_size = portrait(A4)

# === CONFIGURATION DU PDF ===
pdf_path = "rapport_orientation5.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=page_size)

# === STYLES ===
styles = getSampleStyleSheet()
title_style = styles['Title']
subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], textColor=colors.darkblue, spaceAfter=10)
normal_style = styles['BodyText']
bold_style = ParagraphStyle('BoldText', parent=styles['BodyText'], fontName='Helvetica-Bold', textColor=colors.black)

# === CONTENU ===
content = []

content.append(Paragraph("Rapport de Simulation d’Éclairage", title_style))
content.append(Spacer(1, 0.5*cm))
content.append(Paragraph("Rapport de Simulation d’Éclairage", title_style))
content.append(Spacer(0, 0.1*cm))
content.append(Paragraph(f"Orientation du document : {orientation.upper()}", subtitle_style))
content.append(Spacer(1, 0.5*cm))

text = """Ce document a été généré automatiquement avec Python.
L’orientation de la page a été choisie par l’utilisateur (portrait ou paysage)."""
content.append(Paragraph(text, normal_style))
content.append(Spacer(1, 0.5*cm))

data = [
    ["Paramètre", "Valeur", "Unité"],
    ["Intensité", "4500", "lumens"],
    ["Projecteurs", "12", ""],
    ["Durée", "15", "s"],
]
table = Table(data, colWidths=[6*cm, 4*cm, 3*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.darkgrey),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
]))
content.append(table)
content.append(Spacer(1, 0.7*cm))

# Image facultative
img_path = "icone.png"
try:
    image = Image(img_path, width=8*cm, height=8*cm)
    image.hAlign = "CENTER"
    content.append(image)
except Exception as e:
    content.append(Paragraph(f"⚠️ Impossible de charger l’image : {e}", normal_style))

# Texte final
content.append(Spacer(1, 1*cm))
content.append(Paragraph("Fin du rapport.", bold_style))

# === GÉNÉRATION ===
doc.build(content)

print(f"✅ PDF généré avec succès ({orientation.upper()}) : {pdf_path}")
