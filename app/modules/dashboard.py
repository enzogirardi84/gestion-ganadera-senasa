import streamlit as st
from app.utils.helpers import crear_backup
from app.database.db import fetch_data

def render():
    st.title("Panel de Control")
    crear_backup()

    df_bov = fetch_data("SELECT * FROM bovinos WHERE estado = 'Activo'")
    if not df_bov.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Cabezas", len(df_bov))
        c2.metric("Hembras", len(df_bov[df_bov['sexo'] == 'Hembra']))
        c3.metric("Machos", len(df_bov[df_bov['sexo'] == 'Macho']))
        rfid = len(df_bov[df_bov['tipo_identificacion'] == 'RFID (Electronica)'])
        c4.metric("RFID", f"{rfid} / {len(df_bov)}", delta_color="off")

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
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Categorias")
            st.bar_chart(df_bov['categoria'].value_counts(), color="#2e9140")
        with col2:
            st.markdown("### Brucelosis")
            st.bar_chart(df_bov['estatus_brucelosis'].value_counts(), color="#d62728")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("### Razas")
            st.bar_chart(df_bov['raza'].value_counts(), color="#1f77b4")
        with col4:
            st.markdown("### Identificacion")
            st.bar_chart(df_bov['tipo_identificacion'].value_counts(), color="#ff7f0e")

        st.markdown("---")
        st.markdown("### Indicadores")
        ce1, ce2, ce3 = st.columns(3)
        with ce1:
            nac = len(df_bov[df_bov['categoria'].str.contains('Ternero', case=False)])
            st.metric("Tasa Natalidad", f"{(nac/len(df_bov))*100:.1f}%" if len(df_bov)>0 else "0%")
        with ce2:
            df_e = fetch_data("SELECT COUNT(*) as t FROM sanidad WHERE categoria_evento LIKE '%Clinico%'")
            st.metric("Tratamientos", df_e['t'].iloc[0] if not df_e.empty else 0)
        with ce3:
            df_v = fetch_data("SELECT COUNT(DISTINCT caravana) as t FROM sanidad WHERE categoria_evento LIKE '%Aftosa%'")
            st.metric("Vacunados Aftosa", df_v['t'].iloc[0] if not df_v.empty else 0)
    else:
        st.info("Sistema sin registros")

import pandas as pd