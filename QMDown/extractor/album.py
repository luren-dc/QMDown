from typing import final, override

from QMDown.api import album as api
from QMDown.extractor._abc import BatchExtractor


@final
class AlbumExtractor(BatchExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/albumDetail/(?P<id>[0-9A-Za-z]+)",
        r"https?://i\.y\.qq\.com/n2/m/share/details/album\.html\?.*albumId=(?P<id>[0-9]+)",
    )

    @override
    async def extract(self, url: str):
        album_id = self._match_id(url)
        if album_id.isdigit():
            album_id = int(album_id)
        info = await api.get_detail(album_id)
        self.print(f"专辑信息获取成功:[red]{info['basicInfo']['albumName']}")
        return await api.get_song(album_id, 1000)
