from pymoo.core.problem import ElementwiseProblem
import data
from constraint import validateConstraints
from geopy import distance
from random import randrange
from pymoo.core.repair import Repair
from objetivefunctions import f1,f2,f3

#Initialize
data.init(maxDistance=40)

class ADEEProblem(ElementwiseProblem):

    def __init__(self, **kwargs):
        super().__init__(n_var=data.CLASS_SIZE, n_obj=data.N_OBJ,
                         n_constr=data.N_CONSTR, xl=0, xu=data.TEACHER_SIZE-1, type_var=int,**kwargs)

    def _evaluate(self, x, out, *args, **kwargs):
        e=[f1(x), f2(x)*-1, f3(x)*-1]
        print(e)
        out["F"] = e #For minimization context, with multiply *-1 the max f2 and f3
        out["G"] = validateConstraints(x)

class AEEEFeacible(Repair):

    def _do(self, problem, pop, **kwargs):

        print("Start repair")

        # the packing plan for the whole population (each row one individual)
        Z = pop.get("X")

        # now repair each indvidiual zi
        for zi in range(len(Z)):
            # the packing plan for zi
            z = Z[zi]
            valid=validateConstraints(z)
            
            if valid[0]==0 and valid[1]==0 and valid[2]==0:
                continue            
            
            teachersOne=[]
            teachersZero=[]
            c=data.CLASS_SIZE
            for i in range(data.TEACHER_SIZE):                
                assign1=-1                
                assign2=-1            
                for j in range(len(z)):
                    if i==z[j]:
                        if assign1==-1:                           
                            assign1=j
                        elif assign2==-1:
                            if data.C[assign1][1]==data.C[j][1]:
                                z[j]=-1
                                c=c-1
                                continue
                            d=distance.distance((data.E[data.C[assign1][4]-1][1],data.E[data.C[assign1][4]-1][2]),
                                    (data.E[data.C[j][4]-1][1],data.E[data.C[j][4]-1][2])).kilometers       
                            if(d>data.Dmax):#Maximun distances exceeded
                                z[j]=-1
                                c=c-1
                                continue
                            assign2=j
                        else:
                            c=c-1    
                            z[j]=-1
                if assign1>-1 and assign2==-1: #Teacher with one assign
                    teachersOne.append({"pos":assign1,"teacher":i})
                elif assign1==-1:#Teacher don't assigned
                    teachersZero.append(i)

            while len(teachersOne)>0:
                indx=randrange(len(teachersOne)) #Select a Teacher randomly
                i=teachersOne[indx]   
                teachersOne.remove(i)    
                #Search another class for the same teacher that match all constraints with dist min between estableshment
                dist2_min=999999
                pos2_min=-1
                for j in range(data.CLASS_SIZE): 
                    if z[j]==-1:
                        if data.C[j][1]!=data.C[i['pos']][1]:
                            e1=data.C[j][4]-1
                            e2=data.C[i['pos']][4]-1
                            dist=distance.distance((data.E[e1][1],data.E[e1][2]),(data.E[e2][1],data.E[e2][2])).kilometers
                            if dist<=data.Dmax:
                                if dist<dist2_min:
                                    dist2_min=dist    
                                    pos2_min=j
                                    if e1==e2:
                                        break
                if pos2_min!=-1:
                   z[pos2_min]=i['teacher']
                   c=c+1                 
                if c==data.CLASS_SIZE:
                    break
            
            while(c<data.CLASS_SIZE and len(teachersZero)>0):
                indx=randrange(len(teachersZero)) #Select a Teacher randomly
                i=teachersZero[indx]   
                teachersZero.remove(i)                   
                dist_min=999999
                pos_min=-1
                for j in range(data.CLASS_SIZE):
                    if z[j]==-1:
                        e=data.C[j][4]-1
                        dist=distance.distance((data.E[e][1],data.E[e][2]),(data.D[i][1],data.D[i][2])).kilometers
                        if dist<dist_min:
                            dist_min=dist
                            pos_min=j
                z[pos_min]=i
                c=c+1
                if(c==data.CLASS_SIZE):
                    break

                #Search another class for the same teacher that match all constraints with dist min between estableshment
                dist2_min=999999
                pos2_min=-1
                for j in range(data.CLASS_SIZE): 
                    if z[j]==-1:
                        if data.C[j][1]!=data.C[pos_min][1]:
                            e1=data.C[j][4]-1
                            e2=data.C[pos_min][4]-1
                            dist=distance.distance((data.E[e1][1],data.E[e1][2]),(data.E[e2][1],data.E[e2][2])).kilometers
                            if dist<=data.Dmax:
                                if dist<dist2_min:
                                    dist2_min=dist    
                                    pos2_min=j
                                    if e1==e2:
                                        break
                if pos2_min!=-1:
                    z[pos2_min]=i
                    c=c+1   

        # set the design variables for the population
        pop.set("X", Z)
        print("End repair")
        return pop

def generate_ind(name,q): 
    print("Start generate ind "+str(name))
    ind=[-1]*data.CLASS_SIZE
    teachers=[]
    for i in range(data.TEACHER_SIZE):
        teachers.append(i)
    c=0
    while(c<data.CLASS_SIZE and len(teachers)>0):
        indx=randrange(len(teachers)) #Select a Teacher randomly
        i=teachers[indx]        
        teachers.remove(i)
        #print("Asignando docente: "+str(i)+" en hilo "+str(name)+". Disponibles: "+str(len(teachers)))
        dist_min=999999
        pos_min=-1
        for j in range(data.CLASS_SIZE):
            if ind[j]==-1:
                e=data.C[j][4]-1
                dist=distance.distance((data.E[e][1],data.E[e][2]),(data.D[i][1],data.D[i][2])).kilometers
                if dist<dist_min and dist<=data.Dmax:
                    dist_min=dist
                    pos_min=j
        if pos_min==-1:
            continue
        ind[pos_min]=i
        c=c+1
        if(c==data.CLASS_SIZE):
            break

        #Search another class for the same teacher that match all constraints with dist min between estableshment
        dist2_min=999999
        pos2_min=-1
        for j in range(data.CLASS_SIZE): 
            if ind[j]==-1:
                if data.C[j][1]!=data.C[pos_min][1]:
                    e1=data.C[j][4]-1
                    e2=data.C[pos_min][4]-1
                    dist=distance.distance((data.E[e1][1],data.E[e1][2]),(data.E[e2][1],data.E[e2][2])).kilometers
                    if dist<=data.Dmax:
                        if dist<dist2_min:
                            dist2_min=dist    
                            pos2_min=j
                            if e1==e2:
                                break
        if pos2_min!=-1:
            ind[pos2_min]=i
            c=c+1   
    print("Ind added by process: "+str(name))
    q.put(ind)