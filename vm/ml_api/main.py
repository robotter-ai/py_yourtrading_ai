from ariadne import ObjectType, make_executable_schema
from ariadne.asgi import GraphQL
from api import type_defs, resolvers

schema = make_executable_schema(type_defs, [query, user])
app = GraphQL(schema, debug=True)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/classification/lightgbm", )
async def train_lightgbm():
