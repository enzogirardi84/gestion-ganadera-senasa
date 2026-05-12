import os
import sqlite3
import pandas as pd

DB_NAME = os.environ.get("DB_NAME", "gestion_bovinos_senasa.db")
DEFAULT_ADMIN_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def run_query(query, params=()):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        raise e

def fetch_data(query, params=()):
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df

def init_db():
    with get_connection() as conn:
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
        c.execute(
            """
            INSERT OR IGNORE INTO usuarios (username, password_hash, nombre, rol)
            VALUES (?, ?, ?, ?)
            """,
            ("admin", DEFAULT_ADMIN_HASH, "Administrador", "Administrador"),
        )
        conn.commit()
