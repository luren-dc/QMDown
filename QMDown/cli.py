import logging
import re
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.align import Align
from rich.console import Group, RenderableType
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text
from rich_pyfiglet import RichFiglet
from typer import rich_utils

from QMDown import __version__, console
from QMDown.downloader import Downloader, DownloadTask
from QMDown.utils.async_typer import AsyncTyper

app = AsyncTyper(
    invoke_without_command=False,
    add_completion=False,
)


def handle_version(value: bool):
    if value:
        console.print(f"[green bold]QMDown [blue bold]{__version__}")
        raise typer.Exit()


def handle_no_color(value: bool):
    if value:
        console.no_color = value
        rich_utils.COLOR_SYSTEM = None


def handle_debug(value: bool):
    logging.basicConfig(
        level="DEBUG" if value else "INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                show_path=False,
                markup=True,
                rich_tracebacks=True,
                console=console,
            )
        ],
    )


def get_banner() -> RenderableType | None:
    title = RichFiglet(
        "QMDown",
        font="ansi_shadow",
        colors=["green"],
    )
    desc = Text("\n QQ 音乐解析/下载工具", style="bold blue")
    return Panel(
        Group(
            Align.center(title),
            Align.center(desc),
        ),
        box=box.SIMPLE,
    )


@app.callback()
async def main(
    no_color: Annotated[  # pyright: ignore[reportUnusedParameter]
        bool,
        typer.Option(
            "--no-color",
            help="禁用彩色输出",
            is_eager=True,
            callback=handle_no_color,
        ),
    ] = False,
    debug: Annotated[  # pyright: ignore[reportUnusedParameter]
        bool,
        typer.Option(
            "--debug",
            help="启用调试日志输出",
            is_eager=True,
            callback=handle_debug,
        ),
    ] = False,
    version: Annotated[  # pyright: ignore[reportUnusedParameter]
        bool,
        typer.Option(
            "-v",
            "--version",
            help="输出版本信息",
            is_eager=True,
            callback=handle_version,
        ),
    ] = False,
):
    """
    QQ 音乐解析/下载工具
    """
    if banner := get_banner():
        console.print(banner)


@app.command()
async def download(
    urls: Annotated[
        list[str],
        typer.Argument(
            help="歌曲或专辑的 URL(可包含其他字符)",
            metavar="URL",
            show_default=False,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="下载文件存储目录",
            resolve_path=True,
            show_default=False,
            file_okay=False,
        ),
    ] = None,
):
    """
    下载
    """
    pattern = re.compile(r"https?://\S+")
    valid_urls = set[str]()
    for value in urls:
        result = pattern.findall(value)
        if result:
            valid_urls.update(result)
    if not valid_urls:
        console.print("[red]未找到有效的 URL[/red]")
        raise typer.Exit(1)

    downloader = Downloader(
        output=output or Path.cwd(),
    )
    downloader.start()
    [downloader.add_task(DownloadTask(url=url)) for url in valid_urls]
    await downloader.add_stop_task()
    await downloader.wait_for_completion()


@app.command()
async def search(
    query: Annotated[
        str,
        typer.Argument(
            help="搜索关键词",
        ),
    ],
):
    """
    搜索
    """
    console.print(f"[blue]正在搜索: {query}...[/blue]")
