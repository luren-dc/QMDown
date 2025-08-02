import re
from abc import ABC, abstractmethod
from re import Pattern
from typing import Any, override

from rich.console import Console

from QMDown import console


class Extractor(ABC):
    _VALID_URL_RE: tuple[Pattern[str], ...]
    _VALID_URL: tuple[str, ...] | None = None
    _console: Console = console

    @classmethod
    def _match_valid_url(cls, url: str):
        if not cls._VALID_URL:
            return None
        if "_VALID_URL_RE" not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, cls._VALID_URL))
        return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)

    @classmethod
    def suitable(cls, url: str) -> bool:
        return cls._match_valid_url(url) is not None

    @classmethod
    def _match_id(cls, url: str):
        if match := cls._match_valid_url(url):
            return str(match.group("id"))
        raise ValueError("Url invalid")

    @abstractmethod
    async def extract(self, url: str) -> dict[str, Any] | list[dict[str, Any]] | None:  # pyright: ignore[reportExplicitAny]
        raise NotImplementedError

    def print(self, *args: Any):  # pyright: ignore[reportExplicitAny, reportAny]
        self._console.print(f"[[green]{self.__class__.__name__}[/]]", *args)


class SingleExtractor(Extractor, ABC):
    @abstractmethod
    @override
    async def extract(self, url: str) -> dict[str, Any] | None:  # pyright: ignore[reportExplicitAny]
        raise NotImplementedError


class BatchExtractor(Extractor, ABC):
    @abstractmethod
    @override
    async def extract(self, url: str) -> list[dict[str, Any]] | None:  # pyright: ignore[reportExplicitAny]
        raise NotImplementedError
