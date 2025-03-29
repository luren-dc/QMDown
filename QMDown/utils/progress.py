from asyncio import Lock
from typing import ClassVar

from QMDown import console
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TaskID, TextColumn, TransferSpeedColumn
from rich.table import Column


class DownloadProgress:

    DEFAULT_COLUMNS: ClassVar = {
        "description": TextColumn(
            "{task.description}[bold blue]{task.fields[filename]}",
            table_column=Column(ratio=2),
        ),
        "bar": BarColumn(bar_width=None, table_column=Column(ratio=3)),
        "percentage": TextColumn("[progress.percentage]{task.percentage:>4.1f}%"),
        "•": "•",
        "filesize": DownloadColumn(),
        "speed": TransferSpeedColumn(),
    }

    def __init__(self) -> None:
        self._download_progress = Progress(
            *self.DEFAULT_COLUMNS.values(),
            expand=True,
            console=console,
        )
        self._overall_progress = Progress(
            SpinnerColumn("moon"),
            TextColumn("[green]{task.description} [blue]{task.completed}/{task.total}"),
            BarColumn(bar_width=None),
            expand=True,
            console=console,
        )
        self._overall_task_id = self._overall_progress.add_task(
            "下载进度",
            visible=False,
        )
        self._live = Live(
            Group(
                self._overall_progress,
                Panel(self._download_progress),
            ),
            console=console,
            transient=True,
            refresh_per_second=10,
        )
        self._progress_lock = Lock()
        self._active_tasks: set[TaskID] = set()

    async def add_task(
        self,
        description: str,
        filename: str = "",
        start: bool = True,
        total: float | None = 100.0,
        completed: int = 0,
        visible: bool = True,
    ) -> TaskID:
        async with self._progress_lock:
            task_id = self._download_progress.add_task(
                description=description,
                start=start,
                total=total,
                completed=completed,
                visible=visible,
                filename=filename,
            )
            self._active_tasks.add(task_id)
            self._update_overall_progress()
            return task_id

    async def update(
        self,
        task_id: TaskID,
        total: float | None = None,
        completed: float | None = None,
        advance: float | None = None,
        description: str | None = None,
        visible: bool = True,
    ) -> None:
        async with self._progress_lock:
            update_kwargs = {
                "total": total,
                "completed": completed,
                "advance": advance or 0,
                "description": description,
                "visible": visible,
            }
            
            self._download_progress.update(task_id, **update_kwargs)
            
            if self._download_progress.tasks[task_id].finished:
                self._active_tasks.discard(task_id)
                self._update_overall_progress()

    def _update_overall_progress(self) -> None:
        """更新总进度条"""
        self._overall_progress.update(
            self._overall_task_id,
            total=len(self._download_progress.tasks),
            completed=len(self._download_progress.tasks) - len(self._active_tasks),
            visible=bool(self._download_progress.tasks),
        )

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()