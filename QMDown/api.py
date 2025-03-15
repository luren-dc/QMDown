from qqmusic_api import Credential, album, lyric, singer, song, songlist, top, user

from QMDown.model import AlbumDetial, Lyric, SingerDetail, Song, SongDetail, SonglistDetail, SongUrl, ToplistDetail


async def query(value: list[str] | list[int]) -> list[Song]:
    return [Song.model_validate(song) for song in await song.query_song(value)]

async def get_song_detail(mid: str) -> SongDetail:
    return SongDetail.model_validate(await song.get_detail(mid))


async def get_download_url(
    mids: list[str], quality: song.SongFileType, credential: Credential | None = None
) -> list[SongUrl]:
    urls = await song.get_song_urls(mids, quality, credential)
    return [SongUrl(mid=mid, url=url, type=quality) for mid, url in urls.items()]


async def get_album_detail(mid: str | None = None, id: int | None = None):
    if mid:
        data = await album.get_detail(mid)
    elif id:
        data = await album.get_detail(id)
    else:
        raise ValueError("mid 和 id 不能同时为空")

    songs = await album.get_song(data[0])
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
    return SonglistDetail.model_validate(data)


async def get_user_detail(euin: str, credential: Credential):
    return await user.get_homepage(euin, credential)
    

async def get_lyric(mid: str, qrc: bool, trans: bool, roma: bool) -> Lyric:
    return Lyric.model_validate(await lyric.get_lyric(mid=mid, qrc=qrc, trans=trans, roma=roma))


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
