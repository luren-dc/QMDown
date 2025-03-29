from qqmusic_api import Credential, album, lyric, singer, song, songlist, top, user
from qqmusic_api.utils.network import RequestGroup

from QMDown.models import AlbumDetial, Lyric, SingerDetail, Song, SongDetail, SonglistDetail, SongUrl, ToplistDetail


async def query(value: list[str] | list[int]) -> list[Song]:
    return [Song.model_validate(song) for song in await song.query_song(value)]


async def get_song_detail(mid: str) -> SongDetail:
    return SongDetail.model_validate(await song.get_detail(mid))


async def get_download_url(
    mids: list[str], quality: song.SongFileType, credential: Credential | None = None
) -> list[SongUrl]:
    urls = await song.get_song_urls(mids, quality, credential)
    return [SongUrl(mid=mid, url=url, type=quality) for mid, url in urls.items()]


async def get_album_detail(value: str | int):
    rg = RequestGroup()
    rg.add_request(album.get_detail, value)
    rg.add_request(album.get_song, value, 200)
    data, songs = await rg.execute()
    data.update(
        {
            "company": data["company"]["name"],
            "singer": data["singer"]["singerList"],
            "songs": songs,
        }
    )
    return AlbumDetial.model_validate(data)


async def get_songlist_detail(id: int):
    data = await songlist.get_detail(id)
    return SonglistDetail.model_validate({"info": data["dirinfo"], "songs": await songlist.get_songlist(id)})


async def get_user_detail(euin: str, credential: Credential):
    return await user.get_homepage(euin, credential=credential)


async def get_lyric(value: str | int, qrc: bool, trans: bool, roma: bool) -> Lyric:
    return Lyric.model_validate(await lyric.get_lyric(value, qrc=qrc, trans=trans, roma=roma))


async def get_toplist_detail(id: int) -> ToplistDetail:
    data = await top.get_detail(id)
    return ToplistDetail.model_validate(
        {
            "id": data["topId"],
            "title": data["title"],
            "songnum": data["totalNum"],
        }
    )


async def get_singer_detail(mid: str):
    data = await singer.get_info(mid)
    info = data["Info"]["Singer"]
    return SingerDetail.model_validate(
        {
            "mid": info["SingerMid"],
            "name": info["Name"],
            "songs": await singer.get_songs_list_all(mid),
        }
    )


async def get_song_metadata(song_mid: str, album_mid: str):
    songdata, albumdata, a, s = None, None, None, None
    rg = RequestGroup()
    rg.add_request(song.get_detail, song_mid)
    if album_mid:
        rg.add_request(album.get_detail, album_mid)
    data = await rg.execute()
    songdata = data[0]
    s = SongDetail.model_validate(songdata)
    if album_mid:
        albumdata = data[1]
        albumdata.update(
            {
                "company": albumdata["company"]["name"],
                "singer": albumdata["singer"]["singerList"],
                "songs": [],
            }
        )
        a = AlbumDetial.model_validate(albumdata)
    track_info = s.track_info
    metadata = {
        "title": [track_info.title],
        "artist": [s.name for s in track_info.singer],
    }
    if s.company:
        metadata["copyright"] = s.company
    if s.genre:
        metadata["genre"] = s.genre

    if track_info.index_album:
        metadata["tracknumber"] = [str(track_info.index_album)]
    if track_info.index_cd:
        metadata["discnumber"] = [str(track_info.index_cd)]

    if a:
        metadata.update(
            {
                "album": [a.info.name],
                "albumartist": [s.name for s in a.singer],
            }
        )

    if s.time_public and s.time_public[0]:
        metadata["date"] = [str(s.time_public[0])]

    return metadata
