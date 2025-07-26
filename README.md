# Proyecto Conacyt-Uninter  
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)  
[![Streamlit](https://img.shields.io/badge/Streamlit-1.46+-brightgreen.svg)](https://streamlit.io/)  
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-blue.svg)](https://www.postgresql.org/)  
[![Estado](https://img.shields.io/badge/Estado-Activo-success.svg)](#)  

## Desarrolladores
- **Tutor Investigador:** Dr. Fabio Lopez  
- **Investigadora en formación:** Ing. Eliana Telesca  

## Descripción
Este proyecto implementa un sistema interactivo para la asignación multiobjetivo de estudiantes y docentes a instituciones educativas.  
Utiliza algoritmos evolutivos NSGA-II para minimizar distancias, balancear clases y reducir la carga docente, respetando restricciones de capacidad de las instituciones.  

## Características
✅ Mapa interactivo con estudiantes (azul), docentes (verde) e instituciones (rojo).  
✅ Ejecución de optimización desde consola o interfaz web.  
✅ Exportación de asignaciones actuales y optimizadas a Excel.  
✅ Código modular con buenas prácticas y documentación estandarizada.  

## Estructura del Proyecto
```
/database.py                     # Conexión y carga de datos desde PostgreSQL
/integrated_app.py               # Ejecución por consola de la optimización
/integrated_optimization.py      # Lógica de optimización y guardado en BD
/integrated_problem.py           # Definición del problema multiobjetivo
/integrated_viewer_optimizado.py # Interfaz web interactiva con Streamlit
/requirements.txt                # Librerías necesarias
/.env                            # Variables de entorno
```

## Instalación y Uso

### 1. Crear entorno virtual (opcional)
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate    # Windows
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea un archivo .env con el siguiente contenido:
```
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Asignacion_MEC
```
### 4. Ejecutar el sistema

**Optimización por consola:**
```bash
python integrated_app.py
```
**Visualización y Optimización Web:**
```bash
streamlit run integrated_viewer_optimizado.py
```
## Ejemplo de Uso
### Optimización por Consola
```
📊 Mejor solución encontrada:
   ➤ Distancia total: 120.45 km
   ➤ Balance (desvío): 3.2145
```
### Interfaz Web
- Pestaña Visualización Actual: muestra asignaciones guardadas y mapa interactivo.  
- Pestaña Optimización: permite ejecutar la optimización y exportar resultados.  

## Contribución
¡Las contribuciones son bienvenidas!  
1. Realiza un **fork** del repositorio.  
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`).  
3. Realiza tus cambios siguiendo el estándar de comentarios (PEP 257).  
4. Envía un pull request describiendo los cambios realizados.

### Visualización del sistema
1. Vista inicial del sistema AEEE-ADEE Integrado:
<img width="1887" height="782" alt="image" src="https://github.com/user-attachments/assets/e18c7d73-a632-4d7f-b2fd-10802aa5fe02" />
<img width="1884" height="401" alt="image" src="https://github.com/user-attachments/assets/6be4a835-443a-4a72-bb6e-27e579bdae1d" />
2. Ejecución de la optimización: 
<img width="1889" height="390" alt="image" src="https://github.com/user-attachments/assets/29da7914-1995-4ef9-9e05-9fae1b35c9c4" />
3. Resultados de la optimización:
<img width="1892" height="844" alt="image" src="https://github.com/user-attachments/assets/854f5deb-2b5f-4d85-9603-70240257da78" />


