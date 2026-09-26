from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional


app=FastAPI(title="Todo 内存CRUD接口",
            description="简易待办接口，数据存在内存，重启丢失")

todo_db=[
    {"id":1,"title":"学习FastAPI","content": "完成CRUD接口", "is_done": False}   
]
next_id=2

class TodoCreate(BaseModel):
    title:str
    content:Optional[str]=None
    is_done:bool=False

class TodoUpdate(BaseModel):
    title:Optional[str]=None
    content:Optional[str]=None
    is_done:Optional[bool]=None

class Todo(TodoCreate):
    id:int

@app.get("/")
def root():
    return {"msg:服务正常,请访问/docs查看"}
# 1. 获取全部Todo
@app.get("/todos",response_model=list[Todo],summary="查询所有代办")
def get_all_todos():
    return todo_db

# 2. 根据id获取单个Todo
@app.get("/todos/{todo_id}",response_model=Todo,summary="查询部分代办")
def get_todo(todo_id:int):
    for todo in todo_db:
        if todo["id"]==todo_id:
            return todo
    raise HTTPException(status_code=404,detail="todo不存在")

# 3. 新增Todo POST
@app.post("/todos",response_model=Todo,summary="新增代办")
def create_todo(todo:TodoCreate):
    global next_id
    new_todo={
        "id":next_id,
        "title":todo.title,
        "content":todo.content,
        "is_done":todo.is_done
    }
    todo_db.append(new_todo)
    next_id+=1
    return new_todo

# 4. PUT 全量更新Todo
@app.put("/todos/{todo_id}",response_model=Todo,summary='全局更新todo')
def update_todo(todo_id:int,todo:TodoCreate):
    for item in todo_db:
        if item['id']==todo_id:
            item["title"] = todo.title
            item["content"] = todo.content
            item["is_done"] = todo.is_done
            return item
    raise HTTPException(status_code=404,detail='todo不存在')

#5 Patch局部更新Todo
@app.patch('/todos/{todo_id}',response_model=Todo,summary='局部更新')
def patch_todo(todo_id:int,todo:TodoCreate):
    for item in todo_db:
        if item['id']==todo_id:
            update_todo=todo.model_dump(exclude_unset=True)
            for key,value in update_todo.items():
                item[key]=value

# 6. DELETE 删除Todo
@app.delete('/todos/{todo_id}',summary='删除代办')
def delete_todo(todo_id:int):
    global todo_db
    for idx,item in enumerate(todo_db):
        if item['id']==todo_id:
            del todo_db[idx]
            return {"msg:删除id:{todo_id}成功"}
    raise HTTPException(status_code=404,detail="todo不存在")

