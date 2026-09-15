
'''
print("1024*768=" +str(1024*768))

name=input('please enter your name:' )
print('hello',name)

s2 = 'Hello, \'Adam\''
print(s2)

s3 = r'Hello, "Bart"'
print(s3) 

mike=ord('a')
print(mike)

print('hello,%s,你有多少钱:%d' %('mike',123))
'''

'''

print('%2d-%02d' % (3, 1))
print('%.2f' % 3.1415926)

print('hello,{0},你的成绩是{1:.2f}'.format('xiaoming',89.765))
print('hello,%s,你的成绩是:%.2f' %('小明',89.875))

r=2.5
s=3.14*r**2
print(f'the aire of a circle with redius {r} is {s}')
'''

'''
s1=72
s2=85
r=(s2-s1)/s1*100
print(f'小明的成绩提升了{(s2-s1)/s1*100:.2f}%')
#print(f'小明的成绩提升了{r:.2f}%')
'''

'''
classmates=['Michael', 'Bob', 'Tracy']
classmates.append('mike')
print(classmates)
classmates.pop(0)
print(classmates)
classmates.insert(0,'jack')
print(classmates)
print(classmates[0])
'''

'''
t=(1,)
print(t)
tuple=('a','b',['X','Y'])
print(tuple)
tuple[2][0]='z'
print(tuple)
'''

'''
birth=int(input('birth is:'))
if birth>18:
    print('adult')
else:
    print('kid')
'''

'''
L = ['Bart', 'Lisa', 'Adam']
for l in L:
    print(l)

i=0
while i<len(L):
    print(L[i])
    i=i+1
'''

'''
from day1 import gettotal
print(gettotal(1,2))

def my_abs(x):
    if not isinstance(x, (int, float)):
        raise TypeError('bad operand type')
    if x >= 0:
        return x
    else:
        return -x

print(my_abs('-56'))

'''

'''
import math
def quadratic(a, b, c):
    if (math.sqrt(b**2-4*a*c))<0:
        return 
    x1=(-b+math.sqrt(b**2-4*a*c))/(2*a)
    x2=(-b-math.sqrt(b**2-4*a*c))/(2*a)
    return x1,x2

print('quadratic(2, 3, 1) =', quadratic(2, 3, 1))
print('quadratic(1, 3, -4) =', quadratic(1, 3, -4))

if quadratic(2, 3, 1) != (-0.5, -1.0):
    print('测试失败')
elif quadratic(1, 3, -4) != (1.0, -4.0):
    print('测试失败')
else:
    print('测试成功')
'''

'''
nums=[1,2,3]
def calc(*nums):
    sum=0
    for x in nums:
        sum=sum+x
    return sum
print(calc(*nums))
'''

def mul(*nums):
    sum=1
    for x in nums:
        sum=sum*x
    return sum

# 测试
print('mul(5) =', mul(5))
print('mul(5, 6) =', mul(5, 6))
print('mul(5, 6, 7) =', mul(5, 6, 7))
print('mul(5, 6, 7, 9) =', mul(5, 6, 7, 9))
if mul(5) != 5:
    print('mul(5)测试失败!')
elif mul(5, 6) != 30:
    print('mul(5, 6)测试失败!')
elif mul(5, 6, 7) != 210:
    print('mul(5, 6, 7)测试失败!')
elif mul(5, 6, 7, 9) != 1890:
    print('mul(5, 6, 7, 9)测试失败!')
else:
    try:
        mul()
        print('mul()测试失败!')
    except TypeError:
        print('测试成功!')
