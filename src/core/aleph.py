from pydantic import BaseModel
from typing import Type, TypeVar, Set, Union, Dict, ClassVar, List

import aleph_client.asynchronous as client
from aleph_client.chains.ethereum import get_fallback_account

FALLBACK_ACCOUNT = get_fallback_account()

T = TypeVar('T', bound='AlephRecord')


class AlephRecord(BaseModel):
    id: Union[str, int] = None
    item_hash: str = None
    current_revision: int = None
    revision_hashes: List[str] = None
    indices: ClassVar[Dict[str, 'AlephIndex']] = {}

    @property
    def content(self) -> Dict:
        """
        :return: content dictionary of the object, as it is to be stored on Aleph.
        """
        d = vars(self)
        del d['item_hash']
        del d['current_revision']
        del d['revision_hashes']
        del d['indices']
        return d

    async def update_revision_hashes(self: T):
        posts = await fetch_revisions(type(self), ref=self.item_hash)
        self.revision_hashes = [post['item_hash'] for post in posts]

    async def fetch_revision(self: T, rev_no: int = None, rev_hash: str = None) -> T:
        """
        Fetches a revision of the object by revision number (0 => original) or revision hash.
        :param rev_no: the revision number of the revision to fetch.
        :param rev_hash: the hash of the revision to fetch.
        """
        previous_revision = self.current_revision
        if rev_no is not None:
            if rev_no < 0:
                rev_no = len(self.revision_hashes) + rev_no
            if self.current_revision == rev_no:
                return self
            elif rev_no > len(self.revision_hashes):
                raise IndexError(f'No revision no. {rev_no} found for {self.item_hash}')
            else:
                self.current_revision = rev_no
        elif rev_hash is not None:
            try:
                self.current_revision = self.revision_hashes.index(rev_hash)
            except ValueError:
                raise IndexError(f'{rev_hash} is not a revision of {self.item_hash}')
        else:
            raise ValueError('Either rev or hash must be provided')

        if previous_revision != self.current_revision:
            self.__dict__.update((await fetch_records(type(self), item_hashes=[self.item_hash]))[0].__dict__)

        return self

    async def upsert(self) -> T:
        return await post_or_amend_object(self)

    @classmethod
    def create(cls: Type[T], **kwargs) -> T:
        obj = cls(**kwargs)
        return obj.upsert()

    @classmethod
    def query(cls: Type[T], key: str, index: str = 'item_hash') -> List[T]:
        return cls.indices[index].get_by_key(key)


class AlephIndex(AlephRecord):
    datatype: Type[AlephRecord]
    name: str
    hashmap: Dict[str, str] = {}

    @property
    async def items(self) -> List[AlephRecord]:
        return await fetch_records(self.datatype, list(self.hashmap.values()))

    async def get_by_key(self, key: str) -> AlephRecord:
        return (await fetch_records(self.datatype, [self.hashmap[key]]))[0]

    def add_item(self, key: str, item_hash: str):
        self.hashmap[key] = item_hash


class DatabaseSchema(AlephRecord):
    channel: str
    owner: str
    types: Set[Type[AlephRecord]]
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
        return await post_or_amend_object(self, account=self.owner, channel=self.channel)

    def add_type(self, type_: Type[AlephRecord]):
        if type_ in self.types():
            return
        self.types[type_.__name__] = type_
        name = type_.__name__ + '_id'
        self.indices[name] = AlephIndex(datatype=type_, name=name)


async def post_or_amend_object(obj: T, account=None, channel: str = None) -> T:
    """
    Posts or amends an object to Aleph. If the object is already posted, it's ref is updated.
    :param obj:
    :param account:
    :param channel:
    :return:
    """
    if account is None:
        account = FALLBACK_ACCOUNT
    name = type(obj).__name__
    resp = await client.create_post(account, obj.content, post_type=name, channel=channel, ref=obj.item_hash)
    obj.revision_hashes.append(resp['item_hash'])
    obj.current_revision = len(obj.revision_hashes) - 1
    return obj


async def fetch_records(datatype: Type[T],
                        item_hashes: List[str] = None,
                        channel: str = None,
                        owner: str = None) -> List[T]:
    """Retrieves posts as objects by its aleph item_hash.
    :param datatype: The type of the objects to retrieve.
    :param item_hashes: Aleph item_hashes of the objects to fetch.
    :param channel: Channel in which to look for it.
    :param owner: Account that owns the object."""
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    if item_hashes is None and channels is None and owners is None:
        raise ValueError('At least one of item_hashes, channel, or owner must be specified')
    objects_resp = await client.get_posts(hashes=item_hashes, channels=channels, types=[datatype.__name__],
                                          addresses=owners)
    objects = [datatype(**post['content']['content']) for post in objects_resp]
    return objects


async def fetch_revisions(datatype: Type[T],
                          ref: str,
                          channel: str = None,
                          owner: str = None) -> List[Dict]:
    """Retrieves posts of revisions of an object by its item_hash.
    :param datatype: The type of the objects to retrieve.
    :param ref: item_hash of the object, whose revisions to fetch.
    :param channel: Channel in which to look for it.
    :param owner: Account that owns the object."""
    channels = None if channel is None else [channel]
    owners = None if owner is None else [owner]
    return await client.get_posts(refs=[ref], channels=channels, types=[datatype.__name__], addresses=owners)
