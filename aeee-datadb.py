# data of Problem Assign Studen
import psycopg2


def init(grade_input, iteration_input):
    global  C, P, E, CLASS_SIZE, PERSON_SIZE, ESTABLISMENT_SIZE, N_OBJ, N_CONSTR, HOST, GRADE, ITERATION, DATABASE, PASS
    GRADE = grade_input
    ITERATION = iteration_input

    print(grade_input)
    print(iteration_input)

    HOST = 'localhost'
    DATABASE = 'tfmdb'
    PASS = 'Tfm123456'

    # Class
    conn = psycopg2.connect("host=" + HOST +", dbname="+DATABASE+" user=postgres password="+PASS+" port=5432")
    cur = conn.cursor()

    C = []
    cur.execute("select grado, turno, seccion, institucion, (dense_rank() over (order by codigo_establecimiento)-1) as establecimiento, capacidad from tesis_prd.clase"
                " where grado = " + str(GRADE))
    for row in cur:
        C.append([row[0], row[1], row[2], row[3], row[4], row[5]])

    # Persons
    P = []
    cur.execute("select estudiante, latitud, longitud, grado from tesis_prd.persona where grado = " + str(GRADE) + " order by 1")
    for row in cur:
        P.append([row[0], row[1], row[2], row[3]])

    # Establishment
    E = []
    cur.execute("select codigo, latitud, longitus, pri_aulas, pri_sanitarios, pri_otros_espacios from tesis_prd.establecimiento order by 1")
    for row in cur:
        E.append([row[0], row[1], row[2], row[3], row[4], row[5]])

    # Configure size
    CLASS_SIZE = len(C)
    PERSON_SIZE = len(P)
    ESTABLISMENT_SIZE = len(E)
    print(CLASS_SIZE)
    print(PERSON_SIZE)
    print(ESTABLISMENT_SIZE)
    N_OBJ = 3
    N_CONSTR = 2

    cur.close()
    conn.close()
