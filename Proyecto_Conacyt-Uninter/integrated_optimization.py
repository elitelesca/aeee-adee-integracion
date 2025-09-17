# ================================================================
# integrated_optimization.py 
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formación: Ing. Eliana Telesca
# Versión: 1.3  
#
# Descripción del módulo
# --------------
# - Orquestar la optimización multiobjetivo con Pymoo (NSGA-II).
# - Seleccionar el "mejor" individuo del resultado (criterio determinista).
# - Persistir las asignaciones óptimas en PostgreSQL sin tocar el baseline
#   (escribe en la tabla de salida: asignacion_mec_opt).
#
# Decisiones de diseño
# --------------------
# - Se usa NSGA-II y minimize(..., save_history=True) para depuración/diagnóstico.
# - n_jobs=1 por estabilidad/compatibilidad en Windows (multiprocessing).
# - El "mejor" individuo se elige con un orden lexicográfico de F-vectores:
#     * Si hay 2 objetivos: (F2, F1)
#     * Si hay 3 objetivos (por defecto): (F3, F2, F1)
#   Esto da un criterio reproducible y explícito.
# - Persistencia con psycopg2 y transacción segura (rollback ante error).
#   La tabla de salida se crea si no existe y se TRUNCATEA en cada corrida.
# ================================================================

import logging
import numpy as np
from typing import Dict, Any
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DatabaseManager:
    """
    Encapsula la conexión a PostgreSQL y el guardado de asignaciones
    en la tabla de salida `asignacion_mec_opt`.

    Uso:
        db = DatabaseManager(db_config)
        if db.connect():
            try:
                db.save_asignaciones(problem, result)
            finally:
                db.disconnect()
    """

    def __init__(self, db_config: Dict[str, Any]):
        """
        Args:
            db_config: dict con claves requeridas por psycopg2.connect
                       (user, password, host, port, database)
        """
        self.db_config = db_config
        self.conn = None

    def connect(self) -> bool:
        """Abre conexión a PostgreSQL. Loguea éxito o error y retorna bool."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Conexión a la base de datos establecida")
            return True
        except psycopg2.Error as e:
            logger.error(f"❌ Error al conectar a la base de datos: {e}")
            return False

    def disconnect(self) -> None:
        """Cierra la conexión si está abierta (idempotente)."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("🔌 Conexión a la base de datos cerrada")

    def save_asignaciones(self, problem, result) -> None:
        """
        Guarda la mejor solución en **asignacion_mec_opt** (tabla de salida).

        Comportamiento:
            1) Selecciona el mejor individuo del frente Pareto.
            2) Decodifica X en:
               - asignaciones_estudiantes: estudiante -> clase
               - asignaciones_docentes:   clase     -> docente (o 'sin docente')
            3) Asegura la tabla de salida (CREATE IF NOT EXISTS).
            4) TRUNCATE de la tabla de salida (siempre sobrescribe el "después").
            5) Inserta filas para cada estudiante, calculando:
               - clase y docente correspondientes (fallback si falta docente real).
               - distancia (Haversine) estudiante -> establecimiento.
            6) Commit; rollback si ocurre excepción.

        Nota:
            - No modifica la tabla baseline `asignacion_mec`.
            - Si un docente queda "fuera de rango" (valor centinela), elige
              automáticamente el docente más cercano al establecimiento.
        """
        try:
            # 1) Elige al mejor individuo (idx, X[idx], F[idx])
            best_idx, best_solution, best_F = select_best_individual(result)

            # 2) Separa el vector decisión en [XA | XD_class]
            n_estudiantes = problem.n_estudiantes
            asignaciones_estudiantes = best_solution[:n_estudiantes].astype(int)
            asignaciones_docentes = best_solution[n_estudiantes:].astype(int)

            with self.conn.cursor() as cursor:
                # 3) Asegurar tabla de salida: estructura = LIKE baseline (incluye índices/constraints)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS asignacion_mec_opt
                    (LIKE asignacion_mec INCLUDING ALL)
                """)
                # 4) Limpiar salida para esta corrida
                cursor.execute("TRUNCATE asignacion_mec_opt RESTART IDENTITY")

                # 5) Insertar una fila por estudiante con su asignación "después"
                for i, estudiante in problem.estudiantes.iterrows():
                    clase_idx = int(asignaciones_estudiantes[i])
                    clase = problem.clases.iloc[clase_idx]

                    # --- Resolver docente asignado a la clase (con fallback) ---
                    docente_idx = int(asignaciones_docentes[clase_idx])
                    if docente_idx >= problem.n_docentes:
                        # Sin docente real: elige el docente más cercano al establecimiento
                        mejor_doc, mejor_d = 0, float("inf")
                        for j, d in problem.docentes.iterrows():
                            dist = problem._hav(
                                (d["lat"], d["lng"]),
                                (clase["lat"], clase["lng"])
                            )
                            if dist < mejor_d:
                                mejor_d, mejor_doc = dist, j
                        docente_idx = int(mejor_doc)

                    docente = problem.docentes.iloc[docente_idx]

                    # Distancia estudiante -> establecimiento (para control/KPI)
                    distancia = problem._hav(
                        (estudiante["lat"], estudiante["lng"]),
                        (clase["lat"], clase["lng"])
                    )

                    # Insert estándar: mismo layout que baseline
                    cursor.execute("""
                        INSERT INTO asignacion_mec_opt
                        (estudiante_id, docente_id, establecimiento_id, institucion_id, grado, seccion, turno, distancia)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        int(estudiante["estudiante_id"]),
                        int(docente["docente_id"]),
                        int(clase["establecimiento_id"]),
                        int(clase["institucion_id"]),
                        clase["grado"],
                        "A",                     # Sección fija (puede parametrizarse)
                        clase["turno"],
                        float(distancia)
                    ))

            # 6) Persistir cambios
            self.conn.commit()
            logger.info("✅ Asignaciones guardadas en asignacion_mec_opt")

        except Exception as e:
            # En caso de error de inserción, revertimos toda la transacción
            if self.conn:
                self.conn.rollback()
            logger.error(f"❌ Error al guardar asignaciones: {e}", exc_info=True)
            # Re-propaga para que la capa superior decida cómo proceder
            raise


# ===========================
# Utilitarios de selección
# ===========================

def _extract_FX(result):
    """
    Extrae matrices F y X desde un objeto resultado de Pymoo con
    compatibilidad para diferentes estructuras (F/X directos, opt, pop).

    Returns:
        (F, X): ndarrays 2D con objetivos (F) y decisiones (X).

    Raises:
        ValueError: si no logra encontrar F/X en el resultado.
    """
    F = getattr(result, "F", None)
    X = getattr(result, "X", None)
    if F is not None and X is not None:
        return F, X

    pob = getattr(result, "opt", None) or getattr(result, "pop", None)
    if pob is None:
        raise ValueError("Resultado vacío: no hay F/X ni opt/pop.")

    F = pob.get("F")
    X = pob.get("X")
    if F is None or X is None:
        raise ValueError("No se pudieron extraer F/X del resultado.")
    return F, X


def select_best_individual(result):
    """
    Selecciona un individuo "representativo" de manera determinista
    usando orden lexicográfico sobre los objetivos.

    Criterio:
      - Si hay 1 solución: idx=0.
      - Si hay 2 objetivos: ordenar por (F2, F1).
      - Si hay 3 objetivos: ordenar por (F3, F2, F1).

    Returns:
        (best_idx, best_X, best_F): índice y vectores correspondientes.
    """
    F, X = _extract_FX(result)
    F = np.atleast_2d(F)

    if F.shape[0] == 1:
        best_idx = 0
    else:
        # Construir claves de orden según cantidad de objetivos
        # np.lexsort aplica orden por la última clave primero (por eso el tuple)
        claves = [F[:, 1], F[:, 0]] if F.shape[1] == 2 else [F[:, 2], F[:, 1], F[:, 0]]
        best_idx = np.lexsort(tuple(claves))[0]

    return best_idx, X[best_idx], F[best_idx]


# ===========================
# Orquestación de corrida
# ===========================

def run_integrated_optimization(
    problem,
    pop_size: int = 100,
    n_gen: int = 50,
    n_procs: int = 4,
    db_config: Dict[str, Any] = None,
    run_id: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Ejecuta NSGA-II sobre el `problem` y (opcionalmente) persiste el resultado.

    Args:
        problem: instancia de IntegratedProblem ya construida.
        pop_size: tamaño de población NSGA-II.
        n_gen: número de generaciones.
        n_procs: reservado para compatibilidad futura (hoy no se usa).
        db_config: dict de conexión a BD; si se provee, se guardan resultados.
        run_id:  metadata opcional (no utilizado en esta versión).
        metadata: metadata adicional opcional (no utilizada en esta versión).

    Returns:
        result: objeto de Pymoo con F, X, historial, etc.
    """
    # 1) Configurar algoritmo
    algorithm = NSGA2(pop_size=pop_size, eliminate_duplicates=True)

    # 2) Minimizar (seed fija → reproducibilidad). n_jobs=1 por estabilidad cross-OS.
    result = minimize(
        problem,
        algorithm,
        ('n_gen', n_gen),
        seed=42,
        verbose=True,
        save_history=True,
        n_jobs=1
    )

    # 3) Persistir en BD si se suministra configuración
    if db_config:
        db = DatabaseManager(db_config)
        if db.connect():
            try:
                db.save_asignaciones(problem, result)
            finally:
                db.disconnect()

    return result
