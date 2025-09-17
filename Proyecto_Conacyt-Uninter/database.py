# ================================================================
# database.py  
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.3 
#
# Descripción del módulo
# --------------------
# Proveer:
#   1) Un "engine" de SQLAlchemy conectado a PostgreSQL, construido
#      desde variables de entorno (.env o entorno del sistema).
#   2) Funciones utilitarias para:
#        - Cargar los DataFrames base (estudiantes, docentes, clases,
#          establecimientos) con los JOIN necesarios.
#        - Probar la conectividad a la base (health check).
#
# Notas de diseño
# ---------------
# - El módulo se carga una única vez por proceso; por eso define
#   `engine` a nivel de módulo (patrón "singleton" de facto).
# - El fallo al cargar datos no debe interrumpir el proceso: devolvemos
#   DataFrames vacíos para que la UI/CLI maneje el error de forma amigable.
# - Las credenciales se obtienen con `dotenv`; en producción se recomienda
#   inyectarlas por variables de entorno del sistema (no commitear .env).
#
# Dependencias clave:
#   - SQLAlchemy (engine/lectura)
#   - pandas (tabular)
#   - python-dotenv (config)
#   - logging (observabilidad)
# ================================================================

import os
from sqlalchemy import create_engine
import pandas as pd
import logging
from dotenv import load_dotenv

# ================================
# CONFIGURACIÓN DE LOGGING
# ----------------------------
# - Nivel INFO por defecto para ver actividad normal (conexión/carga).
# - Usa el logger del módulo para no mezclar con otros módulos.
# ================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# CARGA DE VARIABLES DE ENTORNO
# -----------------------------
# - Prioriza variables del sistema; si existe un archivo .env
#   en el directorio de ejecución, también las carga.
# - Claves esperadas: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME.
# - Se proveen defaults de desarrollo (no usar en producción).
# ================================
load_dotenv()

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'Admin.123'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'Asignacion_MEC')
}

# Construimos el URI para SQLAlchemy con driver psycopg2.
# Ejemplo: postgresql+psycopg2://user:pass@host:port/dbname
DB_URI = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# ================================================================
# ENGINE GLOBAL
# --------------
# - Objeto reutilizable para todas las lecturas/consultas desde pandas.
# - Alternativas avanzadas (opcionales):
#     * pool_pre_ping=True para desconexiones ociosas
#     * pool_size / max_overflow para tunning de concurrencia
#     * connect_args={'options': '-c statement_timeout=30000'} para timeouts
# ================================================================
engine = create_engine(DB_URI)
# Sugerencias opcionales (comentar/ajustar según necesidad):
# engine = create_engine(DB_URI, pool_pre_ping=True)
# engine = create_engine(DB_URI, pool_pre_ping=True, pool_size=5, max_overflow=10)

def cargar_datos_desde_db():
    """
    Carga estudiantes, docentes, clases (con JOIN a instituciones) y establecimientos.

    ¿Qué entrega?
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            (estudiantes, docentes, clases, establecimientos)

    Estructuras mínimas esperadas:
        - estudiantes:  id->estudiante_id, nombre, grado, lat, lng, departamento, localidad, barrio
        - docentes:     id->docente_id,   nombre, grado, lat, lng, departamento, localidad, barrio
        - clases:       clase_id, grado, turno, capacidad, establecimiento_id,
                        lat (del establecimiento), lng (del establecimiento),
                        nombre_institucion, institucion_id
        - establecimientos: id, institucion_id, lat, lng

    Comportamiento ante error:
        - Loguea el error y retorna 4 DataFrames vacíos (evita romper el flujo
          en la UI). La capa superior decide cómo notificar al usuario.

    Importante:
        - Se hace reset_index(drop=True) para evitar efectos colaterales al
          iterar por posición en algoritmos posteriores.
    """
    try:
        logger.info("Cargando datos desde la base de datos...")

        # -----------------------------
        # Tabla: ESTUDIANTES
        # -----------------------------
        estudiantes = pd.read_sql(
            """
            SELECT 
                id AS estudiante_id,
                nombre, grado, lat, lng,
                departamento, localidad, barrio
            FROM estudiantes
            """,
            engine
        )

        # -----------------------------
        # Tabla: DOCENTES
        # -----------------------------
        docentes = pd.read_sql(
            """
            SELECT 
                id AS docente_id,
                nombre, grado, lat, lng,
                departamento, localidad, barrio
            FROM docentes
            """,
            engine
        )

        # ---------------------------------------------------------
        # Tabla: CLASES + JOIN con ESTABLECIMIENTOS e INSTITUCIONES
        # ---------------------------------------------------------
        # - Aquí obtenemos lat/lng del establecimiento para cada clase,
        #   y el nombre/ID de la institución a la que pertenece.
        clases = pd.read_sql(
            """
            SELECT 
                c.id AS clase_id,
                c.grado, c.turno, c.capacidad,
                c.establecimiento_id,
                e.lat, e.lng,
                i.nombre AS nombre_institucion,
                e.institucion_id
            FROM clases c
            JOIN establecimientos e ON c.establecimiento_id = e.id
            JOIN instituciones i   ON e.institucion_id    = i.id
            """,
            engine
        )

        # -----------------------------
        # Tabla: ESTABLECIMIENTOS
        # -----------------------------
        establecimientos = pd.read_sql(
            """
            SELECT id, institucion_id, lat, lng
            FROM establecimientos
            """,
            engine
        )

        # Normalización de índices (evita problemas con iloc en optimización)
        estudiantes = estudiantes.reset_index(drop=True)
        docentes = docentes.reset_index(drop=True)
        clases = clases.reset_index(drop=True)
        establecimientos = establecimientos.reset_index(drop=True)

        logger.info(
            "Datos cargados correctamente: "
            f"{len(estudiantes)} estudiantes, "
            f"{len(docentes)} docentes, "
            f"{len(clases)} clases, "
            f"{len(establecimientos)} establecimientos"
        )

        return estudiantes, docentes, clases, establecimientos

    except Exception as e:
        # exc_info=True agrega el stack trace al log (útil para depuración)
        logger.error(f"Error al cargar datos: {e}", exc_info=True)
        # Fallback seguro: dataframes vacíos para que la UI/CLI lo maneje
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def test_conexion():
    """
    Health check de conectividad a la base de datos.

    ¿Qué hace?
        - Abre una conexión y ejecuta un SELECT 1 (barato y suficiente).
        - Si la instrucción se ejecuta sin excepciones, retorna True.
        - Cualquier error loguea y retorna False.

    Uso típico:
        >>> from database import test_conexion
        >>> test_conexion()
        True  # si todo ok

    Notas:
        - Usa el `engine` global (pool de conexiones). El context manager
          garantiza cerrar la conexión al salir del bloque.
    """
    try:
        # En SQLAlchemy 2.x, execute acepta texto simple para SELECT 1.
        # Si usas Core: from sqlalchemy import text; conn.execute(text("SELECT 1"))
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Conexión a la base de datos exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")
        return False

