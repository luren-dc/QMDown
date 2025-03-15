import asyncio
import logging
from pathlib import Path

import httpx
import typer
from anyio import open_file
from qqmusic_api import Credential
from qqmusic_api.login import (
    PhoneLoginEvents,
    QRCodeLoginEvents,
    QRLoginType,
    check_qrcode,
    get_qrcode,
    phone_authorize,
    send_authcode,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from QMDown import api, console
from QMDown.model import Song, SongData
from QMDown.processor.downloader import AsyncDownloader
from QMDown.utils.priority import get_priority
from QMDown.utils.tag import Metadata, add_cover_to_audio, write_lyric, write_metadata
from QMDown.utils.utils import safe_filename, show_qrcode
from settings import QMDownSettings


class QMDownHandler:
    def __init__(self, settings: QMDownSettings):
        self.settings = settings

    async def handle_login(self) -> Credential | None:
        credential = await self._handle_cookie_login(self.settings.login.cookies, self.settings.login.load_path)
        if credential:
            return await self._finalize_credential(
                credential, self.settings.login.load_path, self.settings.login.save_path
            )

        if not self.settings.login.login_type:
            return None

        login_type = self.settings.login.login_type.lower()
        if login_type in ("qq", "wx"):
            credential = await self._qr_code_login(login_type)
        elif login_type == "phone":
            credential = await self._phone_login()
        else:
            raise ValueError(f"不支持的登录方式: {login_type}")

        return await self._finalize_credential(credential, self.settings.login.load_path, self.settings.login.save_path)

    async def _qr_code_login(self, login_type: str) -> Credential | None:
        logging.info(f"[blue][二维码登录] [red]{login_type.upper()}")
        with console.status("获取二维码中...") as status:
            qrcode = await get_qrcode(login_type=QRLoginType(login_type))
            status.stop()
            show_qrcode(qrcode.data)
            status.update(f"[red]请使用[blue] {login_type.upper()} [red]扫描二维码登录")
            status.start()

            while True:
                state, credential = await check_qrcode(qrcode)

                if state == QRCodeLoginEvents.DONE:
                    status.stop()
                    logging.info(f"[blue][{login_type.upper()}][green]登录成功")
                    return credential
                if state in (QRCodeLoginEvents.REFUSE, QRCodeLoginEvents.TIMEOUT):
                    error_msg = "二维码登录被拒绝" if state == QRCodeLoginEvents.REFUSE else "二维码登录超时"
                    logging.warning(f"[blue][{login_type.upper()}][yellow]{error_msg}")
                    raise typer.Exit(code=1)
                if state == QRCodeLoginEvents.SCAN:
                    await asyncio.sleep(5)  # 5秒轮询一次
                else:
                    await asyncio.sleep(2)

    async def _phone_login(self) -> Credential:
        phone = typer.prompt("请输入手机号", type=int)

        with console.status("获取验证码中...") as status:
            while True:
                state, auth_url = await send_authcode(phone)
                if state == PhoneLoginEvents.SEND:
                    logging.info("[blue][手机号登录][red]验证码发送成功")
                    break
                if state == PhoneLoginEvents.CAPTCHA:
                    logging.info("[blue][手机号登录][red]需要滑块验证")
                    if not auth_url:
                        logging.warning("[blue][手机号登录][yellow]获取验证链接失败")
                        raise typer.Exit(code=1)
                    console.print(f"[red]请复制链接前往浏览器验证:[/]\n{auth_url}")
                    status.stop()
                    typer.confirm("验证后请回车", prompt_suffix="", show_default=False)
                    status.start()
                else:
                    logging.warning("[blue][手机号登录][yellow]登录失败(未知情况)")
                    raise typer.Exit(code=1)

        code = typer.prompt("请输入验证码", type=int)
        try:
            return await phone_authorize(phone, code)
        except Exception:
            logging.warning("[blue][手机号登录][yellow]验证码错误或已过期")
            raise typer.Exit(code=1)

    async def _handle_cookie_login(self, cookies: str | None, cookies_load_path: Path | None) -> Credential | None:
        if cookies:
            if ":" not in cookies:
                raise typer.BadParameter("格式错误,将'musicid'与'musickey'使用':'连接")
            data = cookies.split(":")
            return Credential(musicid=int(data[0]), musickey=data[1])

        if cookies_load_path:
            return Credential.from_cookies_str(await (await open_file(cookies_load_path)).read())
        return None

    async def _finalize_credential(
        self, credential: Credential | None, cookies_load_path: Path | None, cookies_save_path: Path | None
    ) -> Credential | None:
        if credential:
            if await credential.is_expired():
                logging.warning("[yellow]Cookies 已过期,正在尝试刷新...")
                if not await credential.refresh():
                    logging.warning("[yellow]Cookies 刷新失败")
                    return None
                logging.info("[green]Cookies 刷新成功")

                if cookies_load_path and cookies_load_path.exists():
                    cookies_save_path = cookies_load_path

                if cookies_save_path:
                    logging.info(f"[green]保存 Cookies 到: {cookies_save_path}")
                    await (await open_file(cookies_save_path, "w")).write(credential.as_json())

            user = await api.get_user_detail(euin=credential.encrypt_uin, credential=credential)
            user_info = user["Info"]["BaseInfo"]
            logging.info(f"[blue][Cookies][/] 当前登录账号: [red]{user_info['Name']}({credential.musicid})")

        return credential

    async def handle_song_urls(
        self,
        songs: list[Song],
        max_quality: int,
        credential: Credential | None,
    ) -> list[SongData]:
        qualities = get_priority(max_quality)
        pending_mids = [song.mid for song in songs]
        data: list[SongData] = []
        for current_quality in qualities:
            if not pending_mids:
                break

            try:
                batch_urls = await api.get_download_url(
                    mids=pending_mids,
                    quality=current_quality,
                    credential=credential,
                    timeout=self.settings.basic.timeout,
                )

                url_map = {url.mid: url for url in batch_urls if url.url}
                new_pending_mids = []
                for mid in pending_mids:
                    if mid in url_map:
                        song_data = next(s for s in songs if s.mid == mid)
                        data.append(SongData(info=song_data, url=url_map[mid]))
                    else:
                        new_pending_mids.append(mid)
                logging.info(f"[blue][{current_quality.name}]:[/] 获取成功数量: {len(url_map)}/{len(pending_mids)}")
                pending_mids = new_pending_mids
            except Exception as e:
                logging.error(f"[blue][{current_quality.name}]:[/] {e}", exc_info=True)
                continue

        return data

    async def handle_metadata(self, data: list[SongData]):
        if not self.settings.metadata.enabled:
            logging.info("[blue][元数据][/] 元数据添加已禁用")
            return

        logging.info("[blue][元数据][/] 开始添加元数据")

        async def _add(data: SongData):
            if not data.path:
                return

            song_task = asyncio.create_task(api.get_song_detail(data.info.mid))
            album_task = (
                asyncio.create_task(api.get_album_detail(mid=data.info.album.mid)) if data.info.album.mid else None
            )

            song = await song_task
            track_info = song.track_info

            metadata: Metadata = {
                "title": [track_info.title],
                "artist": [s.name for s in track_info.singer],
            }
            if song.company:
                metadata["copyright"] = song.company
            if song.genre:
                metadata["genre"] = song.genre

            if track_info.index_album:
                metadata["tracknumber"] = [str(track_info.index_album)]
            if track_info.index_cd:
                metadata["discnumber"] = [str(track_info.index_cd)]

            # 处理专辑信息
            if album_task:
                album = await album_task
                metadata.update(
                    {
                        "album": [album.info.name],
                        "albumartist": [s.name for s in album.singer],
                    }
                )

            # 处理发行时间
            if song.time_public and song.time_public[0]:
                metadata["date"] = [str(song.time_public[0])]
            logging.debug(f"[blue][元数据][/] {data.path}: {metadata}")
            await write_metadata(data.path, metadata)

        with console.status("添加元数据中..."):
            await asyncio.gather(*[_add(song) for song in data])
        logging.info("[blue][元数据][green] 元数据添加完成")

    async def handle_cover(self, data: list[SongData], downloader: AsyncDownloader):
        if not self.settings.metadata.embed_cover:
            logging.info("[blue][封面][/] 专辑封面嵌入已禁用")
            return

        # 下载封面
        logging.info("[blue][封面][/] 开始下载专辑封面")

        for song in data:
            if song.path and song.path.exists():
                if mid := song.info.album.mid or song.info.album.pmid:
                    song.cover = await downloader.add_task(
                        url=f"https://y.gtimg.cn/music/photo_new/T002R500x500M000{mid}.jpg",
                        file_name=song.info.get_full_name(),
                        file_suffix=".jpg",
                    )

        await downloader.execute_tasks()

        logging.info("[blue][封面][green] 专辑封面下载完成")

        logging.info("[blue][封面][/] 开始嵌入专辑封面")
        with console.status("嵌入封面中..."):
            await asyncio.gather(
                *[add_cover_to_audio(song.path, song.cover) for song in data if song.path and song.cover]
            )
        logging.info("[blue][封面][green] 专辑封面嵌入完成")

    async def handle_lyric(self, data: list[SongData], save_dir: str | Path = "."):
        if not self.settings.lyric.enabled:
            logging.info("[blue][歌词][/] 歌词下载已禁用")
            return

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        semaphore = asyncio.Semaphore(self.settings.basic.num_workers)

        @retry(
            stop=stop_after_attempt(self.settings.basic.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        )
        async def download_lyric(song: SongData):
            """下载歌词并保存到文件"""
            async with semaphore:
                if not song.path or not song.path.exists():
                    return None

                song_name = song.info.get_full_name()
                lyric_path = save_dir / safe_filename(f"{song.info.get_full_name()}.lrc")

                if not self.settings.basic.overwrite and lyric_path.exists():
                    logging.info(f"[blue][歌词][/] [red]跳过 [cyan]{lyric_path.name}[/] [/]- 歌词已存在")
                    return lyric_path

                try:
                    lyric = await api.get_lyric(
                        mid=song.info.mid, trans=self.settings.lyric.trans, roma=self.settings.lyric.roma
                    )
                except Exception as e:
                    logging.error(f"[blue][歌词][/] [cyan]{song_name}[/] - 下载歌词出错: {e}", exc_info=True)
                    return None

                if not lyric.lyric:
                    logging.warning(f"[blue][歌词][/] [cyan]{song_name}[/] - 未找到歌词")
                    return None

                async with await open_file(lyric_path, "w") as f:
                    await f.write(lyric.get_parser().dump())

                if not self.settings.lyric.embed_lyric:
                    logging.info(f"[blue][歌词][/] 已保存: [cyan]{lyric_path.name}")

                return lyric_path if self.settings.lyric.embed_lyric else None

        async def embed_lyric(song: SongData, lyric_path: Path):
            """嵌入歌词到音频文件"""
            async with semaphore:
                if not song.path or not song.path.exists() or not lyric_path.exists():
                    return

                logging.debug(f"[blue][歌词][/] 正在嵌入歌词: [cyan]{song.info.get_full_name()}")
                async with await open_file(lyric_path, "r") as f:
                    await write_lyric(song.path, await f.read())
                logging.debug(f"[blue][歌词][/] 歌词嵌入成功: [cyan]{song.info.get_full_name()}")
                if self.settings.lyric.del_lyric:
                    lyric_path.unlink(missing_ok=True)

        logging.info("[blue][歌词][/] 开始下载歌词")

        with console.status("[blue]下载歌词中...[/]"):
            lyric_results = await asyncio.gather(*[download_lyric(song) for song in data])

        logging.info("[blue][歌词][/] [green]歌词下载完成")

        if self.settings.lyric.embed_lyric:
            logging.info("[blue][歌词][/] 开始嵌入歌词")

            with console.status("[blue]嵌入歌词中...[/]"):
                await asyncio.gather(
                    *[embed_lyric(song, lyric_path) for song, lyric_path in zip(data, lyric_results) if lyric_path]
                )

            logging.info("[blue][歌词][/] [green]歌词嵌入完成")
