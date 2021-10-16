from dataclasses import *
from typing import Optional, Type
from datetime import datetime

import pandas as pd

import core.aleph as aleph


@dataclass
class AlephObject:
    ref: Optional[str]
    id: str

    def __dict__(self):
        d = super(self).__dict__
        del d['ref']
        return d


@dataclass
class Index(AlephObject):
    refs: dict
    datatype: Type[AlephObject]

    @property
    def items(self) -> {str: AlephObject}:
        return aleph.get_objects(self.datatype, self.refs.values())

    @property
    def is_root(self) -> bool:
        return self.datatype == type(self)


@dataclass
class Source(AlephObject):
    url: str


@dataclass
class Coin(AlephObject):
    symbol: str
    name: str
    cg_id: str  # internal
    logo_url: str
    cg_url: str  # internal
    other_urls: [str]  # internal
    dataseriesDesc_ids: [str]  # internal
    description: Optional[str]

    def __init__(self, *args):

        self.id

    @property
    def urls(self):
        return [self.cg_url].append(self.other_urls)

    @property
    def datasets(self):
        return aleph.get_dataseries_descs(self)


@dataclass
class Dataseries(AlephObject):  # internal class
    values: list
    index: list
    interval: str

    @property
    def series(self):
        return pd.Series(self.values, self.index)

    @series.setter
    def set_series(self, series: pd.Series):
        self.index = series.index.tolist()
        self.values = series.tolist()


@dataclass
class DataseriesDesc(AlephObject):
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

    def __init__(self, source: Source, coin: Coin, dataseries: Dataseries, title: str, description: str = None):
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
