import multiprocessing
import time

def task(name:str,count:int):
    print(f"{name}-start\n",end='')
    result=0
    for n in range(count):
        result+=n+1
    time.sleep(1)
    print(f"{name}-end with:{result}")

def start_process1():
    process=multiprocessing.Process(target=task,args=('a',100))
    process.start()
    process.join()

def start_process2():
    args_list=[('a',100),('b',99),('c',98)]
    processes=[multiprocessing.Process(target=task,args=[name,count]) for name,count in args_list]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

if __name__=="__main__":
    start_process1()