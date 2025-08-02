from typing import final

from typing_extensions import override

from QMDown.api import singer as api
from QMDown.extractor._abc import BatchExtractor


@final
class SingerExtractor(BatchExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/singer/(?P<id>[0-9A-Za-z]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/profile_v2/index\.html\?.*singermid=(?P<id>[0-9A-Za-z]+)",
    )

    @override
    async def extract(self, url: str):
        singer_id = self._match_id(url)
        info = await api.get_info(singer_id)
        songs = await api.get_songs_list_all(singer_id)
        self.print(f"歌手信息获取成功: [red]{info['Info']['Singer']['Name']}")
        return songs
