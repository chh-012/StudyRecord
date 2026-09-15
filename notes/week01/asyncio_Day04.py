import time
import asyncio
async def task1():
    print('task1开始')
    # time.sleep(5)  # 模拟耗时 5 秒的 I/O
    await asyncio.sleep(5)
    print('task1结束')
    return 10

async def task2():
    print('task2开始')
    # time.sleep(3)  # 模拟耗时 3 秒的 I/O
    await asyncio.sleep(3)
    print('task2结束')
    return 20

'''
# async def main():
#     print('main开始')
#     event_loop = asyncio.get_running_loop()  # 获取当前正在运行的事件循环
#     t1 = event_loop.create_task(task1())     # 手动注册任务
#     t2 = event_loop.create_task(task2())
#     result = await t1
#     print('result:', result)
#     result = await t2
#     print('result:', result)
#     print('main结束')

# if __name__ == '__main__':
#     start = time.time()
#     event_loop = asyncio.get_event_loop()    # 老式：创建事件循环
#     event_loop.run_until_complete(main())    # 老式：跑 main
#     print('总耗时:', time.time() - start)
'''

async def main():
    print('main开始')
    results=await asyncio.gather(task1(),task2())
    print(results)
    # t1 = asyncio.create_task(task1())
    # result=await t1
    # print(result)
    print('main结束')

if __name__ =="__main__":
    start=time.time()
    asyncio.run(main())
    print('总耗时:', time.time() - start)



