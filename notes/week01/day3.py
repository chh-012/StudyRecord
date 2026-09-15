'''
def trim(s):
    l=0
    r=len(s)-1
    while l<=r and s[l]==' ':
        l+=1
    while l<=r and s[r]==' ':
        r-=1
    return s[l:r+1]

# 测试:
if trim('hello  ') != 'hello':
    print('测试失败!')
elif trim('  hello') != 'hello':
    print('测试失败!')
elif trim('  hello  ') != 'hello':
    print('测试失败!')
elif trim('  hello  world  ') != 'hello  world':
    print('测试失败!')
elif trim('') != '':
    print('测试失败!')
elif trim('    ') != '':
    print('测试失败!')
else:
    print('测试成功!')
'''

'''
def findMinAndMax(L):
    if len(L)==0:
        return (None, None) 
    min=L[0]
    max=L[0]
    for x in L:
        if(x<=min):
            min=x
        if(x>=max):
            max=x
    return (min,max)

# 测试
if findMinAndMax([]) != (None, None):
    print('测试失败!')
elif findMinAndMax([7]) != (7, 7):
    print('测试失败!')
elif findMinAndMax([7, 1]) != (1, 7):
    print('测试失败!')
elif findMinAndMax([7, 1, 3, 9, 5]) != (1, 9):
    print('测试失败!')
else:
    print('测试成功!')
'''

'''
print([x*x for x in range(1,11) if x%2==0])
print([m + n for m in 'asd' for n in 'qwe'])

#dict
d = {'x': 'A', 'y': 'B', 'z': 'C' }
for k, v in d.items():
    print(k, 'and', v)
'''

'''
L1 = ['hello', 'world', 18, 'apple', None]
L2 = [ x for x in L1 if isinstance(x,str)]

# 测试:
print(L2)
if L2 == ['hello', 'world', 'apple']:
    print('测试通过!')
else:
    print('测试失败!')
'''

'''
def fib(x):
    n,a,b=0,0,1
    while n<x:
        yield b
        a,b=b,a+b
        n=n+1
    return

g=fib(5)
print(next(g))
print(next(g))
'''

'''
def triangles():
    L=[1]
    while True:
        yield L
        L=[1]+[ L[i]+L[i+1] for i in range(len(L)-1)]+[1]



# 期待输出:
# [1]
# [1, 1]
# [1, 2, 1]
# [1, 3, 3, 1]
# [1, 4, 6, 4, 1]
# [1, 5, 10, 10, 5, 1]
# [1, 6, 15, 20, 15, 6, 1]
# [1, 7, 21, 35, 35, 21, 7, 1]
# [1, 8, 28, 56, 70, 56, 28, 8, 1]
# [1, 9, 36, 84, 126, 126, 84, 36, 9, 1]
n = 0
results = []
for t in triangles():
    results.append(t)
    n = n + 1
    if n == 10:
        break

for t in results:
    print(t)

if results == [
    [1],
    [1, 1],
    [1, 2, 1],
    [1, 3, 3, 1],
    [1, 4, 6, 4, 1],
    [1, 5, 10, 10, 5, 1],
    [1, 6, 15, 20, 15, 6, 1],
    [1, 7, 21, 35, 35, 21, 7, 1],
    [1, 8, 28, 56, 70, 56, 28, 8, 1],
    [1, 9, 36, 84, 126, 126, 84, 36, 9, 1]
]:
    print('测试通过!')
else:
    print('测试失败!')
'''

'''
def abs(x):
    if x>=0:
        return x
    else:
        return -x

def add(x,y,f):
    return f(x)+f(y)

x=-5
y=-6
f=abs
print(add(-5, 6, abs))
'''

#print(list(map(str, [1, 2, 3, 4, 5, 6, 7, 8, 9])))

'''
def normalize(name):
    return name[0].upper()+name[1:].lower()
# 测试:
L1 = ['adam', 'LISA', 'barT']
L2 = list(map(normalize, L1))
print(L2)

from functools import reduce
def prod(L):
    i=0
    sum=1
    while i<len(L):
        sum*=L[i]
        i+=1
    return sum

print('3 * 5 * 7 * 9 =', prod([3, 5, 7, 9]))
if prod([3, 5, 7, 9]) == 945:
    print('测试成功!')
else:
    print('测试失败!')
'''

'''
from functools import reduce
def str2float(s):
    def char2num(ch):
        digits = {'0':0, '1':1, '2':2, '3':3, '4':4,
                  '5':5, '6':6, '7':7, '8':8, '9':9}
        return digits[ch]

    def fn(x, y):
        return x * 10 + y

    # 找到小数点位置
    dot_idx = s.index('.')
    # 整数部分字符串
    int_part = s[:dot_idx]
    # 小数部分字符串
    dec_part = s[dot_idx+1:]

    # reduce算出整数部分
    integer = reduce(fn, map(char2num, int_part))
    # reduce算出小数部分：456 → 0.456
    decimal = reduce(fn, map(char2num, dec_part)) / (10 ** len(dec_part))

    return integer + decimal
print('str2float(\'123.456\') =', str2float('123.456'))
if abs(str2float('123.456') - 123.456) < 0.00001:
    print('测试成功!')
else:
    print('测试失败!')
'''

'''
def is_palindrome(n):
    s=str(n)
    return s==s[::-1]

# 测试:
output = filter(is_palindrome, range(1, 1000))
print('1~1000:', list(output))
if list(filter(is_palindrome, range(1, 200))) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33, 44, 55, 66, 77, 88, 99, 101, 111, 121, 131, 141, 151, 161, 171, 181, 191]:
    print('测试成功!')
else:
    print('测试失败!')
'''

#def is_odd(n):
 #   return n % 2 == 1

L = list(filter(lambda x:x%2==1,range(1, 20)))

print(L)





