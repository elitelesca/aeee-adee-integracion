import data
from geopy import distance

#Compute all restrictions
#One teacher with up to two classes with different shifts 
def validateConstraints(X):    
    valid_c1=0
    valid_c2=0
    valid_c3=0
    n_c=len(data.C)
    for j in range(n_c):
        c=1
        for l in range(n_c):
            if(j!=l and X[j]==X[l]):
                c=c+1
                if(c>2):#More than 2 assigs
                    valid_c1=1    
                    break                
                if(data.C[j][1]==data.C[l][1]):#Not Same shifts
                    valid_c2=1          
                    break
                d=distance.distance((data.E[data.C[j][4]-1][1],data.E[data.C[j][4]-1][2]),
                                    (data.E[data.C[l][4]-1][1],data.E[data.C[l][4]-1][2])).kilometers       
                if(d>data.Dmax):#Maximun distances exceeded
                    valid_c3=1
                    break
            
    return [valid_c1,valid_c2,valid_c3]