from ariadne import ObjectType

import core.aleph as aleph

query = ObjectType("Query")


@query.field("sources")
async def resolve_sources(_, info):
    return await aleph.get_sources()


@query.field("coins")
async def resolve_coins(_, info):
    return await aleph.get_coins()
