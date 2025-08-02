from typing import final, override

from QMDown.api import songlist as api
from QMDown.extractor._abc import BatchExtractor


@final
class SonglistExtractor(BatchExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/playlist/(?P<id>[0-9]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/taoge\.html\?.*id=(?P<id>[0-9]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/interactive_playlist\.html\?.*id=(?P<id>[0-9]+)",
    )

    @override
    async def extract(self, url: str):
        songlist_id = int(self._match_id(url))
        songlist = await api.get_songlist(songlist_id)
        info = await api.get_detail(songlist_id)
        self.print(f"歌单信息获取成功:[red]{info['dirinfo']['title']}")
        return songlist
