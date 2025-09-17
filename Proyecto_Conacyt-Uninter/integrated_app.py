# ================================================================
# integrated_app.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.3 
#
# Descripción del módulo
# --------------
# Ejecutar la optimización en modo "batch/CLI":
#   1) Cargar datos desde la base (estudiantes, docentes, clases).
#   2) Construir el problema multiobjetivo (IntegratedProblem).
#   3) Correr NSGA-II (run_integrated_optimization) y, opcionalmente,
#      guardar resultados en la tabla de salida (asignacion_mec_opt).
#   4) Imprimir por consola la mejor solución encontrada (vector F).
# ================================================================

import sys
from pathlib import Path
import logging
import pandas as pd

# Importa la conexión/loader de BD y módulos de optimización
from database import engine, cargar_datos_desde_db
from integrated_problem import IntegratedProblem
from integrated_optimization import run_integrated_optimization, select_best_individual

# -------------------------------
# LOGGING del módulo
# -------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -------------------------------
# PATH raíz del proyecto
# - En caso de ejecución desde ubicaciones distintas, se asegura
#   que el directorio del archivo esté en sys.path.
# -------------------------------
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))


def cargar_asignaciones():
    """
    Carga la tabla baseline 'asignacion_mec' para diagnósticos (opcional).

    Returns:
        pd.DataFrame: Contenido de la tabla; si hay error, DataFrame vacío.

    Notas:
        - Esta función no es requerida para correr la optimización; se incluye
          como utilidad para inspeccionar el estado actual desde CLI.
    """
    try:
        return pd.read_sql("SELECT * FROM asignacion_mec", engine)
    except Exception as e:
        logger.error(f"Error cargando asignaciones: {e}")
        return pd.DataFrame()


def main():
    """
    Punto de entrada del script:
      1) Carga datos base.
      2) Valida disponibilidad.
      3) Ejecuta optimización.
      4) Muestra métricas de la mejor solución.

    Configuración de BD para guardar resultados:
      - En este ejemplo se pasa un diccionario estático (localhost).
      - En producción: leer de variables de entorno o .env para mayor seguridad.
    """
    # 1) Cargar datos desde la BD (estudiantes, docentes, clases, establecimientos)
    estudiantes, docentes, clases, _ = cargar_datos_desde_db()
    if estudiantes.empty or docentes.empty or clases.empty:
        logger.error("❌ No se pudo cargar los datos necesarios.")
        return

    logger.info(
        "✅ Datos cargados para optimización: "
        f"{len(estudiantes)} estudiantes, {len(docentes)} docentes, {len(clases)} clases"
    )

    # 2) Construir el problema multiobjetivo
    problem = IntegratedProblem(estudiantes, docentes, clases)

    # 3) Ejecutar NSGA-II (y guardar resultados en BD)
    #    - pop_size y n_gen pueden ajustarse por argumentos si lo deseas.
    result = run_integrated_optimization(
        problem,
        pop_size=50,
        n_gen=30,
        n_procs=4,  # reservado para uso futuro (hoy n_jobs=1 dentro de run)
        db_config={
            "user": "postgres",
            "password": "Admin.123",
            "host": "localhost",
            "port": "5432",
            "database": "Asignacion_MEC",
        },
    )

    logger.info("✅ Optimización completada")

    # 4) Mostrar la mejor solución (vector F) en consola
    #    - select_best_individual aplica un orden lexicográfico sobre F
    #      para elegir de manera determinista un individuo representativo.
    try:
        _, _, best_F = select_best_individual(result)
        if best_F is not None:
            print("📊 Mejor solución encontrada:")
            for i, v in enumerate(best_F):
                print(f"   ➤ f{i}: {v:.4f}")
        else:
            print("📊 Mejor solución elegida por menor violación de restricciones; F no disponible.")
    except Exception as e:
        logger.error(f"No se pudo resumir la mejor solución: {e}")


# ------------------------------------------------
# Ejecución directa del script (python integrated_app.py)
# ------------------------------------------------
if __name__ == "__main__":
    main()
