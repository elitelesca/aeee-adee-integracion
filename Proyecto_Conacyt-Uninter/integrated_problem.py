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
    """
    Decisión:
      - XA: n_estudiantes enteros en [0, n_clases-1]  => estudiante -> clase
      - XD_class: n_clases enteros en [0, n_docentes] => docente por clase
            * n_docentes = "SIN DOCENTE" (solo permitido si la clase no tiene alumnos)
    Objetivos:
      - F1: Distancia promedio (estudiante->establecimiento) + (docente->establecimiento en clases activas)
      - F2: Desvío estándar de carga (alumnos por clase)
      - F3: -(proporción de docentes con 2 clases en el mismo establecimiento)  [se minimiza]
    Restricciones (G >= 0 viola):
      - g1: Exceso de capacidad por clase (suma de overflow)
      - g2: Clases activas sin docente asignado
      - g3: Docentes con más de 2 clases asignadas
      - g4: Si un docente tiene 2 clases, turnos deben ser distintos
      - g5: Incompatibilidades grado (estudiante != grado clase)
    """

    def __init__(self, estudiantes, docentes, clases):
        if estudiantes.empty or docentes.empty or clases.empty:
            raise ValueError("❌ Los DataFrames de entrada no pueden estar vacíos")

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

        # Vector de decisión: XA (n_est), XD_class (n_clases)
        n_var = self.n_estudiantes + self.n_clases

        xl = np.concatenate([
            np.zeros(self.n_estudiantes, dtype=int),
            np.zeros(self.n_clases, dtype=int)
        ])
        xu = np.concatenate([
            np.full(self.n_estudiantes, self.n_clases - 1, dtype=int),
            np.full(self.n_clases, self.n_docentes, dtype=int)  # include "sin docente"
        ])

        super().__init__(
            n_var=n_var,
            n_obj=3,            # <<<<<<<<<<<<< antes: 2
            n_constr=5,
            xl=xl,
            xu=xu,
            elementwise=True
        )

    def _validar_dataframes(self, estudiantes, docentes, clases):
        req_est = {'lat', 'lng', 'nombre', 'grado'}
        req_doc = {'lat', 'lng', 'nombre'}
        req_cls = {'lat', 'lng', 'grado', 'turno', 'capacidad', 'establecimiento_id', 'institucion_id'}

        def faltantes(df, req):
            return req - set(df.columns)

        me = faltantes(estudiantes, req_est)
        md = faltantes(docentes, req_doc)
        mc = faltantes(clases, req_cls)

        errores = []
        if me: errores.append(f"Estudiantes faltan columnas: {me}")
        if md: errores.append(f"Docentes faltan columnas: {md}")
        if mc: errores.append(f"Clases faltan columnas: {mc}")
        if errores:
            raise ValueError("❌ " + " | ".join(errores))

    def _evaluate(self, x, out, *args, **kwargs):
        try:
            nE = self.n_estudiantes
            XA = x[:nE].astype(int)              # estudiante -> clase
            XD_class = x[nE:].astype(int)        # docente por clase (n_docentes = sin docente)

            # --- Cargas por clase y activación ---
            clase_alumnos = np.zeros(self.n_clases, dtype=int)
            for i, clase_idx in enumerate(XA):
                clase_alumnos[clase_idx] += 1
            clase_activa = clase_alumnos > 0

            # --- g1: capacidad ---
            overflow = 0.0
            for l in range(self.n_clases):
                cap = int(self.clases.iloc[l]["capacidad"])
                if clase_alumnos[l] > cap:
                    overflow += (clase_alumnos[l] - cap)
            g1 = overflow

            # --- g2: clase activa sin docente ---
            sin_docente_activas = 0
            for l in range(self.n_clases):
                if clase_activa[l] and XD_class[l] == self.n_docentes:
                    sin_docente_activas += 1
            g2 = sin_docente_activas

            # --- g3: máx 2 clases por docente ---
            clases_por_docente = np.zeros(self.n_docentes, dtype=int)
            for l in range(self.n_clases):
                d = XD_class[l]
                if d < self.n_docentes:
                    clases_por_docente[d] += 1
            exceso_doc = np.sum(np.maximum(0, clases_por_docente - 2))
            g3 = exceso_doc

            # --- g4: 2 clases de un docente deben tener turnos distintos ---
            conflictos_turno = 0
            if np.any(clases_por_docente >= 2):
                for j in range(self.n_docentes):
                    if clases_por_docente[j] >= 2:
                        turnos = [self.clases.iloc[l]["turno"]
                                  for l in range(self.n_clases) if XD_class[l] == j]
                        if len(turnos) >= 2 and len(set(turnos)) < len(turnos):
                            conflictos_turno += 1
            g4 = conflictos_turno

            # --- g5: compatibilidad grado ---
            incompat = 0
            for i, clase_idx in enumerate(XA):
                grado_e = self.estudiantes.iloc[i]["grado"]
                grado_c = self.clases.iloc[clase_idx]["grado"]
                if pd.notna(grado_e) and pd.notna(grado_c):
                    if str(grado_e).strip() != str(grado_c).strip():
                        incompat += 1
            g5 = incompat

            # --- FO1: distancias ---
            dist_est_prom = 0.0
            for i, clase_idx in enumerate(XA):
                est = self.estudiantes.iloc[i]
                cls = self.clases.iloc[clase_idx]
                dist_est_prom += self._hav((est["lat"], est["lng"]), (cls["lat"], cls["lng"]))
            dist_est_prom /= max(1, self.n_estudiantes)

            total_doc = 0.0
            cnt_doc = 0
            for l in range(self.n_clases):
                if clase_activa[l] and XD_class[l] < self.n_docentes:
                    cls = self.clases.iloc[l]
                    doc = self.docentes.iloc[int(XD_class[l])]
                    total_doc += self._hav((doc["lat"], doc["lng"]), (cls["lat"], cls["lng"]))
                    cnt_doc += 1
            dist_doc_prom = total_doc / max(1, cnt_doc)
            F1 = dist_est_prom + dist_doc_prom

            # --- FO2: balance ---
            F2 = float(np.std(clase_alumnos))

            # --- FO3: maximizar docentes con 2 clases en el mismo establecimiento (negativo para minimizar) ---
            same_school = 0
            for j in range(self.n_docentes):
                # clases de este docente
                idxs = [l for l in range(self.n_clases) if XD_class[l] == j]
                if len(idxs) == 2:
                    est1 = self.clases.iloc[idxs[0]]["establecimiento_id"]
                    est2 = self.clases.iloc[idxs[1]]["establecimiento_id"]
                    if pd.notna(est1) and pd.notna(est2) and int(est1) == int(est2):
                        same_school += 1
            F3 = - (same_school / max(1, self.n_docentes))

            out["F"] = [F1, F2, F3]
            out["G"] = [g1, g2, g3, g4, g5]

        except Exception as e:
            logger.error(f"❌ Error en evaluación: {e}", exc_info=True)
            out["F"] = [1e10, 1e10, 1e10]
            out["G"] = [1e10, 1e10, 1e10, 1e10, 1e10]

    @staticmethod
    def _hav(loc1, loc2):
        R = 6371.0
        lat1, lon1 = np.radians(loc1)
        lat2, lon2 = np.radians(loc2)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
        c = 2*np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R*c
