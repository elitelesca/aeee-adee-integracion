# ================================================================
# integrated_app.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formacion: Ing. Eliana Telesca
# Versión: 1.2
# Descripción:
#     Script principal para ejecutar la optimización de asignaciones
#     educativas. Carga datos desde la base de datos, define el
#     problema de optimización y guarda los resultados.
# Dependencias:
#     pandas, logging, database, integrated_problem, integrated_optimization
# ================================================================

import sys
from pathlib import Path
import logging
import pandas as pd
from database import engine, cargar_datos_desde_db
from integrated_problem import IntegratedProblem
from integrated_optimization import run_integrated_optimization
from integrated_optimization import select_best_individual

# ================================
# CONFIGURACIÓN LOGGING
# ================================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))


def cargar_asignaciones():
    """
    Carga las asignaciones actuales desde la base de datos.

    Returns:
        pd.DataFrame: Asignaciones actuales o DataFrame vacío si falla.
    """
    try:
        return pd.read_sql("SELECT * FROM asignacion_mec", engine)
    except Exception as e:
        logger.error(f"Error cargando asignaciones: {e}")
        return pd.DataFrame()


def main():
    """
    Función principal para cargar datos, ejecutar la optimización
    y mostrar los resultados en consola.
    """
    # ================================
    # CARGAR DATOS DESDE BD
    # ================================
    estudiantes, docentes, clases, establecimientos = cargar_datos_desde_db()

    if estudiantes.empty or docentes.empty or clases.empty:
        logger.error("❌ No se pudo cargar los datos necesarios.")
        return

    logger.info(
        f"✅ Datos cargados para optimización: "
        f"{len(estudiantes)} estudiantes, "
        f"{len(docentes)} docentes, "
        f"{len(clases)} clases"
    )

    # ================================
    # EJECUTAR OPTIMIZACIÓN
    # ================================
    problem = IntegratedProblem(estudiantes, docentes, clases)

    result = run_integrated_optimization(
        problem,
        pop_size=50,    # Ajustable: tamaño de la población
        n_gen=30,       # Ajustable: número de generaciones
        n_procs=4,      # Ajustable: número de procesos paralelos
        db_config={
            "user": "postgres",
            "password": "Admin.123",
            "host": "localhost",
            "port": "5432",
            "database": "Asignacion_MEC"
        }
    )

    logger.info("✅ Optimización completada")   
    try:
        _, _, best_F = select_best_individual(result)
        if best_F is not None:
            print("📊 Mejor solución encontrada:")
            print(f"   ➤ f0: {best_F[0]:.4f}")
        if len(best_F) > 1:
            print(f"   ➤ f1: {best_F[1]:.4f}")
        if len(best_F) > 2:
            print(f"   ➤ f2: {best_F[2]:.4f}")
        if len(best_F) > 3:
            print(f"   ➤ f3: {best_F[3]:.4f}")
        else:
            print("📊 Mejor solución encontrada (elegida por menor violación de restricciones; F no disponible).")
    except Exception as e:
            logger.error(f"No se pudo resumir la mejor solución: {e}")


if __name__ == "__main__":
    main()
