import os
import time
from contextlib import contextmanager

# @contextmanager
# def timer():
#     start_time=time.time()
#     try:
#         yield
#     finally:
#         end_time=time.time()
        
# with timer():
#     time.sleep(2)
# print(f'耗时:{end_time-start_time:.2f}s')

# class Timer():
#     def __init__(self):
#         self.elapsed=0
#     def __enter__(self):
#         self.start=time.time()
#         return self
#     def __exit__(self, exc_type, exc, tb):
#         self.end=time.time()
#         self.elapsed=self.end-self.start

# with Timer() as timer:
#     nums=[]
#     for n in range(1,100):
#         nums.append(n**2)

# print(timer.elapsed)

@contextmanager
def timer():
    class Timer():
        pass
    t=Timer()
    t.start=time.time()
    try:
        yield t
    finally:
        t.end=time.time()
        t.elapsed=t.end-t.start
        print(f'{t.elapsed:.6f}')

with timer() as t:
    nums=[]
    for n in range(1,100):
        nums.append(n**2)


