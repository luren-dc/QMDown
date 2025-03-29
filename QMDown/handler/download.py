from typing_extensions import override

from QMDown.api import get_download_url
from QMDown.models import SongUrl
from QMDown.utils.downloader import AsyncDownloader
from QMDown.utils.priority import get_priority

from ._abc import Context, Handler


class DownloadHandler(Handler):
    @override
    async def process(self, ctx: Context) -> bool:
        fetch_mid = [t["songData"].mid for t in ctx.tasks]
        urls: list[SongUrl] = []
        for ft in get_priority(ctx.settings.basic.quality):
            if not fetch_mid:
                break
            res = await get_download_url(fetch_mid, ft)
            urls.extend(u for u in res if u.url)
            fetch_mid = [u.mid for u in res if not u.url]
            self.report_info(f"{ft.name} 成功: {len(urls)}/{len(fetch_mid)}")

        downloader = AsyncDownloader(
            save_dir=ctx.settings.basic.output,
            num_workers=ctx.settings.basic.num_workers,
            disable_progress=ctx.settings.basic.no_progress,
            timeout=ctx.settings.basic.timeout,
            overwrite=ctx.settings.basic.overwrite,
            retries=ctx.settings.basic.max_retries,
        )

        url_map = {u.mid: u for u in urls}
        tasks = [(t, url) for t in ctx.tasks if (url := url_map.get(t["songData"].mid)) and url.url]

        [await downloader.add_task(url.url, t["songData"].get_full_name(), url.type.e) for t, url in tasks]
        results = await downloader.execute_tasks()

        if not results:
            return True
        ctx.tasks = [t for t, res in zip((x[0] for x in tasks), results) if not isinstance(res, Exception) and res]
        return not ctx.tasks
