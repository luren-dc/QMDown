import logging
import re
from abc import ABC, abstractmethod

from QMDown import console
from QMDown.models import Song

logger = logging.getLogger("extractor")


class Extractor(ABC):
    _VALID_URL: tuple | None = None
    _console = console

    @classmethod
    def _match_valid_url(cls, url: str):
        if not cls._VALID_URL:
            return None
        if "_VALID_URL_RE" not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, cls._VALID_URL))
        return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)

    @classmethod
    def suitable(cls, url):
        return cls._match_valid_url(url) is not None

    @classmethod
    def _match_id(cls, url: str):
        if match := cls._match_valid_url(url):
            return str(match.group("id"))
        raise ValueError("Url invalid")

    @abstractmethod
    async def extract(self, url: str):
        raise NotImplementedError

    def report_info(self, msg: str):
        logger.info(
            f"[blue bold][{self.__class__.__name__}][/] {msg}",
        )

    def report_error(self, msg: str):
        logger.error(
            f"[blue bold][{self.__class__.__name__}][/] {msg}",
        )


class SingleExtractor(Extractor):
    @abstractmethod
    async def extract(self, url: str) -> Song | None:
        raise NotImplementedError


class BatchExtractor(Extractor):
    @abstractmethod
    async def extract(self, url: str) -> list[Song] | None:
        raise NotImplementedError
