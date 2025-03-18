import datadb
from geopy import distance
import datadb as data
#X is a vector of all the students and with have the class asignment as data
#Calculate f1(X) - Average assigments per class
def f1(X):
    result=0
    for i in range(len(data.C)):
        count_student_assigned = 0

        for j in range(len(X)):
            if i==X[j]:
                count_student_assigned=count_student_assigned+1

        distance = abs(30-count_student_assigned)

        result=result+distance

    result=result/data.CLASS_SIZE
    round(result, 6)
    return float(result)

#Calculate f2(X) - Average distance between Student Home and Establishment
def f2(X):
    result=0
    n_p=len(data.P)
    for j in range(n_p):
        #id of class
        i=X[j]
        #Establisment ID
        k=int(data.C[i][4] - 1)
        #Add distance between Student Home and Establishment
        d=distance.distance((data.P[j][1],data.P[j][2]),(data.E[k][1],data.E[k][2])).kilometers
        result=result+d
    result=result/n_p
    round(result, 6)
    return float(result)

#Calculate f3(X) - Average quality of establishments assigments
def f3(X):
    result = 0
    n_p = len(data.P)
    for j in range(n_p):
        # id of class
        i = X[j]
        # Establisment ID
        k = data.C[i][4] - 1
        ##sum the valoration of the establishment per area and divide by 3 to get the average
        quality = data.E[k][3] + data.E[k][4] + data.E[k][5]
        result = result + (quality/3)

    result = result / n_p
    round(result,6)
    return float(result)