from typing_extensions import override

from QMDown.extractor import EXTRACTORS
from QMDown.models import Song
from QMDown.utils.utils import get_real_url

from ._abc import Context, Handler, Task


class ParseUrlHandler(Handler):
    @override
    async def process(self, ctx: Context) -> bool:
        with self._console.status("解析链接中..."):
            for url in ctx.urls:
                original_url = url
                if "c6.y.qq.com/base/fcgi-bin" in url:
                    url = await get_real_url(url) or url
                    if url == original_url:
                        self.report_info(f"获取真实链接失败: {original_url}")
                        continue
                    self.report_info(f"链接跳转: {original_url} -> {url}")
                if songs := await self._extract(url):
                    if isinstance(songs, list):
                        ctx.tasks.extend(
                            [
                                Task(
                                    **{
                                        "url": url,
                                        "songData": song,
                                        "downloadUrl": None,
                                        "audioPath": None,
                                        "coverPath": None,
                                        "lyricPath": None,
                                    }
                                )
                                for song in songs
                            ]
                        )
                    else:
                        ctx.tasks.append(
                            Task(
                                **{
                                    "url": url,
                                    "songData": songs,
                                    "downloadUrl": None,
                                    "audioPath": None,
                                    "coverPath": None,
                                    "lyricPath": None,
                                }
                            )
                        )
            return False

    async def _extract(self, url: str) -> None | list[Song] | Song:
        for extractor in EXTRACTORS:
            if not extractor.suitable(url):
                continue
            try:
                return await extractor.extract(url)
            except Exception as e:
                self.report_error(f"{extractor.__class__.__name__}: {e!s}")
                continue
        else:
            self.report_info(f"不支持的类型: {url}")
            return None
