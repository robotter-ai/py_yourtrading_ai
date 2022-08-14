from dataclasses import *
from typing import Optional
from datetime import datetime

import pandas as pd

import core.aleph as aleph


@dataclass
class Source(aleph.Record):
    url: str


@dataclass
class Coin(aleph.Record):
    symbol: str
    name: str
    cg_id: str  # internal
    logo_url: str
    cg_url: str  # internal
    other_urls: [str]  # internal
    dataseriesDesc_refs: [aleph.AlephRef]  # internal
    description: Optional[str]

    def __init__(self, *args):

        self.id

    @property
    def urls(self):
        return [self.cg_url].append(self.other_urls)

    @property
    def datasets(self):
        refs = [desc.ref for desc in self.dataseriesDesc_refs]
        return aleph.fetch_records(DataseriesDesc, refs)


@dataclass
class Dataseries(aleph.Record):  # internal class
    values: list
    index: list
    interval: str

    @property
    def series(self):
        return pd.Series(self.values, self.index)

    @series.setter
    def series(self, value: pd.Series):
        self.index = value.index.tolist()
        self.values = value.tolist()


@dataclass
class DataseriesDesc(aleph.Record):
    sourceID: str
    coinID: str
    dataseriesID: str  # internal
    title: str
    interval: str
    count: int
    mean: float
    std: float
    min: float
    max: float
    firstDate: datetime
    lastDate: datetime
    description: Optional[str]
    sparkline: [float]

    def __init__(self, id: str, source: Source, coin: Coin, dataseries: Dataseries, title: str,
                 description: str = None):
        super(self).__init__(id)
        assert source.ref
        self.sourceID = source.ref
        assert coin.id
        self.coinID = coin.id
        assert dataseries.ref
        self.dataseriesID = dataseries.ref
        self.title = title
        self.interval = dataseries.interval
        series = dataseries.series
        self.count = series.count()
        self.mean = series.mean()
        self.std = series.std()
        self.min = series.min()
        self.max = series.max()
        self.firstDate = series.index.min()
        self.lastDate = series.index.max()
        self.description = description
        self.sparkline = series[-100:].values.tolist()


async def get_sources() -> [Source]:
    return aleph.get_all_objects_from_lookup(Source)


async def get_coins() -> [Coin]:
    return aleph.get_all_objects_from_lookup(Coin)
