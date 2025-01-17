import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import anyio
import httpx
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from QMDown import console


@dataclass()
class DownloadTask:
    """下载任务数据类

    Args:
        url: 文件 URL。
        filename: 保存的文件名。
    """

    url: str
    filename: str
    filepath: Path


class AsyncDownloader:
    """异步文件下载器。

    支持动态任务管理、下载过程中添加 Hook 回调、并发控制。
    """

    def __init__(
        self,
        save_dir: str | Path = "downloads",
        num_workers: int = 8,
        no_progress: bool = True,
        retries: int = 3,
        timeout: int = 10,
    ):
        """
        Args:
            save_dir: 文件保存目录。
            max_concurrent: 最大并发下载任务数。
            retries: 每个任务的最大重试次数。
            timeout: 每个请求的超时时间(秒)。
            no_progress: 是否显示进度。
            on_start: 下载开始时的回调函数。
            on_complete: 下载完成时的回调函数。
            on_error: 下载失败时的回调函数。
        """
        self.save_dir = Path(save_dir)
        self.max_concurrent = num_workers
        self.retries = retries
        self.timeout = timeout
        self.task_queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(num_workers)
        self.progress = Progress(
            TextColumn(
                "[bold blue]{task.fields[filename]}[/] {task.description}",
                justify="right",
            ),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            disable=no_progress,
        )
        self.no_progress = no_progress

    async def add_task(self, url: str, filename: str):
        """向队列中添加一个下载任务。

        Args:
            url: 文件 URL。
            filename: 保存的文件名。
        """
        task = DownloadTask(url, filename, self.save_dir / filename)
        await self.task_queue.put(task)
        logging.debug(f"Task added: {url} -> {task.filename}")

    async def worker(self, client: httpx.AsyncClient):
        """队列工作者,从任务队列中提取并执行下载任务。

        Args:
            client: 用于发送请求的 HTTP 客户端。
        """
        while True:
            task = await self.task_queue.get()
            if task is None:  # 停止信号
                break
            await self.download(client, task)
            self.task_queue.task_done()

    async def download(self, client: httpx.AsyncClient, task: DownloadTask):
        """下载单个文件任务。

        Args:
            client: 用于发送请求的 HTTP 客户端。
            task: 下载任务对象。
        """
        task_id = self._initialize_task(task)

        if self._is_task_skipped(task, task_id):
            return

        for attempt in range(1, self.retries + 1):
            async with self.semaphore:
                try:
                    self.progress.start_task(task_id)

                    total = await self._fetch_file_size(client, task, task_id)
                    await self._download_file(client, task, task_id, total)

                    return
                except Exception as e:
                    self._handle_retry(task, task_id, attempt, e)

    def _initialize_task(self, task: DownloadTask):
        return self.progress.add_task(
            description="",
            filename=task.filename[:8] if len(task.filename) > 8 else task.filename,
            start=False,
        )

    def _is_task_skipped(self, task: DownloadTask, task_id: TaskID) -> bool:
        if task.filepath.exists():
            logging.debug(f"Skipped: {task.url} -> {task.filename}")
            self.progress.remove_task(task_id)
            logging.info(f"[blue]{task.filename}[/] [red]已存在")
            return True
        return False

    async def _fetch_file_size(self, client: httpx.AsyncClient, task: DownloadTask, task_id: TaskID) -> int:
        response = await client.head(task.url, timeout=self.timeout)
        if response.status_code != 200:
            raise httpx.RequestError(f"HTTP {response.status_code}")
        total = int(response.headers.get("Content-Length", 0))
        self.progress.update(task_id, total=total)
        return total

    async def _download_file(self, client: httpx.AsyncClient, task: DownloadTask, task_id: TaskID, total: int):
        self.save_dir.mkdir(parents=True, exist_ok=True)
        async with client.stream("GET", task.url, timeout=self.timeout) as response:
            if response.status_code != 200:
                raise httpx.RequestError(f"HTTP {response.status_code}")
            async with await anyio.open_file(task.filepath, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 5):
                    await f.write(chunk)
                    self.progress.update(task_id, advance=len(chunk))
        logging.debug(f"Downloaded: {task.url} -> {task.filename}")

    def _handle_retry(self, task: DownloadTask, task_id: TaskID, attempt: int, error: Exception):
        self.progress.update(
            task_id,
            description=f"[yellow]Retry {attempt}/{self.retries}...",
        )
        logging.warning(f"Failed attempt {attempt} for {task.url}: {error}")
        if attempt == self.retries:
            self.progress.update(task_id, description="[red]Failed")
            logging.error(f"Failed: {task.url} -> {task.filename}: {error}")

    async def run(self, headers=None):
        """启动下载器处理队列中的任务。

        Args:
            headers: 自定义请求头(如 User-Agent)
        """
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:

            async def _run():
                workers = [asyncio.create_task(self.worker(client)) for _ in range(self.max_concurrent)]
                # 持续运行直到手动停止或任务完成
                await self.task_queue.join()

                # 停止所有工作者
                for _ in range(self.max_concurrent):
                    await self.task_queue.put(None)
                await asyncio.gather(*workers)

            if self.no_progress:
                with console.status("下载歌曲中..."):
                    await _run()
            else:
                with self.progress:
                    await _run()

            logging.info("下载完成")
