from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
import datetime

styles = getSampleStyleSheet()
normal = styles["Normal"]
title = ParagraphStyle('BoldText', parent=styles['Title'], fontName='Helvetica-Bold', textColor=colors.black, alignment=("center"))


pages_with_header_footer = [2, 3]  # Pages with header/footer
header_font_size = 12
header_font = "Helvetica-Bold"



# --- Fonction pour l'en-tête et le pied de page ---
def draw_header_footer(canvas, doc):
    page_num = canvas.getPageNumber()
    canvas.saveState()

    # Exemple : afficher l'entête uniquement sur les pages 2 et 3
    if page_num in pages_with_header_footer:
        canvas.setFont(header_font, header_font_size)
        canvas.drawString(2 * cm, A4[1] - 1.2 * cm, f"Rapport d’éclairage - Page {page_num}")
        canvas.setStrokeColor(colors.grey)
        canvas.line(2 * cm, A4[1] - 1.4 * cm, A4[0] - 1.4 * cm, A4[1] - 1.4 * cm)

    # Exemple : pied de page uniquement à partir de la page 3
    if page_num >= 3:
        footer_y = 1.5 * cm
        canvas.setFont("Helvetica", 9)
        date_str = datetime.datetime.now().strftime("%d/%m/%Y")
        canvas.drawRightString(A4[0] - 2 * cm, footer_y, f"Généré le {date_str}")
        canvas.drawCentredString(A4[0]/2, footer_y, f"Page {page_num}")
        canvas.line(2 * cm, footer_y + 0.3 * cm, A4[0] - 2 * cm, footer_y + 0.3 * cm)

    canvas.restoreState()

# --- Création du document ---
doc = SimpleDocTemplate(
    "choix_entete_pied.pdf",
    pagesize=A4,
    topMargin=2.5 * cm,
    bottomMargin=2.5 * cm
)

# --- Contenu de test ---
story = []
story.append(Paragraph("Page 1 - sans entête ni pied", title))
story.append(Spacer(1, 12*cm))
story.append(PageBreak())


story.append(Paragraph("Page 2 - entête visible", title))
story.append(Spacer(1, 12*cm))
story.append(PageBreak())

story.append(Paragraph("Page 3 - entête + pied visibles", title))
story.append(Spacer(1, 12*cm))
story.append(PageBreak())

story.append(Paragraph("Page 4 - pied uniquement", title))
story.append(Spacer(1, 12*cm))

# --- Génération du PDF ---
doc.build(story, onLaterPages=draw_header_footer)
print("✅ PDF généré avec entêtes/pieds personnalisés selon la page.")
