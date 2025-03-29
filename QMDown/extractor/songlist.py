from typing_extensions import override

from QMDown import api
from QMDown.extractor._abc import BatchExtractor


class SonglistExtractor(BatchExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/playlist/(?P<id>[0-9]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/taoge\.html\?.*id=(?P<id>[0-9]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/interactive_playlist\.html\?.*id=(?P<id>[0-9]+)",
    )

    @override
    async def extract(self, url: str):
        id = self._match_id(url)
        songlist = await api.get_songlist_detail(int(id))
        self.report_info(f"获取成功: {id} {songlist.info.title} - {songlist.info.host_nick}")
        return songlist.songs
