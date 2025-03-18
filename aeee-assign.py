import multiprocessing
from pymoo.core.problem import starmap_parallelized_eval
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_crossover, get_mutation
from pymoo.optimize import minimize
from pymoo.visualization.scatter import Scatter
from pymoo.core.population import Population
from pymoo.factory import get_sampling
from multiprocessing import Process, Manager
from problem import ADEEProblem,AEEEFeacible,generate_ind
import datadb as data
import psycopg2
import sys

#Initialize
data.init(grade_input=sys.argv[1], iteration_input=sys.argv[2])

if __name__ == '__main__':
    mananger = Manager()
    q = mananger.Queue()
    
    #Init population on 10 group
    process=[]
    cp=10
    for i in range(0):
        print("Start group: "+str(i))
        for index in range(cp):
            print("Main    : create and start process %d." % index)
            p = Process(target=generate_ind, args=(index,q))
            process.append(p) 
            p.start()     
            
        for p in process:
            p.join()

        print("End group: "+str(i))

    pop_0=[]
    while not q.empty():
        pop_0.append(q.get())

    pop_0 = Population.new("X", pop_0)

    # the number of processes to be used for concurrent evaluation of fitness
    n_proccess = 10
    
    pool = multiprocessing.Pool(n_proccess)

    # define the problem by passing the starmap interface of the thread pool
    problem = ADEEProblem(runner=pool.starmap, func_eval=starmap_parallelized_eval)

    # Configure NSGA2 
    algorithm = NSGA2(pop_size=200,sampling=get_sampling('int_random'),
                crossover=get_crossover("int_exp"),
                mutation=get_mutation("int_pm"),
                repair=AEEEFeacible(),
                eliminate_duplicates=True)

    #Optimize
    res = minimize(problem,
                algorithm,
                ('n_gen', 200),
                seed=1,
                verbose=True)


    f = open("result.txt", "w")
    f.write("Time: %s" % res.exec_time)
    f.write("Best solution found:")
    f.write(str(res.X))
    f.write("Function value: %s" % res.F)
    f.write("Constraint violation: %s" % res.CV)
    f.close()

    print('Time:', res.exec_time)

    # Class
    conn = psycopg2.connect("host=" + data.HOST + ", dbname=" + data.DATABASE + " user=postgres password=" + data.PASS + " port=5432")
    cur = conn.cursor()
    sql = "insert into tesis_prd.resultados_py (fo1, fo2, fo3, grado, iteracion) values (%s,%s,%s,%s,%s)"


    print("Best solution found: {0}'".format(res.X) )
    print("Function value: {0}'".format(res.F))
    print("Constraint violation: {0}'" .format(res.CV))

    for i in res.F:
        cur.execute(sql, (i[0], i[1],i[2], data.GRADE, data.ITERATION))
        conn.commit()


    cur.close()
    conn.close()

    pool.close()

    plot = Scatter()
    plot.add(problem.pareto_front(), plot_type="line", color="black", alpha=0.7)
    plot.add(res.F, facecolor="none", edgecolor="red")
    plot.show()