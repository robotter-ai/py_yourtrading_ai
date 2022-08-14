from typing import Type, Set

from src.aars import Record, fetch_records, Index


class DatabaseSchema(Record):
    channel: str
    owner: str
    types: Set[Type[Record]]
    version: int = 1

    @classmethod
    async def fetch_schema(cls, channel: str, owner: str, version: int = None) -> 'DatabaseSchema':
        """
        Fetches a schema from Aleph, which can be used to access active records.
        :param channel: The channel to fetch from
        :param owner: Address of the owner of the schema. It must be supplemented, as anyone can upload a schema for your channel.
        :param version: The version of the schema to fetch. If None, will fetch the latest
        :return: Instance of AARSSchema
        """
        schemas = (await fetch_records(datatype=cls, channel=channel, owner=owner))
        if version is None:
            schemas.sort(key=lambda x: x.version)
            return schemas[-1]
        else:
            return next(filter(lambda x: x.version == version, schemas), None)

    async def upsert(self: T) -> T:
        """Upgrades and uploads the schema to the next version."""
        schema = await self.fetch_schema(channel=self.channel, owner=self.owner)
        if schema is not None:
            self.version = schema.version + 1
        return self

    def add_type(self, type_: Type[Record]):
        if type_ in self.types():
            return
        self.types[type_.__name__] = type_
        name = type_.__name__ + '_id'
        self.indices[name] = Index(datatype=type_, name=name)
