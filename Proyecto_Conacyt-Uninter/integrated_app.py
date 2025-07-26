# ================================================================
# integrated_app.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formacion: Ing. Eliana Telesca
# Versión: 1.1
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
        DataFrame: Tabla con asignaciones actuales desde 'asignacion_mec'.
    """
    try:
        return pd.read_sql("SELECT * FROM asignacion_mec", engine)
    except Exception as e:
        logger.error(f"Error cargando asignaciones: {e}")
        return pd.DataFrame()

def main():
    """
    Función principal que ejecuta el flujo completo:

    1. Carga de datos desde la base de datos.
    2. Ejecución del algoritmo de optimización.
    3. Impresión de la mejor solución encontrada.

    Raises:
        ValueError: Si los datos necesarios no se cargan correctamente.
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
        pop_size=50,    # TODO: Ajustar según rendimiento deseado.
        n_gen=30,       # TODO: Ajustar número de generaciones según calidad esperada.
        n_procs=4,      # TODO: Ajustar paralelismo según capacidad de hardware.
        db_config={
            "user": "postgres",
            "password": "Admin.123",
            "host": "localhost",
            "port": "5432",
            "database": "Asignacion_MEC"
        }
    )

    # ================================
    # MOSTRAR RESULTADOS
    # ================================
    if result.F is not None and len(result.F) > 0:
        best_idx = result.F[:, 0].argmin()  # Seleccionamos según el primer objetivo
        print("\n📊 ✅ Mejor solución encontrada:")
        print(f"   ➤ Balance Clases: {result.F[best_idx, 0]:.2f}")
        print(f"   ➤ Distancia Estudiantes: {result.F[best_idx, 1]:.2f} km")
        print(f"   ➤ Distancia Docentes: {result.F[best_idx, 2]:.2f} km")
        print(f"   ➤ Penalización Turnos: {result.F[best_idx, 3]:.2f}")
    else:
        print("\n⚠️ No se encontraron soluciones válidas en esta ejecución.")


if __name__ == "__main__":
    main()