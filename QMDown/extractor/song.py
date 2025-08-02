from typing import final, override

from QMDown.api import song as api
from QMDown.extractor._abc import SingleExtractor


@final
class SongExtractor(SingleExtractor):
    _VALID_URL = (
        r"https?://y\.qq\.com/n/ryqq/songDetail/(?P<id>[0-9A-Za-z]+)",
        r"https?://i\.y\.qq\.com/v8/playsong\.html\?.*songmid=(?P<id>[0-9A-Za-z]+)",
    )

    @override
    async def extract(self, url: str):
        song_id = self._match_id(url)
        if song_id.isdigit():
            song_id = int(song_id)
        return (await api.query_song([song_id]))[0]  # pyright: ignore[reportArgumentType]
