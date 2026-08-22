from fastapi import FastAPI
from src.users.router import user

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "DH!"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


app.include_router(user)
