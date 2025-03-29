import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import httpx
from rich.progress import TaskID
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from QMDown import console
from QMDown.models import DownloadTask
from QMDown.utils.progress import DownloadProgress
from QMDown.utils.utils import safe_filename


class AsyncDownloader:
    DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB
    MAX_CHUNK_SIZE = 1024 * 1024  # 1MB
    RETRY_EXCEPTIONS = (
        httpx.RequestError,
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
        anyio.ClosedResourceError,
    )

    def __init__(
        self,
        save_dir: str | Path = ".",
        num_workers: int = 3,
        disable_progress: bool = False,
        retries: int = 3,
        timeout: int = 15,
        overwrite: bool = False,
    ):
        self.save_dir = Path(save_dir)
        self.max_concurrent = num_workers
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(num_workers)
        self.download_tasks: list[DownloadTask] = []
        self.active_paths = set()
        self.progress = DownloadProgress()
        self.disable_progress = disable_progress
        self.retrying = AsyncRetrying(
            stop=stop_after_attempt(retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(self.RETRY_EXCEPTIONS),
        )
        self.overwrite = overwrite
        self._client = httpx.AsyncClient(timeout=timeout)

    @asynccontextmanager
    async def get_client(self):
        """HTTP客户端上下文管理"""
        try:
            yield self._client
        finally:
            await self._client.aclose()

    async def _fetch_file_size(self, client: httpx.AsyncClient, url: str) -> int:
        """获取文件大小并处理异常"""
        async for attempt in self.retrying:
            with attempt:
                try:
                    response = await client.head(url)
                    response.raise_for_status()
                    return int(response.headers.get("Content-Length", 0))
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logging.warning(f"获取文件大小失败: {e!s}")
        return 0

    async def _cleanup_failed_download(self, path: Path) -> None:
        """清理失败下载的残留文件"""
        if await anyio.Path(path).exists():
            await anyio.Path(path).unlink()
            logging.debug(f"已清理残留文件: {path.name}")

    async def download_file(self, client: httpx.AsyncClient, task_id: TaskID, url: str, full_path: Path):
        try:
            async for attempt in self.retrying:
                with attempt:
                    try:
                        self.save_dir.mkdir(parents=True, exist_ok=True)
                        content_length = await self._fetch_file_size(client, url)

                        await self.progress.update(
                            task_id,
                            description=f"[blue][{full_path.suffix}]",
                            completed=0,
                            total=content_length,
                        )

                        async with client.stream("GET", url) as response:
                            response.raise_for_status()
                            async with await anyio.open_file(full_path, "wb") as f:
                                chunk_size = self.DEFAULT_CHUNK_SIZE
                                async for chunk in response.aiter_bytes(chunk_size):
                                    chunk_size = min(chunk_size * 2, self.MAX_CHUNK_SIZE)
                                    await f.write(chunk)
                                    await self.progress.update(
                                        task_id,
                                        advance=len(chunk),
                                    )
                        logging.info(f"下载完成: {full_path.name}")
                        return True
                    except Exception as e:
                        await self._cleanup_failed_download(full_path)
                        logging.error(f"第 {attempt.retry_state.attempt_number} 次下载失败: {e!s}")
                        await self.progress.update(task_id, completed=0)
                        raise
        except RetryError as e:
            last_exception = e.last_attempt.exception()
            logging.error(f"歌曲下载失败: {full_path.name},错误原因: {last_exception!s}")
            return False

    async def add_task(self, url: str, file_name: str, file_suffix: str) -> Path | None:
        async with self.semaphore:
            file_path = safe_filename(f"{file_name}{file_suffix}")
            full_path = self.save_dir / file_path

            if not self.overwrite and full_path.exists():
                logging.info(f"跳过已存在文件: {file_path}")
                return None

            if full_path in self.active_paths:
                logging.info(f"任务已存在: {file_path}")
                return None

            self.active_paths.add(full_path)
            task_id = await self.progress.add_task(
                description="[等待]",
                filename=file_name,
                visible=not self.disable_progress,
            )

            self.download_tasks.append(
                DownloadTask(
                    id=task_id,
                    url=url,
                    file_name=file_name,
                    file_suffix=file_suffix,
                    full_path=full_path,
                )
            )
            return full_path

    async def execute_tasks(self):
        """执行所有下载任务"""
        if not self.download_tasks:
            return None

        context = console.status("下载中...") if self.disable_progress else self.progress

        async with self.get_client() as client:
            with context:
                results = await asyncio.gather(
                    *[self.download_file(client, task.id, task.url, task.full_path) for task in self.download_tasks],
                    return_exceptions=True,
                )
        self.download_tasks.clear()
        return results
