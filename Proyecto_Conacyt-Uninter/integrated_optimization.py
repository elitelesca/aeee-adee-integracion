# ================================================================
# integrated_optimization.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.1
# Descripción:
#     Contiene la lógica de optimización multiobjetivo utilizando
#     algoritmos evolutivos (NSGA-II) y la gestión de guardado de
#     resultados en la base de datos.
# Dependencias:
#     pymoo, psycopg2, logging
# ================================================================

import logging
import uuid
from typing import Dict, Any, Optional
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
import psycopg2
import psycopg2.extras
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DatabaseManager:
    """
    Maneja todas las operaciones con la base de datos.
    """
    def __init__(self, db_config: Dict[str, Any]):
        """
        Inicializa la conexión con la base de datos.

        Args:
            db_config (Dict[str, Any]): Diccionario con parámetros de conexión
                                        (user, password, host, port, database).
        """
        self.db_config = db_config
        self.conn = None

    def connect(self) -> bool:
        """
        Establece la conexión con la base de datos.

        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario.
        """
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Conexión a la base de datos establecida")
            return True
        except psycopg2.Error as e:
            logger.error(f"❌ Error al conectar a la base de datos: {e}")
            return False

    def disconnect(self):
        """
        Cierra la conexión con la base de datos si está abierta.
        """
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("🔌 Conexión a la base de datos cerrada")

    def save_asignaciones(self, problem, result):
        """
        Guarda la mejor solución encontrada en la tabla asignacion_mec.

        Args:
            problem (IntegratedProblem): Instancia del problema optimizado.
            result (pymoo.optimize.Result): Resultado de la optimización.

        Raises:
            Exception: Si ocurre un error durante la transacción.
        """
        try:
            if result.F is None or len(result.F) == 0:
                logger.error("❌ No se encontraron soluciones válidas en la optimización.")
                return

            factibles = int((result.G <= 0).all(axis=1).sum())
            logger.info(f"✅ Soluciones factibles encontradas: {factibles} de {len(result.F)}") 

            best_idx = result.F[:, 0].argmin()
            best_solution = result.X[best_idx]

            asign_docentes = best_solution[:problem.n_estudiantes].astype(int)
            asign_clases = best_solution[problem.n_estudiantes:].astype(int)

            with self.conn.cursor() as cursor:
                cursor.execute("TRUNCATE asignacion_mec RESTART IDENTITY")

                for i, est in problem.estudiantes.iterrows():
                    docente_idx = asign_docentes[i] % problem.n_docentes
                    clase_idx = asign_clases[i] % problem.n_clases

                    docente = problem.docentes.iloc[docente_idx]
                    clase = problem.clases.iloc[clase_idx]

                    distancia = problem._calcular_distancia(
                        (est["lat"], est["lng"]),
                        (clase["lat"], clase["lng"])
                    )

                    cursor.execute("""
                        INSERT INTO asignacion_mec
                        (estudiante_id, docente_id, establecimiento_id, institucion_id, grado, seccion, turno, distancia)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        int(est["estudiante_id"]),
                        int(docente["docente_id"]),
                        int(clase["establecimiento_id"]),
                        int(clase["institucion_id"]),
                        clase["grado"],
                        "A",  # Se puede mejorar en el futuro
                        clase["turno"],
                        float(distancia)
                    ))
            self.conn.commit()
            logger.info("✅ Asignaciones guardadas correctamente en asignacion_mec")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Error al guardar asignaciones: {e}", exc_info=True)
            raise


def run_integrated_optimization(
    problem,
    pop_size: int = 100,
    n_gen: int = 50,
    n_procs: int = 4,
    db_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Ejecuta el algoritmo evolutivo NSGA-II para optimizar el problema.

    Args:
        problem (IntegratedProblem): Problema de optimización a resolver.
        pop_size (int): Tamaño de la población.
        n_gen (int): Número de generaciones.
        n_procs (int): Número de procesos paralelos (actualmente no utilizado en n_jobs=1).
        db_config (dict, opcional): Configuración de BD para guardar resultados.
        run_id (str, opcional): Identificador único de la ejecución.
        metadata (dict, opcional): Datos adicionales para rastreo.

    Returns:
        pymoo.optimize.Result: Resultados de la optimización.
    """    
    algorithm = NSGA2(pop_size=pop_size, eliminate_duplicates=True)

    result = minimize(
        problem,
        algorithm,
        ('n_gen', n_gen),
        seed=42,
        verbose=True,
        save_history=True,
        n_jobs=1
    )
    if result.F is not None and len(result.F) > 0:
        best_idx = result.F[:, 0].argmin()
        logger.info(
            f"🏆 Mejor solución: "
            f"Balance Clases={result.F[best_idx,0]:.2f}, "
            f"Dist Estudiantes={result.F[best_idx,1]:.2f} km, "
            f"Dist Docentes={result.F[best_idx,2]:.2f} km, "
            f"Penalización Turnos={result.F[best_idx,3]:.2f}"
        )
    else:
        logger.warning("⚠️ Optimización completada, pero no hay soluciones válidas.")

    if db_config:
        db_manager = DatabaseManager(db_config)
        if db_manager.connect():
            try:
                db_manager.save_asignaciones(problem, result)
            finally:
                db_manager.disconnect()

    return result
