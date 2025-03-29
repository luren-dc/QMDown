import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypedDict

from QMDown import console
from QMDown.models import Song, SongUrl
from QMDown.settings import QMDownSettings

logger = logging.getLogger("handler")


class Task(TypedDict):
    url: str
    songData: Song
    downloadUrl: SongUrl | None
    audioPath: Path | None
    coverPath: Path | None
    lyricPath: Path | None


class Context:
    def __init__(
        self,
        settings: QMDownSettings,
        urls: list[str],
        tasks: list[Task] = [],
    ):
        self.settings = settings
        self.urls = urls
        self.tasks = tasks
        self.current_handler: Handler | None = None


class Handler(ABC):
    _next_handler: "Handler|None" = None
    _console = console

    def set_next(self, handler: "Handler") -> "Handler":
        self._next_handler = handler
        return handler

    async def handle(self, ctx: Context) -> bool:
        ctx.current_handler = self
        if await self.process(ctx):
            return True
        if self._next_handler:
            return await self._next_handler.handle(ctx)
        return False

    @abstractmethod
    async def process(self, ctx: Context) -> bool:
        raise NotImplementedError

    def report_info(self, msg: str):
        logger.info(
            f"[blue bold][{self.__class__.__name__}][/] {msg}",
        )

    def report_error(self, msg: str):
        logger.error(
            f"[blue bold][{self.__class__.__name__}][/] {msg}",
        )
