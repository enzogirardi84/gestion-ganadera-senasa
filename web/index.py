import streamlit as st

st.set_page_config(page_title="Gestion Ganadera SENASA", page_icon="AR", layout="wide")

st.markdown("""
<style>
    .main-title {
        font-size: 2.5em;
        color: #2e9140;
        text-align: center;
        margin-bottom: 20px;
    }
    .subtitle {
        font-size: 1.2em;
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    .card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        background: #f9f9f9;
        text-align: center;
    }
    .card h3 {
        color: #2e9140;
    }
    .footer {
        text-align: center;
        color: #999;
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🐄 Gestion Ganadera SENASA</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sistema Integral de Gestion Veterinaria y Cumplimiento Normativo</div>', unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="card">
        <h3>🔐 Acceso al Sistema</h3>
        <p>Ingresa con tu usuario y contraseña para gestionar tu establecimiento.</p>
        <p><strong>Usuario:</strong> admin<br><strong>Clave:</strong> admin123</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="card">
        <h3>📊 Modulos Disponibles</h3>
        <p>20 modulos integrados para la gestion completa de tu ganaderia.</p>
        <p>Trazabilidad · Sanidad · Reproducción · Farmacia · Finanzas · BI</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🚀 Acceso Rapido")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.link_button("📋 Dashboard", "http://localhost:8501")
with c2:
    st.link_button("🐄 Trazabilidad", "http://localhost:8501")
with c3:
    st.link_button("💉 Sanidad", "http://localhost:8501")
with c4:
    st.link_button("📊 BI", "http://localhost:8501")

st.markdown("---")
st.markdown("""
<div class="footer">
    <p>Desarrollado para cumplimiento normativo SENASA | Res. 540/2015 · 67/2019 · 422/2003</p>
    <p>Version 3.0 | © 2026 Gestion Ganadera SENASA</p>
</div>
""", unsafe_allow_html=True)
