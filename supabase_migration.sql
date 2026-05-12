-- SQL Migration para Supabase
-- Crear todas las tablas del sistema

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
    propietario_id INTEGER REFERENCES propietarios(id),
    foto TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS propietarios (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    apellido TEXT,
    documento TEXT,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    localidad TEXT,
    provincia TEXT,
    cuit TEXT,
    fecha_registro DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS sanidad (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    categoria_evento TEXT,
    medicamento TEXT,
    dosis TEXT,
    fecha_aplicacion DATE,
    veterinario_acreditado TEXT
);

CREATE TABLE IF NOT EXISTS reproduccion (
    id SERIAL PRIMARY KEY,
    caravana_madre TEXT REFERENCES bovinos(caravana),
    tipo_servicio TEXT,
    fecha_servicio DATE,
    resultado_tacto TEXT,
    fecha_parto DATE,
    caravana_cria TEXT
);

CREATE TABLE IF NOT EXISTS pesajes (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    peso_kg REAL,
    fecha_pesaje DATE
);

CREATE TABLE IF NOT EXISTS alertas (
    id SERIAL PRIMARY KEY,
    tipo_alerta TEXT,
    caravana TEXT,
    descripcion TEXT,
    fecha_alerta DATE,
    resuelta INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS interdicciones (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    enfermedad TEXT,
    fecha_interdiccion DATE,
    motivo TEXT,
    resolucion TEXT,
    estado TEXT DEFAULT 'Activa',
    fecha_levantamiento DATE
);

CREATE TABLE IF NOT EXISTS control_normativo (
    id SERIAL PRIMARY KEY,
    tipo_norma TEXT,
    numero TEXT,
    anio INTEGER,
    descripcion TEXT,
    articulo TEXT,
    cumplimiento TEXT DEFAULT 'Pendiente',
    fecha_cumplimiento DATE,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS toros (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    raza TEXT,
    origen TEXT,
    fecha_nacimiento DATE,
    registro TEXT,
    aptitud TEXT,
    comentarios TEXT
);

CREATE TABLE IF NOT EXISTS inseminaciones (
    id SERIAL PRIMARY KEY,
    caravana_vaca TEXT REFERENCES bovinos(caravana),
    toro_id INTEGER REFERENCES toros(id),
    fecha_inseminacion DATE,
    hora_inseminacion TEXT,
    tipo_semen TEXT,
    tecnico TEXT,
    resultado TEXT DEFAULT 'Pendiente',
    fecha_probable_parto DATE,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS agenda (
    id SERIAL PRIMARY KEY,
    fecha_evento DATE,
    hora_evento TEXT,
    tipo_evento TEXT,
    titulo TEXT,
    caravana TEXT REFERENCES bovinos(caravana),
    propietario_id INTEGER REFERENCES propietarios(id),
    veterinario TEXT,
    descripcion TEXT,
    estado TEXT DEFAULT 'Pendiente'
);

CREATE TABLE IF NOT EXISTS farmacia (
    id SERIAL PRIMARY KEY,
    nombre_producto TEXT,
    principio_activo TEXT,
    tipo_producto TEXT,
    proveedor TEXT,
    concentracion TEXT,
    presentacion TEXT,
    laboratorio TEXT
);

CREATE TABLE IF NOT EXISTS stock (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER REFERENCES farmacia(id),
    lote TEXT,
    fecha_vencimiento DATE,
    cantidad INTEGER DEFAULT 0,
    precio_compra REAL DEFAULT 0,
    precio_venta REAL DEFAULT 0,
    ubicacion TEXT
);

CREATE TABLE IF NOT EXISTS recetas (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    propietario_id INTEGER REFERENCES propietarios(id),
    veterinario TEXT,
    fecha_receta DATE DEFAULT CURRENT_DATE,
    diagnostico TEXT,
    indicaciones TEXT,
    firma_digital TEXT
);

CREATE TABLE IF NOT EXISTS receta_detalle (
    id SERIAL PRIMARY KEY,
    receta_id INTEGER REFERENCES recetas(id),
    producto_id INTEGER REFERENCES farmacia(id),
    dosis TEXT,
    frecuencia TEXT,
    duracion TEXT,
    via_administracion TEXT,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS certificados (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    tipo_certificado TEXT,
    fecha_emision DATE DEFAULT CURRENT_DATE,
    fecha_validez DATE,
    veterinario_firmante TEXT,
    matricula TEXT,
    motivo TEXT,
    resultado TEXT,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS intervenciones (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    tipo_intervencion TEXT,
    fecha_intervencion DATE,
    veterinario TEXT,
    diagnostico TEXT,
    procedimiento TEXT,
    hallazgos TEXT,
    recomendaciones TEXT,
    costo REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS historia_clinica (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    fecha_consulta DATE DEFAULT CURRENT_DATE,
    motivo_consulta TEXT,
    anamnesis TEXT,
    exploracion_fisica TEXT,
    diagnostico_presuntivo TEXT,
    diagnostico_definitivo TEXT,
    tratamiento TEXT,
    observaciones TEXT,
    veterinario TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    nombre TEXT,
    rol TEXT DEFAULT 'Veterinario',
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS hospitalizacion (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    fecha_ingreso DATE DEFAULT CURRENT_DATE,
    fecha_egreso DATE,
    motivo TEXT,
    diagnostico_ingreso TEXT,
    tratamiento TEXT,
    veterinario_responsable TEXT,
    estado TEXT DEFAULT 'Internado',
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS kardex_hospitalario (
    id SERIAL PRIMARY KEY,
    hospitalizacion_id INTEGER REFERENCES hospitalizacion(id),
    fecha DATE DEFAULT CURRENT_DATE,
    hora TEXT,
    veterinario TEXT,
    temperatura REAL,
    frecuencia_cardiaca INTEGER,
    frecuencia_respiratoria INTEGER,
    observacion TEXT,
    medicacion TEXT
);

CREATE TABLE IF NOT EXISTS laboratorio (
    id SERIAL PRIMARY KEY,
    caravana TEXT REFERENCES bovinos(caravana),
    fecha_solicitud DATE DEFAULT CURRENT_DATE,
    tipo_analisis TEXT,
    muestra TEXT,
    fecha_toma DATE,
    fecha_resultado DATE,
    solicitado_por TEXT,
    laboratorio_externo TEXT,
    resultado TEXT,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS resultados_laboratorio (
    id SERIAL PRIMARY KEY,
    laboratorio_id INTEGER REFERENCES laboratorio(id),
    parametro TEXT,
    valor TEXT,
    unidad TEXT,
    rango_referencia TEXT,
    estado TEXT
);

CREATE TABLE IF NOT EXISTS facturacion (
    id SERIAL PRIMARY KEY,
    numero_factura TEXT,
    propietario_id INTEGER REFERENCES propietarios(id),
    fecha_emision DATE DEFAULT CURRENT_DATE,
    tipo_comprobante TEXT,
    descripcion TEXT,
    subtotal REAL DEFAULT 0,
    iva REAL DEFAULT 0,
    total REAL DEFAULT 0,
    metodo_pago TEXT,
    estado_pago TEXT DEFAULT 'Pendiente',
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS factura_detalle (
    id SERIAL PRIMARY KEY,
    factura_id INTEGER REFERENCES facturacion(id),
    concepto TEXT,
    cantidad INTEGER DEFAULT 1,
    precio_unitario REAL DEFAULT 0,
    subtotal REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crm_interacciones (
    id SERIAL PRIMARY KEY,
    propietario_id INTEGER REFERENCES propietarios(id),
    fecha_interaccion DATE DEFAULT CURRENT_DATE,
    tipo_interaccion TEXT,
    canal TEXT,
    descripcion TEXT,
    resultado TEXT,
    proximo_seguimiento DATE,
    veterinario TEXT
);

CREATE TABLE IF NOT EXISTS recordatorios (
    id SERIAL PRIMARY KEY,
    propietario_id INTEGER REFERENCES propietarios(id),
    caravana TEXT,
    tipo_recordatorio TEXT,
    fecha_envio DATE,
    fecha_programada DATE,
    mensaje TEXT,
    canal TEXT DEFAULT 'WhatsApp',
    enviado INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lotes (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    superficie_ha REAL,
    tipo_pastura TEXT,
    capacidad_animales INTEGER,
    estado TEXT DEFAULT 'Activo',
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS lote_animales (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    caravana TEXT REFERENCES bovinos(caravana),
    fecha_asignacion DATE DEFAULT CURRENT_DATE,
    fecha_salida DATE
);

CREATE TABLE IF NOT EXISTS finanzas (
    id SERIAL PRIMARY KEY,
    tipo TEXT,
    categoria TEXT,
    descripcion TEXT,
    monto REAL,
    fecha DATE DEFAULT CURRENT_DATE,
    caravana TEXT,
    propietario_id INTEGER REFERENCES propietarios(id),
    forma_pago TEXT,
    comprobante TEXT
);

-- Insertar usuario admin por defecto
INSERT INTO usuarios (username, password_hash, nombre, rol)
VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrador', 'Administrador')
ON CONFLICT (username) DO NOTHING;

-- Insertar normas por defecto
INSERT INTO control_normativo (tipo_norma, numero, anio, descripcion, articulo, cumplimiento) VALUES
('Resolucion', '540/2015', 2015, 'Vacunacion Brucelosis', 'Art. 1 y 3', 'Pendiente'),
('Resolucion', '67/2019', 2019, 'Trazabilidad SIGSA', 'Art. 1-5', 'Pendiente'),
('Resolucion', '422/2003', 2003, 'Tuberculosis Bovina', 'Art. 1-4', 'Pendiente'),
('Ley', '27.274', 2016, 'Vacunacion Aftosa', 'Art. 1-3', 'Pendiente')
ON CONFLICT DO NOTHING;
