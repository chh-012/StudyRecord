from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

tags_metadata=[
    {
        "name":"GET",
        "description":"所有查询接口"
    },
    {
        "name":"CREATE",
        "description":"新增数据接口"
    },
    {
        "name":"UPDATE",
        "description":"全量更新PUT、局部更新PATCH"
    },
    {
        "name":"DELETE",
        "description":"删除接口"
    }
]


app = FastAPI(title="Todo 内存CRUD接口", 
              description="简易待办接口，数据存在内存，重启丢失",
              openapi_tags=tags_metadata)

# 内存数据库
todo_db = [
    {"id": 1, "title": "学习FastAPI", "content": "完成CRUD接口", "is_done": False}
]
next_id = 2

# Pydantic模型：创建Todo用（输入校验）
class TodoCreate(BaseModel):
    title: str
    content: Optional[str] = None
    is_done: bool = False

# Pydantic模型：更新Todo用
class TodoUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_done: Optional[bool] = None

# 返回模型（输出结构）
class Todo(TodoCreate):
    id: int

@app.get('/')
def root():
    return {"msg:服务正常，请访问/docs进入接口文档"}

# 1. 获取全部Todo
@app.get("/todos", response_model=List[Todo], summary="查询所有待办", tags=["GET"])
def get_all_todos():
    return todo_db

# 2. 根据id获取单个Todo
@app.get("/todos/{todo_id}", response_model=Todo, summary="根据ID查询单个待办", tags=["GET"])
def get_todo(todo_id: int):
    for todo in todo_db:
        if todo["id"] == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="todo不存在")

# 3. 新增Todo POST
@app.post("/todos", response_model=Todo, summary="新增待办", tags=["CREATE"])
def create_todo(todo: TodoCreate):
    global next_id
    new_todo = {
        "id": next_id,
        "title": todo.title,
        "content": todo.content,
        "is_done": todo.is_done
    }
    todo_db.append(new_todo)
    next_id += 1
    return new_todo

# 4. PUT 全量更新Todo
@app.put("/todos/{todo_id}", response_model=Todo, summary="全量更新待办", tags=["UPDATE"])
def update_todo(todo_id: int, todo: TodoCreate):
    for item in todo_db:
        if item["id"] == todo_id:
            item["title"] = todo.title
            item["content"] = todo.content
            item["is_done"] = todo.is_done
            return item
    raise HTTPException(status_code=404, detail="todo不存在")

#5 Patch局部更新Todo
@app.patch('/todos/{todo_id}',response_model=Todo,summary="局部更新待办",tags=["UPDATE"])
def patch_todo(todo_id:int,todo:TodoUpdate):
    for item in todo_db:
        if item["id"]==todo_id:
            update_data=todo.model_dump(exclude_unset=True)
            for key,value in update_data.items():
                item[key]=value
            return item
    raise HTTPException(status_code=404, detail="todo不存在")

# 6. DELETE 删除Todo
@app.delete("/todos/{todo_id}", summary="删除待办", tags=["DELETE"])
def delete_todo(todo_id: int):
    global todo_db
    for idx, item in enumerate(todo_db):
        if item["id"] == todo_id:
            del todo_db[idx]
            return {"msg": "删除成功", "id": todo_id}
    raise HTTPException(status_code=404, detail="todo不存在")
