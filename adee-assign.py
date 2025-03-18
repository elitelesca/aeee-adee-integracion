import multiprocessing
from pymoo.core.problem import starmap_parallelized_eval
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_crossover, get_mutation
from pymoo.optimize import minimize
from pymoo.visualization.scatter import Scatter
from pymoo.core.population import Population
from multiprocessing import Process, Manager
from problem import ADEEProblem,AEEEFeacible,generate_ind

if __name__ == '__main__':
    mananger = Manager()
    q = mananger.Queue()
    
    #Init population on 10 group
    process=[]
    cp=10
    for i in range(10):
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
    algorithm = NSGA2(pop_size=100,sampling=pop_0,
                crossover=get_crossover("int_exp"),
                mutation=get_mutation("int_pm"),
                repair=AEEEFeacible(),
                eliminate_duplicates=True)

    #Optimize
    res = minimize(problem,
                algorithm,
                ('n_gen', 100),
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


    print("Best solution found:" % res.X)
    print("Function value: %s" % res.F)
    print("Constraint violation: %s" % res.CV)

    pool.close()

    plot = Scatter()
    plot.add(problem.pareto_front(), plot_type="line", color="black", alpha=0.7)
    plot.add(res.F, facecolor="none", edgecolor="red")
    plot.show()