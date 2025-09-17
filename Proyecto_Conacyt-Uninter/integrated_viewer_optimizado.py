# ================================================================
# integrated_viewer_optimizado.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.3  
#
# Descripción del módulo (UI)
# -------------------
# Aplicación Streamlit con 3 pestañas:
#   1) "Visualización Actual" (ANTES):
#        - Tabla y KPIs de la tabla baseline `asignacion_mec`
#        - Mapa Folium con capas (estudiantes, docentes, instituciones)
#        - Líneas Estudiante→Establecimiento y Docente→Establecimiento
#   2) "Optimización":
#        - Sliders para parámetros (población, generaciones, jobs)
#        - Ejecución del problema (IntegratedProblem) + NSGA2
#        - Persistencia en `asignacion_mec_opt` y resumen de la mejor F
#        - Tabla/Mapa de las asignaciones optimizadas (DESPUÉS)
#   3) "Comparación Antes/Después":
#        - KPIs y Δ% de distancia
#        - Tabla filtrable de reasignados + exportaciones
#        - Gráficos (Plotly) y mapa de trayectorias Antes→Después
#
# Dependencias claves:
#  - Streamlit (UI), pandas/numpy (data), Folium (mapas), Plotly (charts)
#  - SQLAlchemy (lecturas), Pymoo (optimización) vía módulos integrados
#
# Notas de diseño:
#  - Carga de datos cacheada (ttl=600s) para responsividad.
#  - n_jobs se fuerza a 1 en Windows (multiprocessing + Streamlit).
#  - Se igualan estilos de líneas ANTES/DESPUÉS para consistencia visual.
#  - Exportación a Excel de vistas clave (antes, después, comparación).
# ================================================================

from io import BytesIO
import platform
import math
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import folium
from folium import FeatureGroup
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from sqlalchemy.exc import SQLAlchemyError
import plotly.express as px

# Módulos internos del proyecto
from integrated_problem import IntegratedProblem               # Modelo multiobjetivo
from integrated_optimization import (                          # Orquestación NSGA-II
    run_integrated_optimization, select_best_individual
)
from database import cargar_datos_desde_db, engine             # Lectura de BD y engine

# ================================
# CONFIGURACIÓN GENERAL DE PÁGINA
# -------------------------------
# - Título, layout ancho, y cabecera HTML
# ================================
st.set_page_config(page_title="AEEE-ADEE Integrado", layout="wide")
st.markdown("<h1 style='text-align:center'>📊 AEEE-ADEE Integrado</h1>", unsafe_allow_html=True)

# ================================
# HELPERS (turnos, colores, distancias, export, KPIs)
# -------------------------------
# - Normalización de turnos a ids, etiquetas y colores de líneas/capas
# - Haversine en km
# - Exportar a Excel (BytesIO)
# - KPIs simples (n, media, mediana)
# - Validación rápida de coordenadas
# ================================
TURNOS_TO_ID = {
    "mañana": 0, "manana": 0, "matutino": 0,
    "tarde": 1, "vespertino": 1,
    "noche": 2, "nocturno": 2,
    0: 0, 1: 1, 2: 2
}
ID_TO_TURNO = {0: "Mañana", 1: "Tarde", 2: "Noche"}

def to_turno_id(v):
    """Mapea texto/entero de turno a id normalizado {0,1,2}."""
    if pd.isna(v): return 0
    if isinstance(v, (int, np.integer)): return TURNOS_TO_ID.get(int(v), 0)
    return TURNOS_TO_ID.get(str(v).strip().lower(), 0)

def turno_label(v): 
    """Devuelve etiqueta humana del turno."""
    return ID_TO_TURNO.get(to_turno_id(v), str(v))

def turno_color(v): 
    """Color por turno (usado para capas/indicadores)."""
    return {0: "blue", 1: "orange", 2: "purple"}.get(to_turno_id(v), "blue")

def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia haversine en km entre 2 puntos lat/lon."""
    if any(pd.isna([lat1, lon1, lat2, lon2])): return np.nan
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def add_legend(mapa: folium.Map, title: str, items: List[Tuple[str, str]]):
    """Pequeña leyenda HTML fija en la esquina del mapa."""
    rows = "".join(
        f"<div style='margin:4px 0; display:flex; align-items:center;'>"
        f"<span style='display:inline-block;width:12px;height:12px;background:{color};"
        f"margin-right:8px;border-radius:2px;border:1px solid #999'></span>"
        f"<span style='font-size:12px'>{txt}</span></div>"
        for txt, color in items
    )
    html = f"""
    <div style="
        position: fixed; bottom: 24px; right: 24px; z-index: 1000;
        background: rgba(255,255,255,0.9); padding: 10px 12px; border: 1px solid #CCC; border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,.2);
    ">
      <div style="font-weight:600; margin-bottom:6px; font-size:13px">{title}</div>
      {rows}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(html))

def exportar_excel(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    """Serializa un DataFrame a un archivo XLSX en memoria (bytes)."""
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
    return out.getvalue()

def kpis_basicos(df: pd.DataFrame) -> dict:
    """KPIs minimalistas para las asignaciones (n, media y mediana de distancias)."""
    if df is None or df.empty:
        return {"n": 0, "dist_prom": np.nan, "dist_med": np.nan}
    dist = pd.to_numeric(df.get("distancia"), errors="coerce")
    return {
        "n": len(df),
        "dist_prom": float(np.nanmean(dist)) if len(dist) else np.nan,
        "dist_med": float(np.nanmedian(dist)) if len(dist) else np.nan,
    }

def select_cols(df: pd.DataFrame, cols: list) -> list:
    """Devuelve solo las columnas existentes (evita KeyError en vistas parciales)."""
    return [c for c in cols if c in df.columns]

def _valid_coords(*vals):
    """Valida que todos los valores de lat/lon existan y no sean NaN."""
    return all(v is not None and not pd.isna(v) for v in vals)

# ================================
# DATA LOADERS (cacheados)
# -------------------------------
# - Carga de tablas maestras y de "asignaciones" (antes/después),
#   con dos variantes: "full" (coordenadas para mapas) y "simple" (tabla).
# ================================
@st.cache_data(ttl=600)
def cargar_datos_iniciales():
    """Carga estudiantes, docentes, clases y establecimientos desde la BD."""
    return cargar_datos_desde_db()

@st.cache_data(ttl=600)
def cargar_asignaciones_full(tabla="asignacion_mec"):
    """
    Vista FULL (coordenadas y meta) para mapas/analítica.
    - Incluye lat/lon de estudiante, docente y establecimiento.
    """
    try:
        return pd.read_sql(
            f"""
            SELECT 
                a.id, a.grado, a.seccion, a.turno, a.distancia,
                e.id AS estudiante_id, e.nombre AS estudiante, e.lat AS est_lat, e.lng AS est_lng,
                d.id AS docente_id, d.nombre AS docente, d.lat AS doc_lat, d.lng AS doc_lng,
                es.id AS establecimiento_id, es.lat AS estb_lat, es.lng AS estb_lng,
                i.id AS institucion_id, i.nombre AS institucion,
                i.departamento AS inst_departamento, i.localidad AS inst_localidad
            FROM {tabla} a
            JOIN estudiantes e       ON a.estudiante_id      = e.id
            JOIN docentes d          ON a.docente_id         = d.id
            JOIN establecimientos es ON a.establecimiento_id = es.id
            JOIN instituciones i     ON es.institucion_id    = i.id
            ORDER BY a.id DESC
            """,
            engine,
        )
    except SQLAlchemyError as e:
        st.error(f"❌ Error cargando asignaciones ({tabla}): {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_asignaciones_simple(tabla="asignacion_mec"):
    """Vista SIMPLE (tabla legible para usuarios, sin coordenadas)."""
    try:
        return pd.read_sql(
            f"""
            SELECT 
                a.id, e.nombre AS estudiante, d.nombre AS docente, i.nombre AS institucion,
                a.grado, a.seccion, a.turno, a.distancia
            FROM {tabla} a
            JOIN estudiantes e       ON a.estudiante_id      = e.id
            JOIN docentes d          ON a.docente_id         = d.id
            JOIN establecimientos es ON a.establecimiento_id = es.id
            JOIN instituciones i     ON es.institucion_id    = i.id
            ORDER BY a.id DESC
            """,
            engine,
        )
    except SQLAlchemyError as e:
        st.error(f"❌ Error cargando asignaciones ({tabla}): {e}")
        return pd.DataFrame()

# Snapshots en session_state para ANTES/DESPUÉS
if "asignaciones_before" not in st.session_state:
    st.session_state.asignaciones_before = cargar_asignaciones_full("asignacion_mec")
if "asignaciones_after" not in st.session_state:
    st.session_state.asignaciones_after = pd.DataFrame()

# ================================
# TABS
# ================================
tab_actual, tab_opt, tab_comp = st.tabs(
    ["🔍 Visualización Actual", "🚀 Optimización", "📊 Comparación Antes/Después"]
)

# ================================================================
# TAB 1: VISUALIZACIÓN ACTUAL (ANTES)
# - Diagnóstico y baseline desde `asignacion_mec`
# - KPIs, tabla simple y mapa con líneas de unión
# ================================================================
with tab_actual:
    estudiantes, docentes, clases, establecimientos = cargar_datos_iniciales()
    if estudiantes.empty or docentes.empty or clases.empty:
        st.error("❌ Error al cargar datos base (estudiantes/docentes/clases).")
        st.stop()

    st.success(f"✅ Datos cargados: {len(estudiantes)} estudiantes, {len(docentes)} docentes, {len(clases)} clases")

    # Tabla "simple" y KPIs baseline
    asig_simple = cargar_asignaciones_simple("asignacion_mec")
    st.subheader("📋 Asignaciones Actuales (ANTES)")
    st.dataframe(asig_simple, height=360, width="stretch")

    st.markdown("### 🔎 KPIs del estado actual (antes)")
    asig_full = st.session_state.asignaciones_before
    k = kpis_basicos(asig_full)
    c1, c2, c3 = st.columns(3)
    c1.metric("Asignaciones (registros)", f"{k['n']:,}")
    c2.metric("Distancia promedio", f"{k['dist_prom']:.2f} km" if not np.isnan(k['dist_prom']) else "n/d")
    c3.metric("Distancia mediana", f"{k['dist_med']:.2f} km" if not np.isnan(k['dist_med']) else "n/d")

    # Export baseline
    st.download_button(
        "📥 Exportar Asignaciones (antes)",
        data=exportar_excel(asig_simple, "Asignaciones_antes"),
        file_name="asignaciones_antes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_export_antes",
    )

    # ----- MAPA “ANTES”: puntos y líneas de unión (estilo igual al de Optimización)
    st.subheader("🗺️ Mapa de Estudiantes, Docentes e Instituciones (antes)")
    mapa = folium.Map(location=[-25.3, -57.6], zoom_start=7)

    capa_est = FeatureGroup(name="🎓 Estudiantes (Azul)", show=True)
    capa_doc = FeatureGroup(name="👩‍🏫 Docentes (Verde)", show=True)
    capa_inst = FeatureGroup(name="🏫 Instituciones (Rojo)", show=True)

    # Capas de líneas (estudiante y docente)
    capa_linea_est = FeatureGroup(name="Líneas Estudiante → Establecimiento", show=True)
    capa_linea_doc = FeatureGroup(name="Líneas Docente → Establecimiento", show=True)

    # Clusters compactos (evita capa folium por defecto con IDs raros)
    cluster_est = MarkerCluster(name="Cluster Estudiantes").add_to(capa_est)
    cluster_doc = MarkerCluster(name="Cluster Docentes").add_to(capa_doc)
    cluster_ins = MarkerCluster(name="Cluster Instituciones").add_to(capa_inst)

    # Puntos: estudiantes
    for _, r in estudiantes.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lng")):
            folium.CircleMarker(
                [r["lat"], r["lng"]], radius=3, color="blue", fill=True, fill_opacity=0.9,
                popup=f"🎓 {r.get('nombre', r.get('id',''))}"
            ).add_to(cluster_est)

    # Puntos: docentes
    for _, r in docentes.iterrows():
        if pd.notna(r.get("lat")) and pd.notna(r.get("lng")):
            folium.CircleMarker(
                [r["lat"], r["lng"]], radius=3, color="green", fill=True, fill_opacity=0.9,
                popup=f"👩‍🏫 {r.get('nombre', r.get('id',''))}"
            ).add_to(cluster_doc)

    # Puntos: instituciones (desde clases con lat/lon de establecimientos)
    if {"lat", "lng"}.issubset(clases.columns):
        for _, r in clases.iterrows():
            if pd.notna(r["lat"]) and pd.notna(r["lng"]):
                folium.Marker(
                    [r["lat"], r["lng"]],
                    popup=f"🏫 {r.get('nombre_institucion','')}<br>Grado: {r.get('grado','')}<br>Turno: {turno_label(r.get('turno',''))}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(cluster_ins)

    # Líneas: Estudiante → Establecimiento (azul continua)
    for _, row in asig_full.iterrows():
        if _valid_coords(row.get("est_lat"), row.get("est_lng"), row.get("estb_lat"), row.get("estb_lng")):
            folium.PolyLine(
                [(row["est_lat"], row["est_lng"]), (row["estb_lat"], row["estb_lng"])],
                color="#1f77b4", weight=2, opacity=0.85,
                tooltip="Estudiante → Establecimiento (antes)"
            ).add_to(capa_linea_est)

        # Líneas: Docente → Establecimiento (verde punteada)
        if _valid_coords(row.get("doc_lat"), row.get("doc_lng"), row.get("estb_lat"), row.get("estb_lng")):
            folium.PolyLine(
                [(row["doc_lat"], row["doc_lng"]), (row["estb_lat"], row["estb_lng"])],
                color="#2ca02c", weight=2, opacity=0.85, dash_array="6,4",
                tooltip="Docente → Establecimiento (antes)"
            ).add_to(capa_linea_doc)

    # Ensamblar mapa
    for capa in (capa_est, capa_doc, capa_inst, capa_linea_est, capa_linea_doc):
        capa.add_to(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)
    st_folium(mapa, width=1000, height=520, key="mapa_antes")


# ================================================================
# TAB 2: OPTIMIZACIÓN (DESPUÉS)
# - Parámetros de evolución, ejecución y muestra de resultados
# - Lectura de `asignacion_mec_opt` tras persistir
# ================================================================
with tab_opt:
    st.subheader("🚀 Optimización de Asignaciones")

    # Parámetros de corrida (UI)
    pop_size = st.slider("Tamaño de población", 10, 200, 50, key="opt_pop")
    n_gen = st.slider("Generaciones", 10, 200, 30, key="opt_gen")
    jobs_ui = st.slider("Procesos paralelos (solo Linux/macOS)", 1, 8, 1, key="opt_jobs")
    n_jobs = 1 if platform.system() == "Windows" else jobs_ui
    if platform.system() == "Windows" and jobs_ui != 1:
        st.info("ℹ️ En Windows + Streamlit, se fuerza n_jobs=1.")

    # Botón de ejecución
    if st.button("Ejecutar Optimización", type="primary", key="btn_run_opt"):
        with st.status("⏳ Ejecutando optimización...", expanded=False) as status:
            try:
                est, doc, cls, _ = cargar_datos_iniciales()
                problem = IntegratedProblem(est, doc, cls)
                result = run_integrated_optimization(
                    problem, pop_size, n_gen, n_jobs,
                    db_config={
                        "user": "postgres", "password": "Admin.123",
                        "host": "localhost", "port": "5432", "database": "Asignacion_MEC",
                    },
                )
                best_idx, best_X, best_F = select_best_individual(result)
                status.update(label="✅ Optimización completada", state="complete")
                st.success("Optimización finalizada y resultados guardados en la BD.")

                # Métricas de la mejor solución
                st.subheader("📊 Mejor solución (métricas)")
                if best_F is not None:
                    cols = st.columns(min(len(best_F), 4))
                    for i, v in enumerate(best_F[:4]): 
                        cols[i].metric(f"f{i}", f"{v:.4f}")
                else:
                    st.info("Se seleccionó por menor violación de restricciones.")

                # Refrescar caches y snapshot "DESPUÉS"
                st.cache_data.clear()
                st.session_state.asignaciones_after = cargar_asignaciones_full("asignacion_mec_opt")

            except Exception as e:
                status.update(label="❌ Error durante la optimización", state="error")
                st.error(f"❌ Error durante la optimización: {e}")

    # Vista de resultados post-optimización
    opt_df = st.session_state.asignaciones_after
    if not opt_df.empty:
        st.subheader("📋 Asignaciones Optimizadas (DESPUÉS)")
        cols_opt = select_cols(opt_df, ["id","estudiante","docente","institucion","grado","seccion","turno","distancia"])
        st.dataframe(opt_df[cols_opt], height=360, width="stretch")

        st.download_button(
            "📥 Exportar Asignaciones Optimizadas",
            data=exportar_excel(opt_df[cols_opt], "Asignaciones_despues"),
            file_name="asignaciones_optimizadas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_export_despues",
        )

        # Mapa “DESPUÉS” (mismo estilo que ANTES, para comparar visualmente)
        st.subheader("🗺️ Mapa de Estudiantes, Docentes e Instituciones (después)")
        mapa_opt = folium.Map(location=[-25.3, -57.6], zoom_start=7)

        # Capas de puntos
        capa_est_opt  = folium.FeatureGroup(name="🎓 Estudiantes (Azul)", show=True)
        capa_doc_opt  = folium.FeatureGroup(name="👩‍🏫 Docentes (Verde)", show=True)
        capa_inst_opt = folium.FeatureGroup(name="🏫 Instituciones (Rojo)", show=True)

        cluster_est_opt = folium.plugins.MarkerCluster(name="Cluster Estudiantes").add_to(capa_est_opt)
        cluster_doc_opt = folium.plugins.MarkerCluster(name="Cluster Docentes").add_to(capa_doc_opt)
        cluster_ins_opt = folium.plugins.MarkerCluster(name="Cluster Instituciones").add_to(capa_inst_opt)

        # Capas de líneas
        capa_linea_est_opt = folium.FeatureGroup(name="Líneas Estudiante → Establecimiento", show=True)
        capa_linea_doc_opt = folium.FeatureGroup(name="Líneas Docente → Establecimiento", show=True)

        # Puntos y líneas desde opt_df
        for _, fila in opt_df.iterrows():
            # Estudiantes
            if _valid_coords(fila.get("est_lat"), fila.get("est_lng")):
                folium.CircleMarker(
                    [fila["est_lat"], fila["est_lng"]], radius=3, color="blue",
                    fill=True, fill_opacity=0.8, popup=f"🎓 {fila.get('estudiante','')}"
                ).add_to(cluster_est_opt)

            # Docentes
            if _valid_coords(fila.get("doc_lat"), fila.get("doc_lng")):
                folium.CircleMarker(
                    [fila["doc_lat"], fila["doc_lng"]], radius=3, color="green",
                    fill=True, fill_opacity=0.8, popup=f"👩‍🏫 {fila.get('docente','')}"
                ).add_to(cluster_doc_opt)

            # Instituciones
            if _valid_coords(fila.get("estb_lat"), fila.get("estb_lng")):
                folium.Marker(
                    [fila["estb_lat"], fila["estb_lng"]],
                    popup=f"🏫 {fila.get('institucion','')}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(cluster_ins_opt)

            # Líneas Est → Establecimiento (azul continua)
            if _valid_coords(fila.get("est_lat"), fila.get("est_lng"), fila.get("estb_lat"), fila.get("estb_lng")):
                folium.PolyLine(
                    [(fila["est_lat"], fila["est_lng"]), (fila["estb_lat"], fila["estb_lng"])],
                    color="#1f77b4", weight=2, opacity=0.85,
                    tooltip="Estudiante → Establecimiento (después)"
                ).add_to(capa_linea_est_opt)

            # Líneas Doc → Establecimiento (verde punteada)
            if _valid_coords(fila.get("doc_lat"), fila.get("doc_lng"), fila.get("estb_lat"), fila.get("estb_lng")):
                folium.PolyLine(
                    [(fila["doc_lat"], fila["doc_lng"]), (fila["estb_lat"], fila["estb_lng"])],
                    color="#2ca02c", weight=2, opacity=0.85, dash_array="6,4",
                    tooltip="Docente → Establecimiento (después)"
                ).add_to(capa_linea_doc_opt)

        # Ensamblar mapa
        for capa in (capa_est_opt, capa_doc_opt, capa_inst_opt, capa_linea_est_opt, capa_linea_doc_opt):
            capa.add_to(mapa_opt)
        folium.LayerControl(collapsed=False).add_to(mapa_opt)
        st_folium(mapa_opt, width=1000, height=520, key="mapa_despues")

# ================================================================
# TAB 3: COMPARACIÓN ANTES/DESPUÉS
# - KPIs lado a lado, Δ% (si procede)
# - Tabla de reasignados, exportaciones y visualizaciones
# - Mapa de trayectorias Antes→Después con popup detallado
# ================================================================
with tab_comp:
    st.subheader("📊 Comparación Antes/Después")
    df_before = st.session_state.get("asignaciones_before", pd.DataFrame())
    df_after = st.session_state.get("asignaciones_after", pd.DataFrame())

    if df_after.empty:
        st.info("Ejecuta una optimización (pestaña anterior) para habilitar la comparación.")
        st.stop()

    # KPIs y Δ%
    k_antes = kpis_basicos(df_before)
    k_desp  = kpis_basicos(df_after)
    c1, c2, c3 = st.columns(3)
    c1.metric("Distancia prom. (antes)", f"{k_antes['dist_prom']:.2f} km" if not np.isnan(k_antes['dist_prom']) else "n/d")
    c2.metric("Distancia prom. (después)", f"{k_desp['dist_prom']:.2f} km" if not np.isnan(k_desp['dist_prom']) else "n/d")
    if not np.isnan(k_antes['dist_prom']) and not np.isnan(k_desp['dist_prom']) and k_antes['dist_prom'] != 0:
        delta_pct = (k_desp['dist_prom'] - k_antes['dist_prom']) / k_antes['dist_prom'] * 100
        c3.metric("Δ %", f"{delta_pct:+.1f}%")
    else:
        c3.metric("Δ %", "n/d")

    # Unificar columnas clave para merge y deltas
    before_cols = select_cols(df_before, [
        "estudiante_id","estudiante",
        "docente_id","docente",
        "institucion_id","institucion",
        "turno","distancia",
        "est_lat","est_lng","doc_lat","doc_lng","estb_lat","estb_lng",
        "inst_departamento","inst_localidad"
    ])
    after_cols = select_cols(df_after, [
        "estudiante_id","estudiante",
        "docente_id","docente",
        "institucion_id","institucion",
        "turno","distancia",
        "est_lat","est_lng","doc_lat","doc_lng","estb_lat","estb_lng",
        "inst_departamento","inst_localidad"
    ])

    A = df_before[before_cols].rename(columns={
        "docente_id":"docente_id_antes","docente":"docente_antes",
        "institucion_id":"institucion_id_antes","institucion":"institucion_antes",
        "turno":"turno_antes","distancia":"dist_antes",
        "est_lat":"est_lat_antes","est_lng":"est_lng_antes",
        "doc_lat":"doc_lat_antes","doc_lng":"doc_lng_antes",
        "estb_lat":"estb_lat_antes","estb_lng":"estb_lng_antes",
        "inst_departamento":"inst_departamento_antes","inst_localidad":"inst_localidad_antes"
    })
    B = df_after[after_cols].rename(columns={
        "docente_id":"docente_id_despues","docente":"docente_despues",
        "institucion_id":"institucion_id_despues","institucion":"institucion_despues",
        "turno":"turno_despues","distancia":"dist_despues",
        "est_lat":"est_lat_despues","est_lng":"est_lng_despues",
        "doc_lat":"doc_lat_despues","doc_lng":"doc_lng_despues",
        "estb_lat":"estb_lat_despues","estb_lng":"estb_lng_despues",
        "inst_departamento":"inst_departamento_despues","inst_localidad":"inst_localidad_despues"
    })

    # Merge por estudiante + deltas y banderas
    cmp = pd.merge(B, A, on=["estudiante_id","estudiante"], how="left")
    cmp["dist_antes"]   = pd.to_numeric(cmp.get("dist_antes"), errors="coerce")
    cmp["dist_despues"] = pd.to_numeric(cmp.get("dist_despues"), errors="coerce")
    cmp["delta_km"]     = (cmp["dist_despues"] - cmp["dist_antes"]).round(2)

    cmp["cambio_institucion"] = cmp.get("institucion_id_antes")  != cmp.get("institucion_id_despues")
    cmp["cambio_docente"]     = cmp.get("docente_id_antes")      != cmp.get("docente_id_despues")
    cmp["cambio_turno"]       = cmp.get("turno_antes")           != cmp.get("turno_despues")
    cmp["reasignado"] = cmp[["cambio_institucion","cambio_docente","cambio_turno"]].fillna(False).any(axis=1)

    # Vista tabular principal
    st.write("### Detalle de estudiantes")
    only_reas = st.checkbox("Mostrar solo reasignados", value=False, key="cmp_only_reas")
    view_df = cmp.copy()
    if only_reas:
        view_df = view_df[view_df["reasignado"] == True]

    cols_show_pref = [
        "estudiante_id","estudiante",
        "inst_departamento_despues","inst_localidad_despues",
        "turno_antes","turno_despues",
        "dist_antes","dist_despues","delta_km",
        "institucion_antes","institucion_despues",
        "docente_antes","docente_despues",
        "reasignado"
    ]
    cols_show = select_cols(view_df, cols_show_pref)
    st.dataframe(view_df[cols_show].sort_values("delta_km"), height=360, width="stretch")

    # Exportaciones
    cdl1, cdl2 = st.columns(2)
    def _dl(df, name):
        return st.download_button(
            name, data=exportar_excel(df, "Comparacion"),
            file_name="comparacion_antes_despues.xlsx" if "Comparación" in name else "reasignados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with cdl1: _dl(cmp[cols_show], "📥 Exportar Comparación (antes vs después)")
    with cdl2: _dl(cmp.loc[cmp["reasignado"]==True, cols_show], "📥 Exportar SOLO Reasignados")

    # Gráfico de distribución de distancias
    d1 = pd.DataFrame({"Distancia (km)": pd.to_numeric(df_before.get("distancia"), errors="coerce"), "Estado": "Antes"})
    d2 = pd.DataFrame({"Distancia (km)": pd.to_numeric(df_after.get("distancia"), errors="coerce"), "Estado": "Después"})
    dist_df = pd.concat([d1, d2], ignore_index=True).dropna()
    if not dist_df.empty:
        fig1 = px.box(dist_df, x="Estado", y="Distancia (km)", points=False, title="Distribución de distancias (km)")
        st.plotly_chart(fig1, use_container_width=True)

    # Barras: Δ promedio por departamento y turno
    if {"inst_departamento_despues","turno_despues","delta_km"}.issubset(cmp.columns):
        grp = cmp.copy()
        grp["turno_norm"] = grp["turno_despues"].map(turno_label)
        g = grp.groupby(["inst_departamento_despues", "turno_norm"], dropna=True)["delta_km"].mean().reset_index()
        if not g.empty:
            fig2 = px.bar(g, x="inst_departamento_despues", y="delta_km", color="turno_norm",
                          barmode="group", title="Δ promedio de distancia por departamento y turno")
            fig2.update_layout(yaxis_title="Δ km (después - antes)", xaxis_title="Departamento (después)")
            st.plotly_chart(fig2, use_container_width=True)

    # Mapa de trayectorias Antes → Después
    st.write("### 🗺️ Mapa de reasignados (Antes → Después)")
    show_est_lines = True     # Mostrar líneas de estudiante por defecto
    show_doc_lines = False    # Opcional: líneas de docente
    sample_step = 1           # Muestreo (1 = todos)
    max_lines   = 1000        # Tope de líneas para no saturar el navegador

    reas = cmp[cmp["reasignado"] == True].copy()
    if reas.empty:
        st.info("No hubo reasignaciones en esta corrida.")
    else:
        mcmp = folium.Map(location=[-25.3, -57.6], zoom_start=7)
        capa_lineas = FeatureGroup(name="Reasignaciones", show=True)

        def _color_por_delta(delta):
            """Verde si mejora (<0), rojo si empeora (>0), gris si igual/NaN."""
            if pd.isna(delta): return "#888888"
            return "#2ca02c" if delta < 0 else ("#d62728" if delta > 0 else "#888888")

        count = 0
        for _, r in reas.iloc[::sample_step].iterrows():
            if count >= max_lines: break

            # Puntos de referencia: estudiante + establecimientos antes/después
            est_pt = (r.get("est_lat_despues"), r.get("est_lng_despues")) if pd.notna(r.get("est_lat_despues")) else (r.get("est_lat_antes"), r.get("est_lng_antes"))
            estb_before = (r.get("estb_lat_antes"), r.get("estb_lng_antes"))
            estb_after  = (r.get("estb_lat_despues"), r.get("estb_lng_despues"))
            doc_before  = (r.get("doc_lat_antes"), r.get("doc_lng_antes"))
            doc_after   = (r.get("doc_lat_despues"), r.get("doc_lng_despues"))

            # Trazo "Antes" (gris punteado) desde EST → Establecimiento ANTES
            if show_est_lines and _valid_coords(*est_pt) and _valid_coords(*estb_before):
                folium.PolyLine([est_pt, estb_before], color="#888888", weight=2, opacity=0.7,
                                dash_array="5,5", tooltip="Antes").add_to(capa_lineas)
                count += 1
            # Trazo "Después" (color por Δ) desde EST → Establecimiento DESPUÉS
            if show_est_lines and _valid_coords(*est_pt) and _valid_coords(*estb_after) and count < max_lines:
                folium.PolyLine([est_pt, estb_after], color=_color_por_delta(r.get("delta_km")), weight=3, opacity=0.9,
                                tooltip="Después",
                                popup=folium.Popup(
                                    f"<b>🎓 {r.get('estudiante','')}</b>"
                                    f"<br>🏫 {r.get('institucion_antes','')} ➜ <b>{r.get('institucion_despues','')}</b>"
                                    f"<br>👩‍🏫 {r.get('docente_antes','')} ➜ <b>{r.get('docente_despues','')}</b>"
                                    f"<br>Turno: {turno_label(r.get('turno_antes'))} ➜ <b>{turno_label(r.get('turno_despues'))}</b>"
                                    f"<br>Dist.: {r.get('dist_antes')} km ➜ <b>{r.get('dist_despues')} km</b>"
                                    f"<br>Δ km: <b>{r.get('delta_km')}</b>", max_width=360
                                )).add_to(capa_lineas)
                count += 1

            # (Opcional) Líneas de docente
            if show_doc_lines and _valid_coords(*doc_before, *estb_before) and count < max_lines:
                folium.PolyLine([doc_before, estb_before], color="#888888", weight=2, opacity=0.6,
                                dash_array="6,6", tooltip="Docente (antes)").add_to(capa_lineas)
                count += 1
            if show_doc_lines and _valid_coords(*doc_after, *estb_after) and count < max_lines:
                folium.PolyLine([doc_after, estb_after], color="#2ca02c", weight=2, opacity=0.8,
                                tooltip="Docente (después)").add_to(capa_lineas)
                count += 1

        capa_lineas.add_to(mcmp)
        folium.LayerControl(collapsed=False).add_to(mcmp)
        st_folium(mcmp, width=1000, height=520, key="mapa_cmp_reasignados")
