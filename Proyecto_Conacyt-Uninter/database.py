## ================================================================
# database.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formacion: Ing. Eliana Telesca
# Versión: 1.1
# Descripción:
#     Módulo para la conexión a la base de datos PostgreSQL y
#     la carga de datos (estudiantes, docentes, clases, establecimientos).
# Dependencias:
#     sqlalchemy, pandas, dotenv
# ================================================================

import os
from sqlalchemy import create_engine
import pandas as pd
import logging
from dotenv import load_dotenv

# ================================
# CONFIGURACIÓN LOGGING
# ================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# VARIABLES DE ENTORNO
# ================================
load_dotenv()

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'Admin.123'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'Asignacion_MEC')
}

DB_URI = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)
engine = create_engine(DB_URI)

# ================================
# FUNCIÓN PARA CARGAR DATOS
# ================================
def cargar_datos_desde_db():
    """
    Carga estudiantes, docentes, clases y establecimientos con unión de instituciones.

    Returns:
        tuple: (estudiantes, docentes, clases, establecimientos) como DataFrames.
               Si ocurre un error, devuelve DataFrames vacíos.
    """
    try:
        logger.info("Cargando datos desde la base de datos...")

        estudiantes = pd.read_sql("""
            SELECT 
                id AS estudiante_id,
                nombre, grado, lat, lng,
                departamento, localidad, barrio
            FROM estudiantes
        """, engine)

        docentes = pd.read_sql("""
            SELECT 
                id AS docente_id,
                nombre, grado, lat, lng,
                departamento, localidad, barrio
            FROM docentes
        """, engine)

        clases = pd.read_sql("""
        SELECT 
            c.id AS clase_id,
            c.grado, c.turno, c.capacidad,
            c.establecimiento_id,
            e.lat, e.lng,
            i.departamento, i.localidad, i.barrio,
            i.nombre AS nombre_institucion,
            e.institucion_id
            FROM clases c
            JOIN establecimientos e ON c.establecimiento_id = e.id
            JOIN instituciones i ON e.institucion_id = i.id
        """, engine)

        establecimientos = pd.read_sql("""
            SELECT id, institucion_id, lat, lng
            FROM establecimientos
        """, engine)

        # ✅ Resetear índices para evitar problemas en iteraciones posteriores
        estudiantes = estudiantes.reset_index(drop=True)
        docentes = docentes.reset_index(drop=True)
        clases = clases.reset_index(drop=True)
        establecimientos = establecimientos.reset_index(drop=True)

        logger.info(
            f"Datos cargados correctamente: "
            f"{len(estudiantes)} estudiantes, "
            f"{len(docentes)} docentes, "
            f"{len(clases)} clases, "
            f"{len(establecimientos)} establecimientos"
        )

        return estudiantes, docentes, clases, establecimientos

    except Exception as e:
        logger.error(f"Error al cargar datos: {e}", exc_info=True)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def test_conexion():
    """
    Verifica la conexión a la base de datos.

    Returns:
        bool: True si la conexión es exitosa, False en caso contrario.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Conexión a la base de datos exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False
