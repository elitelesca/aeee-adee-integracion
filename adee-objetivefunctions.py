import data
from geopy import distance

#Calculate f1(X) - Average distance between Teacher Home and Establishment
def f1(X):
    result=0
    n_c=len(data.C)
    for j in range(n_c):
        i=X[j]
        k=data.C[j][4]-1
        #Add distance between Teacher Home and Establishment
        d=distance.distance((data.D[i][1],data.D[i][2]),(data.E[k][1],data.E[k][2])).kilometers      
        result=result+d
    result=result/n_c
    return result

#Calculate f2(X) - Max teacher with two shigt in the same establishment
def f2(X):
    result=0
    countTeacherAssigned=0
    assign1=-1
    assign2=-1
    for i in range(len(data.D)):
        assign1=-1
        assign2=-1
        for j in range(len(X)):
            if i==X[j]:                
                if assign1==-1:
                    countTeacherAssigned=countTeacherAssigned+1
                    assign1=j
                else:
                    assign2=j
        if(assign1!=-1): #Assigned
            if(assign2!=-1): #Two assigned
                if(data.C[assign1][4]==data.C[assign2][4]): #Same Establishment
                    result=result+1              
    result=result/countTeacherAssigned
    return result

#Calculate f3(X) - Average class per teacher
def f3(X):
    result=0
    countTeacherAssigned=len(data.D)
    assign1=-1
    assign2=-1
    for i in range(len(data.D)):
        assign1=-1
        assign2=-1
        for j in range(len(X)):
            if i==X[j]:
                if assign1==-1:
                    assign1=j
                else:
                    assign2=j
        if(assign1!=-1): #Assigned
            if(assign2!=-1): #Two assigned
                result=result+2
            else: #One assigned
                result=result+1
        else: #Not Assigned
            countTeacherAssigned=countTeacherAssigned-1
    result=result/countTeacherAssigned
    return result