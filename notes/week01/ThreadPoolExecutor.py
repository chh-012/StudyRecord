import time 
from concurrent.futures import ThreadPoolExecutor

def task(name:str,count:int):
    print(f"{name} - step1 \n", end='')
    time.sleep(1)
    print(f"{name} -step2 \n",end='')

    return f"{name} is completed"

with ThreadPoolExecutor() as executor:
    result1=executor.submit(task,'a',2)
    result2=executor.submit(task,'b',2)
    print(result1.result())
    print(result2.result())
