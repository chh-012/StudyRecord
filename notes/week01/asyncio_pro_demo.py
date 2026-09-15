import time
import asyncio
from asyncio.exceptions import TimeoutError

async def play_music(music:str):
    print(f"start playing {music}")
    await asyncio.sleep(3)
    print(f"finished playing {music}")
    return music

async def call_api():
    print(f"call api.............")
    raise ValueError("not found")

#cancel取消
async def my_cancel():
    task=asyncio.create_task(play_music("A"))
    await asyncio.sleep(1)
    if not task.done():
        task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("任务A被取消")

#超时取消（默认，会杀掉task）
async def my_timeout1():
    task=asyncio.create_task(play_music('B'))
    try:
        await asyncio.wait_for(task,timeout=2)
    except TimeoutError:
        print("timeout")

#超时但是不取消（shield保护）
async def my_timeout2():
    task=asyncio.create_task(play_music('c'))
    try:
        await asyncio.wait_for(asyncio.shield(task),timeout=2)
    except TimeoutError:
        print("timeout")
        await task

#gather
async def my_gather():
    results=await asyncio.gather(play_music('Aa'),play_music('Bb'))
    print(results)

#gather with error
async def my_gather_with_error():
    results=await asyncio.gather(play_music('Aa'),play_music('Bb'),call_api(),return_exceptions=True)
    print(results)

if __name__=='__main__':
    asyncio.run(my_gather_with_error())
