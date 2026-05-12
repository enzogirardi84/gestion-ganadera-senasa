import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import tempfile
import os
import shutil
import hashlib
import hmac
import secrets
import io
import csv
import unicodedata

# Configuracion - cambiar a False para usar Supabase
USAR_SUPABASE = False  # False = SQLite local/cloud | True = Supabase cloud

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

DB_NAME = 'gestion_bovinos_senasa.db'
BACKUP_DIR = 'backups'
APP_NAME = "Gestion Ganadera SENASA"
APP_SUBTITLE = "Trazabilidad, sanidad, reproduccion y gestion operativa"
ROLES_USUARIO = ["Administrador", "Veterinario", "Tecnico", "Propietario"]
PBKDF2_ITERATIONS = 260000
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_LEGACY_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
TABLAS_EXPORTABLES = [
    "bovinos", "sanidad", "reproduccion", "pesajes", "propietarios",
    "farmacia", "stock", "certificados", "intervenciones", "finanzas",
    "lotes", "agenda", "facturacion", "recetas", "alertas",
    "ehr_templates", "ehr_template_items", "workflow_pacientes", "workflow_tareas",
    "ordenes_compra", "automation_log", "audit_log",
]

_supabase = None

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS bovinos (
                caravana TEXT PRIMARY KEY,
                tipo_identificacion TEXT,
                raza TEXT,
                sexo TEXT,
                categoria TEXT,
                peso_nacimiento REAL,
                fecha_nacimiento DATE,
                estado TEXT DEFAULT 'Activo',
                estatus_brucelosis TEXT DEFAULT 'Sin Diagnostico',
                propietario_id INTEGER,
                foto TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS sanidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                categoria_evento TEXT,
                medicamento TEXT,
                dosis TEXT,
                fecha_aplicacion DATE,
                veterinario_acreditado TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS reproduccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana_madre TEXT,
                tipo_servicio TEXT,
                fecha_servicio DATE,
                resultado_tacto TEXT,
                fecha_parto DATE,
                caravana_cria TEXT,
                FOREIGN KEY(caravana_madre) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pesajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                peso_kg REAL,
                fecha_pesaje DATE,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_alerta TEXT,
                caravana TEXT,
                descripcion TEXT,
                fecha_alerta DATE,
                resuelta INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS interdicciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                enfermedad TEXT,
                fecha_interdiccion DATE,
                motivo TEXT,
                resolucion TEXT,
                estado TEXT DEFAULT 'Activa',
                fecha_levantamiento DATE,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS control_normativo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_norma TEXT,
                numero TEXT,
                anio INTEGER,
                descripcion TEXT,
                articulo TEXT,
                cumplimiento TEXT DEFAULT 'Pendiente',
                fecha_cumplimiento DATE,
                observaciones TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS toros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                raza TEXT,
                origen TEXT,
                fecha_nacimiento DATE,
                registro TEXT,
                aptitud TEXT,
                comentarios TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS inseminaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana_vaca TEXT,
                toro_id INTEGER,
                fecha_inseminacion DATE,
                hora_inseminacion TEXT,
                tipo_semen TEXT,
                tecnico TEXT,
                resultado TEXT DEFAULT 'Pendiente',
                fecha_probable_parto DATE,
                observaciones TEXT,
                FOREIGN KEY(caravana_vaca) REFERENCES bovinos(caravana),
                FOREIGN KEY(toro_id) REFERENCES toros(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS propietarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                apellido TEXT,
                documento TEXT,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                localidad TEXT,
                provincia TEXT,
                cuit TEXT,
                fecha_registro DATE DEFAULT (DATE('now'))
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_evento DATE,
                hora_evento TEXT,
                tipo_evento TEXT,
                titulo TEXT,
                caravana TEXT,
                propietario_id INTEGER,
                veterinario TEXT,
                descripcion TEXT,
                estado TEXT DEFAULT 'Pendiente',
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS farmacia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_producto TEXT,
                principio_activo TEXT,
                tipo_producto TEXT,
                proveedor TEXT,
                concentracion TEXT,
                presentacion TEXT,
                laboratorio TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                lote TEXT,
                fecha_vencimiento DATE,
                cantidad INTEGER DEFAULT 0,
                precio_compra REAL DEFAULT 0,
                precio_venta REAL DEFAULT 0,
                ubicacion TEXT,
                stock_minimo INTEGER DEFAULT 0,
                proveedor_predeterminado TEXT,
                FOREIGN KEY(producto_id) REFERENCES farmacia(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS recetas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                propietario_id INTEGER,
                veterinario TEXT,
                fecha_receta DATE DEFAULT (DATE('now')),
                diagnostico TEXT,
                indicaciones TEXT,
                firma_digital TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS receta_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receta_id INTEGER,
                producto_id INTEGER,
                dosis TEXT,
                frecuencia TEXT,
                duracion TEXT,
                via_administracion TEXT,
                observaciones TEXT,
                FOREIGN KEY(receta_id) REFERENCES recetas(id),
                FOREIGN KEY(producto_id) REFERENCES farmacia(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                tipo_certificado TEXT,
                fecha_emision DATE DEFAULT (DATE('now')),
                fecha_validez DATE,
                veterinario_firmante TEXT,
                matricula TEXT,
                motivo TEXT,
                resultado TEXT,
                observaciones TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS intervenciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                tipo_intervencion TEXT,
                fecha_intervencion DATE,
                veterinario TEXT,
                diagnostico TEXT,
                procedimiento TEXT,
                hallazgos TEXT,
                recomendaciones TEXT,
                costo REAL DEFAULT 0,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS historia_clinica (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                fecha_consulta DATE DEFAULT (DATE('now')),
                motivo_consulta TEXT,
                anamnesis TEXT,
                exploracion_fisica TEXT,
                diagnostico_presuntivo TEXT,
                diagnostico_definitivo TEXT,
                tratamiento TEXT,
                observaciones TEXT,
                veterinario TEXT,
                subjetivo TEXT,
                objetivo TEXT,
                analisis TEXT,
                plan TEXT,
                template_id INTEGER,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS ehr_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                motivo TEXT,
                subjetivo TEXT,
                objetivo TEXT,
                analisis TEXT,
                plan TEXT,
                activo INTEGER DEFAULT 1
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS ehr_template_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                concepto TEXT,
                cantidad REAL DEFAULT 1,
                precio_unitario REAL DEFAULT 0,
                producto_id INTEGER,
                stock_cantidad INTEGER DEFAULT 0,
                recordatorio_meses INTEGER DEFAULT 0,
                recordatorio_mensaje TEXT,
                FOREIGN KEY(template_id) REFERENCES ehr_templates(id),
                FOREIGN KEY(producto_id) REFERENCES farmacia(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                nombre TEXT,
                rol TEXT DEFAULT 'Veterinario',
                propietario_id INTEGER,
                activo INTEGER DEFAULT 1
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS hospitalizacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                fecha_ingreso DATE DEFAULT (DATE('now')),
                fecha_egreso DATE,
                motivo TEXT,
                diagnostico_ingreso TEXT,
                tratamiento TEXT,
                veterinario_responsable TEXT,
                estado TEXT DEFAULT 'Internado',
                observaciones TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS kardex_hospitalario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospitalizacion_id INTEGER,
                fecha DATE DEFAULT (DATE('now')),
                hora TEXT,
                veterinario TEXT,
                temperatura REAL,
                frecuencia_cardiaca INTEGER,
                frecuencia_respiratoria INTEGER,
                observacion TEXT,
                medicacion TEXT,
                FOREIGN KEY(hospitalizacion_id) REFERENCES hospitalizacion(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                fecha_solicitud DATE DEFAULT (DATE('now')),
                tipo_analisis TEXT,
                muestra TEXT,
                fecha_toma DATE,
                fecha_resultado DATE,
                solicitado_por TEXT,
                laboratorio_externo TEXT,
                resultado TEXT,
                observaciones TEXT,
                archivo_path TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS resultados_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                laboratorio_id INTEGER,
                parametro TEXT,
                valor TEXT,
                unidad TEXT,
                rango_referencia TEXT,
                estado TEXT,
                FOREIGN KEY(laboratorio_id) REFERENCES laboratorio(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS facturacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_factura TEXT,
                propietario_id INTEGER,
                fecha_emision DATE DEFAULT (DATE('now')),
                tipo_comprobante TEXT,
                descripcion TEXT,
                subtotal REAL DEFAULT 0,
                iva REAL DEFAULT 0,
                total REAL DEFAULT 0,
                metodo_pago TEXT,
                estado_pago TEXT DEFAULT 'Pendiente',
                observaciones TEXT,
                FOREIGN KEY(propietario_id) REFERENCES propietarios(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS factura_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factura_id INTEGER,
                concepto TEXT,
                cantidad INTEGER DEFAULT 1,
                precio_unitario REAL DEFAULT 0,
                subtotal REAL DEFAULT 0,
                FOREIGN KEY(factura_id) REFERENCES facturacion(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS crm_interacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                propietario_id INTEGER,
                fecha_interaccion DATE DEFAULT (DATE('now')),
                tipo_interaccion TEXT,
                canal TEXT,
                descripcion TEXT,
                resultado TEXT,
                proximo_seguimiento DATE,
                veterinario TEXT,
                FOREIGN KEY(propietario_id) REFERENCES propietarios(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS recordatorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                propietario_id INTEGER,
                caravana TEXT,
                tipo_recordatorio TEXT,
                fecha_envio DATE,
                fecha_programada DATE,
                mensaje TEXT,
                canal TEXT DEFAULT 'WhatsApp',
                enviado INTEGER DEFAULT 0,
                FOREIGN KEY(propietario_id) REFERENCES propietarios(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS workflow_pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT UNIQUE,
                estado TEXT DEFAULT 'Espera',
                responsable TEXT,
                prioridad TEXT DEFAULT 'Normal',
                actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                observaciones TEXT,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS workflow_tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caravana TEXT,
                tarea TEXT,
                asignado_a TEXT,
                vence_en DATETIME,
                estado TEXT DEFAULT 'Pendiente',
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS ordenes_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                proveedor TEXT,
                cantidad_sugerida INTEGER,
                motivo TEXT,
                estado TEXT DEFAULT 'Borrador',
                fecha_creacion DATE DEFAULT (DATE('now')),
                FOREIGN KEY(producto_id) REFERENCES farmacia(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS automation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento TEXT,
                entidad TEXT,
                entidad_id INTEGER,
                detalle TEXT,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT,
                rol TEXT,
                accion TEXT,
                entidad TEXT,
                entidad_id TEXT,
                detalle TEXT,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                superficie_ha REAL,
                tipo_pastura TEXT,
                capacidad_animales INTEGER,
                estado TEXT DEFAULT 'Activo',
                observaciones TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS lote_animales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER,
                caravana TEXT,
                fecha_asignacion DATE DEFAULT (DATE('now')),
                fecha_salida DATE,
                FOREIGN KEY(lote_id) REFERENCES lotes(id),
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS finanzas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                categoria TEXT,
                descripcion TEXT,
                monto REAL,
                fecha DATE DEFAULT (DATE('now')),
                caravana TEXT,
                propietario_id INTEGER,
                forma_pago TEXT,
                comprobante TEXT
            )
        ''')
        conn.commit()

try:
    os.makedirs(BACKUP_DIR, exist_ok=True)
except:
    pass

init_db()

def run_query(query, params=()):
    try:
        if USAR_SUPABASE and _supabase:
            _supabase.rpc("exec_sql", {"sql_text": query}).execute()
            return True
        else:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute(query, params)
                conn.commit()
                return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        return False

def run_insert_return_id(query, params=()):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return c.lastrowid
    except Exception:
        return None

# Migraciones: agregar columnas faltantes a tablas existentes
try:
    run_query("ALTER TABLE bovinos ADD COLUMN propietario_id INTEGER")
except:
    pass

def fetch_data(query, params=()):
    if USAR_SUPABASE and _supabase:
        try:
            result = _supabase.rpc("exec_sql", {"sql_text": query}).execute()
            if result.data:
                return pd.DataFrame(result.data)
            return pd.DataFrame()
        except:
            pass
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df

def obtener_lista_caravanas(solo_hembras=False):
    query = "SELECT caravana FROM bovinos WHERE estado = 'Activo'"
    if solo_hembras:
        query += " AND sexo = 'Hembra'"
    df = fetch_data(query)
    return df['caravana'].tolist() if not df.empty else []

def obtener_toros():
    df = fetch_data("SELECT id, nombre, raza FROM toros ORDER BY nombre")
    return df

def crear_backup():
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_{fecha}.db")
    shutil.copy2(DB_NAME, backup_file)
    return backup_file

def texto_pdf(valor):
    texto = "" if valor is None or pd.isna(valor) else str(valor)
    texto = unicodedata.normalize("NFKD", texto).encode("latin-1", "ignore").decode("latin-1")
    return texto.replace("\n", " ").replace("\r", " ").strip()

class ReportPDF(FPDF):
    def __init__(self, titulo):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.titulo = texto_pdf(titulo)
        self.set_auto_page_break(auto=True, margin=14)

    def header(self):
        self.set_fill_color(17, 94, 89)
        self.rect(0, 0, 297, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, text=APP_NAME, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, text=self.titulo, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(8)
        self.set_text_color(24, 24, 27)

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(113, 113, 122)
        generado = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 6, text=f"Generado {generado} | Pagina {self.page_no()}", align="C")
        self.set_text_color(24, 24, 27)

def generar_pdf(df, titulo):
    df = df.copy()
    df.columns = [texto_pdf(c).replace("_", " ").title() for c in df.columns]
    pdf = ReportPDF(titulo)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, text=texto_pdf(titulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(82, 82, 91)
    pdf.cell(0, 6, text=f"Registros: {len(df)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(24, 24, 27)
    pdf.ln(3)

    if df.empty:
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(277, 10, text="No hay registros disponibles.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    else:
        max_cols = min(len(df.columns), 10)
        df = df.iloc[:, :max_cols]
        ancho_col = 277 / max_cols
        alto_fila = 7
        pdf.set_fill_color(20, 83, 45)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        for col in df.columns:
            pdf.cell(ancho_col, alto_fila, text=texto_pdf(col)[:26], border=0, align="C", fill=True)
        pdf.ln(alto_fila)
        pdf.set_text_color(24, 24, 27)
        pdf.set_font("Helvetica", "", 7)
        for idx, (_, row) in enumerate(df.head(250).iterrows()):
            fill = idx % 2 == 0
            pdf.set_fill_color(244, 244, 245) if fill else pdf.set_fill_color(255, 255, 255)
            for item in row:
                valor = texto_pdf(item) or "-"
                pdf.cell(ancho_col, alto_fila, text=valor[:32], border=0, align="L", fill=True)
            pdf.ln(alto_fila)
        if len(df) > 250:
            pdf.ln(3)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 6, text="Vista limitada a 250 registros. Use Excel para el detalle completo.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
    os.remove(tmp.name)
    return pdf_bytes

def generar_excel_completo(tablas):
    output = io.BytesIO()
    resumen = []
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for tabla in tablas:
            try:
                df = fetch_data(f"SELECT * FROM {tabla}")
            except Exception:
                continue
            sheet = tabla[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
            resumen.append({"Tabla": tabla, "Registros": len(df), "Columnas": len(df.columns)})

            ws = writer.book[sheet]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True, color="FFFFFF")
                cell.fill = cell.fill.copy(fill_type="solid", fgColor="14532D")
            for column_cells in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 38)

        pd.DataFrame(resumen).to_excel(writer, sheet_name="Resumen", index=False)
        ws = writer.book["Resumen"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True, color="FFFFFF")
            cell.fill = cell.fill.copy(fill_type="solid", fgColor="115E59")
        for column_cells in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 32)
    return output.getvalue()

def verificar_alertas():
    bovinos = fetch_data("SELECT caravana, fecha_nacimiento, estatus_brucelosis FROM bovinos WHERE estado = 'Activo'")
    today = date.today()
    run_query("DELETE FROM alertas WHERE tipo_alerta IN ('Brucelosis Pendiente', 'Vencimiento Stock')")

    def crear_alerta_unica(tipo, caravana, descripcion):
        run_query(
            "INSERT INTO alertas (tipo_alerta, caravana, descripcion, fecha_alerta) VALUES (?, ?, ?, ?)",
            (tipo, caravana, descripcion, today),
        )

    for _, row in bovinos.iterrows():
        try:
            fecha_nac = datetime.strptime(str(row['fecha_nacimiento']), '%Y-%m-%d').date()
        except Exception:
            continue
        edad = relativedelta(today, fecha_nac)
        edad_meses = edad.years * 12 + edad.months
        if 3 <= edad_meses <= 8 and row['estatus_brucelosis'] == 'Sin Diagnostico':
            crear_alerta_unica(
                "Brucelosis Pendiente",
                row["caravana"],
                f"Verificar vacunacion Cepa 19 (edad: {edad_meses} meses)",
            )

    stock = fetch_data("""
        SELECT s.id, f.nombre_producto, s.lote, s.fecha_vencimiento, s.cantidad
        FROM stock s JOIN farmacia f ON s.producto_id = f.id
        WHERE s.fecha_vencimiento BETWEEN DATE('now') AND DATE('now', '+90 days')
    """)
    for _, row in stock.iterrows():
        try:
            dias = (datetime.strptime(row['fecha_vencimiento'], '%Y-%m-%d').date() - today).days
        except Exception:
            continue
        crear_alerta_unica(
            "Vencimiento Stock",
            "Sistema",
            f"{row['nombre_producto']} lote {row['lote']} vence en {dias} dias",
        )

def log_automatizacion(evento, entidad, entidad_id, detalle):
    run_query(
        "INSERT INTO automation_log (evento, entidad, entidad_id, detalle) VALUES (?, ?, ?, ?)",
        (evento, entidad, entidad_id, detalle),
    )

def registrar_auditoria(accion, entidad, entidad_id="", detalle=""):
    usuario = st.session_state.get("usuario") if hasattr(st, "session_state") else None
    nombre = str((usuario or {}).get("username") or (usuario or {}).get("nombre") or "sistema")
    rol = str((usuario or {}).get("rol") or "sistema")
    run_query(
        "INSERT INTO audit_log (usuario, rol, accion, entidad, entidad_id, detalle) VALUES (?, ?, ?, ?, ?, ?)",
        (nombre, rol, accion, entidad, str(entidad_id or ""), str(detalle or "")),
    )

def sembrar_templates_ehr():
    templates = [
        {
            "nombre": "Vacunacion anual",
            "motivo": "Control preventivo y aplicacion de vacuna anual.",
            "subjetivo": "Propietario refiere animal sin signos clinicos relevantes.",
            "objetivo": "Examen general sin hallazgos de alarma. Temperatura y condicion corporal dentro de parametros esperados.",
            "analisis": "Paciente apto para vacunacion preventiva.",
            "plan": "Aplicar vacuna indicada. Controlar reaccion local. Programar recordatorio preventivo.",
            "items": [("Vacuna anual", 1, 0, 0, 11, "Recordatorio de revacunacion anual")],
        },
        {
            "nombre": "Consulta general",
            "motivo": "Consulta clinica general.",
            "subjetivo": "Motivo referido por el propietario.",
            "objetivo": "Examen fisico completo: actitud, mucosas, hidratacion, temperatura, auscultacion y palpacion.",
            "analisis": "Diagnostico presuntivo segun signos clinicos.",
            "plan": "Indicar tratamiento, controles y pautas de alarma.",
            "items": [("Consulta veterinaria", 1, 0, 0, 0, "")],
        },
        {
            "nombre": "Control reproductivo",
            "motivo": "Evaluacion reproductiva.",
            "subjetivo": "Antecedentes reproductivos y observaciones del establecimiento.",
            "objetivo": "Evaluacion clinica/reproductiva segun protocolo.",
            "analisis": "Estado reproductivo a confirmar o controlar.",
            "plan": "Registrar hallazgos, indicar seguimiento y proxima revision.",
            "items": [("Control reproductivo", 1, 0, 0, 1, "Seguimiento reproductivo")],
        },
    ]
    for tpl in templates:
        ok = run_query(
            "INSERT OR IGNORE INTO ehr_templates (nombre, motivo, subjetivo, objetivo, analisis, plan) VALUES (?, ?, ?, ?, ?, ?)",
            (tpl["nombre"], tpl["motivo"], tpl["subjetivo"], tpl["objetivo"], tpl["analisis"], tpl["plan"]),
        )
        df = fetch_data("SELECT id FROM ehr_templates WHERE nombre = ?", (tpl["nombre"],))
        if df.empty:
            continue
        template_id = int(df["id"].iloc[0])
        existing = fetch_data("SELECT COUNT(*) as total FROM ehr_template_items WHERE template_id = ?", (template_id,))
        if int(existing["total"].iloc[0] or 0) == 0:
            for item in tpl["items"]:
                run_query(
                    """
                    INSERT INTO ehr_template_items
                    (template_id, concepto, cantidad, precio_unitario, stock_cantidad, recordatorio_meses, recordatorio_mensaje)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (template_id, item[0], item[1], item[2], item[3], item[4], item[5]),
                )

def obtener_propietario_animal(caravana):
    df = fetch_data("SELECT propietario_id FROM bovinos WHERE caravana = ?", (caravana,))
    if df.empty or pd.isna(df["propietario_id"].iloc[0]):
        return None
    return int(df["propietario_id"].iloc[0])

def aplicar_automatizaciones_consulta(consulta_id, caravana, template_id):
    if not template_id:
        return
    items = fetch_data("SELECT * FROM ehr_template_items WHERE template_id = ?", (template_id,))
    if items.empty:
        return
    propietario_id = obtener_propietario_animal(caravana)
    facturables = items[items["precio_unitario"].fillna(0) > 0]
    if propietario_id and not facturables.empty:
        subtotal = float((facturables["cantidad"].astype(float) * facturables["precio_unitario"].astype(float)).sum())
        iva = subtotal * 0.21
        factura_id = run_insert_return_id(
            """
            INSERT INTO facturacion
            (numero_factura, propietario_id, tipo_comprobante, descripcion, subtotal, iva, total, metodo_pago, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"AUTO-{consulta_id}", propietario_id, "Presupuesto", f"Auto-billing consulta {caravana}", subtotal, iva, subtotal + iva, "Cuenta corriente", "Generado automaticamente desde historia clinica"),
        )
        if factura_id:
            for _, item in facturables.iterrows():
                cantidad = float(item["cantidad"] or 1)
                precio = float(item["precio_unitario"] or 0)
                run_query(
                    "INSERT INTO factura_detalle (factura_id, concepto, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
                    (factura_id, item["concepto"], cantidad, precio, cantidad * precio),
                )
            log_automatizacion("auto_billing", "historia_clinica", consulta_id, f"Factura borrador AUTO-{consulta_id} generada")

    for _, item in items.iterrows():
        producto_id = item.get("producto_id")
        stock_cantidad = int(item.get("stock_cantidad") or 0)
        if pd.notna(producto_id) and int(producto_id) > 0 and stock_cantidad > 0:
            run_query(
                "UPDATE stock SET cantidad = MAX(cantidad - ?, 0) WHERE producto_id = ?",
                (stock_cantidad, int(producto_id)),
            )
            log_automatizacion("stock_descuento", "historia_clinica", consulta_id, f"Stock descontado: {item['concepto']}")

        meses = int(item.get("recordatorio_meses") or 0)
        if propietario_id and meses > 0:
            mensaje = item.get("recordatorio_mensaje") or f"Seguimiento: {item['concepto']}"
            fecha = (date.today() + relativedelta(months=meses)).isoformat()
            run_query(
                "INSERT INTO recordatorios (propietario_id, caravana, tipo_recordatorio, fecha_programada, mensaje, canal) VALUES (?, ?, ?, ?, ?, ?)",
                (propietario_id, caravana, "Automatico", fecha, mensaje, "Email"),
            )
            log_automatizacion("recordatorio", "historia_clinica", consulta_id, f"Recordatorio programado para {fecha}")

def revisar_reorden_stock():
    df = fetch_data(
        """
        SELECT s.producto_id, f.nombre_producto, SUM(s.cantidad) as cantidad_total,
               MAX(s.stock_minimo) as stock_minimo,
               MAX(COALESCE(s.proveedor_predeterminado, f.proveedor, '')) as proveedor
        FROM stock s JOIN farmacia f ON s.producto_id = f.id
        GROUP BY s.producto_id, f.nombre_producto
        HAVING stock_minimo > 0 AND cantidad_total <= stock_minimo
        """
    )
    for _, row in df.iterrows():
        existente = fetch_data(
            "SELECT id FROM ordenes_compra WHERE producto_id = ? AND estado = 'Borrador'",
            (int(row["producto_id"]),),
        )
        if existente.empty:
            sugerida = max(int(row["stock_minimo"] or 0) * 2 - int(row["cantidad_total"] or 0), int(row["stock_minimo"] or 0))
            run_query(
                "INSERT INTO ordenes_compra (producto_id, proveedor, cantidad_sugerida, motivo) VALUES (?, ?, ?, ?)",
                (int(row["producto_id"]), row["proveedor"], sugerida, f"Stock bajo: {row['nombre_producto']}"),
            )
            log_automatizacion("reorden_stock", "stock", int(row["producto_id"]), "Orden de compra borrador generada")

def render_busqueda_global():
    render_app_header("Busqueda Global", "Encontrar rapido animales, clientes, historia clinica, stock y facturas.")
    termino = st.text_input("Buscar", placeholder="Caravana, cliente, producto, diagnostico, factura...")
    if not termino or len(termino.strip()) < 2:
        st.info("Escribi al menos 2 caracteres para buscar en todo el sistema.")
        return

    like = f"%{termino.strip()}%"
    tabs = st.tabs(["Animales", "Clientes", "Clinica", "Stock", "Facturacion"])
    with tabs[0]:
        df = fetch_data(
            """
            SELECT b.caravana, b.raza, b.sexo, b.categoria, b.estado, b.estatus_brucelosis,
                   COALESCE(p.nombre || ' ' || p.apellido, 'Sin propietario') as propietario
            FROM bovinos b LEFT JOIN propietarios p ON b.propietario_id = p.id
            WHERE b.caravana LIKE ? OR b.raza LIKE ? OR b.categoria LIKE ? OR p.nombre LIKE ? OR p.apellido LIKE ?
            ORDER BY b.caravana LIMIT 100
            """,
            (like, like, like, like, like),
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tabs[1]:
        df = fetch_data(
            """
            SELECT id, nombre, apellido, documento, cuit, telefono, email, localidad, provincia
            FROM propietarios
            WHERE nombre LIKE ? OR apellido LIKE ? OR documento LIKE ? OR cuit LIKE ? OR telefono LIKE ? OR email LIKE ?
            ORDER BY apellido LIMIT 100
            """,
            (like, like, like, like, like, like),
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tabs[2]:
        df = fetch_data(
            """
            SELECT fecha_consulta, caravana, motivo_consulta, diagnostico_definitivo, veterinario, observaciones
            FROM historia_clinica
            WHERE caravana LIKE ? OR motivo_consulta LIKE ? OR diagnostico_definitivo LIKE ? OR tratamiento LIKE ? OR observaciones LIKE ?
            ORDER BY fecha_consulta DESC LIMIT 100
            """,
            (like, like, like, like, like),
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tabs[3]:
        df = fetch_data(
            """
            SELECT f.nombre_producto, f.tipo_producto, f.proveedor, s.lote, s.fecha_vencimiento, s.cantidad, s.ubicacion
            FROM farmacia f LEFT JOIN stock s ON f.id = s.producto_id
            WHERE f.nombre_producto LIKE ? OR f.principio_activo LIKE ? OR f.proveedor LIKE ? OR s.lote LIKE ?
            ORDER BY f.nombre_producto LIMIT 100
            """,
            (like, like, like, like),
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tabs[4]:
        df = fetch_data(
            """
            SELECT fa.numero_factura, fa.fecha_emision, fa.tipo_comprobante, fa.total, fa.estado_pago,
                   COALESCE(p.nombre || ' ' || p.apellido, 'Sin cliente') as cliente
            FROM facturacion fa LEFT JOIN propietarios p ON fa.propietario_id = p.id
            WHERE fa.numero_factura LIKE ? OR fa.descripcion LIKE ? OR p.nombre LIKE ? OR p.apellido LIKE ?
            ORDER BY fa.fecha_emision DESC LIMIT 100
            """,
            (like, like, like, like),
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

def render_portal_cliente():
    render_app_header("Portal del Cliente", "Consulta privada de animales, turnos, certificados, recordatorios y facturacion.")
    propietario_id = propietario_id_usuario_actual()
    if not propietario_id:
        st.warning("Tu usuario aun no esta vinculado a un cliente. Pedi a un administrador que lo asocie desde Usuarios y Seguridad.")
        return

    propietario = fetch_data("SELECT * FROM propietarios WHERE id = ?", (propietario_id,))
    if propietario.empty:
        st.error("No encontramos el cliente vinculado a este usuario.")
        return
    p = propietario.iloc[0]
    st.markdown(f"### {p['nombre']} {p['apellido']}")
    st.caption(f"{p['email'] or 'Sin email'} | {p['telefono'] or 'Sin telefono'}")

    tab_animales, tab_turnos, tab_cert, tab_rec, tab_fact = st.tabs(["Animales", "Turnos", "Certificados", "Recordatorios", "Facturas"])
    with tab_animales:
        animales = fetch_data(
            """
            SELECT caravana, tipo_identificacion, raza, sexo, categoria, fecha_nacimiento, estado, estatus_brucelosis
            FROM bovinos WHERE propietario_id = ? ORDER BY caravana
            """,
            (propietario_id,),
        )
        st.dataframe(animales, use_container_width=True, hide_index=True)
    with tab_turnos:
        turnos = fetch_data(
            """
            SELECT fecha_evento, hora_evento, tipo_evento, titulo, caravana, veterinario, estado
            FROM agenda WHERE propietario_id = ? ORDER BY fecha_evento DESC, hora_evento DESC
            """,
            (propietario_id,),
        )
        st.dataframe(turnos, use_container_width=True, hide_index=True)
    with tab_cert:
        certificados = fetch_data(
            """
            SELECT c.fecha_emision, c.fecha_validez, c.caravana, c.tipo_certificado, c.veterinario_firmante, c.resultado
            FROM certificados c JOIN bovinos b ON c.caravana = b.caravana
            WHERE b.propietario_id = ? ORDER BY c.fecha_emision DESC
            """,
            (propietario_id,),
        )
        st.dataframe(certificados, use_container_width=True, hide_index=True)
    with tab_rec:
        recordatorios = fetch_data(
            """
            SELECT fecha_programada, tipo_recordatorio, caravana, mensaje, canal, enviado
            FROM recordatorios WHERE propietario_id = ? ORDER BY fecha_programada DESC
            """,
            (propietario_id,),
        )
        st.dataframe(recordatorios, use_container_width=True, hide_index=True)
    with tab_fact:
        facturas = fetch_data(
            """
            SELECT numero_factura, fecha_emision, tipo_comprobante, descripcion, total, estado_pago
            FROM facturacion WHERE propietario_id = ? ORDER BY fecha_emision DESC
            """,
            (propietario_id,),
        )
        st.dataframe(facturas, use_container_width=True, hide_index=True)

# --- USUARIOS ---
def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"

def verificar_password(password, password_hash):
    stored = str(password_hash or "")
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, digest = stored.split("$", 3)
            calculated = hashlib.pbkdf2_hmac(
                "sha256",
                str(password).encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(calculated, digest)
        except Exception:
            return False

    legacy_digest = hashlib.sha256(str(password).encode()).hexdigest()
    return hmac.compare_digest(legacy_digest, stored)

def requiere_rehash(password_hash):
    return not str(password_hash or "").startswith("pbkdf2_sha256$")

def normalizar_usuario(username):
    return str(username or "").strip().lower()

def requiere_configuracion_inicial():
    usuarios = fetch_data("SELECT id, username, password_hash FROM usuarios ORDER BY id")
    if usuarios.empty:
        return True
    if len(usuarios) == 1:
        unico = usuarios.iloc[0]
        return (
            normalizar_usuario(unico["username"]) == DEFAULT_ADMIN_USERNAME
            and str(unico["password_hash"] or "") == DEFAULT_ADMIN_LEGACY_HASH
        )
    return False

def usuario_actual_es_admin():
    usuario = st.session_state.get("usuario") or {}
    return str(usuario.get("rol", "")).strip().lower() == "administrador"

MENUS_POR_ROL = {
    "Administrador": "TODOS",
    "Veterinario": [
        "Dashboard Analitico", "Busqueda Global", "Trazabilidad e Inventario", "Propietarios/Clientes",
        "Pizarra Clinica", "Historia Clinica", "Sanidad y Brucelosis", "Hospitalizacion",
        "Agenda/Citas", "Laboratorio", "Farmacia/Stock", "Recetario Digital", "Facturacion",
        "CRM y Seguimiento", "Recordatorios", "Produccion y Pesajes", "Reproduccion",
        "Intervenciones", "Certificados", "Lotes/Potreros", "Alertas y Notificaciones",
        "Exportar Reportes (PDF)", "BI - Analitica Avanzada",
    ],
    "Tecnico": [
        "Dashboard Analitico", "Busqueda Global", "Trazabilidad e Inventario", "Pizarra Clinica",
        "Sanidad y Brucelosis", "Hospitalizacion", "Agenda/Citas", "Laboratorio",
        "Farmacia/Stock", "Recordatorios", "Produccion y Pesajes", "Reproduccion",
        "Intervenciones", "Certificados", "Lotes/Potreros", "Alertas y Notificaciones",
        "Exportar Reportes (PDF)",
    ],
    "Propietario": ["Portal del Cliente"],
}

def rol_actual():
    usuario = st.session_state.get("usuario") or {}
    return str(usuario.get("rol") or "Propietario")

def menus_disponibles(opciones):
    rol = rol_actual()
    permitidos = MENUS_POR_ROL.get(rol, ["Portal del Cliente"])
    if permitidos == "TODOS":
        return opciones + ["Usuarios y Seguridad"]
    return [m for m in opciones if m in permitidos]

def propietario_id_usuario_actual():
    usuario = st.session_state.get("usuario") or {}
    propietario_id = usuario.get("propietario_id")
    if propietario_id is None or pd.isna(propietario_id):
        return None
    try:
        return int(propietario_id)
    except Exception:
        return None

def crear_usuario_app(username, password, nombre, rol, activo=1, propietario_id=None):
    username = normalizar_usuario(username)
    nombre = str(nombre or "").strip()
    rol = rol if rol in ROLES_USUARIO else "Veterinario"
    propietario_id = propietario_id if rol == "Propietario" else None
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres."
    if len(str(password or "")) < 8:
        return False, "La clave debe tener al menos 8 caracteres."
    if not nombre:
        nombre = username
    ok = run_query(
        "INSERT INTO usuarios (username, password_hash, nombre, rol, propietario_id, activo) VALUES (?, ?, ?, ?, ?, ?)",
        (username, hash_password(password), nombre, rol, propietario_id, int(bool(activo))),
    )
    if not ok:
        return False, "El usuario ya existe."
    return True, "Usuario creado."

def guardar_admin_inicial(username, password, nombre):
    username = normalizar_usuario(username)
    nombre = str(nombre or "").strip() or username
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres."
    if len(str(password or "")) < 8:
        return False, "La clave debe tener al menos 8 caracteres."

    usuarios = fetch_data("SELECT id, username, password_hash FROM usuarios ORDER BY id")
    if len(usuarios) == 1:
        unico = usuarios.iloc[0]
        if (
            normalizar_usuario(unico["username"]) == DEFAULT_ADMIN_USERNAME
            and str(unico["password_hash"] or "") == DEFAULT_ADMIN_LEGACY_HASH
        ):
            ok = run_query(
                "UPDATE usuarios SET username = ?, password_hash = ?, nombre = ?, rol = 'Administrador', activo = 1 WHERE id = ?",
                (username, hash_password(password), nombre, int(unico["id"])),
            )
            return (ok, "Administrador actualizado.") if ok else (False, "No se pudo actualizar el administrador inicial.")

    return crear_usuario_app(username, password, nombre, "Administrador", activo=1)

def actualizar_usuario_app(user_id, nombre, rol, activo, propietario_id=None):
    rol = rol if rol in ROLES_USUARIO else "Veterinario"
    propietario_id = propietario_id if rol == "Propietario" else None
    ok = run_query(
        "UPDATE usuarios SET nombre = ?, rol = ?, propietario_id = ?, activo = ? WHERE id = ?",
        (str(nombre or "").strip(), rol, propietario_id, int(bool(activo)), int(user_id)),
    )
    return ok

def cambiar_password_usuario_app(user_id, password):
    if len(str(password or "")) < 8:
        return False, "La clave debe tener al menos 8 caracteres."
    ok = run_query("UPDATE usuarios SET password_hash = ? WHERE id = ?", (hash_password(password), int(user_id)))
    return ok, "Clave actualizada." if ok else "No se pudo actualizar la clave."

def render_setup_inicial():
    st.markdown('<div class="gg-auth-kicker">Gestion Ganadera SENASA</div>', unsafe_allow_html=True)
    st.title("Configuracion inicial")
    st.caption("Crea el primer administrador. Despues, los usuarios se gestionan solo desde dentro del sistema.")
    col_form, col_info = st.columns([0.58, 0.42], gap="large")
    with col_form:
        with st.form("setup_admin_inicial"):
            username = st.text_input("Usuario administrador")
            nombre = st.text_input("Nombre")
            password = st.text_input("Clave", type="password")
            password2 = st.text_input("Repetir clave", type="password")
            if st.form_submit_button("Crear administrador"):
                if password != password2:
                    st.error("Las claves no coinciden.")
                else:
                    ok, msg = guardar_admin_inicial(username, password, nombre)
                    if ok:
                        st.success("Administrador creado. Ahora inicia sesion.")
                        st.rerun()
                    else:
                        st.error(msg)
    with col_info:
        st.markdown(
            """
            <div class="gg-auth-panel">
                <div class="gg-auth-panel-title">Acceso protegido</div>
                <p>El primer usuario queda como administrador y desde ahi se crean los demas accesos.</p>
                <p>Usa una clave fuerte. El sistema guarda contrasenas con hash seguro PBKDF2.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

def render_login():
    st.markdown('<div class="gg-auth-kicker">Gestion Ganadera SENASA</div>', unsafe_allow_html=True)
    st.title("Inicio de Sesion")
    st.caption("Acceso privado para gestion sanitaria, trazabilidad y administracion ganadera.")
    col_form, col_info = st.columns([0.58, 0.42], gap="large")
    with col_form:
        with st.form("login"):
            username = st.text_input("Usuario")
            password = st.text_input("Clave", type="password")
            if st.form_submit_button("Ingresar"):
                username_norm = normalizar_usuario(username)
                df = fetch_data("SELECT * FROM usuarios WHERE username = ? AND activo = 1", (username_norm,))
                if not df.empty and verificar_password(password, df["password_hash"].iloc[0]):
                    if requiere_rehash(df["password_hash"].iloc[0]):
                        run_query("UPDATE usuarios SET password_hash = ? WHERE id = ?", (hash_password(password), int(df["id"].iloc[0])))
                        df = fetch_data("SELECT * FROM usuarios WHERE id = ?", (int(df["id"].iloc[0]),))
                    st.session_state.usuario = df.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos")
    with col_info:
        st.markdown(
            """
            <div class="gg-auth-panel">
                <div class="gg-auth-panel-title">Sistema ganadero integral</div>
                <p>Gestiona inventario, sanidad, reproduccion, farmacia, facturacion y reportes desde un unico panel.</p>
                <p>Si necesitas acceso, solicitalo a un administrador del establecimiento.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

def render_usuarios_admin():
    st.title("Usuarios y Seguridad")
    st.caption("Solo los administradores pueden crear usuarios, cambiar roles, activar accesos o resetear claves.")
    propietarios = fetch_data("SELECT id, nombre, apellido, email FROM propietarios ORDER BY apellido, nombre")
    propietario_opciones = [0] + (propietarios["id"].tolist() if not propietarios.empty else [])
    def nombre_propietario(pid):
        if pid == 0 or propietarios.empty:
            return "Sin cliente vinculado"
        fila = propietarios[propietarios["id"] == pid].iloc[0]
        return f"{fila['nombre']} {fila['apellido']} - {fila['email'] or 'sin email'}"

    with st.expander("Crear usuario", expanded=True):
        with st.form("crear_usuario_admin", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                username = st.text_input("Usuario")
                nombre = st.text_input("Nombre completo")
                rol = st.selectbox("Rol", ROLES_USUARIO, index=1)
            with c2:
                password = st.text_input("Clave inicial", type="password")
                activo = st.checkbox("Activo", value=True)
                propietario_sel = st.selectbox("Cliente vinculado", propietario_opciones, format_func=nombre_propietario)
            if st.form_submit_button("Crear usuario"):
                propietario_id = None if propietario_sel == 0 else propietario_sel
                ok, msg = crear_usuario_app(username, password, nombre, rol, activo, propietario_id)
                if ok:
                    registrar_auditoria("crear_usuario", "usuarios", username, f"Rol: {rol}")
                    st.success(msg)
                else:
                    st.error(msg)

    usuarios = fetch_data("""
        SELECT u.id, u.username, u.nombre, u.rol, u.activo, u.propietario_id,
               COALESCE(p.nombre || ' ' || p.apellido, '') as cliente_vinculado
        FROM usuarios u LEFT JOIN propietarios p ON u.propietario_id = p.id
        ORDER BY u.username
    """)
    st.dataframe(usuarios, width=1200, hide_index=True)

    if usuarios.empty:
        return

    st.markdown("### Editar usuario")
    user_id = st.selectbox(
        "Usuario",
        usuarios["id"].tolist(),
        format_func=lambda uid: usuarios.loc[usuarios["id"] == uid, "username"].iloc[0],
    )
    usuario_row = usuarios[usuarios["id"] == user_id].iloc[0]

    with st.form("editar_usuario_admin"):
        nombre_edit = st.text_input("Nombre", value=str(usuario_row["nombre"] or ""))
        rol_edit = st.selectbox("Rol", ROLES_USUARIO, index=ROLES_USUARIO.index(usuario_row["rol"]) if usuario_row["rol"] in ROLES_USUARIO else 1)
        prop_actual = int(usuario_row["propietario_id"]) if pd.notna(usuario_row["propietario_id"]) else 0
        prop_index = propietario_opciones.index(prop_actual) if prop_actual in propietario_opciones else 0
        propietario_edit = st.selectbox("Cliente vinculado", propietario_opciones, index=prop_index, format_func=nombre_propietario)
        activo_edit = st.checkbox("Activo", value=bool(usuario_row["activo"]))
        if st.form_submit_button("Guardar cambios"):
            propietario_id = None if propietario_edit == 0 else propietario_edit
            if actualizar_usuario_app(user_id, nombre_edit, rol_edit, activo_edit, propietario_id):
                if st.session_state.usuario.get("id") == user_id:
                    st.session_state.usuario.update({"nombre": nombre_edit, "rol": rol_edit, "propietario_id": propietario_id, "activo": int(bool(activo_edit))})
                registrar_auditoria("actualizar_usuario", "usuarios", user_id, f"Rol: {rol_edit} Activo: {int(bool(activo_edit))}")
                st.success("Usuario actualizado.")
            else:
                st.error("No se pudo actualizar el usuario.")

    with st.form("reset_password_admin"):
        nueva = st.text_input("Nueva clave", type="password")
        nueva2 = st.text_input("Repetir nueva clave", type="password")
        if st.form_submit_button("Resetear clave"):
            if nueva != nueva2:
                st.error("Las claves no coinciden.")
            else:
                ok, msg = cambiar_password_usuario_app(user_id, nueva)
                if ok:
                    registrar_auditoria("reset_password", "usuarios", user_id, "Clave actualizada por administrador")
                    st.success(msg)
                else:
                    st.error(msg)

    with st.expander("Auditoria del sistema"):
        auditoria = fetch_data(
            "SELECT creado_en, usuario, rol, accion, entidad, entidad_id, detalle FROM audit_log ORDER BY creado_en DESC LIMIT 200"
        )
        st.dataframe(auditoria, use_container_width=True, hide_index=True)

def aplicar_estilo_global():
    st.markdown(
        """
        <style>
        :root {
            --gg-bg: #0b1120;
            --gg-panel: #111827;
            --gg-panel-2: #162033;
            --gg-border: #253247;
            --gg-text: #e5e7eb;
            --gg-muted: #9ca3af;
            --gg-green: #22c55e;
            --gg-teal: #2dd4bf;
            --gg-gold: #f59e0b;
            --gg-danger: #f87171;
        }
        .stApp {
            background: var(--gg-bg);
            color: var(--gg-text);
        }
        section[data-testid="stSidebar"] {
            background: #080d19;
            border-right: 1px solid var(--gg-border);
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--gg-text);
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--gg-green);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }
        [data-testid="stAppViewContainer"] > .main .block-container {
            background: transparent;
        }
        .gg-header {
            border: 1px solid var(--gg-border);
            background: #101827;
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 18px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
        }
        .gg-kicker {
            color: var(--gg-teal);
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .gg-title {
            color: var(--gg-green);
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
        }
        .gg-subtitle {
            color: var(--gg-muted);
            margin-top: 8px;
            max-width: 900px;
        }
        .gg-auth-kicker {
            color: var(--gg-teal);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .gg-auth-panel {
            background: #111827;
            border: 1px solid var(--gg-border);
            border-radius: 8px;
            padding: 22px;
            min-height: 220px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
        }
        .gg-auth-panel-title {
            color: var(--gg-green);
            font-size: 1.15rem;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .gg-auth-panel p {
            color: var(--gg-muted);
            margin-bottom: 10px;
            line-height: 1.55;
        }
        .st-emotion-cache-1jicfl2, .st-emotion-cache-13ln4jf {
            padding-top: 2rem;
        }
        div[data-testid="stMetric"] {
            background: var(--gg-panel);
            border: 1px solid var(--gg-border);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.18);
        }
        div[data-testid="stMetricLabel"] p {
            color: var(--gg-muted);
            font-size: .82rem;
        }
        div[data-testid="stMetricValue"] {
            color: var(--gg-green);
        }
        div[data-testid="stExpander"] {
            background: var(--gg-panel);
            border: 1px solid var(--gg-border);
            border-radius: 8px;
        }
        div[data-testid="stForm"] {
            background: var(--gg-panel);
            border: 1px solid var(--gg-border);
            border-radius: 8px;
            padding: 22px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--gg-border);
            border-radius: 8px;
            overflow: hidden;
        }
        label, .stTextInput label, .stSelectbox label, .stNumberInput label,
        .stDateInput label, .stTextArea label, .stRadio label, .stCheckbox label {
            color: var(--gg-text) !important;
            font-weight: 700;
        }
        input, textarea, [data-baseweb="input"] input {
            color: #f9fafb !important;
            background: #0f172a !important;
        }
        div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
            background: #0f172a !important;
            border-color: #334155 !important;
            color: #f9fafb !important;
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
            border-color: var(--gg-green) !important;
            box-shadow: 0 0 0 1px rgba(34, 197, 94, .45) !important;
        }
        .stButton > button, .stDownloadButton > button, button[kind="primaryFormSubmit"] {
            border-radius: 6px;
            border: 1px solid #22c55e;
            background: #16a34a;
            color: #06120b;
            font-weight: 700;
        }
        .stButton > button p, .stDownloadButton > button p, button[kind="primaryFormSubmit"] p {
            color: #06120b;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, button[kind="primaryFormSubmit"]:hover {
            border-color: #86efac;
            background: #22c55e;
            color: #06120b;
        }
        h1, h2, h3 {
            color: var(--gg-green);
        }
        p, span, div {
            color: inherit;
        }
        [data-testid="stAlert"] {
            border-radius: 8px;
        }
        div[role="radiogroup"] label {
            color: var(--gg-text) !important;
        }
        /* ====== MOBILE ====== */
        @media (max-width: 768px) {
            .block-container { padding: 0.8rem; max-width: 100%; }
            .gg-title { font-size: 1.3rem; }
            .gg-header { padding: 12px 16px; }
            button[kind="primary"] { width: 100% !important; }
            div[data-testid="column"] { min-width: 100% !important; }
            section[data-testid="stSidebar"] { width: 100% !important; min-width: 100% !important; }
            [data-testid="stMetric"] { padding: 6px 0; }
            [data-testid="stMetric"] label { font-size: .7rem; }
            [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.2rem; }
            .stDataFrame { overflow-x: auto; }
            .stDataFrame table { font-size: .72rem; }
            input, select, textarea { font-size: 16px !important; }
            div[data-testid="stExpander"] { font-size: .85rem; }
            .row-widget.stRadio { flex-direction: column; }
        }
        @media (max-width: 480px) {
            .gg-title { font-size: 1.1rem; }
            .gg-subtitle { font-size: .8rem; }
            [data-testid="stMetricValue"] { font-size: 1rem !important; }
            .stTabs [data-baseweb="tab"] { font-size: .72rem; padding: 8px 10px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_app_header(titulo, subtitulo=None):
    st.markdown(
        f"""
        <div class="gg-header">
            <div class="gg-kicker">{APP_NAME}</div>
            <h1 class="gg-title">{titulo}</h1>
            <div class="gg-subtitle">{subtitulo or APP_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_sidebar_usuario():
    usuario = st.session_state.usuario
    st.sidebar.markdown(
        f"""
        <div style="padding:12px;border:1px solid #253247;border-radius:8px;background:#111827;margin-bottom:12px;">
            <div style="font-size:.72rem;color:#9ca3af;text-transform:uppercase;font-weight:700;">Sesion</div>
            <div style="font-weight:800;color:#22c55e;">{usuario['nombre']}</div>
            <div style="font-size:.85rem;color:#9ca3af;">{usuario['rol']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- UI ---
st.set_page_config(page_title=APP_NAME, page_icon="AR", layout="wide", initial_sidebar_state="collapsed")
aplicar_estilo_global()

# Inicializar Supabase si está configurado
if USAR_SUPABASE:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except:
        pass

# Migraciones
def agregar_columna_si_falta(tabla, columna, definicion):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()]
            if columna not in cols:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
                conn.commit()
    except:
        pass

try:
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("ALTER TABLE bovinos ADD COLUMN propietario_id INTEGER")
        conn.commit()
except:
    pass
for tabla, columna, definicion in [
    ("historia_clinica", "subjetivo", "TEXT"),
    ("historia_clinica", "objetivo", "TEXT"),
    ("historia_clinica", "analisis", "TEXT"),
    ("historia_clinica", "plan", "TEXT"),
    ("historia_clinica", "template_id", "INTEGER"),
    ("stock", "stock_minimo", "INTEGER DEFAULT 0"),
    ("stock", "proveedor_predeterminado", "TEXT"),
    ("usuarios", "propietario_id", "INTEGER"),
]:
    agregar_columna_si_falta(tabla, columna, definicion)
sembrar_templates_ehr()
try:
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("ALTER TABLE bovinos ADD COLUMN foto TEXT")
        conn.commit()
except:
    pass

if st.session_state.usuario is None:
    if requiere_configuracion_inicial():
        render_setup_inicial()
    else:
        render_login()
    st.stop()

render_sidebar_usuario()
if st.sidebar.button("Cerrar Sesion"):
    st.session_state.usuario = None
    st.rerun()

st.sidebar.markdown("### Menu")
opciones_menu = [
    "Dashboard Analitico", "Portal del Cliente", "Busqueda Global", "Trazabilidad e Inventario", "Propietarios/Clientes",
    "Pizarra Clinica", "Historia Clinica", "Sanidad y Brucelosis", "Hospitalizacion",
    "Agenda/Citas", "Laboratorio", "Farmacia/Stock",
    "Recetario Digital", "Facturacion", "CRM y Seguimiento",
    "Recordatorios", "Produccion y Pesajes",
    "Reproduccion", "Intervenciones", "Certificados",
    "Lotes/Potreros", "Finanzas",
    "Alertas y Notificaciones", "Marco Legal y Normativas", "Exportar Reportes (PDF)",
    "BI - Analitica Avanzada"
]
opciones_menu = menus_disponibles(opciones_menu)
if not opciones_menu:
    st.error("Tu rol no tiene modulos habilitados. Contacta a un administrador.")
    st.stop()
menu = st.sidebar.radio("Navegacion", opciones_menu)
render_app_header(menu)

# ====================== USUARIOS ======================
if menu == "Usuarios y Seguridad":
    if usuario_actual_es_admin():
        render_usuarios_admin()
    else:
        st.error("No tenes permisos para administrar usuarios.")

# ====================== PORTAL CLIENTE ======================
elif menu == "Portal del Cliente":
    render_portal_cliente()

# ====================== DASHBOARD ======================
elif menu == "Dashboard Analitico":
    render_app_header("Dashboard Analitico", "Indicadores clave y estado general del establecimiento")
    crear_backup()
    df_bov = fetch_data("SELECT * FROM bovinos WHERE estado = 'Activo'")
    if not df_bov.empty:
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Cabezas", len(df_bov))
            c2.metric("Hembras", len(df_bov[df_bov['sexo'] == 'Hembra']))
            c3.metric("Machos", len(df_bov[df_bov['sexo'] == 'Macho']))
            rfid_count = len(df_bov[df_bov['tipo_identificacion'] == 'RFID (Electronica)'])
            c4.metric("RFID", f"{rfid_count} / {len(df_bov)}", delta_color="off")
        with st.container():
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Brucelosis +", len(df_bov[df_bov['estatus_brucelosis'] == 'Positivo']), delta_color="inverse")
            df_pes = fetch_data("SELECT AVG(peso_kg) as p FROM pesajes")
            prom = df_pes['p'].iloc[0] if not df_pes.empty and pd.notna(df_pes['p'].iloc[0]) else 0
            c6.metric("Peso Promedio", f"{prom:.1f} kg")
            df_repr = fetch_data("SELECT COUNT(*) as t FROM reproduccion WHERE fecha_parto IS NOT NULL")
            c7.metric("Partos", df_repr['t'].iloc[0])
            df_al = fetch_data("SELECT COUNT(*) as t FROM alertas WHERE resuelta = 0")
            c8.metric("Alertas", df_al['t'].iloc[0], delta_color="inverse")
        st.markdown("---")
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("### Categorias")
            st.bar_chart(df_bov['categoria'].value_counts(), color="#2e9140")
        with col_graf2:
            st.markdown("### Brucelosis")
            st.bar_chart(df_bov['estatus_brucelosis'].value_counts(), color="#d62728")
        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            st.markdown("### Razas")
            st.bar_chart(df_bov['raza'].value_counts(), color="#1f77b4")
        with col_graf4:
            st.markdown("### Identificacion")
            st.bar_chart(df_bov['tipo_identificacion'].value_counts(), color="#ff7f0e")
        st.markdown("---")
        st.markdown("### Indicadores")
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            nac = len(df_bov[df_bov['categoria'].str.contains('Ternero', case=False)])
            st.metric("Tasa Natalidad", f"{(nac/len(df_bov))*100:.1f}%" if len(df_bov)>0 else "0%")
        with col_e2:
            df_e = fetch_data("SELECT COUNT(*) as t FROM sanidad WHERE categoria_evento LIKE '%Clinico%'")
            st.metric("Tratamientos", df_e['t'].iloc[0] if not df_e.empty else 0)
        with col_e3:
            df_v = fetch_data("SELECT COUNT(DISTINCT caravana) as t FROM sanidad WHERE categoria_evento LIKE '%Aftosa%'")
            st.metric("Vacunados Aftosa", df_v['t'].iloc[0] if not df_v.empty else 0)
        with st.expander("Alertas de Stock - Proximos a vencer"):
            df_venc = fetch_data("""
                SELECT f.nombre_producto, s.lote, s.fecha_vencimiento, s.cantidad
                FROM stock s JOIN farmacia f ON s.producto_id = f.id
                WHERE s.fecha_vencimiento BETWEEN DATE('now') AND DATE('now', '+90 days')
            """)
            if not df_venc.empty:
                st.dataframe(df_venc, width=1200, hide_index=True)
            else:
                st.success("No hay productos proximos a vencer")
    else:
        st.info("Sistema sin registros")

# ====================== BUSQUEDA GLOBAL ======================
elif menu == "Busqueda Global":
    render_busqueda_global()

# ====================== TRAZABILIDAD ======================
elif menu == "Trazabilidad e Inventario":
    render_app_header("Trazabilidad e Inventario", "Registro oficial SIGSA - Res. SENASA 67/2019")
    df_props = fetch_data("SELECT id, nombre, apellido FROM propietarios")
    props_list = ["Sin propietario"] + [f"{r['nombre']} {r['apellido']}" for _, r in df_props.iterrows()]
    tab_alt, tab_mod = st.tabs(["Alta de Animal", "Modificar Estado"])
    with tab_alt:
        with st.form("form_alta", clear_on_submit=True):
            st.info("A partir de 2026 RFID obligatorio")
            c1, c2 = st.columns(2)
            with c1:
                caravana = st.text_input("Caravana Oficial")
                tipo_id = st.selectbox("Tecnologia", ["Visual (Tradicional)", "RFID (Electronica)", "Bolo Ruminal"])
                raza = st.selectbox("Raza", ["Angus", "Hereford", "Braford", "Brangus", "Holando", "Criolla", "Otra"])
                sexo = st.radio("Sexo", ["Macho", "Hembra"], horizontal=True)
            with c2:
                categoria = st.selectbox("Categoria", ["Ternero/a", "Vaquillona", "Novillo", "Vaca", "Toro"])
                peso_nac = st.number_input("Peso (Kg)", min_value=10.0, value=35.0)
                fecha_nac = st.date_input("Fecha Nacimiento", date.today())
                prop_idx = st.selectbox("Propietario", range(len(props_list)), format_func=lambda i: props_list[i])
            if st.form_submit_button("Registrar"):
                if caravana.strip():
                    prop_id = None if prop_idx == 0 else df_props.iloc[prop_idx - 1]['id']
                    q = "INSERT INTO bovinos (caravana, tipo_identificacion, raza, sexo, categoria, peso_nacimiento, fecha_nacimiento, propietario_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                    if run_query(q, (caravana.upper(), tipo_id, raza, sexo, categoria, peso_nac, fecha_nac, prop_id)):
                        registrar_auditoria("crear_animal", "bovinos", caravana.upper(), f"Categoria: {categoria}")
                        st.success(f"Animal {caravana.upper()} registrado.")
                    else:
                        st.error("La caravana ya existe.")
                else:
                    st.error("Caravana obligatoria.")

    with tab_mod:
        caravanas_all = obtener_lista_caravanas()
        if caravanas_all:
            with st.form("form_mod"):
                car_sel = st.selectbox("Seleccionar", caravanas_all)
                nuevo_estado = st.selectbox("Estado", ["Activo", "Mortandad", "Venta", "Cambio de Dueno"])
                if st.form_submit_button("Actualizar"):
                    run_query("UPDATE bovinos SET estado = ? WHERE caravana = ?", (nuevo_estado, car_sel))
                    registrar_auditoria("actualizar_estado_animal", "bovinos", car_sel, nuevo_estado)
                    st.success("Actualizado.")
        else:
            st.warning("No hay animales registrados.")

    st.markdown("### Padron")
    df_inv = fetch_data("""
        SELECT b.caravana, b.tipo_identificacion, b.sexo, b.categoria, b.fecha_nacimiento, b.estatus_brucelosis,
               COALESCE(p.nombre || ' ' || p.apellido, 'Sin propietario') as propietario
        FROM bovinos b LEFT JOIN propietarios p ON b.propietario_id = p.id
        WHERE b.estado='Activo'
    """)
    st.dataframe(df_inv, width=1200, hide_index=True)

# ====================== PROPIETARIOS ======================
elif menu == "Propietarios/Clientes":
    render_app_header("Propietarios y Clientes", "Alta y consulta de clientes vinculados a animales, turnos y facturacion.")
    with st.expander("Nuevo cliente", expanded=True):
        with st.form("form_propietario", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                documento = st.text_input("Documento")
            with c2:
                cuit = st.text_input("CUIT")
                telefono = st.text_input("Telefono")
                email = st.text_input("Email")
            with c3:
                direccion = st.text_input("Direccion")
                localidad = st.text_input("Localidad")
                provincia = st.text_input("Provincia")
            if st.form_submit_button("Guardar cliente"):
                if nombre.strip() or apellido.strip():
                    ok = run_query(
                        """
                        INSERT INTO propietarios
                        (nombre, apellido, documento, telefono, email, direccion, localidad, provincia, cuit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (nombre, apellido, documento, telefono, email, direccion, localidad, provincia, cuit),
                    )
                    if ok:
                        registrar_auditoria("crear_propietario", "propietarios", f"{nombre} {apellido}", email)
                        st.success("Cliente guardado.")
                    else:
                        st.error("No se pudo guardar el cliente.")
                else:
                    st.error("Nombre o apellido es obligatorio.")

    clientes = fetch_data("SELECT id, nombre, apellido, documento, cuit, telefono, email, localidad, provincia, fecha_registro FROM propietarios ORDER BY apellido, nombre")
    st.dataframe(clientes, use_container_width=True, hide_index=True)

# ====================== PIZARRA CLINICA ======================
elif menu == "Pizarra Clinica":
    render_app_header("Pizarra Clinica", "Flujo tipo Kanban para pacientes, tareas y responsables.")
    caravanas = obtener_lista_caravanas()
    estados = ["Espera", "En Consulta", "Pre-quirurgico", "Quirofano", "Recuperacion", "Listo para Alta"]

    tab_flujo, tab_tareas = st.tabs(["Flujo de pacientes", "Tareas"])
    with tab_flujo:
        with st.form("form_workflow"):
            c1, c2, c3 = st.columns(3)
            with c1:
                car_w = st.selectbox("Paciente", caravanas) if caravanas else st.text_input("Paciente")
                estado_w = st.selectbox("Estado", estados)
            with c2:
                responsable_w = st.text_input("Responsable", st.session_state.usuario["nombre"])
                prioridad_w = st.selectbox("Prioridad", ["Normal", "Alta", "Urgente"])
            with c3:
                obs_w = st.text_area("Observaciones")
            if st.form_submit_button("Actualizar estado"):
                run_query(
                    """
                    INSERT INTO workflow_pacientes (caravana, estado, responsable, prioridad, observaciones, actualizado_en)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(caravana) DO UPDATE SET
                        estado=excluded.estado,
                        responsable=excluded.responsable,
                        prioridad=excluded.prioridad,
                        observaciones=excluded.observaciones,
                        actualizado_en=CURRENT_TIMESTAMP
                    """,
                    (car_w, estado_w, responsable_w, prioridad_w, obs_w),
                )
                registrar_auditoria("actualizar_pizarra", "workflow_pacientes", car_w, f"{estado_w} - {prioridad_w}")
                st.success("Estado actualizado.")

        df_flow = fetch_data("SELECT * FROM workflow_pacientes ORDER BY actualizado_en DESC")
        cols = st.columns(3)
        for idx, estado in enumerate(estados):
            with cols[idx % 3]:
                st.markdown(f"### {estado}")
                subset = df_flow[df_flow["estado"] == estado] if not df_flow.empty else pd.DataFrame()
                if subset.empty:
                    st.info("Sin pacientes")
                else:
                    st.dataframe(subset[["caravana", "prioridad", "responsable", "actualizado_en"]], use_container_width=True, hide_index=True)

    with tab_tareas:
        with st.form("form_tarea"):
            c1, c2 = st.columns(2)
            with c1:
                car_t = st.selectbox("Paciente", caravanas, key="tarea_car") if caravanas else st.text_input("Paciente", key="tarea_car_text")
                tarea = st.text_input("Tarea")
            with c2:
                asignado = st.text_input("Asignado a")
                vence = st.date_input("Vence", date.today())
            if st.form_submit_button("Crear tarea"):
                run_query(
                    "INSERT INTO workflow_tareas (caravana, tarea, asignado_a, vence_en) VALUES (?, ?, ?, ?)",
                    (car_t, tarea, asignado, vence),
                )
                registrar_auditoria("crear_tarea_clinica", "workflow_tareas", car_t, tarea)
                st.success("Tarea creada.")
        df_tareas = fetch_data("SELECT * FROM workflow_tareas ORDER BY estado, vence_en")
        st.dataframe(df_tareas, use_container_width=True, hide_index=True)

# ====================== HISTORIA CLINICA ======================
elif menu == "Historia Clinica":
    render_app_header("Historia Clinica SOAP", "Plantillas, auto-billing, recordatorios y trazabilidad clinica.")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        car_sel = st.selectbox("Seleccionar Animal", caravanas, key="hc_car")
        templates = fetch_data("SELECT * FROM ehr_templates WHERE activo = 1 ORDER BY nombre")
        df_hist = fetch_data("""
            SELECT fecha_consulta, motivo_consulta, subjetivo, objetivo, analisis, plan, veterinario
            FROM historia_clinica WHERE caravana = ? ORDER BY fecha_consulta DESC
        """, (car_sel,))
        st.dataframe(df_hist, width=1200, hide_index=True)

        with st.expander("Nueva Consulta SOAP", expanded=True):
            tpl_id = None
            tpl = {}
            if not templates.empty:
                tpl_id = st.selectbox(
                    "Plantilla",
                    [0] + templates["id"].tolist(),
                    format_func=lambda x: "Sin plantilla" if x == 0 else templates.loc[templates["id"] == x, "nombre"].iloc[0],
                )
                if tpl_id:
                    tpl = templates[templates["id"] == tpl_id].iloc[0].to_dict()
                    st.info("La plantilla carga SOAP, cargos sugeridos y recordatorios automaticos.")
            with st.form("form_hc", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    motivo = st.text_area("Motivo de consulta", value=tpl.get("motivo", ""))
                    subjetivo = st.text_area("S - Subjetivo", value=tpl.get("subjetivo", ""))
                    objetivo = st.text_area("O - Objetivo", value=tpl.get("objetivo", ""))
                with c2:
                    analisis = st.text_area("A - Analisis / Diagnostico", value=tpl.get("analisis", ""))
                    plan = st.text_area("P - Plan / Tratamiento", value=tpl.get("plan", ""))
                    diagnostico = st.text_input("Diagnostico principal")
                observaciones = st.text_area("Observaciones")
                if st.form_submit_button("Guardar Consulta"):
                    consulta_id = run_insert_return_id(
                        """
                        INSERT INTO historia_clinica
                        (caravana, motivo_consulta, anamnesis, exploracion_fisica, diagnostico_presuntivo,
                         diagnostico_definitivo, tratamiento, observaciones, veterinario,
                         subjetivo, objetivo, analisis, plan, template_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            car_sel, motivo, subjetivo, objetivo, analisis,
                            diagnostico, plan, observaciones, st.session_state.usuario['nombre'],
                            subjetivo, objetivo, analisis, plan, tpl_id,
                        ),
                    )
                    if consulta_id:
                        aplicar_automatizaciones_consulta(consulta_id, car_sel, tpl_id)
                        registrar_auditoria("crear_historia_clinica", "historia_clinica", consulta_id, f"Paciente: {car_sel}")
                        st.success("Consulta registrada. Automatizaciones aplicadas.")
                    else:
                        st.error("No se pudo guardar la consulta.")

        with st.expander("Plantillas y reglas de automatizacion"):
            if not templates.empty:
                st.dataframe(templates[["id", "nombre", "motivo", "activo"]], use_container_width=True, hide_index=True)
                template_sel = st.selectbox("Plantilla para ver reglas", templates["id"].tolist(), format_func=lambda x: templates.loc[templates["id"] == x, "nombre"].iloc[0])
                reglas = fetch_data("SELECT concepto, cantidad, precio_unitario, stock_cantidad, recordatorio_meses, recordatorio_mensaje FROM ehr_template_items WHERE template_id = ?", (template_sel,))
                st.dataframe(reglas, use_container_width=True, hide_index=True)
                with st.form("form_regla_template", clear_on_submit=True):
                    st.markdown("#### Agregar regla")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        concepto = st.text_input("Concepto")
                        cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
                    with c2:
                        precio = st.number_input("Precio unitario", min_value=0.0, value=0.0, step=100.0)
                        stock_cant = st.number_input("Descontar stock", min_value=0, value=0, step=1)
                    with c3:
                        meses = st.number_input("Recordatorio en meses", min_value=0, value=0, step=1)
                        mensaje = st.text_input("Mensaje recordatorio")
                    if st.form_submit_button("Agregar regla"):
                        if concepto.strip():
                            run_query(
                                """
                                INSERT INTO ehr_template_items
                                (template_id, concepto, cantidad, precio_unitario, stock_cantidad, recordatorio_meses, recordatorio_mensaje)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (template_sel, concepto.strip(), cantidad, precio, stock_cant, meses, mensaje),
                            )
                            registrar_auditoria("crear_regla_template", "ehr_template_items", template_sel, concepto)
                            st.success("Regla agregada.")
                        else:
                            st.error("El concepto es obligatorio.")
            with st.form("form_template_ehr", clear_on_submit=True):
                st.markdown("#### Crear plantilla SOAP")
                nombre_tpl = st.text_input("Nombre de plantilla")
                motivo_tpl = st.text_area("Motivo")
                c1, c2 = st.columns(2)
                with c1:
                    subj_tpl = st.text_area("S - Subjetivo")
                    obj_tpl = st.text_area("O - Objetivo")
                with c2:
                    ana_tpl = st.text_area("A - Analisis")
                    plan_tpl = st.text_area("P - Plan")
                if st.form_submit_button("Crear plantilla"):
                    if nombre_tpl.strip():
                        ok = run_query(
                            "INSERT INTO ehr_templates (nombre, motivo, subjetivo, objetivo, analisis, plan) VALUES (?, ?, ?, ?, ?, ?)",
                            (nombre_tpl.strip(), motivo_tpl, subj_tpl, obj_tpl, ana_tpl, plan_tpl),
                        )
                        if ok:
                            registrar_auditoria("crear_template_ehr", "ehr_templates", nombre_tpl, "Plantilla SOAP creada")
                            st.success("Plantilla creada.")
                        else:
                            st.error("No se pudo crear la plantilla. Revisa que no exista otra con el mismo nombre.")
                    else:
                        st.error("El nombre es obligatorio.")
    else:
        st.warning("No hay animales registrados.")

# ====================== SANIDAD ======================
elif menu == "Sanidad y Brucelosis":
    st.title("Gestion Sanitaria")
    verificar_alertas()
    caravanas = obtener_lista_caravanas()
    if caravanas:
        tab1, tab2 = st.tabs(["Vacunacion y Tratamientos", "Control Brucelosis"])
        with tab1:
            with st.form("form_med", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    caravana_sel = st.selectbox("Caravana", caravanas)
                    tipo_ev = st.selectbox("Evento", ["Aftosa (Campania)", "Carbunclo", "Desparasitacion", "Tratamiento Clinico"])
                    med = st.text_input("Producto")
                with c2:
                    dosis = st.text_input("Dosis (ml)")
                    fecha = st.date_input("Fecha", date.today())
                    vet = st.text_input("Matricula")
                if st.form_submit_button("Guardar"):
                    if med:
                        run_query("INSERT INTO sanidad (caravana, categoria_evento, medicamento, dosis, fecha_aplicacion, veterinario_acreditado) VALUES (?, ?, ?, ?, ?, ?)",
                                 (caravana_sel, tipo_ev, med, dosis, fecha, vet))
                        st.success("Registrado.")
                    else:
                        st.error("Ingrese producto.")
        with tab2:
            st.warning("Terneras 3-8 meses deben recibir Cepa 19")
            with st.form("form_brucelosis"):
                car_bruc = st.selectbox("Animal", caravanas, key="bruc")
                accion = st.radio("Accion", ["Vacunacion Cepa 19", "Resultado Sangrado"])
                resultado = st.selectbox("Resultado", ["Negativo", "Positivo (Interdictar)", "Sospechoso"])
                if st.form_submit_button("Actualizar"):
                    if accion == "Resultado Sangrado":
                        est = "Negativo" if resultado == "Negativo" else "Positivo"
                        run_query("UPDATE bovinos SET estatus_brucelosis = ? WHERE caravana = ?", (est, car_bruc))
                        run_query("INSERT INTO sanidad (caravana, categoria_evento, medicamento, dosis, fecha_aplicacion) VALUES (?, 'Sangrado Brucelosis', ?, '-', DATE('now'))", (car_bruc, resultado))
                        if est == "Positivo":
                            st.error(f"ALERTA: {car_bruc} interdictado. Informar a SENASA.")
                        else:
                            st.success("Actualizado.")
                    else:
                        run_query("INSERT INTO sanidad (caravana, categoria_evento, medicamento, dosis, fecha_aplicacion) VALUES (?, 'Vacuna Brucelosis', 'Cepa 19', 'Unica', DATE('now'))", (car_bruc,))
                        st.success("Vacunacion registrada.")

        st.markdown("### Historial")
        df_sani = fetch_data("SELECT fecha_aplicacion, caravana, categoria_evento, medicamento FROM sanidad ORDER BY fecha_aplicacion DESC")
        st.dataframe(df_sani, width=1200, hide_index=True)
    else:
        st.warning("No hay animales activos.")

# ====================== HOSPITALIZACION ======================
elif menu == "Hospitalizacion":
    st.title("Hospitalizacion y Kardex")
    caravanas = obtener_lista_caravanas()

    tab_h1, tab_h2, tab_h3 = st.tabs(["Internados", "Nuevo Ingreso", "Kardex Diario"])

    with tab_h1:
        df_int = fetch_data("""
            SELECT h.id, h.caravana, h.fecha_ingreso, h.motivo, h.diagnostico_ingreso,
                   h.veterinario_responsable, h.estado, b.raza
            FROM hospitalizacion h JOIN bovinos b ON h.caravana = b.caravana
            WHERE h.estado = 'Internado' ORDER BY h.fecha_ingreso DESC
        """)
        if not df_int.empty:
            st.warning(f"{len(df_int)} animales internados")
            for _, r in df_int.iterrows():
                dias = (date.today() - datetime.strptime(r['fecha_ingreso'], '%Y-%m-%d').date()).days
                with st.container():
                    st.markdown(f"**{r['caravana']}** ({r['raza']}) - Ingreso: {r['fecha_ingreso']} ({dias}dias)")
                    st.markdown(f"Motivo: {r['motivo']} | Vet: {r['veterinario_responsable']}")
                    if st.button(f"Dar de alta {r['id']}", key=f"alta_{r['id']}"):
                        run_query("UPDATE hospitalizacion SET estado = 'Alta', fecha_egreso = DATE('now') WHERE id = ?", (r['id'],))
                        st.rerun()
        else:
            st.success("No hay animales internados")

    with tab_h2:
        with st.form("form_internacion", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                car_int = st.selectbox("Animal", caravanas)
                motivo = st.text_area("Motivo internacion")
                diag = st.text_area("Diagnostico ingreso")
            with c2:
                trat = st.text_area("Tratamiento")
                vet_resp = st.text_input("Veterinario responsable", st.session_state.usuario['nombre'])
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Internar"):
                run_query("INSERT INTO hospitalizacion (caravana, motivo, diagnostico_ingreso, tratamiento, veterinario_responsable, observaciones) VALUES (?, ?, ?, ?, ?, ?)",
                         (car_int, motivo, diag, trat, vet_resp, obs))
                st.success(f"{car_int} internado.")

    with tab_h3:
        df_hosp_act = fetch_data("SELECT id, caravana FROM hospitalizacion WHERE estado = 'Internado'")
        if not df_hosp_act.empty:
            sel_h = st.selectbox("Seleccionar internado", df_hosp_act['id'].tolist(),
                                format_func=lambda i: f"{df_hosp_act[df_hosp_act['id']==i]['caravana'].values[0]} (ID:{i})")
            with st.form("form_kardex", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    temp = st.number_input("Temperatura C", 35.0, 42.0, 38.5)
                    fc = st.number_input("FC (lpm)", 30, 120, 70)
                with c2:
                    fr = st.number_input("FR (rpm)", 10, 80, 30)
                    obs_k = st.text_area("Observacion")
                with c3:
                    med_k = st.text_input("Medicacion")
                    vet_k = st.text_input("Veterinario", st.session_state.usuario['nombre'])
                if st.form_submit_button("Registrar"):
                    run_query("INSERT INTO kardex_hospitalario (hospitalizacion_id, veterinario, temperatura, frecuencia_cardiaca, frecuencia_respiratoria, observacion, medicacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (sel_h, vet_k, temp, fc, fr, obs_k, med_k))
                    st.success("Registro kardex guardado.")

            st.markdown("### Historial Kardex")
            df_kardex = fetch_data("SELECT * FROM kardex_hospitalario WHERE hospitalizacion_id = ? ORDER BY fecha DESC", (sel_h,))
            st.dataframe(df_kardex, width=1200, hide_index=True)

# ====================== AGENDA ======================
elif menu == "Agenda/Citas":
    st.title("Agenda y Calendario de Citas")
    hoy = date.today()
    sel_fecha = st.date_input("Fecha", hoy)

    with st.expander("Nuevo Evento"):
        caravanas = obtener_lista_caravanas()
        df_props = fetch_data("SELECT id, nombre, apellido FROM propietarios")
        with st.form("form_evento", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                fecha_ev = st.date_input("Fecha", hoy)
                hora_ev = st.time_input("Hora", datetime.now().time())
                tipo_ev = st.selectbox("Tipo", ["Consulta", "Vacunacion", "Inseminacion", "Sangrado", "Parto", "Desparasitacion", "Cirugia", "Visita a campo"])
                titulo = st.text_input("Titulo")
            with c2:
                car_ev = st.selectbox("Animal (opcional)", ["N/A"] + caravanas)
                props_opts = df_props['id'].tolist()
                prop_ev = st.selectbox("Propietario (opcional)", ["N/A"] + props_opts)
                vet = st.text_input("Veterinario", st.session_state.usuario['nombre'])
                desc = st.text_area("Descripcion")

            if st.form_submit_button("Agendar"):
                run_query("INSERT INTO agenda (fecha_evento, hora_evento, tipo_evento, titulo, caravana, propietario_id, veterinario, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (fecha_ev, str(hora_ev), tipo_ev, titulo,
                          None if car_ev == "N/A" else car_ev,
                          None if prop_ev == "N/A" else prop_ev,
                          vet, desc))
                st.success("Evento agendado.")

    df_agenda = fetch_data("""
        SELECT a.fecha_evento, a.hora_evento, a.tipo_evento, a.titulo, a.caravana, a.veterinario, a.estado
        FROM agenda a WHERE a.fecha_evento = ? ORDER BY a.hora_evento
    """, (sel_fecha,))

    if not df_agenda.empty:
        st.markdown(f"### Eventos del {sel_fecha}")
        for _, row in df_agenda.iterrows():
            color = {"Pendiente": "warning", "Realizado": "success", "Cancelado": "error"}.get(row['estado'], "info")
            with st.container():
                st.markdown(f":{color}[**{row['hora_evento']}** - {row['tipo_evento']}: {row['titulo']} (Vet: {row['veterinario']})]")
    else:
        st.info("Sin eventos para esta fecha.")

    st.markdown("### Todas las citas pendientes")
    df_pend = fetch_data("SELECT * FROM agenda WHERE estado = 'Pendiente' ORDER BY fecha_evento")
    st.dataframe(df_pend, width=1200, hide_index=True)

    with st.expander("Marcar como Realizada"):
        pend_ids = df_pend['id'].tolist() if not df_pend.empty else []
        if pend_ids:
            with st.form("form_realizada"):
                sel_ev = st.selectbox("Evento", pend_ids)
                if st.form_submit_button("Marcar Realizada"):
                    run_query("UPDATE agenda SET estado = 'Realizado' WHERE id = ?", (sel_ev,))
                    st.success("Marcado.")

# ====================== LABORATORIO ======================
elif menu == "Laboratorio":
    st.title("Laboratorio y Diagnosticos")
    caravanas = obtener_lista_caravanas()

    tab_l1, tab_l2, tab_l3 = st.tabs(["Solicitar Analisis", "Resultados", "Historial"])

    with tab_l1:
        with st.form("form_lab", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                car_lab = st.selectbox("Animal", caravanas)
                tipo = st.selectbox("Tipo analisis", ["Analisis clinico", "Serologia", "Parasitologico", "PCR", "Brucelosis", "Tuberculosis", "Leucosis", "IBR", "BVD", "Coprologico", "Histopatologia", "Otro"])
                muestra = st.text_input("Tipo de muestra")
            with c2:
                fecha_toma = st.date_input("Fecha toma muestra", date.today())
                lab_ext = st.text_input("Laboratorio externo")
                soli_por = st.text_input("Solicitado por", st.session_state.usuario['nombre'])
            if st.form_submit_button("Solicitar"):
                run_query("INSERT INTO laboratorio (caravana, tipo_analisis, muestra, fecha_toma, solicitado_por, laboratorio_externo) VALUES (?, ?, ?, ?, ?, ?)",
                         (car_lab, tipo, muestra, fecha_toma, soli_por, lab_ext))
                st.success("Analisis solicitado.")

    with tab_l2:
        df_labs_pend = fetch_data("SELECT * FROM laboratorio WHERE fecha_resultado IS NULL ORDER BY fecha_solicitud DESC")
        if not df_labs_pend.empty:
            sel_lab = st.selectbox("Seleccionar analisis", df_labs_pend['id'].tolist(),
                                  format_func=lambda i: f"{df_labs_pend[df_labs_pend['id']==i]['caravana'].values[0]} - {df_labs_pend[df_labs_pend['id']==i]['tipo_analisis'].values[0]} ({df_labs_pend[df_labs_pend['id']==i]['fecha_solicitud'].values[0]})")
            with st.form("form_resultado"):
                resultado = st.text_area("Resultado del analisis")
                obs_lab = st.text_area("Observaciones")
                num_params = st.number_input("Parametros a registrar", 0, 20, 0)
                params = []
                for i in range(num_params):
                    cols = st.columns(5)
                    with cols[0]:
                        p = st.text_input("Parametro", key=f"p_{i}")
                    with cols[1]:
                        v = st.text_input("Valor", key=f"v_{i}")
                    with cols[2]:
                        u = st.text_input("Unidad", key=f"u_{i}")
                    with cols[3]:
                        r = st.text_input("Rango ref", key=f"r_{i}")
                    with cols[4]:
                        e = st.selectbox("Estado", ["Normal", "Alto", "Bajo", "Critico"], key=f"e_{i}")
                    params.append((p, v, u, r, e))
                if st.form_submit_button("Guardar Resultados"):
                    run_query("UPDATE laboratorio SET resultado = ?, fecha_resultado = DATE('now'), observaciones = ? WHERE id = ?", (resultado, obs_lab, sel_lab))
                    for p in params:
                        if p[0]:
                            run_query("INSERT INTO resultados_laboratorio (laboratorio_id, parametro, valor, unidad, rango_referencia, estado) VALUES (?, ?, ?, ?, ?, ?)", (sel_lab, p[0], p[1], p[2], p[3], p[4]))
                    st.success("Resultados guardados.")
        else:
            st.success("No hay analisis pendientes")

    with tab_l3:
        df_labs = fetch_data("""
            SELECT l.fecha_solicitud, l.caravana, l.tipo_analisis, l.muestra, l.fecha_resultado, l.resultado, l.laboratorio_externo
            FROM laboratorio l ORDER BY l.fecha_solicitud DESC LIMIT 100
        """)
        st.dataframe(df_labs, width=1200, hide_index=True)

# ====================== FACTURACION ======================
elif menu == "Facturacion":
    st.title("Facturacion y Cobros")
    df_props = fetch_data("SELECT id, nombre, apellido, cuit FROM propietarios ORDER BY apellido")

    tab_f1, tab_f2 = st.tabs(["Nueva Factura", "Historial"])

    with tab_f1:
        with st.form("form_factura"):
            c1, c2 = st.columns(2)
            with c1:
                nro_fact = st.text_input("Numero de factura")
                prop_sel = st.selectbox("Propietario/Cliente", df_props['id'].tolist(),
                                       format_func=lambda i: f"{df_props[df_props['id']==i]['nombre'].values[0]} {df_props[df_props['id']==i]['apellido'].values[0]} - CUIT: {df_props[df_props['id']==i]['cuit'].values[0]}" if not df_props.empty else "")
                tipo_comp = st.selectbox("Tipo", ["Factura A", "Factura B", "Factura C", "Recibo", "Presupuesto", "Nota de debito", "Nota de credito"])
            with c2:
                fecha_fac = st.date_input("Fecha emision", date.today())
                metodo = st.selectbox("Metodo pago", ["Efectivo", "Transferencia", "Tarjeta credito", "Tarjeta debito", "Cheque", "Mercado Pago", "Cuenta corriente"])
                desc_fac = st.text_area("Descripcion")

            st.markdown("#### Detalle")
            num_items = st.number_input("Items", 1, 20, 1)
            items = []
            total_calc = 0
            for i in range(num_items):
                cols = st.columns(4)
                with cols[0]:
                    conc = st.text_input("Concepto", key=f"conc_{i}")
                with cols[1]:
                    cant = st.number_input("Cant", 1, 9999, 1, key=f"cant_{i}")
                with cols[2]:
                    pu = st.number_input("Precio unit", 0.0, 999999.0, 0.0, key=f"pu_{i}")
                with cols[3]:
                    sub = cant * pu
                    st.write(f"Subtotal: ${sub:,.2f}")
                    total_calc += sub
                items.append((conc, cant, pu, sub))

            st.info(f"**TOTAL:** ${total_calc:,.2f}")
            iva = total_calc * 0.21
            st.info(f"IVA 21%: ${iva:,.2f}")
            st.success(f"**TOTAL FINAL:** ${total_calc + iva:,.2f}")

            if st.form_submit_button("Emitir Factura"):
                if nro_fact and prop_sel:
                    fact_id = run_insert_return_id(
                        "INSERT INTO facturacion (numero_factura, propietario_id, fecha_emision, tipo_comprobante, descripcion, subtotal, iva, total, metodo_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (nro_fact, prop_sel, fecha_fac, tipo_comp, desc_fac, total_calc, iva, total_calc + iva, metodo),
                    )
                    if fact_id:
                        for item in items:
                            if item[0]:
                                run_query("INSERT INTO factura_detalle (factura_id, concepto, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (fact_id, item[0], item[1], item[2], item[3]))
                        st.success(f"Factura {nro_fact} emitida.")
                    else:
                        st.error("No se pudo emitir la factura.")
                else:
                    st.error("Numero factura y cliente obligatorios")

    with tab_f2:
        df_fac = fetch_data("""
            SELECT f.numero_factura, f.fecha_emision, p.nombre || ' ' || p.apellido as cliente,
                   f.tipo_comprobante, f.total, f.metodo_pago, f.estado_pago
            FROM facturacion f JOIN propietarios p ON f.propietario_id = p.id
            ORDER BY f.fecha_emision DESC
        """)
        st.dataframe(df_fac, width=1200, hide_index=True)

        total_ventas = fetch_data("SELECT SUM(total) as total FROM facturacion WHERE estado_pago = 'Pendiente' OR estado_pago = 'Pagado'")['total'].iloc[0] or 0
        pend_cobro = fetch_data("SELECT SUM(total) as total FROM facturacion WHERE estado_pago = 'Pendiente'")['total'].iloc[0] or 0
        col_f1, col_f2 = st.columns(2)
        col_f1.metric("Total facturado", f"${total_ventas:,.2f}")
        col_f2.metric("Pendiente cobro", f"${pend_cobro:,.2f}", delta_color="inverse")

# ====================== CRM ======================
elif menu == "CRM y Seguimiento":
    st.title("CRM - Gestion de Clientes")
    df_props = fetch_data("SELECT id, nombre, apellido, telefono, email FROM propietarios ORDER BY apellido")

    tab_c1, tab_c2 = st.tabs(["Nueva interaccion", "Historial interacciones"])

    with tab_c1:
        if not df_props.empty:
            with st.form("form_crm", clear_on_submit=True):
                prop_crm = st.selectbox("Cliente", df_props['id'].tolist(),
                                       format_func=lambda i: f"{df_props[df_props['id']==i]['nombre'].values[0]} {df_props[df_props['id']==i]['apellido'].values[0]} - {df_props[df_props['id']==i]['telefono'].values[0]}")
                tipo_int = st.selectbox("Tipo", ["Llamada", "WhatsApp", "Email", "Visita", "Consulta", "Reclamo", "Seguimiento", "Recordatorio", "Promocion"])
                canal = st.selectbox("Canal", ["Telefono", "WhatsApp", "Email", "Presencial", "Otra app"])
                desc_crm = st.text_area("Descripcion")
                resultado_crm = st.text_area("Resultado")
                prox_seg = st.date_input("Proximo seguimiento", date.today() + relativedelta(days=15))
                if st.form_submit_button("Registrar"):
                    run_query("INSERT INTO crm_interacciones (propietario_id, tipo_interaccion, canal, descripcion, resultado, proximo_seguimiento, veterinario) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (prop_crm, tipo_int, canal, desc_crm, resultado_crm, prox_seg, st.session_state.usuario['nombre']))
                    st.success("Interaccion registrada.")

    with tab_c2:
        df_crm = fetch_data("""
            SELECT c.fecha_interaccion, p.nombre || ' ' || p.apellido as cliente, c.tipo_interaccion, c.canal, c.descripcion, c.proximo_seguimiento, c.veterinario
            FROM crm_interacciones c JOIN propietarios p ON c.propietario_id = p.id
            ORDER BY c.fecha_interaccion DESC LIMIT 200
        """)
        st.dataframe(df_crm, width=1200, hide_index=True)

        st.markdown("### Proximos seguimientos")
        df_pend_seg = fetch_data("""
            SELECT c.proximo_seguimiento, p.nombre || ' ' || p.apellido as cliente, c.tipo_interaccion, c.descripcion
            FROM crm_interacciones c JOIN propietarios p ON c.propietario_id = p.id
            WHERE c.proximo_seguimiento BETWEEN DATE('now') AND DATE('now', '+15 days')
            ORDER BY c.proximo_seguimiento
        """)
        if not df_pend_seg.empty:
            for _, r in df_pend_seg.iterrows():
                st.warning(f"{r['proximo_seguimiento']} - {r['cliente']}: {r['tipo_interaccion']} - {r['descripcion'][:50]}")
        else:
            st.success("Sin seguimientos pendientes")

# ====================== RECORDATORIOS ======================
elif menu == "Recordatorios":
    st.title("Recordatorios y Notificaciones")

    tab_r1, tab_r2 = st.tabs(["Programar recordatorio", "Recordatorios enviados"])

    with tab_r1:
        df_props = fetch_data("SELECT id, nombre, apellido, telefono FROM propietarios ORDER BY apellido")
        caravanas = obtener_lista_caravanas()
        with st.form("form_recordatorio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                prop_rec = st.selectbox("Propietario", df_props['id'].tolist(),
                                       format_func=lambda i: f"{df_props[df_props['id']==i]['nombre'].values[0]} {df_props[df_props['id']==i]['apellido'].values[0]} - {df_props[df_props['id']==i]['telefono'].values[0]}" if not df_props.empty else "")
                tipo_rec = st.selectbox("Tipo", ["Vacunacion", "Desparasitacion", "Cita pendiente", "Resultado laboratorio", "Pago pendiente", "Cumpleanios animal", "Seguimiento", "Promocion"])
                canal_rec = st.selectbox("Canal envio", ["WhatsApp", "SMS", "Email", "Llamada"])
            with c2:
                fecha_prog = st.date_input("Fecha programada", date.today())
                car_rec = st.selectbox("Animal (opcional)", ["N/A"] + caravanas)
                mensaje = st.text_area("Mensaje personalizado")

            if st.form_submit_button("Programar Recordatorio"):
                run_query("INSERT INTO recordatorios (propietario_id, caravana, tipo_recordatorio, fecha_programada, mensaje, canal) VALUES (?, ?, ?, ?, ?, ?)",
                         (prop_rec, None if car_rec == "N/A" else car_rec, tipo_rec, fecha_prog, mensaje, canal_rec))
                st.success("Recordatorio programado.")

    with tab_r2:
        df_recs = fetch_data("""
            SELECT r.fecha_programada, r.tipo_recordatorio, p.nombre || ' ' || p.apellido as propietario,
                   r.mensaje, r.canal, r.enviado
            FROM recordatorios r JOIN propietarios p ON r.propietario_id = p.id
            ORDER BY r.fecha_programada DESC LIMIT 100
        """)
        st.dataframe(df_recs, width=1200, hide_index=True)

        df_pend = fetch_data("SELECT id, fecha_programada, tipo_recordatorio FROM recordatorios WHERE enviado = 0 AND fecha_programada <= DATE('now')")
        if not df_pend.empty:
            st.warning(f"{len(df_pend)} recordatorios pendientes de envio")
            with st.form("form_enviar"):
                ids_rec = df_pend['id'].tolist()
                sel_rec = st.selectbox("Seleccionar para enviar", ids_rec)
                if st.form_submit_button("Marcar como Enviado"):
                    run_query("UPDATE recordatorios SET enviado = 1, fecha_envio = DATE('now') WHERE id = ?", (sel_rec,))
                    st.success("Marcado como enviado.")
                    st.rerun()

# ====================== FARMACIA ======================
elif menu == "Farmacia/Stock":
    st.title("Farmacia y Control de Stock")
    revisar_reorden_stock()

    tab_f1, tab_f2, tab_f3, tab_f4 = st.tabs(["Productos", "Stock/Lotes", "Proximos a vencer", "Reorden"])

    with tab_f1:
        with st.expander("Nuevo Producto"):
            with st.form("form_producto", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nom_prod = st.text_input("Nombre comercial")
                    principio = st.text_input("Principio activo")
                    tipo_prod = st.selectbox("Tipo", ["Vacuna", "Antibiotico", "Antiparasitario", "Antiinflamatorio", "Vitaminico", "Desinfectante", "Insumo", "Otro"])
                with c2:
                    proveedor = st.text_input("Proveedor")
                    concentracion = st.text_input("Concentracion")
                    presentacion = st.text_input("Presentacion")
                    laboratorio = st.text_input("Laboratorio")
                if st.form_submit_button("Agregar"):
                    run_query("INSERT INTO farmacia (nombre_producto, principio_activo, tipo_producto, proveedor, concentracion, presentacion, laboratorio) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (nom_prod, principio, tipo_prod, proveedor, concentracion, presentacion, laboratorio))
                    registrar_auditoria("crear_producto", "farmacia", nom_prod, tipo_prod)
                    st.success("Producto agregado.")

        df_prod = fetch_data("SELECT * FROM farmacia ORDER BY nombre_producto")
        st.dataframe(df_prod, width=1200, hide_index=True)

    with tab_f2:
        df_prod_list = fetch_data("SELECT id, nombre_producto, presentacion FROM farmacia ORDER BY nombre_producto")
        if not df_prod_list.empty:
            with st.expander("Agregar Stock/Lote"):
                with st.form("form_stock", clear_on_submit=True):
                    prod_id = st.selectbox("Producto", df_prod_list['id'].tolist(),
                                          format_func=lambda i: f"{df_prod_list[df_prod_list['id']==i]['nombre_producto'].values[0]} - {df_prod_list[df_prod_list['id']==i]['presentacion'].values[0]}")
                    lote = st.text_input("Nro de Lote")
                    fecha_venc = st.date_input("Fecha vencimiento")
                    cantidad = st.number_input("Cantidad", min_value=1, step=1)
                    precio_c = st.number_input("Precio compra $", min_value=0.0, step=100.0)
                    precio_v = st.number_input("Precio venta $", min_value=0.0, step=100.0)
                    ubicacion = st.text_input("Ubicacion")
                    stock_minimo = st.number_input("Stock minimo", min_value=0, step=1)
                    proveedor_pred = st.text_input("Proveedor predeterminado")
                    if st.form_submit_button("Agregar Stock"):
                        run_query("INSERT INTO stock (producto_id, lote, fecha_vencimiento, cantidad, precio_compra, precio_venta, ubicacion, stock_minimo, proveedor_predeterminado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (prod_id, lote, fecha_venc, cantidad, precio_c, precio_v, ubicacion, stock_minimo, proveedor_pred))
                        registrar_auditoria("crear_stock", "stock", prod_id, f"Lote {lote} cantidad {cantidad}")
                        st.success("Stock agregado.")

            df_stock = fetch_data("""
                SELECT f.nombre_producto, f.tipo_producto, s.lote, s.fecha_vencimiento, s.cantidad,
                       s.stock_minimo, s.proveedor_predeterminado, s.precio_compra, s.precio_venta, s.ubicacion
                FROM stock s JOIN farmacia f ON s.producto_id = f.id
                ORDER BY s.fecha_vencimiento
            """)
            st.dataframe(df_stock, width=1200, hide_index=True)

    with tab_f3:
        df_venc = fetch_data("""
            SELECT f.nombre_producto, f.tipo_producto, s.lote, s.fecha_vencimiento, s.cantidad,
                   CAST(julianday(s.fecha_vencimiento) - julianday('now') AS INTEGER) as dias_restantes
            FROM stock s JOIN farmacia f ON s.producto_id = f.id
            WHERE s.fecha_vencimiento <= DATE('now', '+90 days')
            ORDER BY s.fecha_vencimiento
        """)
        if not df_venc.empty:
            for _, row in df_venc.iterrows():
                if row['dias_restantes'] < 0:
                    st.error(f"VENCIDO: {row['nombre_producto']} lote {row['lote']} (vencio hace {abs(row['dias_restantes'])} dias)")
                elif row['dias_restantes'] <= 30:
                    st.warning(f"VENCE PRONTO: {row['nombre_producto']} lote {row['lote']} - {row['dias_restantes']} dias restantes")
                else:
                    st.info(f"{row['nombre_producto']} lote {row['lote']} - {row['dias_restantes']} dias restantes")
        else:
            st.success("No hay productos proximos a vencer")

    with tab_f4:
        st.caption("Cuando el stock queda por debajo del minimo, el sistema crea una orden de compra en borrador.")
        df_oc = fetch_data("""
            SELECT oc.id, f.nombre_producto, oc.proveedor, oc.cantidad_sugerida, oc.motivo, oc.estado, oc.fecha_creacion
            FROM ordenes_compra oc JOIN farmacia f ON oc.producto_id = f.id
            ORDER BY oc.fecha_creacion DESC, oc.id DESC
        """)
        st.dataframe(df_oc, use_container_width=True, hide_index=True)
        ids_oc = df_oc["id"].tolist() if not df_oc.empty else []
        if ids_oc:
            with st.form("form_oc_estado"):
                oc_sel = st.selectbox("Orden", ids_oc)
                estado_oc = st.selectbox("Estado", ["Borrador", "Solicitada", "Recibida", "Cancelada"])
                if st.form_submit_button("Actualizar orden"):
                    run_query("UPDATE ordenes_compra SET estado = ? WHERE id = ?", (estado_oc, oc_sel))
                    registrar_auditoria("actualizar_orden_compra", "ordenes_compra", oc_sel, estado_oc)
                    st.success("Orden actualizada.")

# ====================== RECETARIO ======================
elif menu == "Recetario Digital":
    st.title("Recetario Digital")
    caravanas = obtener_lista_caravanas()
    df_props = fetch_data("SELECT id, nombre, apellido FROM propietarios")

    with st.expander("Nueva Receta"):
        with st.form("form_receta", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                car_rec = st.selectbox("Animal", caravanas)
                prop_opts = df_props['id'].tolist()
                prop_rec = st.selectbox("Propietario", ["N/A"] + prop_opts)
                diagnostico = st.text_area("Diagnostico")
            with c2:
                indicaciones = st.text_area("Indicaciones generales")
                fecha_rec = st.date_input("Fecha", date.today())

            st.markdown("#### Medicamentos")
            df_prods = fetch_data("SELECT id, nombre_producto, presentacion FROM farmacia ORDER BY nombre_producto")
            prods_opts = df_prods['id'].tolist()
            meds_data = []
            num_meds = st.number_input("Cantidad de medicamentos", min_value=1, max_value=10, value=1)
            for i in range(num_meds):
                cols = st.columns(5)
                with cols[0]:
                    prod = st.selectbox("Producto", prods_opts, key=f"prod_{i}",
                                       format_func=lambda x: f"{df_prods[df_prods['id']==x]['nombre_producto'].values[0]}" if not df_prods.empty else "")
                with cols[1]:
                    dosis = st.text_input("Dosis", key=f"dosis_{i}")
                with cols[2]:
                    frec = st.text_input("Frecuencia", key=f"frec_{i}")
                with cols[3]:
                    dur = st.text_input("Duracion", key=f"dur_{i}")
                with cols[4]:
                    via = st.selectbox("Via", ["IM", "IV", "SC", "Oral", "Topica"], key=f"via_{i}")
                meds_data.append((prod, dosis, frec, dur, via))

            if st.form_submit_button("Emitir Receta"):
                receta_id = run_insert_return_id(
                    "INSERT INTO recetas (caravana, propietario_id, veterinario, fecha_receta, diagnostico, indicaciones, firma_digital) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (car_rec, None if prop_rec == "N/A" else prop_rec, st.session_state.usuario['nombre'], fecha_rec, diagnostico, indicaciones, "Firma digital pendiente"),
                )
                if receta_id:
                    for md in meds_data:
                        run_query("INSERT INTO receta_detalle (receta_id, producto_id, dosis, frecuencia, duracion, via_administracion) VALUES (?, ?, ?, ?, ?, ?)",
                                 (receta_id, md[0], md[1], md[2], md[3], md[4]))
                    st.success("Receta emitida.")
                else:
                    st.error("No se pudo emitir la receta.")

    st.markdown("### Recetas Emitidas")
    df_recetas = fetch_data("""
        SELECT r.id, r.fecha_receta, r.caravana, r.veterinario, r.diagnostico,
               COALESCE(p.nombre || ' ' || p.apellido, 'N/A') as propietario
        FROM recetas r LEFT JOIN propietarios p ON r.propietario_id = p.id
        ORDER BY r.fecha_receta DESC
    """)
    st.dataframe(df_recetas, width=1200, hide_index=True)

    with st.expander("Ver detalle de receta"):
        ids_rec = df_recetas['id'].tolist() if not df_recetas.empty else []
        if ids_rec:
            sel_rec = st.selectbox("Receta ID", ids_rec)
            df_det = fetch_data("""
                SELECT f.nombre_producto, rd.dosis, rd.frecuencia, rd.duracion, rd.via_administracion
                FROM receta_detalle rd JOIN farmacia f ON rd.producto_id = f.id
                WHERE rd.receta_id = ?
            """, (sel_rec,))
            st.dataframe(df_det, width=1200, hide_index=True)

# ====================== PRODUCCION ======================
elif menu == "Produccion y Pesajes":
    st.title("Produccion y Pesajes")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        with st.form("form_peso", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                car_p = st.selectbox("Caravana", caravanas)
                peso = st.number_input("Peso (Kg)", min_value=10.0, step=1.0)
            with c2:
                fecha_peso = st.date_input("Fecha", date.today())
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO pesajes (caravana, peso_kg, fecha_pesaje) VALUES (?, ?, ?)", (car_p, peso, fecha_peso))
                st.success("Pesaje guardado.")

        st.markdown("### Evolucion")
        df_graf = fetch_data("SELECT fecha_pesaje, caravana, peso_kg FROM pesajes ORDER BY fecha_pesaje ASC")
        if not df_graf.empty:
            df_pivot = df_graf.pivot(index='fecha_pesaje', columns='caravana', values='peso_kg')
            st.line_chart(df_pivot)

        st.markdown("### Historial")
        df_pes_hist = fetch_data("SELECT fecha_pesaje, caravana, peso_kg FROM pesajes ORDER BY fecha_pesaje DESC")
        st.dataframe(df_pes_hist, width=1200, hide_index=True)
    else:
        st.warning("Sin animales.")

# ====================== REPRODUCCION ======================
elif menu == "Reproduccion":
    st.title("Control Reproductivo")
    hembras = obtener_lista_caravanas(solo_hembras=True)
    if hembras:
        tab1, tab2, tab3, tab4 = st.tabs(["Inseminaciones", "Partos", "Ciclos", "Toros"])
        with tab1:
            st.markdown("### Registro de Inseminacion")
            df_toros = obtener_toros()
            opciones = ["Sin especificar"] + [f"{r['nombre']} ({r['raza']})" for _, r in df_toros.iterrows()]
            with st.form("form_ins", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    madre = st.selectbox("Vaca", hembras)
                    toro = st.selectbox("Toro", opciones)
                    tipo = st.selectbox("Semen", ["Fresco", "Congelado", "Sexado"])
                with c2:
                    f_ins = st.date_input("Fecha", date.today())
                    hora = st.time_input("Hora", datetime.now().time())
                    tec = st.text_input("Tecnico")
                dias = st.slider("Dias gestion", 275, 290, 283)
                f_parto = f_ins + relativedelta(days=dias)
                st.info(f"Parto probable: **{f_parto}**")
                if st.form_submit_button("Registrar"):
                    toro_id = None
                    if toro != "Sin especificar":
                        nom = toro.split(" (")[0]
                        df_t = fetch_data("SELECT id FROM toros WHERE nombre = ?", (nom,))
                        if not df_t.empty:
                            toro_id = df_t['id'].iloc[0]
                    run_query("INSERT INTO inseminaciones (caravana_vaca, toro_id, fecha_inseminacion, hora_inseminacion, tipo_semen, tecnico, fecha_probable_parto) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (madre, toro_id, f_ins, str(hora), tipo, tec, f_parto))
                    st.success("Inseminacion registrada.")

            st.markdown("### Historial")
            df_ins = fetch_data("""
                SELECT i.fecha_inseminacion, i.caravana_vaca, COALESCE(t.nombre, 'N/A') as toro, i.tipo_semen, i.fecha_probable_parto, i.resultado
                FROM inseminaciones i LEFT JOIN toros t ON i.toro_id = t.id ORDER BY i.fecha_inseminacion DESC
            """)
            st.dataframe(df_ins, width=1200, hide_index=True)

        with tab2:
            st.markdown("### Calendario de Partos")
            df_p = fetch_data("""
                SELECT caravana_vaca, fecha_inseminacion, fecha_probable_parto,
                       CASE WHEN date(fecha_probable_parto) < date('now') THEN 'VENCIDO'
                            WHEN date(fecha_probable_parto) BETWEEN date('now') AND date('now', '+7 days') THEN 'ESTA SEMANA'
                            WHEN date(fecha_probable_parto) BETWEEN date('now', '+8 days') AND date('now', '+30 days') THEN 'PROXIMO MES'
                            ELSE 'PROGRAMADO' END as estado
                FROM inseminaciones WHERE resultado = 'Pendiente' ORDER BY fecha_probable_parto
            """)
            if not df_p.empty:
                col1, col2, col3 = st.columns(3)
                col1.metric("Vencidos", len(df_p[df_p['estado']=='VENCIDO']), delta_color="inverse")
                col2.metric("Esta semana", len(df_p[df_p['estado']=='ESTA SEMANA']))
                col3.metric("Proximo mes", len(df_p[df_p['estado']=='PROXIMO MES']))
                st.dataframe(df_p, width=1200, hide_index=True)

            st.markdown("### Registrar Parto")
            with st.form("form_parto", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    madre_p = st.selectbox("Madre", hembras, key="madre_parto")
                    fecha_p = st.date_input("Fecha parto", date.today())
                with c2:
                    cria = st.text_input("Caravana cria")
                    sexo = st.selectbox("Sexo cria", ["Hembra", "Macho"])
                    peso_c = st.number_input("Peso (kg)", 10.0, 100.0, 35.0)
                dif = st.selectbox("Dificultad", ["Normal", "Ayuda", "Cesarea"])
                resultado = st.selectbox("Resultado", ["Vivo Sano", "Vivo Debil", "Mortinato", "Aborto"])
                if st.form_submit_button("Registrar"):
                    run_query("INSERT INTO reproduccion (caravana_madre, tipo_servicio, fecha_servicio, fecha_parto, caravana_cria, resultado_tacto) VALUES (?, 'IA', ?, ?, ?, ?)",
                             (madre_p, fecha_p - relativedelta(days=283), fecha_p, cria, resultado))
                    if cria:
                        run_query("INSERT INTO bovinos (caravana, tipo_identificacion, raza, sexo, categoria, peso_nacimiento, fecha_nacimiento) VALUES (?, 'Visual', 'Por definir', ?, 'Ternero/a', ?, ?)",
                                 (cria, sexo, peso_c, fecha_p))
                    run_query("UPDATE inseminaciones SET resultado = 'Parto Registrado' WHERE caravana_vaca = ? AND fecha_probable_parto >= ?", (madre_p, fecha_p))
                    st.success("Parto registrado.")

        with tab3:
            st.markdown("### Ciclos Estrales")
            st.markdown("Duracion ciclo: 21d | Estro: 12-18hs | Periodo post-parto: 60d")
            df_ciclos = fetch_data("""
                SELECT caravana_madre, fecha_parto, DATE(fecha_parto, '+60 days') as proximo_estro,
                       CAST((julianday('now') - julianday(fecha_parto))/21 AS INTEGER) as ciclos
                FROM reproduccion WHERE fecha_parto IS NOT NULL ORDER BY fecha_parto DESC
            """)
            if not df_ciclos.empty:
                for _, r in df_ciclos.iterrows():
                    prox = datetime.strptime(r['proximo_estro'], '%Y-%m-%d').date()
                    dias_desde = (date.today() - datetime.strptime(r['fecha_parto'], '%Y-%m-%d').date()).days
                    with st.container():
                        cc1, cc2, cc3 = st.columns(3)
                        cc1.write(f"**{r['caravana_madre']}**")
                        if date.today() >= prox:
                            cc2.success(f"Estro: {prox}")
                        else:
                            cc2.info(f"Faltan {(prox-date.today()).days} dias")
                        cc3.write(f"Post-parto: {dias_desde}d")
            else:
                st.info("Sin datos de partos")

        with tab4:
            st.markdown("### Toros")
            with st.expander("Nuevo Toro"):
                with st.form("form_toro", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        nom_t = st.text_input("Nombre")
                        raza_t = st.selectbox("Raza", ["Angus", "Hereford", "Braford", "Brangus", "Charolais", "Limousin", "Salers", "Otra"])
                        origen = st.selectbox("Origen", ["Nacional", "Importado"])
                    with c2:
                        fnac_t = st.date_input("Nacimiento", date.today())
                        registro = st.text_input("Registro")
                        apt = st.selectbox("Aptitud", ["Cria", "Carga", "Doble Proposito", "Consumo"])
                    coment = st.text_area("Comentarios")
                    if st.form_submit_button("Registrar"):
                        run_query("INSERT INTO toros (nombre, raza, origen, fecha_nacimiento, registro, aptitud, comentarios) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (nom_t, raza_t, origen, fnac_t, registro, apt, coment))
                        st.success("Toro registrado.")
            df_t = fetch_data("SELECT * FROM toros ORDER BY nombre")
            st.dataframe(df_t, width=1200, hide_index=True)
            st.markdown("### Estadisticas")
            total_i = fetch_data("SELECT COUNT(*) as t FROM inseminaciones")['t'].iloc[0]
            pend = fetch_data("SELECT COUNT(*) as t FROM inseminaciones WHERE resultado='Pendiente'")['t'].iloc[0]
            st.metric("Total Inseminaciones", total_i)
            st.progress(pend/total_i if total_i > 0 else 0, text=f"Tasa actividad: {pend/total_i*100:.1f}%" if total_i > 0 else "Sin datos")
    else:
        st.warning("No hay hembras registradas.")

# ====================== INTERVENCIONES ======================
elif menu == "Intervenciones":
    st.title("Registro de Intervenciones y Cirugias")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        with st.expander("Nueva Intervencion"):
            with st.form("form_interv", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    car_int = st.selectbox("Animal", caravanas)
                    tipo_int = st.selectbox("Tipo", ["Cirugia", "Curacion", "Extraccion", "Exploracion", "Cesarea", "Cauterio", "Amputacion", "Otra"])
                    fecha_int = st.date_input("Fecha", date.today())
                    vet = st.text_input("Veterinario", st.session_state.usuario['nombre'])
                with c2:
                    diag = st.text_area("Diagnostico")
                    proc = st.text_area("Procedimiento")
                hall = st.text_area("Hallazgos")
                reco = st.text_area("Recomendaciones post-operatorias")
                costo = st.number_input("Costo ($)", min_value=0.0, step=500.0)
                if st.form_submit_button("Registrar"):
                    run_query("INSERT INTO intervenciones (caravana, tipo_intervencion, fecha_intervencion, veterinario, diagnostico, procedimiento, hallazgos, recomendaciones, costo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (car_int, tipo_int, fecha_int, vet, diag, proc, hall, reco, costo))
                    st.success("Intervencion registrada.")

        st.markdown("### Historial")
        df_int = fetch_data("""
            SELECT fecha_intervencion, caravana, tipo_intervencion, veterinario, diagnostico, costo
            FROM intervenciones ORDER BY fecha_intervencion DESC
        """)
        st.dataframe(df_int, width=1200, hide_index=True)

        if not df_int.empty:
            total_costos = df_int['costo'].sum()
            st.metric("Costo total intervenciones", f"${total_costos:,.2f}")
    else:
        st.warning("No hay animales.")

# ====================== CERTIFICADOS ======================
elif menu == "Certificados":
    st.title("Certificados Sanitarios y Documentos")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        with st.expander("Emitir Certificado"):
            with st.form("form_cert", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    car_cert = st.selectbox("Animal", caravanas)
                    tipo_cert = st.selectbox("Tipo", ["Certificado Sanitario", "Certificado de Vacunacion", "Certificado de Brucelosis", "Certificado de Aftosa", "Certificado de Exportacion", "Certificado de Traslado", "Certificado de Interdiccion", "Certificado de Libre Venta"])
                    fecha_emision = st.date_input("Fecha emision", date.today())
                with c2:
                    fecha_validez = st.date_input("Fecha validez", date.today() + relativedelta(days=90))
                    matricula = st.text_input("Matricula profesional")
                    motivo = st.text_area("Motivo")
                resultado = st.selectbox("Resultado", ["Apto", "No Apto", "Interdicto", "Observado"])
                observaciones = st.text_area("Observaciones")
                if st.form_submit_button("Emitir Certificado"):
                    run_query("INSERT INTO certificados (caravana, tipo_certificado, fecha_emision, fecha_validez, veterinario_firmante, matricula, motivo, resultado, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (car_cert, tipo_cert, fecha_emision, fecha_validez, st.session_state.usuario['nombre'], matricula, motivo, resultado, observaciones))
                    st.success("Certificado emitido.")

        st.markdown("### Certificados Emitidos")
        df_cert = fetch_data("""
            SELECT fecha_emision, caravana, tipo_certificado, resultado, fecha_validez, veterinario_firmante
            FROM certificados ORDER BY fecha_emision DESC
        """)
        st.dataframe(df_cert, width=1200, hide_index=True)

        with st.expander("Certificados proximos a vencer"):
            df_prox = fetch_data("""
                SELECT * FROM certificados
                WHERE fecha_validez BETWEEN DATE('now') AND DATE('now', '+30 days')
                ORDER BY fecha_validez
            """)
            if not df_prox.empty:
                st.warning(f"{len(df_prox)} certificados proximos a vencer")
                st.dataframe(df_prox, width=1200, hide_index=True)
            else:
                st.success("Ningun certificado proximo a vencer")
    else:
        st.warning("No hay animales.")

# ====================== ALERTAS ======================
elif menu == "Alertas y Notificaciones":
    st.title("Alertas y Notificaciones")
    verificar_alertas()

    tabs_al = st.tabs(["Alertas activas", "Alertas de stock", "Historial"])
    with tabs_al[0]:
        df_al = fetch_data("SELECT * FROM alertas WHERE resuelta = 0 AND tipo_alerta NOT LIKE '%Stock%' ORDER BY fecha_alerta DESC")
        if not df_al.empty:
            st.warning(f"{len(df_al)} alertas")
            st.dataframe(df_al, width=1200, hide_index=True)
            with st.form("form_resolver"):
                ids_al = df_al['id'].tolist()
                sel_al = st.selectbox("Resolver", ids_al)
                if st.form_submit_button("Marcar resuelta"):
                    run_query("UPDATE alertas SET resuelta = 1 WHERE id = ?", (sel_al,))
                    st.rerun()
        else:
            st.success("Sin alertas activas")

    with tabs_al[1]:
        df_venc = fetch_data("""
            SELECT f.nombre_producto, s.lote, s.fecha_vencimiento, s.cantidad,
                   CAST(julianday(s.fecha_vencimiento) - julianday('now') AS INTEGER) as dias
            FROM stock s JOIN farmacia f ON s.producto_id = f.id
            WHERE s.fecha_vencimiento BETWEEN DATE('now') AND DATE('now', '+90 days')
            ORDER BY s.fecha_vencimiento
        """)
        if not df_venc.empty:
            for _, r in df_venc.iterrows():
                if r['dias'] < 0:
                    st.error(f"VENCIDO: {r['nombre_producto']} lote {r['lote']}")
                elif r['dias'] <= 30:
                    st.warning(f"VENCE PRONTO: {r['nombre_producto']} lote {r['lote']} ({r['dias']}d)")
                else:
                    st.info(f"{r['nombre_producto']} lote {r['lote']} ({r['dias']}d)")
        else:
            st.success("Sin vencimientos")

    with tabs_al[2]:
        df_res = fetch_data("SELECT * FROM alertas WHERE resuelta = 1 ORDER BY fecha_alerta DESC LIMIT 100")
        st.dataframe(df_res, width=1200, hide_index=True)

# ====================== MARCO LEGAL ======================
elif menu == "Marco Legal y Normativas":
    st.title("Marco Legal y Normativas SENASA")
    st.info("**LEY 22.465** - Ley Federal de Fauna")
    st.info("**LEY 24.091** - Ley de Actividades Rizocida")
    st.info("**LEY 27.233** - Ley de Regimen Ganadero")

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.success("**RES SENASA 540/2015**\n- Vacunacion Brucelosis obligatoria\n- Cepa 19 a terneras 3-8 meses")
        st.success("**RES SENASA 67/2019**\n- SIGSA\n- RFID obligatorio desde 2026")
    with col_n2:
        st.warning("**RES SENASA 422/2003**\n- Tuberculosis Bovina\n- DOES")
        st.warning("**LEY 27.274**\n- Vacunas obligatorias aftosa")

    with st.expander("Codigo Rural - Articulos"):
        st.markdown("""
        **Art. 22:** Inscripcion en RENSPA obligatoria
        **Art. 23:** Caravana obligatoria e intransferible
        **Art. 24:** Identificar nacidos en 90 dias
        **Art. 24 bis:** RFID desde 2026
        **Art. 25:** Informar movimientos a SENASA
        **Art. 26:** Vacunacion aftosa y brucelosis obligatoria
        **Art. 27:** Interdiccion por enfermedades denunciables
        **Art. 28:** Prohibido trasladar animales interdictos
        """)

    df_check = fetch_data("SELECT COUNT(*) as t FROM control_normativo")
    if df_check.empty or df_check['t'].iloc[0] == 0:
        defaults = [
            ("Resolucion", "540/2015", 2015, "Vacunacion Brucelosis", "Art. 1 y 3", "Pendiente"),
            ("Resolucion", "67/2019", 2019, "Trazabilidad SIGSA", "Art. 1-5", "Pendiente"),
            ("Resolucion", "422/2003", 2003, "Tuberculosis Bovina", "Art. 1-4", "Pendiente"),
            ("Ley", "27.274", 2016, "Vacunacion Aftosa", "Art. 1-3", "Pendiente"),
        ]
        for n in defaults:
            run_query("INSERT INTO control_normativo (tipo_norma, numero, anio, descripcion, articulo, cumplimiento) VALUES (?, ?, ?, ?, ?, ?)", n)

    df_norm = fetch_data("SELECT * FROM control_normativo ORDER BY anio DESC")
    st.dataframe(df_norm, width=1200, hide_index=True)

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        with st.form("form_cump"):
            ids_n = df_norm['id'].tolist() if not df_norm.empty else []
            s = st.selectbox("Norma", ids_n) if ids_n else st.text_input("ID")
            est = st.selectbox("Estado", ["Cumplido", "Pendiente", "En Proceso", "No Aplica"])
            f_c = st.date_input("Fecha", date.today())
            if st.form_submit_button("Actualizar") and ids_n:
                run_query("UPDATE control_normativo SET cumplimiento=?, fecha_cumplimiento=? WHERE id=?", (est, f_c, s))
                st.success("Actualizado")
    with col_u2:
        with st.form("form_norma"):
            t = st.selectbox("Tipo", ["Ley", "Resolucion", "Decreto"])
            num = st.text_input("Numero")
            anio = st.number_input("Anio", 1900, 2030, 2024)
            desc = st.text_input("Descripcion")
            art = st.text_input("Articulo(s)")
            if st.form_submit_button("Agregar"):
                run_query("INSERT INTO control_normativo (tipo_norma, numero, anio, descripcion, articulo, cumplimiento) VALUES (?, ?, ?, ?, ?, 'Pendiente')", (t, num, anio, desc, art))
                st.success("Norma agregada")

    st.markdown("### Interdicciones")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        with st.form("form_inter"):
            c1, c2 = st.columns(2)
            with c1:
                ca = st.selectbox("Animal", caravanas)
                enf = st.selectbox("Enfermedad", ["Carbunclo", "Tuberculosis", "Brucelosis", "Aftosa", "Rabia"])
                fi = st.date_input("Fecha", date.today())
            with c2:
                mo = st.text_input("Motivo")
                res = st.text_input("Resolucion")
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO interdicciones (caravana, enfermedad, fecha_interdiccion, motivo, resolucion) VALUES (?, ?, ?, ?, ?)", (ca, enf, fi, mo, res))
                st.warning(f"Interdiccion por {enf}")
        df_int = fetch_data("SELECT * FROM interdicciones ORDER BY fecha_interdiccion DESC")
        st.dataframe(df_int, width=1200, hide_index=True)

# ====================== LOTES/POTREROS ======================
elif menu == "Lotes/Potreros":
    st.title("Gestion de Lotes y Potreros")

    tab_l1, tab_l2 = st.tabs(["Lotes", "Asignacion Animales"])

    with tab_l1:
        with st.expander("Nuevo Lote/Potrero"):
            with st.form("form_lote", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nom_lote = st.text_input("Nombre del lote/potrero")
                    sup = st.number_input("Superficie (ha)", 0.0, 10000.0, 50.0)
                with c2:
                    pastura = st.text_input("Tipo de pastura")
                    cap = st.number_input("Capacidad animales", 0, 5000, 100)
                obs_l = st.text_area("Observaciones")
                if st.form_submit_button("Crear Lote"):
                    run_query("INSERT INTO lotes (nombre, superficie_ha, tipo_pastura, capacidad_animales, observaciones) VALUES (?, ?, ?, ?, ?)",
                             (nom_lote, sup, pastura, cap, obs_l))
                    st.success("Lote creado.")

        df_lotes = fetch_data("""
            SELECT l.*, (SELECT COUNT(*) FROM lote_animales la WHERE la.lote_id = l.id AND la.fecha_salida IS NULL) as animales_actuales
            FROM lotes l ORDER BY l.nombre
        """)
        st.dataframe(df_lotes, width=1200, hide_index=True)

    with tab_l2:
        df_lotes_act = fetch_data("SELECT id, nombre FROM lotes WHERE estado = 'Activo'")
        caravanas = obtener_lista_caravanas()
        if not df_lotes_act.empty and caravanas:
            with st.form("form_asignar", clear_on_submit=True):
                lote_sel = st.selectbox("Lote", df_lotes_act['id'].tolist(),
                                       format_func=lambda i: df_lotes_act[df_lotes_act['id']==i]['nombre'].values[0])
                car_sel = st.selectbox("Animal", caravanas)
                if st.form_submit_button("Asignar a Lote"):
                    run_query("INSERT INTO lote_animales (lote_id, caravana) VALUES (?, ?)", (lote_sel, car_sel))
                    st.success(f"{car_sel} asignado a lote.")

            st.markdown("### Animales por Lote")
            df_asign = fetch_data("""
                SELECT l.nombre as lote, la.caravana, la.fecha_asignacion
                FROM lote_animales la JOIN lotes l ON la.lote_id = l.id
                WHERE la.fecha_salida IS NULL ORDER BY l.nombre
            """)
            st.dataframe(df_asign, width=1200, hide_index=True)
        else:
            st.warning("No hay lotes o animales disponibles")

# ====================== FINANZAS ======================
elif menu == "Finanzas":
    st.title("Control Financiero")

    tab_f1, tab_f2, tab_f3 = st.tabs(["Registrar", "Movimientos", "Resumen"])

    with tab_f1:
        with st.form("form_finanza", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tipo_f = st.selectbox("Tipo", ["Ingreso", "Gasto"])
                cat_f = st.selectbox("Categoria", ["Venta de animales", "Compra de animales", "Alimentacion", "Sanidad", "Insumos", "Servicios", "Personal", "Mantenimiento", "Transporte", "Impuestos", "Otro"])
                monto = st.number_input("Monto $", 0.0, 999999999.0, 0.0)
            with c2:
                fecha_f = st.date_input("Fecha", date.today())
                forma_pago = st.selectbox("Forma pago", ["Efectivo", "Transferencia", "Cheque", "Tarjeta", "Cuenta corriente"])
                comprob = st.text_input("Comprobante Nro")
            desc_f = st.text_area("Descripcion")
            car_f = st.text_input("Caravana (opcional)")
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO finanzas (tipo, categoria, descripcion, monto, fecha, caravana, forma_pago, comprobante) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (tipo_f, cat_f, desc_f, monto, fecha_f, car_f if car_f else None, forma_pago, comprob))
                st.success("Movimiento registrado.")

    with tab_f2:
        periodos = {"Hoy": "date('now')", "Esta semana": "date('now', 'weekday 0', '-7 days')", "Este mes": "date('now', 'start of month')", "Este año": "date('now', 'start of year')"}
        per_sel = st.selectbox("Periodo", list(periodos.keys()))
        df_mov = fetch_data(f"SELECT * FROM finanzas WHERE fecha >= {periodos[per_sel]} ORDER BY fecha DESC")
        st.dataframe(df_mov, width=1200, hide_index=True)

    with tab_f3:
        periodo_r = st.selectbox("Resumen de", ["Hoy", "Este mes", "Este año", "Todo"], key="resumen")
        filtro = {"Hoy": "date('now')", "Este mes": "date('now', 'start of month')", "Este año": "date('now', 'start of year')", "Todo": "'1900-01-01'"}
        df_res = fetch_data(f"""
            SELECT tipo, SUM(monto) as total FROM finanzas
            WHERE fecha >= {filtro[periodo_r]}
            GROUP BY tipo
        """)
        if not df_res.empty:
            ingresos = df_res[df_res['tipo']=='Ingreso']['total'].iloc[0] if len(df_res[df_res['tipo']=='Ingreso']) > 0 else 0
            gastos = df_res[df_res['tipo']=='Gasto']['total'].iloc[0] if len(df_res[df_res['tipo']=='Gasto']) > 0 else 0
            col_f1, col_f2, col_f3 = st.columns(3)
            col_f1.metric("Ingresos", f"${ingresos:,.2f}")
            col_f2.metric("Gastos", f"${gastos:,.2f}", delta_color="inverse")
            col_f3.metric("Balance", f"${ingresos - gastos:,.2f}", delta=f"{ingresos - gastos:,.2f}")

        df_cat = fetch_data(f"""
            SELECT categoria, SUM(monto) as total FROM finanzas
            WHERE fecha >= {filtro[periodo_r]}
            GROUP BY categoria ORDER BY total DESC
        """)
        if not df_cat.empty:
            st.markdown("### Gastos por Categoria")
            st.bar_chart(df_cat.set_index('categoria'), color="#d62728")

# ====================== BI - ANALITICA AVANZADA ======================
elif menu == "BI - Analitica Avanzada":
    st.title("Business Intelligence - Analitica Avanzada")

    df_bov = fetch_data("SELECT * FROM bovinos WHERE estado = 'Activo'")

    if not df_bov.empty:
        tab_b1, tab_b2, tab_b3, tab_b4 = st.tabs(["Demografia", "Produccion", "Sanidad", "Reproduccion"])

        with tab_b1:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Distribucion por Edad")
                hoy = date.today()
                edades = []
                for _, r in df_bov.iterrows():
                    fnac = datetime.strptime(r['fecha_nacimiento'], '%Y-%m-%d').date() if isinstance(r['fecha_nacimiento'], str) else r['fecha_nacimiento']
                edades.append(relativedelta(hoy, fnac).years)
                df_bov['edad'] = edades
                df_edades = df_bov['edad'].value_counts().sort_index()
                if not df_edades.empty:
                    st.bar_chart(df_edades, color="#2e9140")
                with c2:
                    st.markdown("### Proporcion Sexo")
                    st.bar_chart(df_bov['sexo'].value_counts(), color=["#1f77b4", "#ff7f0e"])

        with tab_b2:
            df_pes = fetch_data("""
                SELECT caravana, AVG(peso_kg) as peso_prom, MIN(peso_kg) as peso_min, MAX(peso_kg) as peso_max, COUNT(*) as pesajes
                FROM pesajes GROUP BY caravana
            """)
            if not df_pes.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Peso Promedio General", f"{df_pes['peso_prom'].mean():.1f} kg")
                c2.metric("Animal mas pesado", f"{df_pes['peso_max'].max():.1f} kg")
                c3.metric("Animal mas liviano", f"{df_pes['peso_min'].min():.1f} kg")
                st.dataframe(df_pes.sort_values('peso_prom', ascending=False), width=1200, hide_index=True)

        with tab_b3:
            df_ev = fetch_data("""
                SELECT categoria_evento, COUNT(*) as total FROM sanidad
                GROUP BY categoria_evento ORDER BY total DESC
            """)
            if not df_ev.empty:
                st.markdown("### Eventos Sanitarios")
                st.bar_chart(df_ev.set_index('categoria_evento'), color="#d62728")

            df_bruc = fetch_data("SELECT estatus_brucelosis, COUNT(*) as total FROM bovinos WHERE estado='Activo' GROUP BY estatus_brucelosis")
            if not df_bruc.empty:
                st.markdown("### Estatus Brucelosis")
                st.bar_chart(df_bruc.set_index('estatus_brucelosis'))

        with tab_b4:
            df_ins = fetch_data("""
                SELECT strftime('%m', fecha_inseminacion) as mes, COUNT(*) as total
                FROM inseminaciones GROUP BY mes ORDER BY mes
            """)
            if not df_ins.empty:
                st.markdown("### Inseminaciones por Mes")
                st.bar_chart(df_ins.set_index('mes'))

            df_partos = fetch_data("""
                SELECT strftime('%m', fecha_parto) as mes, COUNT(*) as total
                FROM reproduccion WHERE fecha_parto IS NOT NULL GROUP BY mes ORDER BY mes
            """)
            if not df_partos.empty:
                st.markdown("### Partos por Mes")
                st.bar_chart(df_partos.set_index('mes'), color="#2e9140")

        st.markdown("---")
        st.markdown("### Indicadores Clave (KPI)")
        k1, k2, k3, k4 = st.columns(4)
        total = len(df_bov)
        hembras = len(df_bov[df_bov['sexo']=='Hembra'])
        k1.metric("Total Animales", total)
        k2.metric("% Hembras", f"{(hembras/total)*100:.1f}%")
        df_par = fetch_data("SELECT COUNT(DISTINCT caravana_madre) as t FROM reproduccion WHERE fecha_parto >= date('now', '-1 year')")
        k3.metric("Partos ultimo ano", df_par['t'].iloc[0] if not df_par.empty else 0)
        k4.metric("Eficiencia Reproductiva", f"{(df_par['t'].iloc[0]/hembras*100) if hembras>0 else 0:.1f}%")
    else:
        st.info("No hay datos para analizar")

# ====================== EXPORTAR ======================
elif menu == "Exportar Reportes (PDF)":
    st.title("Centro de Exportaciones")
    st.caption("Genera reportes ejecutivos en PDF y respaldos completos en Excel/CSV.")

    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Inventario")
        df1 = fetch_data("SELECT caravana, tipo_identificacion, raza, sexo, categoria, estado FROM bovinos")
        pdf1 = generar_pdf(df1, "Inventario Ganadero")
        st.download_button("Descargar Inventario PDF", data=pdf1, file_name=f"inventario_ganadero_{fecha_archivo}.pdf", mime='application/pdf')

        st.markdown("### Sanidad")
        df2 = fetch_data("SELECT s.fecha_aplicacion, s.caravana, s.categoria_evento, s.medicamento, b.estatus_brucelosis FROM sanidad s JOIN bovinos b ON s.caravana=b.caravana")
        pdf2 = generar_pdf(df2, "Libro Sanitario")
        st.download_button("Descargar Sanidad PDF", data=pdf2, file_name=f"libro_sanitario_{fecha_archivo}.pdf", mime='application/pdf')
    with c2:
        st.markdown("### Pesajes")
        df3 = fetch_data("SELECT fecha_pesaje, caravana, peso_kg FROM pesajes")
        pdf3 = generar_pdf(df3, "Pesajes")
        st.download_button("Descargar Pesajes PDF", data=pdf3, file_name=f"pesajes_{fecha_archivo}.pdf", mime='application/pdf')

        st.markdown("### Reproduccion")
        df4 = fetch_data("SELECT id, caravana_madre, tipo_servicio, fecha_servicio, resultado_tacto, fecha_parto, caravana_cria FROM reproduccion")
        pdf4 = generar_pdf(df4, "Reproduccion")
        st.download_button("Descargar Reproduccion PDF", data=pdf4, file_name=f"reproduccion_{fecha_archivo}.pdf", mime='application/pdf')

    st.markdown("---")
    st.markdown("### Datos completos")

    tab_csv, tab_excel = st.tabs(["CSV", "Excel"])

    with tab_csv:
        tabla_csv = st.selectbox("Tabla", TABLAS_EXPORTABLES)
        df_csv = fetch_data(f"SELECT * FROM {tabla_csv}")
        if not df_csv.empty:
            csv_buffer = io.StringIO()
            df_csv.to_csv(csv_buffer, index=False)
            st.download_button(
                "Descargar CSV",
                data=csv_buffer.getvalue().encode("utf-8-sig"),
                file_name=f"{tabla_csv}_{fecha_archivo}.csv",
                mime="text/csv",
            )
            st.dataframe(df_csv.head(25), use_container_width=True, hide_index=True)
        else:
            st.info("La tabla seleccionada no tiene registros.")

    with tab_excel:
        st.write("Incluye una hoja de resumen y una hoja por tabla disponible, con filtros y columnas ajustadas.")
        excel_bytes = generar_excel_completo(TABLAS_EXPORTABLES)
        st.download_button(
            "Descargar Excel completo",
            data=excel_bytes,
            file_name=f"exportacion_completa_senasa_{fecha_archivo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown("---")
    st.markdown("### Curva de Crecimiento Individual")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        car_curva = st.selectbox("Seleccionar Animal", caravanas)
        df_curva = fetch_data("SELECT fecha_pesaje, peso_kg FROM pesajes WHERE caravana = ? ORDER BY fecha_pesaje", (car_curva,))
        if not df_curva.empty:
            df_curva['fecha_pesaje'] = pd.to_datetime(df_curva['fecha_pesaje'])
            st.line_chart(df_curva.set_index('fecha_pesaje'), color="#2e9140")

            col_c1, col_c2, col_c3 = st.columns(3)
            col_c1.metric("Peso inicial", f"{df_curva['peso_kg'].iloc[0]:.1f} kg")
            col_c2.metric("Peso actual", f"{df_curva['peso_kg'].iloc[-1]:.1f} kg")
            ganancia = df_curva['peso_kg'].iloc[-1] - df_curva['peso_kg'].iloc[0]
            col_c3.metric("Ganancia total", f"{ganancia:.1f} kg")

            if len(df_curva) > 1:
                dias = (df_curva['fecha_pesaje'].iloc[-1] - df_curva['fecha_pesaje'].iloc[0]).days
                gpd = ganancia / dias if dias > 0 else 0
                st.metric("Ganancia diaria promedio", f"{gpd:.2f} kg/dia")
        else:
            st.info("Sin registros de pesaje para este animal")

    st.markdown("---")
    st.success("Backup automatico creado")
