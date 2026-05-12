import hashlib
import hmac
import secrets
import streamlit as st

from app.database.db import fetch_data, run_query

ROLES_USUARIO = ["Administrador", "Veterinario", "Tecnico", "Propietario"]
PBKDF2_ITERATIONS = 260000

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"

def verify_password(password, password_hash):
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
    return hmac.compare_digest(hashlib.sha256(str(password).encode()).hexdigest(), stored)

def login(username, password):
    username = str(username or "").strip().lower()
    df = fetch_data("SELECT * FROM usuarios WHERE username = ? AND activo = 1", (username,))
    if not df.empty and verify_password(password, df['password_hash'].iloc[0]):
        if not str(df['password_hash'].iloc[0]).startswith("pbkdf2_sha256$"):
            run_query("UPDATE usuarios SET password_hash = ? WHERE id = ?", (hash_password(password), int(df["id"].iloc[0])))
            df = fetch_data("SELECT * FROM usuarios WHERE id = ?", (int(df["id"].iloc[0]),))
        return df.iloc[0].to_dict()
    return None

def register(username, password, nombre, rol):
    username = str(username or "").strip().lower()
    nombre = str(nombre or "").strip() or username
    rol = rol if rol in ROLES_USUARIO else "Veterinario"
    if len(username) < 3 or len(str(password or "")) < 8:
        return False
    q = "INSERT INTO usuarios (username, password_hash, nombre, rol, activo) VALUES (?, ?, ?, ?, 1)"
    return run_query(q, (username, hash_password(password), nombre, rol))

def render_login():
    st.title("Inicio de Sesion")
    with st.form("login"):
        username = st.text_input("Usuario")
        password = st.text_input("Clave", type="password")
        if st.form_submit_button("Ingresar"):
            user = login(username, password)
            if user:
                st.session_state.usuario = user
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")

    st.info("Si necesitas acceso, pedile a un administrador que cree tu usuario dentro del sistema.")
