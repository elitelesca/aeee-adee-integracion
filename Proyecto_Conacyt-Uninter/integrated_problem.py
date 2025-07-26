# ================================================================
# integrated_problem.py
# Proyecto Conacyt-Uninter
# Tutor investigador: Dr. Fabio Lopez 
# Investigador en formacion: Ing. Eliana Telesca
# Versión: 1.1
# Descripción:
#     Define el problema de optimización multiobjetivo para la
#     asignación de estudiantes a docentes y clases, minimizando
#     distancias y balanceando cargas.
# Dependencias:
#     numpy, pandas, pymoo, logging
# ================================================================

import numpy as np
from pymoo.core.problem import ElementwiseProblem
import logging
import pandas as pd

logger = logging.getLogger("integrated_problem")
logger.setLevel(logging.INFO)

class IntegratedProblem(ElementwiseProblem):
    def __init__(self, estudiantes, docentes, clases, max_distance=40):
        """
        Problema de optimización integrado (Docente + Estudiante + Clase).
        Combina la lógica ADEE (docentes) y AEEE (estudiantes).

        Args:
            estudiantes (pd.DataFrame): Datos de estudiantes (lat, lng, etc.)
            docentes (pd.DataFrame): Datos de docentes (lat, lng, etc.)
            clases (pd.DataFrame): Datos de clases (capacidad, lat, lng, etc.)
            max_distance (float): Distancia máxima permitida para asignar docente.

        Raises:
            ValueError: Si los DataFrames están vacíos.
        """
        if estudiantes.empty or docentes.empty or clases.empty:
            raise ValueError("❌ Los DataFrames no pueden estar vacíos")

        # Resetear índices para evitar problemas con iterrows
        estudiantes = estudiantes.reset_index(drop=True)
        docentes = docentes.reset_index(drop=True)
        clases = clases.reset_index(drop=True)

        self._validar_dataframes(estudiantes, docentes, clases)

        self.estudiantes = estudiantes
        self.docentes = docentes
        self.clases = clases

        self.n_estudiantes = len(estudiantes)
        self.n_docentes = len(docentes)
        self.n_clases = len(clases)
        self.max_distance = max_distance # Distancia máxima permitida docente ↔ establecimiento

        # Variables de decisión (2 por estudiante: docente + clase)
        n_var = self.n_estudiantes * 2

        super().__init__(
            n_var=n_var,
            n_obj=4,    # 4 objetivos: AEEE(f1,f2) + ADEE(f1,f2)
            n_constr=3, # Restricciones: capacidad, docente válido, distancia máxima
            xl=np.zeros(n_var),
            xu=np.concatenate([
                np.full(self.n_estudiantes, self.n_docentes - 1),
                np.full(self.n_estudiantes, self.n_clases - 1)
            ]),
            elementwise=True
        )

    def _validar_dataframes(self, estudiantes, docentes, clases):
        required_est = {'lat', 'lng', 'nombre'}
        required_doc = {'lat', 'lng', 'nombre'}
        required_cls = {'lat', 'lng', 'grado', 'turno', 'capacidad'}

        if not required_est.issubset(estudiantes.columns):
            missing = required_est - set(estudiantes.columns)
            raise ValueError(f"❌ Estudiantes faltan columnas: {missing}")

        if not required_doc.issubset(docentes.columns):
            missing = required_doc - set(docentes.columns)
            raise ValueError(f"❌ Docentes faltan columnas: {missing}")

        if not required_cls.issubset(clases.columns):
            missing = required_cls - set(clases.columns)
            raise ValueError(f"❌ Clases faltan columnas: {missing}")

    def _evaluate(self, x, out, *args, **kwargs):
        """
        Evalúa una solución candidata calculando objetivos y restricciones.

        Args:
            x (np.ndarray): Vector de decisión [docente_idx, clase_idx].
            out (dict): Diccionario con objetivos y restricciones.

        Returns:
            None. Modifica `out` con:
                F (list): [balance_clases, dist_estudiante, dist_docente, penalizacion_turnos]
                G (list): [capacidad_excedida, docentes_invalidos, distancia_maxima]
        """
        try:
            n = self.n_estudiantes
            asign_docentes = x[:n].astype(int)
            asign_clases = x[n:].astype(int)

            total_dist = 0.0
            clases_count = np.zeros(self.n_clases)
            docentes_count = np.zeros(self.n_docentes)
            
            # ============================
            # Objetivos combinados ADEE + AEEE
            # ============================

            # AEEE f1: Balance de estudiantes por clase (equilibrio)
            for c in asign_clases:
                clases_count[c % self.n_clases] += 1
            f1_balance_clases = np.mean(np.abs(30 - clases_count))

            # AEEE f2: Distancia estudiante ↔ establecimiento
            f2_dist_estudiante_clase = 0.0
            for i, est in self.estudiantes.iterrows():
                clase_idx = asign_clases[i] % self.n_clases
                clase = self.clases.iloc[clase_idx]
                f2_dist_estudiante_clase += self._calcular_distancia(
                    (est["lat"], est["lng"]),
                    (clase["lat"], clase["lng"])
                )
            f2_dist_estudiante_clase /= self.n_estudiantes

            # ADEE f1: Distancia docente ↔ establecimiento
            f3_dist_docente_establecimiento = 0.0
            for i in range(self.n_estudiantes):
                docente_idx = asign_docentes[i] % self.n_docentes
                clase_idx = asign_clases[i] % self.n_clases
                docente = self.docentes.iloc[docente_idx]
                clase = self.clases.iloc[clase_idx]
                f3_dist_docente_establecimiento += self._calcular_distancia(
                    (docente["lat"], docente["lng"]),
                    (clase["lat"], clase["lng"])
                )
            f3_dist_docente_establecimiento /= self.n_estudiantes

            # ADEE f2: Penalización docentes con dos turnos en el mismo establecimiento
            # (Evita sobrecarga docente)
            docentes_turnos = {}
            f4_penalizacion_turnos = 0
            for i in range(self.n_estudiantes):
                docente_idx = asign_docentes[i] % self.n_docentes
                clase_idx = asign_clases[i] % self.n_clases
                establecimiento = self.clases.iloc[clase_idx]["establecimiento_id"]

                if docente_idx not in docentes_turnos:
                    docentes_turnos[docente_idx] = set()
                else:
                    if establecimiento in docentes_turnos[docente_idx]:
                        f4_penalizacion_turnos += 1
                docentes_turnos[docente_idx].add(establecimiento)

            # ============================
            # Restricciones
            # ============================

            # G1: Capacidad excedida por clase
            g1 = sum(
                max(0, clases_count[i] - self.clases.iloc[i]["capacidad"])
                for i in range(self.n_clases)
            )

            # G2: Docentes asignados fuera de rango (teóricamente 0)
            g2 = sum(1 for d in asign_docentes if d >= self.n_docentes)

            # G3: Distancia máxima docente ↔ establecimiento (ADEE Dmax)
            g3 = 0
            for i in range(self.n_estudiantes):
                docente_idx = asign_docentes[i] % self.n_docentes
                clase_idx = asign_clases[i] % self.n_clases
                d_docente = self._calcular_distancia(
                    (self.docentes.iloc[docente_idx]["lat"], self.docentes.iloc[docente_idx]["lng"]),
                    (self.clases.iloc[clase_idx]["lat"], self.clases.iloc[clase_idx]["lng"])
                )
                if d_docente > self.max_distance:
                    g3 += 1
            # ============================
            # Salida
            # ============================
            out["F"] = [
                f1_balance_clases,
                f2_dist_estudiante_clase,
                f3_dist_docente_establecimiento,
                f4_penalizacion_turnos
            ]
            out["G"] = [g1, g2, g3]

        except Exception as e:
            logger.error(f"❌ Error en evaluación integrada: {e}", exc_info=True)
            out["F"] = [1e10, 1e10, 1e10, 1e10]
            out["G"] = [1e10, 1e10, 1e10]

    def _calcular_distancia(self, loc1, loc2):
        """
        Calcula la distancia Haversine entre dos puntos geográficos.

        Args:
            loc1 (tuple): Coordenadas (lat, lng) del punto 1.
            loc2 (tuple): Coordenadas (lat, lng) del punto 2.

        Returns:
            float: Distancia en kilómetros.
        """
        R = 6371  # Radio de la Tierra en km
        lat1, lon1 = np.radians(loc1)
        lat2, lon2 = np.radians(loc2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c
