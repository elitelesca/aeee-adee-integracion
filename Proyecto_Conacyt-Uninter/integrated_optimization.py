# ================================================================
# integrated_optimization.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.2
# Descripción:
#     Contiene la lógica de optimización multiobjetivo utilizando
#     algoritmos evolutivos (NSGA-II) y la gestión de guardado de
#     resultados en la base de datos.
# Dependencias:
#     pymoo, psycopg2, logging
# ================================================================

import logging
import uuid
import numpy as np 
from typing import Dict, Any, Optional
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DatabaseManager:
    """
    Maneja todas las operaciones con la base de datos PostgreSQL.
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
        Guarda la mejor solución en asignacion_mec.

         Cromosoma en tu modelo:
        - best_solution = [ XA(0..nE-1) , XD_class(0..nC-1) ]
        * XA[i] = índice de clase asignada al estudiante i
        * XD_class[l] = índice de docente asignado a la clase l
                         (o == n_docentes para "sin docente")
        """
        try:
            # 1) Elegir mejor individuo (robusto si result.F es None)
            best_idx, best_solution, best_F = select_best_individual(result)

            # 2) Decodificar cromosoma según tu IntegratedProblem
            nE = problem.n_estudiantes
            XA = best_solution[:nE].astype(int)               # estudiante -> clase
            XD_class = best_solution[nE:].astype(int)         # docente por clase

            with self.conn.cursor() as cursor:
                cursor.execute("TRUNCATE asignacion_mec RESTART IDENTITY")

                for i, est in problem.estudiantes.iterrows():
                    # clase del estudiante i
                    clase_idx = int(XA[i])
                    cls = problem.clases.iloc[clase_idx]

                    # docente asignado a esa clase
                    docente_idx = int(XD_class[clase_idx])

                    if docente_idx >= problem.n_docentes:
                        # Fallback: si la clase está activa pero quedó "sin docente",
                        # elegir el docente más cercano al establecimiento de la clase.
                        best_j, best_d = 0, float("inf")
                        for j, doc in problem.docentes.iterrows():
                            d = problem._hav((doc["lat"], doc["lng"]), (cls["lat"], cls["lng"]))
                            if d < best_d:
                                best_d, best_j = d, j
                        docente_idx = int(best_j)

                    docente = problem.docentes.iloc[docente_idx]

                    # Distancia estudiante -> establecimiento de la clase
                    distancia = problem._hav((est["lat"], est["lng"]), (cls["lat"], cls["lng"]))

                    cursor.execute("""
                        INSERT INTO asignacion_mec
                        (estudiante_id, docente_id, establecimiento_id, institucion_id, grado, seccion, turno, distancia)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        int(est["estudiante_id"]),
                        int(docente["docente_id"]),
                        int(cls["establecimiento_id"]),
                        int(cls["institucion_id"]),
                        cls["grado"],
                        "A",
                        cls["turno"],
                        float(distancia)
                    ))
            self.conn.commit()
            logger.info("✅ Asignaciones guardadas correctamente en asignacion_mec")
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"❌ Error al guardar asignaciones: {e}", exc_info=True)
            raise

def _extract_FX(result):
    """
    Devuelve (F, X) desde result.F/result.X o, si vienen None,
    desde result.opt (o result.pop).
    """
    F = getattr(result, "F", None)
    X = getattr(result, "X", None)
    if F is not None and X is not None:
        return F, X

    pop = getattr(result, "opt", None) or getattr(result, "pop", None)
    if pop is None:
        raise ValueError("Resultado vacío: no hay F/X ni opt/pop.")
    F = pop.get("F")
    X = pop.get("X")
    if F is None or X is None:
        raise ValueError("No se pudieron extraer F/X del resultado.")
    return F, X

# Reemplaza select_best_individual en integrated_optimization.py
def select_best_individual(result):
    import numpy as np
    F, X = _extract_FX(result)
    F = np.atleast_2d(F)
    if F.shape[0] == 1:
        best_idx = 0
    else:
        # Orden lexicográfico: F1, luego F2, luego (si existe) F3
        keys = [F[:, 1], F[:, 0]] if F.shape[1] == 2 else [F[:, 2], F[:, 1], F[:, 0]]
        best_idx = np.lexsort(tuple(keys))[0]
    return best_idx, X[best_idx], F[best_idx]


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

    if db_config:
        db_manager = DatabaseManager(db_config)
        if db_manager.connect():
            try:
                db_manager.save_asignaciones(problem, result)
            finally:
                db_manager.disconnect()

    return result
