from typing import Any, cast, final

from typing_extensions import override

from QMDown.api import top as api
from QMDown.extractor._abc import BatchExtractor


@final
class ToplistExtractor(BatchExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/toplist/(?P<id>[0-9]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/toplist\.html\?.*id=(?P<id>[0-9]+)",
    )

    @override
    async def extract(self, url: str):
        id = self._match_id(url)
        toplist = await api.get_detail(int(id), num=1000)
        self.print(f"榜单信息获取成功: [red]{toplist['data']['title']}")
        return cast(list[dict[str, Any]], toplist["songInfoList"])  # pyright: ignore[reportExplicitAny]
