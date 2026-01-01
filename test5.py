from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)

# === CHOIX DE L’ORIENTATION ===
orientation = input("Orientation du PDF (portrait/paysage) ? ").strip().lower()
page_size = landscape(A4) if orientation == "paysage" else portrait(A4)

# === CONFIGURATION DU PDF ===
pdf_path = "rapport_multipe_pages.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=page_size)

# === STYLES ===
styles = getSampleStyleSheet()
title_style = styles['Title']
subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], textColor=colors.darkblue, spaceAfter=10)
normal_style = styles['BodyText']
bold_style = ParagraphStyle('BoldText', parent=styles['BodyText'], fontName='Helvetica-Bold', textColor=colors.black)

# === CONTENU MULTI-PAGES ===
content = []




# --- PAGE 1 ---
content.append(Paragraph("Rapport de Simulation d’Éclairage", title_style))
content.append(Spacer(1, 0.5*cm))
content.append(Paragraph(f"Orientation du document : {orientation.upper()}", subtitle_style))
content.append(Spacer(1, 0.5*cm))

intro_text = """Ce document présente la première page du rapport.
Chaque section suivante sera affichée sur une nouvelle page.
"""
content.append(Paragraph(intro_text, normal_style))
content.append(PageBreak())




# --- PAGE 2 : TABLEAU DE DONNÉES ---
content.append(Paragraph("Résultats de la Simulation", title_style))
content.append(Spacer(1, 0.3*cm))

data = [
    ["Paramètre", "Valeur", "Unité"],
    ["Intensité moyenne", "4500", "lumens"],
    ["Nombre de projecteurs", "12", ""],
    ["Durée de la simulation", "15", "secondes"],
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
content.append(PageBreak())

# --- PAGE 3 : IMAGE ---
content.append(Paragraph("Illustration graphique", title_style))
content.append(Spacer(1, 0.5*cm))

img_path = "icone.png"
try:
    image = Image(img_path, width=10*cm, height=10*cm)
    image.hAlign = "CENTER"
    content.append(image)
except Exception as e:
    content.append(Paragraph(f"⚠️ Erreur chargement image : {e}", normal_style))

content.append(Spacer(1, 1*cm))
content.append(Paragraph("Figure 1 : Exemple de rendu de projecteur.", normal_style))
content.append(PageBreak())

# --- PAGE 4 : CONCLUSION ---
content.append(Paragraph("Conclusion du Rapport", title_style))
content.append(Spacer(1, 0.5*cm))
conclusion = """Ce rapport multi-pages montre comment séparer les éléments
(titres, tableaux, images) dans des sections distinctes avec des sauts de page.
"""
content.append(Paragraph(conclusion, normal_style))
content.append(Spacer(1, 1*cm))
content.append(Paragraph("Fin du rapport.", bold_style))

# === GÉNÉRATION DU PDF ===
doc.build(content)
print(f"✅ PDF généré avec succès ({orientation.upper()}) : {pdf_path}")
