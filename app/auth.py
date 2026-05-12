import hashlib
import streamlit as st

from app.database.db import fetch_data, run_query

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login(username, password):
    df = fetch_data("SELECT * FROM usuarios WHERE username = ? AND activo = 1", (username,))
    if not df.empty and df['password_hash'].iloc[0] == hash_password(password):
        return df.iloc[0].to_dict()
    return None

def register(username, password, nombre, rol):
    q = "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?, ?, ?, ?)"
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

    with st.expander("Registrarse"):
        with st.form("registro"):
            new_user = st.text_input("Usuario nuevo")
            new_pass = st.text_input("Clave", type="password")
            new_nombre = st.text_input("Nombre completo")
            new_rol = st.selectbox("Rol", ["Veterinario", "Administrador", "Tecnico", "Propietario"])
            if st.form_submit_button("Crear cuenta"):
                if new_user and new_pass:
                    if register(new_user, new_pass, new_nombre, new_rol):
                        st.success("Cuenta creada")
                    else:
                        st.error("El usuario ya existe")