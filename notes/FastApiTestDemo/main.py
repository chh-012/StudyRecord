from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def hello_world2():
    return {"message": "Hello World 2"}

@app.get("/helloworld")
async def hello_world():
    return {"message": "Hello World123"}

if __name__ == "__main__":
    # 直接在py文件内部启动uvicorn服务
    uvicorn.run(app="main:app", reload=True)
