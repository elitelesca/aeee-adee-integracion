import csv
from re import S
import psycopg2
from geopy import distance
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import pandas as pd
import sys

print("Load results...")



if __name__ == '__main__':

    global  HOST, GRADE, DATABASE, PASS
    GRADE = 1


    HOST = '143.255.142.228'
    DATABASE = 'tesis_ceci'
    PASS = 'tita92'

    # Class
    conn = psycopg2.connect(
        "host=" + HOST + ", dbname=" + DATABASE + " user=postgres password=" + PASS + " port=5432")
    cur = conn.cursor()

    cur.execute("select * from tesis_prd.get_fo("+str(GRADE)+")")

    for row in cur:
        f1m = row[0]
        f2m = row[1]
        f3m = row[2]

    cur.execute("select fo1, fo2, fo3 from tesis_prd.resultados_py where grado = " + str(GRADE))

    P = set()
    # Non-dominated solutions
    ND = set()
    # Search Non-dominated Solutions


    for row in cur:
       f1a2 = row[0]
       f2a2 = row[1]
       f3a2 = row[2]
       P.add((f1a2, f2a2, f3a2, "Conjunto Pareto", 10))


    for i1 in P:
        isNonDominated = True
        c = 0
        for i2 in P:
            if i1 != i2:
                if i1[0] >= i2[0] and i1[1] >= i2[1] and i1[2] <= i2[2]:  # Min f1, Min f2, Max f3
                    if i1[0] > i2[0] or i1[1] > i2[1] or i1[2] < i2[2]:
                        c = c + 1
        if c == 0:
            ND.add(i1)

    P = ND

    f1a = 0
    for i1 in P:
        f1a = f1a + i1[0]

    f1a = f1a / len(P)

    f2a = 0
    for i1 in P:
        f2a = f2a + i1[1]

    f2a = f2a / len(P)

    f3a = 0
    for i1 in P:
        f3a = f3a + i1[2]

    f3a = f3a / len(P)


    # P.add((0,1,2,"Óptimo Teórico",10))
    P.add((f1a, f2a, f3a, "ND", 10))
    P.add((f1m, f2m, f3m, "X MEC", 10))

    print("ND: " + str(len(P)))
    print("X_A: " + str([f1a, f2a, f3a]))
    print("X_MEC: " + str([f1m, f2m, f3m]))

    # creating a list of column names
    column_values = ['f1(X)', 'f2(X)', 'f3(X)', "datos", "size"]

    # creating the dataframe
    df = pd.DataFrame(data=P,
                      columns=column_values)

    fig = px.scatter_3d(df, x='f1(X)', y='f2(X)', z='f3(X)', color='datos', size="size", labels={

    })

    fig.show()