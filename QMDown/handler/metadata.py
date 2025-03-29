import asyncio
from typing import cast

from typing_extensions import override

from QMDown.api import get_song_metadata
from QMDown.utils.downloader import AsyncDownloader
from QMDown.utils.metadata import Metadata, set_audio_cover, set_metadata

from ._abc import Context, Handler, Task


class MetaDataHandler(Handler):
    @override
    async def process(self, ctx: Context) -> bool:
        settings = ctx.settings.metadata
        if not settings.enabled:
            return False
        self.report_info("添加歌曲元数据...")
        await asyncio.gather(*[self._set_matedata(task) for task in ctx.tasks])
        self.report_info("歌曲元数据添加完成")

        self.downloader = AsyncDownloader(
            save_dir=ctx.settings.basic.output,
            num_workers=ctx.settings.basic.num_workers,
            disable_progress=ctx.settings.basic.no_progress,
            timeout=ctx.settings.basic.timeout,
            overwrite=ctx.settings.basic.overwrite,
            retries=ctx.settings.basic.max_retries,
        )

        self.report_info("专辑封面下载中...")
        await self._download_cover(ctx.tasks)
        self.report_info("专辑封面下载完成")

        if not settings.embed_cover:
            return False

        self.report_info("嵌入专辑封面...")
        await asyncio.gather(
            *[
                set_audio_cover(task["audioPath"], task["coverPath"])
                for task in ctx.tasks
                if task["audioPath"] and task["coverPath"]
            ]
        )
        self.report_info("专辑封面嵌入完成")
        return False

    async def _set_matedata(self, task: Task):
        if audio := task["audioPath"]:
            if not audio.exists():
                return
            song = task["songData"]
            metadata = cast(Metadata, await get_song_metadata(song.mid, song.album.mid))
            await set_metadata(audio, metadata)
        else:
            return

    async def _download_cover(self, tasks: list[Task]):
        for task in tasks:
            if audio := task["audioPath"]:
                if not audio.exists():
                    return
                song = task["songData"]
                pic = None
                if song.singer[0].mid:
                    pic = f"T001R800x800M000{song.singer[0].mid}"
                if song.vs[1]:
                    pic = f"T062R800x800M000{song.vs[1]}"
                if song.album.mid:
                    pic = f"T002R800x800M000{song.album.mid}"
                if pic:
                    task["coverPath"] = await self.downloader.add_task(
                        url=f"https://y.gtimg.cn/music/photo_new/{pic}.jpg",
                        file_name=song.get_full_name(),
                        file_suffix=".jpg",
                    )
        await self.downloader.execute_tasks()
