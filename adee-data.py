#data of Problem Assign Teacher
import psycopg2

def init(maxDistance):
    #Maximum distance on kilometers
    global Dmax, C, D, E, CLASS_SIZE, TEACHER_SIZE, N_OBJ, N_CONSTR
    Dmax=maxDistance
    #Class
    conn = psycopg2.connect("dbname=tfmdb user=tfm password=Tfm123456 port=5432")
    cur = conn.cursor()
    
    C = []
    cur.execute("select nro,g,t,s,i,e from c order by 1")
    for row in cur:
        C.append([row[1],row[2],row[3],row[4],row[5]])
   
    #Teachers
    D=[]
    cur.execute("select nro,lat,long from d order by 1")
    for row in cur:
        D.append([row[0],row[1],row[2]])

    #Establishment
    E=[]
    cur.execute("select nro,lat,long from e order by 1")
    for row in cur:
        E.append([row[0],row[1],row[2]])

    #Configure size
    CLASS_SIZE = len(C)
    TEACHER_SIZE = len(D)
    N_OBJ = 3
    N_CONSTR = 3

    cur.close()
    conn.close()