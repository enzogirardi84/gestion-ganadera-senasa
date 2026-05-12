import os
import shutil
import tempfile
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pandas as pd

from app.database.db import DB_NAME, BACKUP_DIR

def crear_backup():
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    backup_file = os.path.join(BACKUP_DIR, f"backup_{fecha}.db")
    shutil.copy2(DB_NAME, backup_file)
    return backup_file

def generar_pdf(df, titulo):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(277, 10, text=titulo, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)
    if df.empty:
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(277, 10, text="No hay registros disponibles.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        pdf.set_font("Helvetica", 'B', 9)
        ancho_col = 277 / len(df.columns)
        alto_fila = 8
        for col in df.columns:
            pdf.cell(ancho_col, alto_fila, text=str(col)[:20].capitalize(), border=1, align='C')
        pdf.ln(alto_fila)
        pdf.set_font("Helvetica", '', 8)
        for _, row in df.iterrows():
            for item in row:
                valor = str(item) if pd.notna(item) else "-"
                pdf.cell(ancho_col, alto_fila, text=valor[:25], border=1, align='C')
            pdf.ln(alto_fila)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.remove(tmp.name)
    return pdf_bytes