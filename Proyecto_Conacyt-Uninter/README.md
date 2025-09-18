# Proyecto Conacyt-Uninter

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.46+-brightgreen.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-blue.svg)](https://www.postgresql.org/)
[![Estado](https://img.shields.io/badge/Estado-Activo-success.svg)](#)

---
## 📌 Dirección del Proyecto

* **Directora:** Dra. Andrea Giménez
* **Tutor Investigador:** Dr. Fabio Lopez
* **Investigadora en formación:** Ing. Eliana Telesca

---
## 📝 Descripción

**AEEE-ADEE Integrado — Asignación multiobjetivo (CONACYT-UNINTER)**

Sistema interactivo para la **asignación multiobjetivo** de estudiantes y docentes a instituciones educativas. Optimiza múltiples criterios (distancias, balance de carga, compatibilidad docente-clase) usando algoritmos evolutivos **NSGA-II** con **pymoo**, visualización en **Streamlit** y persistencia en **PostgreSQL**.

**Objetivos de optimización:**

* Minimizar distancias estudiante→establecimiento y docente→establecimiento.
* Balancear la cantidad de alumnos por clase.
* Reducir sobrecarga de docentes y asignaciones conflictivas.

---
## ✨ Características principales

* ✅ **Mapa interactivo** con estudiantes (azul), docentes (verde) e instituciones (rojo).
* ✅ **Optimización automática** desde consola o interfaz web.
* ✅ **Exportación a Excel** de asignaciones antes y después de la optimización.
* ✅ **Comparación visual y tabular** de reasignaciones.
* ✅ **Código modular y documentado** siguiendo buenas prácticas.

---
## 📂 Estructura del Proyecto

```
/database.py                     # Conexión SQLAlchemy + carga de datos base (estudiantes, docentes, clases, establecimientos).
/integrated_problem.py           # Define el problema multiobjetivo (variables, objetivos, restricciones) con pymoo.
/integrated_optimization.py      # Orquestación NSGA-II, selección de mejor individuo, guardado en asignacion_mec_opt.
/integrated_app.py               # Script CLI: ejecución de optimización en consola.
/integrated_viewer_optimizado.py # App Streamlit con 3 pestañas: Antes / Optimización / Comparación.
/requirements.txt                # Dependencias del proyecto.
/.env                            # Variables de entorno (no versionar).
```

---
## 🗄️ Modelo de Datos

El sistema **lee** de tablas base y **escribe** en una tabla de salida:

**Tablas base**

* `estudiantes(id, nombre, grado, lat, lng, departamento, localidad, barrio)`
* `docentes(id, nombre, grado, lat, lng, departamento, localidad, barrio)`
* `establecimientos(id, institucion_id, lat, lng)`
* `instituciones(id, nombre, departamento, localidad, barrio)`
* `clases(id, grado, turno, capacidad, establecimiento_id, institucion_id, nombre_institucion)`

**Tablas de asignación**

* **Antes:** `asignacion_mec` (baseline actual).
* **Después:** `asignacion_mec_opt` (creada si no existe, truncada en cada corrida).

---
## ⚙️ Instalación

1. **Crear entorno virtual** (opcional):

```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
```

2. **Instalar dependencias**:

```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno** en `.env`:

```
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Asignacion_MEC
```

---
## ▶️ Uso

### **Optimización desde consola**

```bash
python integrated_app.py
```

### **Optimización y visualización en Streamlit**

```bash
streamlit run integrated_viewer_optimizado.py
```

---
## 📊 Ejemplo de salida

### Consola:

```
📊 Mejor solución encontrada:
   ➤ f0: 120.4500
   ➤ f1: 3.2145
   ➤ f2: -0.0500
```

### Interfaz Web:

* **Visualización Actual:** muestra asignaciones guardadas y mapa interactivo.
* **Optimización:** ejecuta NSGA-II y exporta resultados.
* **Comparación:** lista y mapa de reasignaciones (antes → después).

---
## 🔍 Detalle por Módulo

* **`database.py`**
  Configura conexión con PostgreSQL, carga estudiantes/docentes/clases/establecimientos y provee `test_conexion()`.

* **`integrated_problem.py`**
  Define el problema multiobjetivo con 3 objetivos y 5 restricciones, usando `ElementwiseProblem` de pymoo.

* **`integrated_optimization.py`**
  Ejecuta NSGA-II, selecciona el mejor individuo (`select_best_individual`) y guarda asignaciones en `asignacion_mec_opt` (sin tocar la baseline).

* **`integrated_app.py`**
  Script CLI que corre la optimización y muestra métricas de la mejor solución en consola.

* **`integrated_viewer_optimizado.py`**
  Interfaz Streamlit con 3 pestañas: baseline (antes), ejecución de optimización, y comparación con KPIs, gráficos y mapas.

* **`requirements.txt`**
  Lista dependencias fijadas: Streamlit, pymoo, SQLAlchemy, Folium, Plotly, etc.

---
## 📸 Capturas del Sistema

1. **Vista inicial Pestaña Visualización Actual:**
   <img width="1894" height="1078" alt="PESTAÑA ANTES" src="https://github.com/user-attachments/assets/4b200ab0-e6bd-4f0b-a970-a8b9e5cb2c90" />

2. **Vista inicial Pestaña Optimización:**
   ![PESTAÑA OPTIMIZACION ANTES DE EJECUTAR](https://github.com/user-attachments/assets/bdfc40cc-7519-4418-908a-c5d84fe45012)

3. **Vista inicial Pestaña Comparación Antes/Después:**
   ![PESTAÑA COMPARACION ANTES DE EJECUTAR OPTIMIZACION](https://github.com/user-attachments/assets/2bdef4ef-2cb9-400d-9575-fc086110371a)

4. **Ejecución de la optimización:**
   ![PESTAÑA OPTIMIZACION DURANTE LA EJECUCION](https://github.com/user-attachments/assets/f45c63f3-0565-4e8b-9235-c9eccd7d2954)  

5. **Resultados optimizados:**
   ![PESTAÑA OPTIMIZACION DESPUES DE LA EJECUCION](https://github.com/user-attachments/assets/50c8a19f-0afa-482c-8683-d2e178464c53) 

6. **Resultados comparados antes y despues:**
   ![PESTAÑA COMPARACION DESPUES DE LA EJECUCION](https://github.com/user-attachments/assets/c174a602-cdbb-4ffd-b44a-ba769261adb5)
---
## 🤝 Contribución


1. Haz un **fork** del repositorio.
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`).
3. Aplica cambios siguiendo **PEP 257** y la convención de comentarios del repo.
4. Envía un **pull request** describiendo tus aportes.




