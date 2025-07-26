# 📊 AEEE-ADEE WebSystem
**Sistema de Asignación Multiobjetivo de Estudiantes y Docentes a Instituciones Educativas**

## 📌 Descripción
Este proyecto implementa un sistema completo de optimización multiobjetivo para asignar estudiantes a docentes e instituciones educativas, minimizando distancias y balanceando la carga de las clases.  
El sistema incluye:  
✅ **Optimización multiobjetivo** con algoritmos evolutivos (NSGA-II, Pymoo).  
✅ **Base de datos PostgreSQL** para almacenar estudiantes, docentes, instituciones y asignaciones.  
✅ **Visualización interactiva** con Streamlit, mapas dinámicos y exportación a Excel.  
✅ **Ejecución automática de la optimización** y actualización de asignaciones en la base de datos.

---

## ⚙️ Tecnologías Utilizadas

### Lenguaje y Frameworks
- **Python 3.13.1**  
- **Streamlit** (interfaz web)  
- **Pymoo** (algoritmos evolutivos)  
- **Folium y Plotly** (visualización de datos geográficos)  
- **SQLAlchemy y psycopg2** (conexión a PostgreSQL)

### Base de Datos
- **PostgreSQL 17.4**

---

## 📂 Estructura del Proyecto

```
📁 Proyecto_Asignacion
│
├── integrated_app.py               # Ejecución principal de la optimización
├── integrated_viewer_optimizado.py # Interfaz web con Streamlit
├── integrated_problem.py           # Definición del problema de optimización
├── integrated_optimization.py      # Algoritmo de optimización y guardado en BD
├── database.py                      # Carga de datos desde la BD
├── requirements.txt                 # Librerías necesarias
├── .env                             # Configuración de conexión a la BD
└── README.md                        # Este archivo
```

---

## 🗄️ Configuración de la Base de Datos

1. Crear una base de datos PostgreSQL llamada `Asignacion_MEC`.  
2. Configurar las credenciales en el archivo `.env`:
   ```
   DB_USER=postgres
   DB_PASSWORD=Admin.123
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=Asignacion_MEC
   ```
3. Cargar las tablas necesarias (`estudiantes`, `docentes`, `clases`, `establecimientos`, `instituciones`, `asignacion_mec`).

---

## 🚀 Instalación y Ejecución

### 1. Crear y activar entorno virtual
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Verificar conexión a la BD
```bash
python -c "from database import test_conexion; test_conexion()"
```

### 4. Ejecutar optimización desde consola
```bash
python integrated_app.py
```

### 5. Iniciar interfaz web
```bash
streamlit run integrated_viewer_optimizado.py
```

Abrir en el navegador:  
`http://localhost:8501`

---

## 🧠 Funcionamiento General

1. **Carga de Datos**  
   - Los datos se extraen automáticamente de la BD con `cargar_datos_desde_db()`.

2. **Optimización**  
   - `IntegratedProblem` define las variables, objetivos y restricciones.  
   - `run_integrated_optimization` ejecuta el algoritmo NSGA-II y guarda los resultados en `asignacion_mec`.

3. **Visualización**  
   - Mapas interactivos con estudiantes (azul), docentes (verde) e instituciones (rojo).  
   - Exportación de asignaciones a Excel.

---

## 📊 Objetivos de Optimización
- **F1:** Minimizar la distancia total (estudiante-docente-institución).  
- **F2:** Minimizar el desbalance en la distribución de estudiantes por clase.  
- **Restricciones:**  
  - Capacidad máxima de clases.  
  - Asignación válida de docentes.

---

## ✨ Próximas Mejoras
- Incorporar más algoritmos (MOEAD, RVEA, etc.).  
- Visualización de **líneas de asignación dinámicas** en el mapa.  
- Filtros avanzados por departamento, ciudad y barrio.
