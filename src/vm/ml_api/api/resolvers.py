from ariadne import ObjectType

query = ObjectType("Query")


@query.field("user")
def resolve_user(_, info):
    return info.context["user"]


user = ObjectType("User")


@user.field("username")
def resolve_username(obj, *_):
    return f'{obj.first_name} {obj.last_name}'