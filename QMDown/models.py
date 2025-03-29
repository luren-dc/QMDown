from datetime import date
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, AliasPath, BaseModel, BeforeValidator, Field, model_validator
from qqmusic_api.song import SongFileType
from rich.progress import TaskID

PublicTimeField = AliasChoices("time_public", "pub_time", "publishDate")
PublicTime = Annotated[date | None, BeforeValidator(lambda value: None if not value else value)]


class DownloadTask(BaseModel):
    """下载任务"""

    id: TaskID
    url: str
    file_name: str
    file_suffix: str
    full_path: Path


class Singer(BaseModel):
    id: int = Field(validation_alias=AliasChoices("id", "singerID"))
    mid: str
    name: str
    pmid: str | None = None
    title: str | None = None


class Album(BaseModel):
    id: int = Field(validation_alias=AliasChoices("id", "albumID"))
    mid: str = Field(validation_alias=AliasChoices("mid", "albumMid"))
    name: str = Field(validation_alias=AliasChoices("name", "albumName"))
    title: str | None = None
    pmid: str | None = None
    subtitle: str | None = None
    time_public: PublicTime = Field(None, validation_alias=PublicTimeField)


class PayInfo(BaseModel):
    pay_month: int
    price_track: int
    price_album: int
    pay_play: int
    pay_down: int
    pay_status: int
    time_free: int


class FileInfo(BaseModel):
    media_mid: str
    size_24aac: int
    size_48aac: int
    size_96aac: int
    size_192ogg: int
    size_320ogg: int = Field(0, validation_alias=AliasPath("size_new", 3))
    size_640ogg: int = Field(0, validation_alias=AliasPath("size_new", 5))
    size_192aac: int
    size_128mp3: int
    size_320mp3: int
    size_flac: int
    size_dts: int
    size_try: int
    try_begin: int
    try_end: int
    size_hires: int
    hires_sample: int
    hires_bitdepth: int
    size_96ogg: int
    size_360ra: list[int]
    size_dolby: int
    size_new: list[int]
    size_master: int = Field(0, validation_alias=AliasPath("size_new", 0))
    size_atmos_2: int = Field(0, validation_alias=AliasPath("size_new", 1))
    size_atmos_51: int = Field(0, validation_alias=AliasPath("size_new", 2))


class Song(BaseModel):
    id: int
    mid: str
    name: str
    title: str
    subtitle: str
    singer: list[Singer]
    album: Album
    file: FileInfo | None = None
    pay: PayInfo | None = None
    language: int | None = None
    genre: int | None = None
    index_cd: int | None = None
    index_album: int | None = None
    time_public: PublicTime = None
    vs: list[str]

    def singer_to_str(self, sep: str = ",") -> str:
        return sep.join([s.name for s in self.singer])

    def get_full_name(self, format: str = "{title} - {singer}", sep: str = ",") -> str:
        if "{title}" not in format or "{singer}" not in format:
            raise ValueError("format 必须包含 {title} 和 {singer}")
        return format.format(title=self.title, singer=self.singer_to_str(sep=sep))


class SongUrl(BaseModel):
    mid: str
    url: str
    type: SongFileType


class SongDetail(BaseModel):
    track_info: Song
    company: list[str] = []
    genre: list[str] = []
    lan: list[str] = []
    time_public: list[PublicTime] = Field([], validation_alias=PublicTimeField)

    @model_validator(mode="before")
    @classmethod
    def parse_info(cls, data):
        info = data.pop("info", {})

        def get_first_value(key: str):
            if section := info.get(key):
                if content := section.get("content"):
                    if content and isinstance(content, list):
                        return [v.get("value") for v in content]
            return []

        field = ["company", "genre", "lan", "pub_time"]
        for f in field:
            data[f] = get_first_value(f)
        return data


class AlbumDetial(BaseModel):
    info: Album = Field(validation_alias="basicInfo")
    company: str
    singer: list[Singer]
    songs: list[Song]

    def singer_to_str(self, sep: str = ",") -> str:
        return sep.join([s.name for s in self.singer])


class DirInfo(BaseModel):
    id: int
    dirid: int
    title: str
    songnum: int
    host_uin: int
    host_nick: str


class SonglistDetail(BaseModel):
    info: DirInfo
    songs: list[Song]


class Lyric(BaseModel):
    lyric: str
    trans: str
    roma: str


class ToplistDetail(BaseModel):
    id: int
    title: str
    songnum: int
    songs: list[Song]


class SingerDetail(BaseModel):
    mid: str
    name: str
    songs: list[Song]
