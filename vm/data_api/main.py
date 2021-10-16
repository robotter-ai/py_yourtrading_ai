from ariadne import make_executable_schema
from ariadne.asgi import GraphQL
from vm.data_api.api import type_defs, resolvers


schema = make_executable_schema(type_defs, [resolvers.query])
app = GraphQL(schema, debug=True)
