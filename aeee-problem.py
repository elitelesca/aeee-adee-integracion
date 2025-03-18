from pymoo.core.problem import ElementwiseProblem
import datadb as data
from constraint import validateConstraints
from geopy import distance
from random import randrange
from pymoo.core.repair import Repair
from objetivefunctions import f1,f2,f3


class ADEEProblem(ElementwiseProblem):

    def __init__(self, **kwargs):
        super().__init__(n_var=data.PERSON_SIZE, n_obj=data.N_OBJ,
                         n_constr=0, xl=0, xu=data.CLASS_SIZE-1, type_var=int,**kwargs)

    def _evaluate(self, x, out, *args, **kwargs):
        e=[f1(x), f2(x), f3(x)*-1]
        print(e)
        out["F"] = e #For minimization context, with multiply *-1
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
            
            if valid[0]==0 and valid[1]==0:
                continue


            for j in range(len(z)):
                class_index = z[j]
                # if the student is assigned to a diferent grade
                if data.P[j][3] != data.C[class_index][0]:
                    z[j] = -1
                    continue

            #searh over the students with not assignments
            for j in range(len(z)):


                if z[j]==-1:
                    class_index = randrange(data.CLASS_SIZE)
                    z[j] = class_index


       # set the design variables for the population
        pop.set("X", Z)
        print("End repair")
        return pop

def generate_ind(name,q): 
    print("Start generate ind "+str(name))
    ind=[-1]*data.PERSON_SIZE



    for j in range(data.PERSON_SIZE):
        indx = randrange(data.CLASS_SIZE)
        ind[j] = indx


    print("Ind added by process: "+str(name))
    q.put(ind)