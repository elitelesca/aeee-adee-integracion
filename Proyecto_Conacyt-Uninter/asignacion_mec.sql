-- ================================================================
-- Creación de la base de datos: Asignacion_MEC
-- Proyecto Conacyt-Uninter
-- Tutor investigador: Dr. Fabio Lopez
-- Investigador en formación: Ing. Eliana Telesca
-- Versión: 1.0
-- ================================================================

-- 1. Crear Base de Datos (ejecutar con privilegios)
CREATE DATABASE "Asignacion_MEC";
\c Asignacion_MEC;

-- ================================================================
-- 2. TABLAS
-- ================================================================

-- ====================
-- Tabla: INSTITUTO
-- ====================
CREATE TABLE instituciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    departamento VARCHAR(50) NOT NULL,
    localidad VARCHAR(50) NOT NULL,
    barrio VARCHAR(50) NOT NULL
);

-- ====================
-- Tabla: ESTABLECIMIENTO
-- ====================
CREATE TABLE establecimientos (
    id SERIAL PRIMARY KEY,
    institucion_id INT NOT NULL REFERENCES instituciones(id) ON DELETE CASCADE,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL
);

-- ====================
-- Tabla: CLASE
-- ====================
CREATE TABLE clases (
    id SERIAL PRIMARY KEY,
    grado VARCHAR(20) NOT NULL,
    turno VARCHAR(20) NOT NULL,
    capacidad INT NOT NULL CHECK (capacidad > 0),
    establecimiento_id INT NOT NULL REFERENCES establecimientos(id) ON DELETE CASCADE
);

-- ====================
-- Tabla: ESTUDIANTE
-- ====================
CREATE TABLE estudiantes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    grado VARCHAR(20) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    departamento VARCHAR(50) NOT NULL,
    localidad VARCHAR(50) NOT NULL,
    barrio VARCHAR(50) NOT NULL
);

-- ====================
-- Tabla: DOCENTE
-- ====================
CREATE TABLE docentes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    grado VARCHAR(20) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    departamento VARCHAR(50) NOT NULL,
    localidad VARCHAR(50) NOT NULL,
    barrio VARCHAR(50) NOT NULL
);

-- ====================
-- Tabla: ASIGNACIÓN MEC
-- ====================
CREATE TABLE asignacion_mec (
    id SERIAL PRIMARY KEY,
    estudiante_id INT NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    docente_id INT NOT NULL REFERENCES docentes(id) ON DELETE CASCADE,
    establecimiento_id INT NOT NULL REFERENCES establecimientos(id) ON DELETE CASCADE,
    institucion_id INT NOT NULL REFERENCES instituciones(id) ON DELETE CASCADE,
    grado VARCHAR(20) NOT NULL,
    seccion VARCHAR(5) NOT NULL,
    turno VARCHAR(20) NOT NULL,
    distancia DOUBLE PRECISION NOT NULL
);

-- ================================================================
-- 3. INSERTS DE EJEMPLO (Datos mínimos para probar el proyecto)
-- ================================================================

-- INSTITUCIONES
INSERT INTO instituciones (nombre, departamento, localidad, barrio)
VALUES
('Colegio Nacional', 'Central', 'San Lorenzo', 'Centro'),
('Escuela Básica', 'Central', 'Luque', 'San Miguel');

-- ESTABLECIMIENTOS
INSERT INTO establecimientos (institucion_id, lat, lng)
VALUES
(1, -25.339, -57.508),
(2, -25.267, -57.490);

-- CLASES
INSERT INTO clases (grado, turno, capacidad, establecimiento_id)
VALUES
('6to', 'Mañana', 30, 1),
('7mo', 'Tarde', 35, 2);

-- ESTUDIANTES
INSERT INTO estudiantes (nombre, grado, lat, lng, departamento, localidad, barrio)
VALUES
('Ana López', '6to', -25.340, -57.509, 'Central', 'San Lorenzo', 'Centro'),
('Juan Pérez', '7mo', -25.268, -57.491, 'Central', 'Luque', 'San Miguel');

-- DOCENTES
INSERT INTO docentes (nombre, grado, lat, lng, departamento, localidad, barrio)
VALUES
('Marta García', '6to', -25.341, -57.507, 'Central', 'San Lorenzo', 'Centro'),
('Carlos Ruiz', '7mo', -25.266, -57.492, 'Central', 'Luque', 'San Miguel');
