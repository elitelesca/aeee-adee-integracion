# ================================================================
# integrated_viewer_optimizado.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.1
# Descripción:
#     Interfaz interactiva construida con Streamlit para visualizar
#     datos y ejecutar la optimización de asignaciones educativas.
#     Muestra estudiantes, docentes e instituciones en un mapa
#     interactivo, con opción de exportar resultados.
# Dependencias:
#     streamlit, pandas, folium, streamlit_folium, plotly, xlsxwriter
# ================================================================

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from integrated_problem import IntegratedProblem
from integrated_optimization import run_integrated_optimization
from database import cargar_datos_desde_db, engine
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO

# ================================
# CONFIGURACIÓN INICIAL DE PÁGINA
# ================================
st.set_page_config(page_title="AEEE-ADEE WebSystem", layout="wide")
st.markdown(
    "<h1 style='text-align: center; color: white;'>📊 AEEE-ADEE Integrado</h1>",
    unsafe_allow_html=True,
)

# ================================
# CARGA INICIAL DE DATOS (CACHÉ)
# ================================
@st.cache_data(ttl=600)
def cargar_datos_iniciales():
    """
    Carga estudiantes, docentes y clases desde la base de datos.

    Returns:
        tuple: (estudiantes, docentes, clases, establecimientos)
    """
    return cargar_datos_desde_db()

estudiantes, docentes, clases, establecimientos = cargar_datos_iniciales()

if estudiantes.empty or docentes.empty or clases.empty:
    st.error("❌ Error al cargar datos. Verifica la conexión con la base de datos.")
    st.stop()

# ================================
# CARGAR ASIGNACIONES
# ================================
@st.cache_data(ttl=600)
def cargar_asignaciones():
    """
    Carga asignaciones actuales desde la base de datos.

    Returns:
        pd.DataFrame: Asignaciones actuales.
    """
    try:
        return pd.read_sql("""
            SELECT 
                a.id,
                e.nombre AS estudiante,
                d.nombre AS docente,
                i.nombre AS institucion,
                a.grado,
                a.seccion,
                a.turno,
                a.distancia
            FROM asignacion_mec a
            JOIN estudiantes e ON a.estudiante_id = e.id
            JOIN docentes d ON a.docente_id = d.id
            JOIN establecimientos es ON a.establecimiento_id = es.id
            JOIN instituciones i ON es.institucion_id = i.id
        """, engine)
    except SQLAlchemyError as e:
        st.error(f"❌ Error cargando asignaciones: {e}")
        return pd.DataFrame()

# ================================
# DESCARGA EN EXCEL
# ================================
def exportar_excel(df: pd.DataFrame):
    """
    Exporta un DataFrame a un archivo Excel.

    Args:
        df (pd.DataFrame): Datos a exportar.

    Returns:
        bytes: Archivo Excel en memoria.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Asignaciones")
    return output.getvalue()

# ================================
# FILTROS DINÁMICOS
# ================================
def aplicar_filtros(df, tipo="estudiantes"):
    if departamento_sel != "Todos":
        df = df[df["departamento"] == departamento_sel]
    if localidad_sel != "Todos":
        df = df[df["localidad"] == localidad_sel]
    if barrio_sel != "Todos" and tipo == "estudiantes":
        df = df[df["barrio"] == barrio_sel]
    if institucion_sel != "Todos" and tipo == "clases":
        df = df[df["nombre_institucion"] == institucion_sel]
    return df

# ================================
# INTERFAZ PRINCIPAL CON TABS
# ================================
tabs = st.tabs(["🔍 Visualización Actual", "🚀 Optimización"])

# ================================
# 1. VISUALIZACIÓN ACTUAL
# ================================
with tabs[0]:
    st.success(f"✅ Datos cargados: {len(estudiantes)} estudiantes, {len(docentes)} docentes, {len(clases)} clases")
    asignaciones = cargar_asignaciones()

    # --- Filtros dinámicos
    st.subheader("🎛️ Filtros")
    departamentos = estudiantes["departamento"].dropna().unique()
    departamento_sel = st.selectbox("Departamento", ["Todos"] + list(departamentos))

    localidades = estudiantes.query("departamento == @departamento_sel")["localidad"].dropna().unique() \
        if departamento_sel != "Todos" else estudiantes["localidad"].dropna().unique()
    localidad_sel = st.selectbox("Localidad", ["Todos"] + list(localidades))

    barrios = estudiantes.query("localidad == @localidad_sel")["barrio"].dropna().unique() \
        if localidad_sel != "Todos" else estudiantes["barrio"].dropna().unique()
    barrio_sel = st.selectbox("Barrio", ["Todos"] + list(barrios))

    instituciones = clases["nombre_institucion"].dropna().unique()
    institucion_sel = st.selectbox("Institución", ["Todos"] + list(instituciones))

    # Filtrar datasets
    estudiantes_f = aplicar_filtros(estudiantes, "estudiantes")
    docentes_f = aplicar_filtros(docentes, "docentes")
    clases_f = aplicar_filtros(clases, "clases")

    if not asignaciones.empty:
        st.subheader("📋 Asignaciones Actuales")
        st.dataframe(asignaciones, use_container_width=True)

        excel_bytes = exportar_excel(asignaciones)
        st.download_button(
            label="📥 Exportar Asignaciones a Excel",
            data=excel_bytes,
            file_name="asignaciones_actuales.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("🗺️ Mapa de Estudiantes, Docentes e Instituciones")
        mapa = folium.Map(location=[-25.3, -57.6], zoom_start=7)
        marker_cluster = MarkerCluster().add_to(mapa)

        # Marcadores de estudiantes
        for _, est in estudiantes_f.iterrows():
            folium.Marker(
                [est["lat"], est["lng"]],
                popup=(
                    f"🎓 <b>Estudiante:</b> {est['nombre']}<br>"
                    f"<b>Grado:</b> {est.get('grado', 'N/A')}<br>"
                    f"<b>Barrio:</b> {est.get('barrio', 'N/A')}"
                ),
                icon=folium.Icon(color="blue", icon="user"),
            ).add_to(marker_cluster)

            asign = asignaciones[asignaciones["estudiante"] == est["nombre"]]
            if not asign.empty:
                docente = docentes_f[docentes_f["nombre"] == asign["docente"].values[0]]
                clase = clases_f[clases_f["nombre_institucion"] == asign["institucion"].values[0]]

                if not docente.empty and not clase.empty:
                    est_coord = [est["lat"], est["lng"]]
                    doc_coord = [docente.iloc[0]["lat"], docente.iloc[0]["lng"]]
                    cls_coord = [clase.iloc[0]["lat"], clase.iloc[0]["lng"]]

                    # Línea Estudiante → Docente
                    folium.PolyLine([est_coord, doc_coord], color="blue", weight=1.5).add_to(mapa)
                    # Línea Docente → Clase
                    folium.PolyLine([doc_coord, cls_coord], color="green", weight=1.5).add_to(mapa)
        # Marcadores de docentes
        for _, doc in docentes.iterrows():
            folium.Marker(
                [doc["lat"], doc["lng"]],
                popup=f"👨‍🏫 Docente: {doc['nombre']}",
                icon=folium.Icon(color="green", icon="user"),
            ).add_to(marker_cluster)

        # Marcadores de instituciones
        for _, cls in clases.iterrows():
            folium.Marker(
                [cls["lat"], cls["lng"]],
                popup=(
                    f"🏫 {cls['nombre_institucion']}<br>"
                    f"Grado: {cls['grado']}<br>"
                    f"Turno: {cls['turno']}"
                ),
                icon=folium.Icon(color="red", icon="education"),
            ).add_to(marker_cluster)

        st_folium(mapa, width=1000, height=500, key="mapa_actual")

    else:
        st.warning("⚠️ No hay asignaciones guardadas todavía.")

# ================================
# 2. OPTIMIZACIÓN
# ================================
with tabs[1]:
    st.subheader("🚀 Optimización de Asignaciones")
    pop_size = st.slider("Tamaño de población", 10, 200, 50)
    n_gen = st.slider("Generaciones", 10, 200, 30)
    n_jobs = st.slider("Procesos paralelos", 1, 8, 1)

    if "asignaciones_opt" not in st.session_state:
        st.session_state.asignaciones_opt = pd.DataFrame()

    if st.button("Ejecutar Optimización"):
        try:
            st.info("⏳ Ejecutando optimización, espera por favor...")
            problem = IntegratedProblem(estudiantes, docentes, clases)

            result = run_integrated_optimization(
                problem,
                pop_size,
                n_gen,
                n_jobs,
                db_config={
                    "user": "postgres",
                    "password": "Admin.123",
                    "host": "localhost",
                    "port": "5432",
                    "database": "Asignacion_MEC"
                }
            )

            if result:
                st.success("✅ Optimización completada y resultados guardados en la BD.")
                st.session_state.asignaciones_opt = cargar_asignaciones()
        except Exception as e:
            st.error(f"❌ Error durante la optimización: {e}")

    if not st.session_state.asignaciones_opt.empty:
        st.subheader("📋 Asignaciones Optimizadas")
        st.dataframe(
            st.session_state.asignaciones_opt,
            use_container_width=True,
            height=500
        )

        excel_opt_bytes = exportar_excel(st.session_state.asignaciones_opt)
        st.download_button(
            label="📥 Exportar Asignaciones Optimizadas a Excel",
            data=excel_opt_bytes,
            file_name="asignaciones_optimizadas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("🗺️ Mapa de Estudiantes, Docentes e Instituciones (Optimizado)")
        mapa_opt = folium.Map(location=[-25.3, -57.6], zoom_start=7)
        marker_cluster_opt = MarkerCluster().add_to(mapa_opt)

        for _, est in estudiantes.iterrows():
            folium.Marker(
                [est["lat"], est["lng"]],
                popup=f"🎓 Estudiante: {est['nombre']}",
                icon=folium.Icon(color="blue", icon="user"),
            ).add_to(marker_cluster_opt)

        for _, doc in docentes.iterrows():
            folium.Marker(
                [doc["lat"], doc["lng"]],
                popup=f"👨‍🏫 Docente: {doc['nombre']}",
                icon=folium.Icon(color="green", icon="user"),
            ).add_to(marker_cluster_opt)

        for _, cls in clases.iterrows():
            folium.Marker(
                [cls["lat"], cls["lng"]],
                popup=(
                    f"🏫 {cls['nombre_institucion']}<br>"
                    f"Grado: {cls['grado']}<br>"
                    f"Turno: {cls['turno']}"
                ),
                icon=folium.Icon(color="red", icon="education"),
            ).add_to(marker_cluster_opt)

        st_folium(mapa_opt, width=1000, height=500, key="mapa_opt_persistente")
