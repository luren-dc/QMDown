import logging

from ..models import Song
from ._abc import Extractor
from .album import AlbumExtractor
from .singer import SingerExtractor
from .song import SongExtractor
from .songlist import SonglistExtractor
from .top import ToplistExtractor

__all__ = ["AlbumExtractor", "SingerExtractor", "SongExtractor", "SonglistExtractor", "ToplistExtractor"]

EXTRACTORS: list[Extractor] = [
    SongExtractor(),
    SonglistExtractor(),
    AlbumExtractor(),
    ToplistExtractor(),
    SingerExtractor(),
]

