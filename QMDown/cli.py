import logging
from pathlib import Path
from typing import Annotated

import click
import typer
from qqmusic_api import Credential
from rich.table import Table
from typer import rich_utils

from QMDown import __version__, console
from QMDown.extractor import AlbumExtractor, SongExtractor, SonglistExtractor
from QMDown.model import Song
from QMDown.processor.downloader import AsyncDownloader
from QMDown.processor.handler import handle_cover, handle_login, handle_lyric, handle_metadata, handle_song_urls
from QMDown.utils.async_typer import AsyncTyper
from QMDown.utils.priority import SongFileTypePriority
from QMDown.utils.utils import get_real_url

app = AsyncTyper(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
    invoke_without_command=True,
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
    if value:
        logging.getLogger().setLevel(logging.DEBUG)


def parse_cookies(value: str | None) -> Credential | None:
    if value:
        if ":" in value:
            data = value.split(":")
            return Credential(
                musicid=int(data[0]),
                musickey=data[1],
            )
        raise typer.BadParameter("格式错误,将'musicid'与'musickey'使用':'连接")
    return None


def print_params(ctx: typer.Context):
    console.print("🌈 当前运行参数:", style="bold blue")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("参数项", style="bold cyan", width=20)
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
    console.print(table)
    console.print("🚀 开始执行下载任务...", style="bold blue")


@app.command()
async def cli(
    ctx: typer.Context,
    urls: Annotated[
        list[str],
        typer.Argument(
            help="QQ 音乐链接(支持多个链接)",
            show_default=False,
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
            rich_help_panel="[blue bold]Download[/] [green bold]下载",
        ),
    ] = Path.cwd(),
    num_workers: Annotated[
        int,
        typer.Option(
            "-n",
            "--num-workers",
            help="并发下载协程数量",
            rich_help_panel="[blue bold]Download[/] [green bold]下载",
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
                [str(_.value) for _ in SongFileTypePriority],
            ),
            rich_help_panel="[blue bold]Download[/] [green bold]下载",
        ),
    ] = str(SongFileTypePriority.MP3_128.value),
    overwrite: Annotated[
        bool,
        typer.Option(
            "-w",
            "--overwrite",
            help="覆盖已存在文件",
            rich_help_panel="[blue bold]Download[/] [green bold]下载",
        ),
    ] = False,
    lyric: Annotated[
        bool,
        typer.Option(
            "--lyric",
            help="下载原始歌词文件",
            rich_help_panel="[blue bold]Lyric[/] [green bold]歌词",
        ),
    ] = False,
    trans: Annotated[
        bool,
        typer.Option(
            "--trans",
            help="下载双语翻译歌词(需配合`--lyric`使用)",
            rich_help_panel="[blue bold]Lyric[/] [green bold]歌词",
        ),
    ] = False,
    roma: Annotated[
        bool,
        typer.Option(
            "--roma",
            help="下载罗马音歌词(需配合`--lyric`使用)",
            rich_help_panel="[blue bold]Lyric[/] [green bold]歌词",
        ),
    ] = False,
    no_embed_lyric: Annotated[
        bool,
        typer.Option(
            "--no-embed-lyric",
            help="禁用歌词文件嵌入",
            rich_help_panel="[blue bold]Lyric[/] [green bold]歌词",
        ),
    ] = False,
    no_metadata: Annotated[
        bool,
        typer.Option(
            "--no-metadata",
            help="禁用元数据添加",
            rich_help_panel="[blue bold]Metadata[/] [green bold]元数据",
        ),
    ] = False,
    no_cover: Annotated[
        bool,
        typer.Option(
            "--no-cover",
            help="禁用专辑封面嵌入",
            rich_help_panel="[blue bold]Metadata[/] [green bold]元数据",
        ),
    ] = False,
    cookies: Annotated[
        str | None,
        typer.Option(
            "-c",
            "--cookies",
            help="QQ音乐Cookie凭证(从浏览器开发者工具获取 `musicid` 和 `musickey`,拼接为 `musicid:musickey` 格式)",
            metavar="MUSICID:MUSICKEY",
            show_default=False,
            rich_help_panel="[blue bold]Authentication[/] [green bold]认证管理",
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
            rich_help_panel="[blue bold]Authentication[/] [green bold]认证管理",
            show_default=False,
        ),
    ] = None,
    load: Annotated[
        Path | None,
        typer.Option(
            "--load",
            help="加载 Cookies 文件路径",
            rich_help_panel="[blue bold]Authentication[/] [green bold]认证管理",
            resolve_path=True,
            dir_okay=False,
            show_default=False,
        ),
    ] = None,
    save: Annotated[
        Path | None,
        typer.Option(
            "--save",
            help="持久化 Cookies 文件路径",
            rich_help_panel="[blue bold]Authentication[/] [green bold]认证管理",
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
        bool | None,
        typer.Option(
            "--debug",
            help="启用调试日志输出",
            is_eager=True,
            callback=handle_debug,
        ),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option(
            "-v",
            "--version",
            help="输出版本信息",
            is_eager=True,
            callback=handle_version,
        ),
    ] = None,
):
    """
    QQ 音乐解析/下载工具
    """
    print_params(ctx)

    if (cookies, login, load).count(None) < 1:
        raise typer.BadParameter("选项 '--credential' , '--login' 或 '--load' 不能共用")

    # 登录
    credential = await handle_login(cookies, login, load, save)

    data = await get_song_data(urls, int(quality), credential)

    if len(data) == 0:
        raise typer.Exit()

    logging.info(f"[blue][歌曲][/] 开始下载 总共 {len(data)} 首")

    song_downloader = AsyncDownloader(
        save_dir=output,
        num_workers=num_workers,
        no_progress=no_progress,
        overwrite=overwrite,
    )

    for song in data:
        if song.url:
            path = await song_downloader.add_task(
                url=song.url.url,
                file_name=song.info.get_full_name(),
                file_suffix=song.url.type.e,
            )
            song.path = path

    await song_downloader.execute_tasks()

    logging.info("[blue][歌曲][green bold] 下载完成")

    if not no_metadata:
        await handle_metadata(data)

    if not no_cover:
        await handle_cover(data, output, num_workers, overwrite)

    if lyric:
        await handle_lyric(data, output, no_embed_lyric, num_workers, overwrite, trans, roma)


async def get_song_data(urls: list[str], max_quality: int, credential: Credential | None):
    extractors = [SongExtractor(), SonglistExtractor(), AlbumExtractor()]
    song_data: list[Song] = []
    with console.status("解析链接中...") as status:
        for url in urls:
            # 获取真实链接(如果适用)
            original_url = url
            if "c6.y.qq.com/base/fcgi-bin" in url:
                url = await get_real_url(url) or url
                if url == original_url:
                    logging.info(f"[blue][Extractor][/] 获取真实链接失败: {original_url}")
                    continue
                logging.info(f"{original_url} -> {url}")

            # 尝试用提取器解析链接
            for extractor in extractors:
                if extractor.suitable(url):
                    try:
                        songs = await extractor.extract(url)
                        if isinstance(songs, list):
                            song_data.extend(songs)
                        else:
                            song_data.append(songs)
                    except Exception as e:
                        logging.error(f"[blue bold][{extractor.__class__.__name__}][/] {e}", exc_info=True)
                    break
            else:
                logging.info(f"Not Supported: {url}")
        # 歌曲去重
        mids = list({item.mid: item for item in song_data}.values())

        if len(mids) == 0:
            raise typer.Exit()

        # 获取歌曲链接
        status.update(f"[green]获取歌曲链接中[/] 共{len(mids)}首...")
        data = await handle_song_urls(mids, max_quality, credential)

        logging.info(f"[red]获取歌曲链接成功: {len(data)}/{len(mids)}")

        s_mids = [song.info.mid for song in data]
        f_data = [song for song in song_data if song.mid not in s_mids]
        if len(f_data) > 0:
            logging.info(f"[red]获取歌曲链接失败: {[song.get_full_name() for song in f_data]}")

    return data


if __name__ == "__main__":
    app()
