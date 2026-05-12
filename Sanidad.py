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
import io
import csv

# Configuracion - cambiar a False para usar Supabase
USAR_SUPABASE = False  # False = SQLite local/cloud | True = Supabase cloud

SUPABASE_URL = "https://tfdgaxowacbxqtuvhhdp.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

DB_NAME = 'gestion_bovinos_senasa.db'
BACKUP_DIR = 'backups'

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
                FOREIGN KEY(caravana) REFERENCES bovinos(caravana)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                nombre TEXT,
                rol TEXT DEFAULT 'Veterinario',
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

# Crear usuario admin por defecto si no existe
try:
    run_query("INSERT OR IGNORE INTO usuarios (username, password_hash, nombre, rol) VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrador', 'Administrador')")
except:
    pass

# Migraciones: agregar columnas faltantes a tablas existentes
try:
    run_query("ALTER TABLE bovinos ADD COLUMN propietario_id INTEGER")
except:
    pass

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

def verificar_alertas():
    bovinos = fetch_data("SELECT caravana, fecha_nacimiento, estatus_brucelosis FROM bovinos WHERE estado = 'Activo'")
    today = date.today()
    run_query("DELETE FROM alertas WHERE resuelta = 1")
    for _, row in bovinos.iterrows():
        fecha_nac = datetime.strptime(str(row['fecha_nacimiento']), '%Y-%m-%d').date()
        edad_meses = relativedelta(today, fecha_nac).months
        if 3 <= edad_meses <= 8 and row['estatus_brucelosis'] == 'Sin Diagnostico':
            run_query("INSERT INTO alertas (tipo_alerta, caravana, descripcion, fecha_alerta) VALUES (?, ?, ?, ?)",
                     ('Brucelosis Pendiente', row['caravana'], f'Verificar vacunacion Cepa 19 (edad: {edad_meses} meses)', today))

    stock = fetch_data("""
        SELECT s.id, f.nombre_producto, s.lote, s.fecha_vencimiento, s.cantidad
        FROM stock s JOIN farmacia f ON s.producto_id = f.id
        WHERE s.fecha_vencimiento BETWEEN DATE('now') AND DATE('now', '+90 days')
    """)
    for _, row in stock.iterrows():
        dias = (datetime.strptime(row['fecha_vencimiento'], '%Y-%m-%d').date() - date.today()).days
        run_query("INSERT INTO alertas (tipo_alerta, caravana, descripcion, fecha_alerta) VALUES (?, ?, ?, ?)",
                 ('Vencimiento Stock', 'Sistema', f"{row['nombre_producto']} lote {row['lote']} vence en {dias} dias", today))

# --- USUARIOS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- UI ---
st.set_page_config(page_title="Gestion Ganadera SENASA", page_icon="AR", layout="wide")

# Inicializar Supabase si está configurado
if USAR_SUPABASE:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except:
        pass

# Migraciones
try:
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("ALTER TABLE bovinos ADD COLUMN propietario_id INTEGER")
        conn.commit()
except:
    pass
try:
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("ALTER TABLE bovinos ADD COLUMN foto TEXT")
        conn.commit()
except:
    pass

if st.session_state.usuario is None:
    st.title("Inicio de Sesion")
    with st.form("login"):
        username = st.text_input("Usuario")
        password = st.text_input("Clave", type="password")
        if st.form_submit_button("Ingresar"):
            df = fetch_data("SELECT * FROM usuarios WHERE username = ? AND activo = 1", (username,))
            if not df.empty and df['password_hash'].iloc[0] == hash_password(password):
                st.session_state.usuario = df.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")

    st.markdown("---")
    col_reg1, _ = st.columns(2)
    with col_reg1:
        with st.expander("Registrarse"):
            with st.form("registro"):
                new_user = st.text_input("Usuario nuevo")
                new_pass = st.text_input("Clave", type="password")
                new_nombre = st.text_input("Nombre completo")
                new_rol = st.selectbox("Rol", ["Veterinario", "Administrador", "Tecnico", "Propietario"])
                if st.form_submit_button("Crear cuenta"):
                    if new_user and new_pass:
                        q = "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?, ?, ?, ?)"
                        if run_query(q, (new_user, hash_password(new_pass), new_nombre, new_rol)):
                            st.success("Cuenta creada")
                        else:
                            st.error("El usuario ya existe")
    st.stop()

st.sidebar.markdown(f"**Usuario:** {st.session_state.usuario['nombre']} ({st.session_state.usuario['rol']})")
if st.sidebar.button("Cerrar Sesion"):
    st.session_state.usuario = None
    st.rerun()

st.markdown("![Logo SENASA](https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Logo_Senasa_%28Argentina%29.svg/512px-Logo_Senasa_%28Argentina%29.svg.png)")
st.sidebar.title("Menu")
menu = st.sidebar.radio("Navegacion", [
    "Dashboard Analitico", "Trazabilidad e Inventario", "Propietarios/Clientes",
    "Historia Clinica", "Sanidad y Brucelosis", "Hospitalizacion",
    "Agenda/Citas", "Laboratorio", "Farmacia/Stock",
    "Recetario Digital", "Facturacion", "CRM y Seguimiento",
    "Recordatorios", "Produccion y Pesajes",
    "Reproduccion", "Intervenciones", "Certificados",
    "Lotes/Potreros", "Finanzas",
    "Alertas y Notificaciones", "Marco Legal y Normativas", "Exportar Reportes (PDF)",
    "BI - Analitica Avanzada"
])

# ====================== DASHBOARD ======================
if menu == "Dashboard Analitico":
    st.title("Panel de Control")
    crear_backup()
    df_bov = fetch_data("SELECT * FROM bovinos WHERE estado = 'Activo'")
    if not df_bov.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Cabezas", len(df_bov))
        c2.metric("Hembras", len(df_bov[df_bov['sexo'] == 'Hembra']))
        c3.metric("Machos", len(df_bov[df_bov['sexo'] == 'Macho']))
        rfid_count = len(df_bov[df_bov['tipo_identificacion'] == 'RFID (Electronica)'])
        c4.metric("RFID", f"{rfid_count} / {len(df_bov)}", delta_color="off")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Brucelosis +", len(df_bov[df_bov['estatus_brucelosis'] == 'Positivo']), delta_color="inverse")
        df_pes = fetch_data("SELECT AVG(peso_kg) as promedio FROM pesajes")
        prom = df_pes['promedio'].iloc[0] if not df_pes.empty and pd.notna(df_pes['promedio'].iloc[0]) else 0
        c6.metric("Peso Promedio", f"{prom:.1f} kg")
        df_repr = fetch_data("SELECT COUNT(*) as total FROM reproduccion WHERE fecha_parto IS NOT NULL")
        c7.metric("Partos", df_repr['total'].iloc[0])
        df_al = fetch_data("SELECT COUNT(*) as total FROM alertas WHERE resuelta = 0")
        c8.metric("Alertas", df_al['total'].iloc[0], delta_color="inverse")

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
            nacimientos = len(df_bov[df_bov['categoria'].str.contains('Ternero', case=False)])
            tasa = (nacimientos / len(df_bov)) * 100
            st.metric("Tasa Natalidad", f"{tasa:.1f}%")
        with col_e2:
            df_enf = fetch_data("SELECT COUNT(*) as total FROM sanidad WHERE categoria_evento LIKE '%Clinico%'")
            st.metric("Tratamientos Clinicos", df_enf['total'].iloc[0] if not df_enf.empty else 0)
        with col_e3:
            df_vac = fetch_data("SELECT COUNT(DISTINCT caravana) as total FROM sanidad WHERE categoria_evento LIKE '%Aftosa%'")
            st.metric("Vacunados Aftosa", df_vac['total'].iloc[0] if not df_vac.empty else 0)

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

# ====================== TRAZABILIDAD ======================
elif menu == "Trazabilidad e Inventario":
    st.title("Trazabilidad e Inventario (SIGSA)")

    df_props = fetch_data("SELECT id, nombre, apellido FROM propietarios")
    props_list = ["Sin propietario"] + [f"{r['nombre']} {r['apellido']}" for _, r in df_props.iterrows()]

    with st.expander("Alta de Animal"):
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
                        st.success(f"Animal {caravana.upper()} registrado.")
                    else:
                        st.error("La caravana ya existe.")
                else:
                    st.error("Caravana obligatoria.")

    st.markdown("### Padron")
    df_inv = fetch_data("""
        SELECT b.caravana, b.tipo_identificacion, b.sexo, b.categoria, b.fecha_nacimiento, b.estatus_brucelosis,
               COALESCE(p.nombre || ' ' || p.apellido, 'Sin propietario') as propietario
        FROM bovinos b LEFT JOIN propietarios p ON b.propietario_id = p.id
        WHERE b.estado='Activo'
    """)
    st.dataframe(df_inv, width=1200, hide_index=True)

    with st.expander("Modificar Animal"):
        caravanas_all = obtener_lista_caravanas()
        if caravanas_all:
            with st.form("form_mod"):
                car_sel = st.selectbox("Seleccionar", caravanas_all)
                nuevo_estado = st.selectbox("Estado", ["Activo", "Mortandad", "Venta", "Cambio de Dueno"])
                if st.form_submit_button("Actualizar"):
                    run_query("UPDATE bovinos SET estado = ? WHERE caravana = ?", (nuevo_estado, car_sel))
                    st.success("Actualizado.")

# ====================== PROPIETARIOS ======================
elif menu == "Propietarios/Clientes":
    st.title("Gestion de Propietarios/Clientes")
    with st.expander("Nuevo Propietario"):
        with st.form("form_prop", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                documento = st.text_input("DNI/LE")
                telefono = st.text_input("Telefono")
            with c2:
                email = st.text_input("Email")
                direccion = st.text_input("Direccion")
                localidad = st.text_input("Localidad")
                provincia = st.selectbox("Provincia", ["Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Cordoba", "Corrientes", "Entre Rios", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquen", "Rio Negro", "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero", "Tierra del Fuego", "Tucuman"])
                cuit = st.text_input("CUIT")

            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO propietarios (nombre, apellido, documento, telefono, email, direccion, localidad, provincia, cuit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (nombre, apellido, documento, telefono, email, direccion, localidad, provincia, cuit))
                st.success("Propietario registrado.")

    df_props = fetch_data("SELECT * FROM propietarios ORDER BY apellido")
    st.dataframe(df_props, width=1200, hide_index=True)

    with st.expander("Animales por Propietario"):
        if not df_props.empty:
            sel_prop = st.selectbox("Propietario", df_props['id'].tolist(), format_func=lambda i: f"{df_props[df_props['id']==i]['nombre'].values[0]} {df_props[df_props['id']==i]['apellido'].values[0]}")
            df_bov_prop = fetch_data("SELECT caravana, raza, sexo, categoria FROM bovinos WHERE propietario_id = ?", (sel_prop,))
            st.dataframe(df_bov_prop, width=1200, hide_index=True)

# ====================== HISTORIA CLINICA ======================
elif menu == "Historia Clinica":
    st.title("Historia Clinica Electronica")
    caravanas = obtener_lista_caravanas()
    if caravanas:
        car_sel = st.selectbox("Seleccionar Animal", caravanas, key="hc_car")
        df_hist = fetch_data("""
            SELECT fecha_consulta, motivo_consulta, diagnostico_presuntivo, diagnostico_definitivo, tratamiento, veterinario
            FROM historia_clinica WHERE caravana = ? ORDER BY fecha_consulta DESC
        """, (car_sel,))
        st.dataframe(df_hist, width=1200, hide_index=True)

        with st.expander("Nueva Consulta"):
            with st.form("form_hc", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    motivo = st.text_area("Motivo de consulta")
                    anamnesis = st.text_area("Anamnesis")
                    exploracion = st.text_area("Exploracion fisica")
                with c2:
                    diag_p = st.text_area("Diagnostico presuntivo")
                    diag_d = st.text_area("Diagnostico definitivo")
                    tratamiento = st.text_area("Tratamiento indicado")
                observaciones = st.text_area("Observaciones")
                if st.form_submit_button("Guardar Consulta"):
                    run_query("INSERT INTO historia_clinica (caravana, motivo_consulta, anamnesis, exploracion_fisica, diagnostico_presuntivo, diagnostico_definitivo, tratamiento, observaciones, veterinario) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (car_sel, motivo, anamnesis, exploracion, diag_p, diag_d, tratamiento, observaciones, st.session_state.usuario['nombre']))
                    st.success("Consulta registrada.")
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
                    run_query("INSERT INTO facturacion (numero_factura, propietario_id, fecha_emision, tipo_comprobante, descripcion, subtotal, iva, total, metodo_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (nro_fact, prop_sel, fecha_fac, tipo_comp, desc_fac, total_calc, iva, total_calc + iva, metodo))
                    fact_id = fetch_data("SELECT last_insert_rowid() as id")['id'].iloc[0]
                    for item in items:
                        if item[0]:
                            run_query("INSERT INTO factura_detalle (factura_id, concepto, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (fact_id, item[0], item[1], item[2], item[3]))
                    st.success(f"Factura {nro_fact} emitida.")
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

    tab_f1, tab_f2, tab_f3 = st.tabs(["Productos", "Stock/Lotes", "Proximos a vencer"])

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
                    if st.form_submit_button("Agregar Stock"):
                        run_query("INSERT INTO stock (producto_id, lote, fecha_vencimiento, cantidad, precio_compra, precio_venta, ubicacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (prod_id, lote, fecha_venc, cantidad, precio_c, precio_v, ubicacion))
                        st.success("Stock agregado.")

            df_stock = fetch_data("""
                SELECT f.nombre_producto, f.tipo_producto, s.lote, s.fecha_vencimiento, s.cantidad, s.precio_compra, s.precio_venta, s.ubicacion
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
                run_query("INSERT INTO recetas (caravana, propietario_id, veterinario, fecha_receta, diagnostico, indicaciones, firma_digital) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (car_rec, None if prop_rec == "N/A" else prop_rec, st.session_state.usuario['nombre'], fecha_rec, diagnostico, indicaciones, "Firma digital pendiente"))
                receta_id = fetch_data("SELECT last_insert_rowid() as id")['id'].iloc[0]
                for md in meds_data:
                    run_query("INSERT INTO receta_detalle (receta_id, producto_id, dosis, frecuencia, duracion, via_administracion) VALUES (?, ?, ?, ?, ?, ?)",
                             (receta_id, md[0], md[1], md[2], md[3], md[4]))
                st.success("Receta emitida.")

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
    st.title("Exportar Reportes PDF")
    c1, c2 = st.columns(2)
    with c1:
        st.info("Inventario")
        df1 = fetch_data("SELECT caravana, tipo_identificacion, raza, sexo, categoria, estado FROM bovinos")
        pdf1 = generar_pdf(df1, "Inventario Ganadero")
        st.download_button("Descargar Inventario", data=pdf1, file_name='Inventario.pdf', mime='application/pdf')
        st.info("Sanidad")
        df2 = fetch_data("SELECT s.fecha_aplicacion, s.caravana, s.categoria_evento, s.medicamento, b.estatus_brucelosis FROM sanidad s JOIN bovinos b ON s.caravana=b.caravana")
        pdf2 = generar_pdf(df2, "Libro Sanitario")
        st.download_button("Descargar Sanidad", data=pdf2, file_name='Sanidad.pdf', mime='application/pdf')
    with c2:
        st.info("Pesajes")
        df3 = fetch_data("SELECT fecha_pesaje, caravana, peso_kg FROM pesajes")
        pdf3 = generar_pdf(df3, "Pesajes")
        st.download_button("Descargar Pesajes", data=pdf3, file_name='Pesajes.pdf', mime='application/pdf')
        st.info("Reproduccion")
        df4 = fetch_data("SELECT id, caravana_madre, tipo_servicio, fecha_servicio, resultado_tacto, fecha_parto, caravana_cria FROM reproduccion")
        pdf4 = generar_pdf(df4, "Reproduccion")
        st.download_button("Descargar Reproduccion", data=pdf4, file_name='Reproduccion.pdf', mime='application/pdf')

    st.markdown("---")
    st.markdown("### Exportar a CSV / Excel")

    tab_csv, tab_excel = st.tabs(["CSV", "Excel"])

    with tab_csv:
        st.markdown("Selecciona la tabla a exportar:")
        tabla_csv = st.selectbox("Tabla", ["bovinos", "sanidad", "reproduccion", "pesajes", "farmacia", "stock", "certificados", "intervenciones", "finanzas", "lotes"])
        df_csv = fetch_data(f"SELECT * FROM {tabla_csv}")
        if not df_csv.empty:
            csv_buffer = io.StringIO()
            df_csv.to_csv(csv_buffer, index=False)
            st.download_button("Descargar CSV", data=csv_buffer.getvalue(), file_name=f'{tabla_csv}.csv', mime='text/csv')
            st.dataframe(df_csv.head(10), width=1200, hide_index=True)

    with tab_excel:
        st.markdown("Descarga completa de todas las tablas en un archivo Excel:")
        if st.button("Generar Excel completo"):
            with pd.ExcelWriter("exportacion_completa.xlsx", engine='openpyxl') as writer:
                for tabla in ["bovinos", "sanidad", "reproduccion", "pesajes", "propietarios", "farmacia", "stock", "certificados", "intervenciones", "finanzas", "lotes", "agenda"]:
                    try:
                        df = fetch_data(f"SELECT * FROM {tabla}")
                        df.to_excel(writer, sheet_name=tabla, index=False)
                    except:
                        pass
            with open("exportacion_completa.xlsx", "rb") as f:
                st.download_button("Descargar Excel", data=f, file_name='exportacion_completa.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            os.remove("exportacion_completa.xlsx")
            st.success("Excel generado.")

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
