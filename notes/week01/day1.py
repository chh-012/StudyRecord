'''
from functools import wraps

def timer(func):
    @wraps(func)  # 保留原函数元信息(__name__,__doc__)，工程必加
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        res = func(*args, **kwargs)
        print(f"耗时:{time.time()-start:.3f}s")
        return res
    return wrapper 

@timer
def add(a, b):
    return a + b
add(1,133)
'''
import time, functools

def metric(fn):
    @functools.wraps(fn)
    def wrapper(*args,**kwargs):
        start_time=time.time()
        res=fn(*args,**kwargs)
        end_time=time.time()
        print('%s executed in %s ms'%(fn.__name__,(end_time-start_time)*1000))
        return res
    return wrapper

# 测试
@metric
def fast(x, y):
    time.sleep(0.0012)
    return x + y;

@metric
def slow(x, y, z):
    time.sleep(0.1234)
    return x * y * z;

f = fast(11, 22)
s = slow(11, 22, 33)
if f != 33:
    print('测试失败!')
elif s != 7986:
    print('测试失败!')


