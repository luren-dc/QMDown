import logging
import re
from pathlib import Path
from typing import Annotated

import click
import typer
from rich.logging import RichHandler
from rich.table import Table
from typer import rich_utils

from QMDown import __version__, console
from QMDown.handler import DownloadHandler, LoginHandler, MetaDataHandler, ParseUrlHandler
from QMDown.handler._abc import Context
from QMDown.settings import (
    QMDownBasicSettings,
    QMDownLoginSettings,
    QMDownLyricSettings,
    QMDownMetadataSettings,
    QMDownSettings,
)
from QMDown.utils.async_typer import AsyncTyper
from QMDown.utils.priority import SongFileTypePriority

app = AsyncTyper(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
    invoke_without_command=True,
)


def search_url(values: list[str]) -> tuple:
    pattern = re.compile(r"https?:\/\/[^\s]+")
    url = set()
    for value in values:
        result = pattern.findall(value)
        if result:
            url.update(result)
    return tuple(url)


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


def callback_cookies(value: str | None):
    if value:
        if ":" not in value:
            raise typer.BadParameter("格式错误, 正确格式:'musicid(uin):musickey(qqmusic_key)'")
    return value


def print_params(ctx: typer.Context):
    console.print("🌈 当前运行参数:", style="blue")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("参数项", style="cyan", width=20)
    table.add_column("配置值", style="yellow", overflow="fold")
    sensitive_params = {"cookies"}
    for name, value in ctx.params.items():
        if value is None:
            continue

        if name in sensitive_params and value:
            display_value = f"{value[:4]}****{value[-4:]}" if isinstance(value, str) else "****"
        else:
            if isinstance(value, Path):
                display_value = f"{value.resolve()}"
            elif isinstance(value, list):
                display_value = "\n".join([f"{_}" for _ in value]) if value else "空列表"
            else:
                display_value = str(value)

        if isinstance(value, bool):
            display_value = f"[{'bold green' if value else 'bold red'}]{display_value}[/]"
        elif isinstance(value, int):
            display_value = f"[bold blue]{display_value}[/]"
        param_name = f"--{name.replace('_', '-')}"
        table.add_row(param_name, display_value)
    console.print(table, "🚀 开始执行下载任务...", style="bold blue")


@app.command()
async def cli(
    ctx: typer.Context,
    urls: Annotated[
        list[str],
        typer.Argument(
            help="支持多个链接,可混杂其他文本",
            show_default=False,
            callback=search_url,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "-o",
            "--output",
            help="下载文件存储目录",
            resolve_path=True,
            file_okay=False,
            rich_help_panel="Download 下载",
        ),
    ] = Path.cwd(),
    num_workers: Annotated[
        int,
        typer.Option(
            "-n",
            "--num-workers",
            help="并发下载协程数量",
            rich_help_panel="Download 下载",
            min=1,
        ),
    ] = 8,
    quality: Annotated[
        str,
        typer.Option(
            "-q",
            "--quality",
            help="首选音频品质",
            click_type=click.Choice(
                [str(_.name) for _ in SongFileTypePriority],
                case_sensitive=False,
            ),
            rich_help_panel="Download 下载",
        ),
    ] = SongFileTypePriority.MP3_128.name,
    overwrite: Annotated[
        bool,
        typer.Option(
            "-w",
            "--overwrite",
            help="覆盖已存在文件",
            rich_help_panel="Download 下载",
        ),
    ] = False,
    max_retries: Annotated[
        int,
        typer.Option(
            "-r",
            "--max-retries",
            help="下载失败重试次数",
            rich_help_panel="Download 下载",
            min=0,
        ),
    ] = 3,
    timeout: Annotated[
        int,
        typer.Option(
            "-t",
            "--timeout",
            help="下载超时时间",
            rich_help_panel="Download 下载",
            min=0,
        ),
    ] = 15,
    lyric: Annotated[
        bool,
        typer.Option(
            "--lyric",
            help="启用下载歌词功能",
            rich_help_panel="Lyric 歌词",
        ),
    ] = False,
    trans: Annotated[
        bool,
        typer.Option(
            "--trans",
            help="下载双语翻译歌词",
            rich_help_panel="Lyric 歌词",
        ),
    ] = False,
    roma: Annotated[
        bool,
        typer.Option(
            "--roma",
            help="下载罗马音歌词",
            rich_help_panel="Lyric 歌词",
        ),
    ] = False,
    no_embed_lyric: Annotated[
        bool,
        typer.Option(
            "--no-embed-lyric",
            help="禁用歌词文件嵌入",
            rich_help_panel="Lyric 歌词",
        ),
    ] = False,
    no_del_lyric: Annotated[
        bool,
        typer.Option(
            "--no-del-lyric",
            help="禁用清除已嵌入歌词文件",
            rich_help_panel="Lyric 歌词",
        ),
    ] = False,
    no_metadata: Annotated[
        bool,
        typer.Option(
            "--no-metadata",
            help="禁用元数据添加",
            rich_help_panel="Metadata 元数据",
        ),
    ] = False,
    no_cover: Annotated[
        bool,
        typer.Option(
            "--no-cover",
            help="禁用专辑封面嵌入",
            rich_help_panel="Metadata 元数据",
        ),
    ] = False,
    cookies: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--cookies",
            help="Cookies 凭证",
            metavar="UIN:QQMUSIC_KEY",
            show_default=False,
            rich_help_panel="Authentication 认证管理",
            callback=callback_cookies,
        ),
    ] = None,
    login: Annotated[
        str | None,
        typer.Option(
            "--login",
            help="第三方登录方式",
            click_type=click.Choice(
                ["QQ", "WX", "PHONE"],
                case_sensitive=False,
            ),
            rich_help_panel="Authentication 认证管理",
            show_default=False,
        ),
    ] = None,
    load: Annotated[
        Path | None,
        typer.Option(
            "--load",
            help="加载 Cookies 文件路径",
            rich_help_panel="Authentication 认证管理",
            resolve_path=True,
            dir_okay=False,
            exists=True,
            show_default=False,
        ),
    ] = None,
    save: Annotated[
        Path | None,
        typer.Option(
            "--save",
            help="持久化 Cookies 文件路径",
            rich_help_panel="Authentication 认证管理",
            resolve_path=True,
            dir_okay=False,
            writable=True,
            show_default=False,
        ),
    ] = None,
    no_progress: Annotated[
        bool,
        typer.Option(
            "--no-progress",
            help="禁用进度条显示",
        ),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            help="禁用彩色输出",
            is_eager=True,
            callback=handle_no_color,
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="启用调试日志输出",
            is_eager=True,
            callback=handle_debug,
        ),
    ] = False,
    version: Annotated[
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
    if (cookies, login, load).count(None) < 1:
        raise typer.BadParameter("选项 '--credential' , '--login' 或 '--load' 不能共用")

    if not urls:
        raise typer.BadParameter("未获取到有效链接")

    print_params(ctx)

    settings = QMDownSettings(
        basic=QMDownBasicSettings(
            num_workers=num_workers,
            overwrite=overwrite,
            max_retries=max_retries,
            output=output,
            timeout=timeout,
            quality=SongFileTypePriority[quality].value,
            debug=bool(debug),
            no_color=bool(no_color),
            no_progress=no_progress,
        ),
        login=QMDownLoginSettings(
            cookies=cookies,
            login_type=login,
            load_path=load,
            save_path=save or load,
        ),
        lyric=QMDownLyricSettings(
            enabled=lyric,
            trans=trans,
            roma=roma,
            embed_lyric=not no_embed_lyric,
            del_lyric=not no_del_lyric,
        ),
        metadata=QMDownMetadataSettings(
            enabled=not no_metadata,
            embed_cover=not no_cover,
        ),
    )

    handler = LoginHandler()
    handler.set_next(ParseUrlHandler()).set_next(DownloadHandler()).set_next(MetaDataHandler())
    await handler.handle(Context(urls=urls, settings=settings))


if __name__ == "__main__":
    app()
