import asyncio
from dataclasses import dataclass
from queue import Queue
from typing import Any

from QMDown import console
from QMDown.extractor import Extractor, SongExtractor
from QMDown.extractor.album import AlbumExtractor
from QMDown.extractor.singer import SingerExtractor
from QMDown.extractor.songlist import SonglistExtractor
from QMDown.extractor.top import ToplistExtractor


@dataclass
class DownloadTask:
    url: str


class Downloader:
    queue: Queue[DownloadTask | None] = Queue()

    def __init__(self, **kwargs: Any):  # pyright: ignore[reportExplicitAny, reportAny]
        self.extractors: list[Extractor] = []
        self.options: dict[str, Any] = kwargs  # pyright: ignore[reportExplicitAny]
        self.loop_task: asyncio.Task[None] | None = None

    def start(self):
        self.loop_task = asyncio.create_task(self.loop())

    def add_task(self, task: DownloadTask):
        if self.loop_task is None:
            raise RuntimeError("Task manager is not started.")
        self.queue.put(task)

    async def wait_for_completion(self):
        if self.loop_task is None:
            raise RuntimeError("Task manager is not started.")
        if self.loop_task.done():
            return
        await self.loop_task
        self.queue.join()

    async def add_stop_task(self):
        self.queue.put(None)

    async def stop(self):
        if self.loop_task is None:
            raise RuntimeError("Task manager is not started.")
        if self.loop_task.done():
            return
        while not self.queue.empty():
            self.queue.task_done()
        self.queue.join()

    async def loop(self):
        while True:
            task = self.queue.get()
            try:
                if task is None:
                    break
                await self.process_task(task)
            finally:
                self.queue.task_done()

    def _setup_extractors(self):
        if self.extractors:
            return
        self.extractors = [
            SongExtractor(),
            SonglistExtractor(),
            AlbumExtractor(),
            SingerExtractor(),
            ToplistExtractor(),
        ]

    async def process_task(self, task: DownloadTask):
        self._setup_extractors()
        data = None
        for extractor in self.extractors:
            if extractor.suitable(task.url):
                data = await extractor.extract(task.url)
                break

        if data is None:
            console.print("[red]不支持的 URL:[/]", task.url)
