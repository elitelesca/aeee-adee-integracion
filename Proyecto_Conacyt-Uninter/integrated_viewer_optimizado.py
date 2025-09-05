# ================================================================
# integrated_viewer_optimizado.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.2
#  - Filtros + tabla + mapa en Optimización
#  - Fix turno string/int, width="stretch" en dataframes
# ================================================================

import platform
import numpy as np
import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from io import BytesIO
from sqlalchemy.exc import SQLAlchemyError

from integrated_problem import IntegratedProblem
from integrated_optimization import run_integrated_optimization, select_best_individual
from database import cargar_datos_desde_db, engine

# ================================
# CONFIGURACIÓN INICIAL
# ================================
st.set_page_config(page_title="AEEE-ADEE Integrado", layout="wide")
st.markdown(
    "<h1 style='text-align: center; color: white;'>📊 AEEE-ADEE Integrado</h1>",
    unsafe_allow_html=True,
)

# ================================
# UTILIDADES DE TURNO (robustas)
# ================================
TURNOS_TO_ID = {
    "mañana": 0, "tarde": 1, "noche": 2,
    "manana": 0,               # sin tilde
    0: 0, 1: 1, 2: 2
}
ID_TO_TURNO = {0: "Mañana", 1: "Tarde", 2: "Noche"}

def to_turno_id(x):
    if pd.isna(x):
        return 0
    if isinstance(x, (int, np.integer)):
        return TURNOS_TO_ID.get(int(x), 0)
    s = str(x).strip().lower()
    return TURNOS_TO_ID.get(s, 0)

def turno_label(x):
    return ID_TO_TURNO.get(to_turno_id(x), str(x))

def turno_color(turno_text: str):
    """Color estable por turno (para líneas)."""
    t = to_turno_id(turno_text)
    return {0: "blue", 1: "orange", 2: "purple"}.get(t, "blue")

# ================================
# CARGA INICIAL DE DATOS (CACHÉ)
# ================================
@st.cache_data(ttl=600)
def cargar_datos_iniciales():
    return cargar_datos_desde_db()

estudiantes, docentes, clases, establecimientos = cargar_datos_iniciales()
if estudiantes.empty or docentes.empty or clases.empty:
    st.error("❌ Error al cargar datos. Verifica la conexión con la base de datos.")
    st.stop()

# ================================
# CARGAR ASIGNACIONES (dos formatos)
# ================================
@st.cache_data(ttl=600)
def cargar_asignaciones_simple():
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
            ORDER BY a.id DESC
        """, engine)
    except SQLAlchemyError as e:
        st.error(f"❌ Error cargando asignaciones: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_asignaciones_full():
    """Incluye coordenadas para trazar líneas y filtros por destino."""
    try:
        return pd.read_sql("""
            SELECT 
                a.id,
                a.grado, a.seccion, a.turno, a.distancia,
                -- Estudiante (origen)
                e.id        AS estudiante_id,
                e.nombre    AS estudiante,
                e.departamento AS est_departamento,
                e.localidad AS est_localidad,
                e.barrio    AS est_barrio,
                e.lat       AS est_lat,
                e.lng       AS est_lng,
                -- Docente
                d.id        AS docente_id,
                d.nombre    AS docente,
                d.departamento AS doc_departamento,
                d.localidad AS doc_localidad,
                d.barrio    AS doc_barrio,
                d.lat       AS doc_lat,
                d.lng       AS doc_lng,
                -- Establecimiento / Institución (destino)
                es.id       AS establecimiento_id,
                es.lat      AS estb_lat,
                es.lng      AS estb_lng,
                i.id        AS institucion_id,
                i.nombre    AS institucion,
                i.departamento AS inst_departamento,
                i.localidad AS inst_localidad,
                i.barrio    AS inst_barrio
            FROM asignacion_mec a
            JOIN estudiantes e     ON a.estudiante_id      = e.id
            JOIN docentes d        ON a.docente_id         = d.id
            JOIN establecimientos es ON a.establecimiento_id = es.id
            JOIN instituciones i   ON es.institucion_id    = i.id
            ORDER BY a.id DESC
        """, engine)
    except SQLAlchemyError as e:
        st.error(f"❌ Error cargando asignaciones (full): {e}")
        return pd.DataFrame()

# ================================
# EXPORTAR A EXCEL
# ================================
def exportar_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Asignaciones")
    return output.getvalue()

# ================================
# HELPERS RESÚMENES (KPIs)
# ================================
def build_summaries(problem: IntegratedProblem, best_X: np.ndarray):
    """
    Cromosoma:
      - best_X = [ XA(0..N-1), XD_class(0..C-1) ]
    Devuelve: df_classes, df_teachers
    """
    N = problem.n_estudiantes
    C = problem.n_clases

    XA = best_X[:N].astype(int)          # estudiante -> clase
    XD_class = best_X[N:].astype(int)    # docente por clase

    class_load = np.bincount(XA, minlength=C)
    docente_por_clase = XD_class.copy()
    tiene_docente = docente_por_clase < problem.n_docentes
    docentes_unicos = tiene_docente.astype(int)

    cls_df = problem.clases.reset_index(drop=True).copy()

    if hasattr(problem, "cap_min") and problem.cap_min is not None:
        cap_min = np.asarray(problem.cap_min, dtype=int)
    elif "cap_min" in cls_df.columns:
        cap_min = cls_df["cap_min"].fillna(0).astype(int).values
    else:
        cap_min = np.zeros(C, dtype=int)

    if hasattr(problem, "cap_max") and problem.cap_max is not None:
        cap_max = np.asarray(problem.cap_max, dtype=int)
    elif "capacidad" in cls_df.columns:
        cap_max = cls_df["capacidad"].fillna(10**9).astype(int).values
    else:
        cap_max = np.full(C, 10**9, dtype=int)

    viol_min = np.maximum(0, cap_min - class_load)
    viol_max = np.maximum(0, class_load - cap_max)
    ok = (viol_min == 0) & (viol_max == 0) & tiene_docente

    if "turno" in cls_df.columns and not np.issubdtype(cls_df["turno"].dtype, np.number):
        turnos_id = cls_df["turno"].map(to_turno_id).astype(int).values
    else:
        turnos_id = cls_df.get("turno", pd.Series([0]*C)).fillna(0).astype(int).values

    df_classes = pd.DataFrame({
        "clase_id": cls_df["id"].values if "id" in cls_df.columns else np.arange(C),
        "establecimiento_id": cls_df.get("establecimiento_id", pd.Series([-1]*C)).values,
        "turno": [turno_label(t) for t in turnos_id],
        "cap_min": cap_min,
        "cap_max": cap_max,
        "carga_est": class_load,
        "docente_asignado_idx": docente_por_clase,
        "docentes_unicos": docentes_unicos,
        "tiene_docente": tiene_docente,
        "viol_min": viol_min,
        "viol_max": viol_max,
        "ok": ok
    }).sort_values(by=["ok", "viol_max", "viol_min"], ascending=[True, False, False]).reset_index(drop=True)

    estab_por_clase = cls_df.get("establecimiento_id", pd.Series([0]*C)).values
    rows = []
    for j in range(problem.n_docentes):
        cls_set = {int(c) for c in range(C) if docente_por_clase[c] == j}
        k = len(cls_set)

        turns = sorted({int(turnos_id[c]) for c in cls_set})
        rep_turno = 0
        for t in (0, 1, 2):
            rep = sum(1 for c in cls_set if int(turnos_id[c]) == t)
            if rep > 1:
                rep_turno += (rep - 1)

        estabs = sorted({int(estab_por_clase[c]) for c in cls_set}) if k > 0 else []
        rows.append({
            "docente_id": j,
            "n_clases_asignadas": k,
            "turnos": ", ".join(turno_label(t) for t in turns) if turns else "",
            "rep_turno": rep_turno,
            "mas_de_2_clases": max(0, k - 2),
            "establecimientos_distintos": len(estabs),
        })

    df_teachers = pd.DataFrame(rows).sort_values(
        by=["mas_de_2_clases", "rep_turno", "n_clases_asignadas"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    return df_classes, df_teachers

# ================================
# UI CON TABS
# ================================
tabs = st.tabs(["🔍 Visualización Actual", "🚀 Optimización"])

# -------------------------------
# 1) VISUALIZACIÓN ACTUAL
# -------------------------------
with tabs[0]:
    st.success(f"✅ Datos cargados: {len(estudiantes)} estudiantes, {len(docentes)} docentes, {len(clases)} clases")
    asignaciones = cargar_asignaciones_simple()

    st.subheader("📋 Asignaciones Actuales")
    st.dataframe(asignaciones, width="stretch", height=420)

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

    for _, est in estudiantes.iterrows():
        folium.Marker(
            [est["lat"], est["lng"]],
            popup=f"🎓 Estudiante: {est.get('nombre', est.get('id', ''))}",
            icon=folium.Icon(color="blue", icon="user"),
        ).add_to(marker_cluster)

    for _, doc in docentes.iterrows():
        folium.Marker(
            [doc["lat"], doc["lng"]],
            popup=f"👩‍🏫 Docente: {doc.get('nombre', doc.get('id', ''))}",
            icon=folium.Icon(color="green", icon="user"),
        ).add_to(marker_cluster)

    if {"lat", "lng"}.issubset(clases.columns):
        for _, cls in clases.iterrows():
            folium.Marker(
                [cls["lat"], cls["lng"]],
                popup=(f"🏫 {cls.get('nombre_institucion', '')}<br>"
                       f"Grado: {cls.get('grado', '')}<br>"
                       f"Turno: {cls.get('turno', '')}"),
                icon=folium.Icon(color="red", icon="education"),
            ).add_to(marker_cluster)

    st_folium(mapa, width=1000, height=500, key="mapa_actual")

# -------------------------------
# 2) OPTIMIZACIÓN
# -------------------------------
with tabs[1]:
    st.subheader("🚀 Optimización de Asignaciones")

    # Sliders
    pop_size  = st.slider("Tamaño de población", 10, 200, 50)
    n_gen     = st.slider("Generaciones", 10, 200, 30)
    n_jobs_ui = st.slider("Procesos paralelos (solo Linux/macOS)", 1, 8, 1)

    # Forzar n_jobs=1 en Windows/Streamlit para evitar 'ReleaseSemaphore failed'
    n_jobs = 1 if platform.system() == "Windows" else n_jobs_ui
    if platform.system() == "Windows" and n_jobs_ui != 1:
        st.info("ℹ️ En Windows + Streamlit, se fuerza n_jobs=1 para evitar errores de semáforo del sistema.")

    # Estado para mostrar resultados
    if "asignaciones_opt_full" not in st.session_state:
        st.session_state.asignaciones_opt_full = pd.DataFrame()

    # Botón ejecutar
    if st.button("Ejecutar Optimización", type="primary", use_container_width=True):
        with st.status("⏳ Ejecutando optimización, espera por favor...", expanded=False) as status:
            try:
                problem = IntegratedProblem(estudiantes, docentes, clases)
                result = run_integrated_optimization(
                    problem, pop_size, n_gen, n_jobs,
                    db_config={"user": "postgres","password": "Admin.123","host": "localhost","port": "5432","database": "Asignacion_MEC"}
                )
                best_idx, best_X, best_F = select_best_individual(result)

                status.update(label="✅ Optimización completada", state="complete")
                st.success("Optimización finalizada y resultados guardados en la BD.")

                # KPIs
                st.subheader("📊 Mejor solución")
                if best_F is not None:
                    cols = st.columns(min(len(best_F), 4))
                    for i, v in enumerate(best_F[:4]):
                        cols[i].metric(f"f{i}", f"{v:.4f}")
                else:
                    st.info("Se seleccionó la mejor solución por menor violación de restricciones (F no disponible).")

                # Resúmenes
                pop = getattr(result, "pop", None)
                if pop is None and getattr(result, "history", None):
                    pop = result.history[-1].pop
                if pop is not None and pop.get("G") is not None:
                    G = pop.get("G")
                    cv = np.maximum(0, G).sum(axis=1)
                    st.caption(f"Factibilidad (población final): "
                               f"cv_min={cv.min():.2f} | cv_avg={cv.mean():.2f} | factibles={(cv==0).sum()}/{len(cv)}")

                df_classes, df_teachers = build_summaries(problem, best_X)

                st.subheader("🏫 Resumen por Clase")
                st.dataframe(df_classes, width="stretch", height=320)

                total_viol_min = int(df_classes["viol_min"].sum())
                total_viol_max = int(df_classes["viol_max"].sum())
                sin_docente = int((~df_classes["tiene_docente"] & (df_classes["carga_est"] > 0)).sum())
                c1, c2, c3 = st.columns(3)
                c1.metric("Alumnos faltantes bajo mínimo", f"{total_viol_min}")
                c2.metric("Alumnos excedidos sobre máximo", f"{total_viol_max}")
                c3.metric("Clases con alumnos sin docente", f"{sin_docente}")

                st.subheader("👩‍🏫 Resumen por Docente")
                st.dataframe(df_teachers, width="stretch", height=280)

                # Cargar asignaciones optimizadas
                st.session_state.asignaciones_opt_full = cargar_asignaciones_full()

            except Exception as e:
                status.update(label="❌ Error durante la optimización", state="error")
                st.error(f"❌ Error durante la optimización: {e}")

    # ===== Vista tipo "Visualización Actual" para resultados optimizados =====
    opt_df = st.session_state.asignaciones_opt_full
    if not opt_df.empty:
        st.subheader("Filtros (Resultados Optimizados)")
        col1, col2, col3, col4 = st.columns(4)
        deptos = ["Todos"] + sorted(opt_df["inst_departamento"].dropna().unique().tolist())
        locs   = ["Todos"] + sorted(opt_df["inst_localidad"].dropna().unique().tolist())
        turns  = ["Todos"] + ["Mañana", "Tarde"]  # añade "Noche" si la usas
        insts  = ["Todos"] + sorted(opt_df["institucion"].dropna().unique().tolist())

        f_depto = col1.selectbox("Departamento", deptos, index=0)
        f_local = col2.selectbox("Localidad", locs, index=0)
        f_turno = col3.selectbox("Turno", turns, index=0)
        f_inst  = col4.selectbox("Institución", insts, index=0)

        dff = opt_df.copy()
        if f_depto != "Todos":
            dff = dff[dff["inst_departamento"] == f_depto]
        if f_local != "Todos":
            dff = dff[dff["inst_localidad"] == f_local]
        if f_turno != "Todos":
            dff = dff[dff["turno"] == f_turno]
        if f_inst != "Todos":
            dff = dff[dff["institucion"] == f_inst]

        # Tabla
        cols_show = ["id", "estudiante", "docente", "institucion", "grado", "seccion", "turno", "distancia"]
        st.subheader("📋 Asignaciones Optimizadas (BD)")
        st.dataframe(dff[cols_show], width="stretch", height=420)

        excel_opt_bytes = exportar_excel(dff[cols_show])
        st.download_button(
            label="📥 Exportar Asignaciones Optimizadas a Excel",
            data=excel_opt_bytes,
            file_name="asignaciones_optimizadas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Controles de líneas
        st.subheader("🗺️ Mapa de Estudiantes, Docentes e Instituciones")
        
        # Mapa
        mapa_opt = folium.Map(location=[-25.3, -57.6], zoom_start=7)
        cluster_opt = MarkerCluster().add_to(mapa_opt)

        # Marcadores y líneas (con submuestreo/limitador)
        line_count = 0
        for idx, row in dff.iterrows():
            # Marcadores
            if pd.notna(row["est_lat"]) and pd.notna(row["est_lng"]):
                folium.CircleMarker(
                    [row["est_lat"], row["est_lng"]],
                    radius=3, color="blue", fill=True, fill_opacity=0.8,
                    popup=f"🎓 {row['estudiante']}",
                ).add_to(cluster_opt)

            if pd.notna(row["doc_lat"]) and pd.notna(row["doc_lng"]):
                folium.CircleMarker(
                    [row["doc_lat"], row["doc_lng"]],
                    radius=3, color="green", fill=True, fill_opacity=0.8,
                    popup=f"👩‍🏫 {row['docente']}",
                ).add_to(cluster_opt)

            if pd.notna(row["estb_lat"]) and pd.notna(row["estb_lng"]):
                folium.Marker(
                    [row["estb_lat"], row["estb_lng"]],
                    popup=f"🏫 {row['institucion']}",
                    icon=folium.Icon(color="red", icon="education"),
                ).add_to(cluster_opt)
           
        st_folium(mapa_opt, width=1000, height=520, key="mapa_opt_lineas")
