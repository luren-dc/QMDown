import base64
import logging
import mimetypes
from pathlib import Path

from anyio import open_file
from mutagen._file import File
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, USLT
from mutagen.id3._specs import Encoding
from mutagen.id3._util import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

Metadata = dict[str, str | list[str]]


async def set_audio_cover(audio_path: str | Path, cover_path: str | Path, cleanup: bool = True) -> None:
    """
    为音频文件添加封面 (支持 MP3/FLAC/OGG/AAC)

    Args:
        audio_path: 音频文件路径
        cover_path: 封面图片路径
        cleanup: 是否在成功后删除封面文件
    """
    audio_path = Path(audio_path)
    cover_path = Path(cover_path)

    if not audio_path.exists() or not cover_path.exists():
        return

    try:
        async with await open_file(cover_path, "rb") as f:
            cover_data = await f.read()
        mime_type, _ = mimetypes.guess_type(cover_path)
        if mime_type not in ("image/jpeg", "image/png", "image/webp"):
            logging.debug(f"[blue][封面][/] 不支持的图片格式: {mime_type}")
            return
        await _set_cover(audio_path.suffix.lower(), audio_path, cover_data, mime_type)
        logging.debug(f"[blue][封面][/] 成功嵌入封面到 {audio_path.name}")
    except Exception as e:
        logging.error(f"[blue][封面][/] 处理 {audio_path.name} 失败: {e}", exc_info=True)
    finally:
        if cleanup and cover_path.exists:
            cover_path.unlink(True)


async def _set_cover(ext: str, path: Path, data: bytes, mime: str):
    """统一处理不同音频格式的封面添加"""

    def _create_picture():
        pic = Picture()
        pic.type, pic.mime, pic.data, pic.desc = 3, mime, data, "Cover"
        return pic

    match ext:
        case ".mp3":
            try:
                audio = ID3(path)
            except ID3NoHeaderError:
                audio = ID3()
            audio.delall("APIC")
            audio.add(APIC(encoding=0, mime=mime, type=3, desc="Cover", data=data))
            audio.save(path, v2_version=3)
        case ".flac" | ".oga":
            audio = FLAC(path)
            audio.clear_pictures()
            audio.add_picture(_create_picture())
            audio.save()
        case ".ogg" | ".opus":
            audio = File(path)
            if not isinstance(audio, OggOpus | OggVorbis):
                raise ValueError(f"不支持的 Ogg 格式: {path.suffix}")
            pic = _create_picture()
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode()]
            audio.save()
        case ".m4a" | ".aac" | ".mp4":
            audio = MP4(path)
            fmt = MP4Cover.FORMAT_JPEG if mime == "image/jpeg" else MP4Cover.FORMAT_PNG
            audio["covr"] = [MP4Cover(data, fmt)]
            audio.save()
        case _:
            logging.debug(f"[blue][封面][/] 不支持的音频格式: {path}")


async def set_metadata(file: str | Path, metadata: Metadata) -> None:
    """写入元数据到音频文件"""
    file = Path(file)
    if not file.exists():
        logging.debug(f"[blue][元数据][/] 文件不存在: {file}")
        return

    try:
        audio = File(str(file), easy=True)
        if audio is None:
            logging.debug(f"[blue][元数据][/] 不支持的音频格式: {file}")
            return

        for key, value in metadata.items():
            try:
                audio[key] = value
            except (KeyError, ValueError, TypeError) as e:
                logging.debug(f"[blue][元数据][/] {key}={value} 写入失败: {e}")

        audio.save()
        logging.debug(f"[blue][元数据][/] 元数据写入成功: {file.name}")

    except Exception as e:
        logging.error(f"[blue][元数据][/] 处理 {file.name} 失败: {e}", exc_info=True)


async def set_lyrics(file: str | Path, lyrics: str) -> None:
    """写入歌词到音频文件"""
    file = Path(file)
    if not file.exists() or not lyrics:
        return

    ext = Path(file).suffix.lower()
    try:
        match ext:
            case ".mp3":
                audio = MP3(file, ID3=ID3)
                if audio.tags is None:
                    audio.tags = ID3()
                audio.tags.add(USLT(encoding=Encoding.UTF8, desc="", text=lyrics))
                audio.save()
            case ".flac" | ".oga":
                audio = FLAC(file)
                audio["LYRICS"] = lyrics
                audio.save()
            case ".ogg" | ".opus":
                audio = OggVorbis(file)
                audio["LYRICS"] = lyrics
                audio.save()
            case ".m4a" | ".aac" | ".mp4":
                audio = MP4(file)
                audio["\xa9lyr"] = lyrics
                audio.save()
            case _:
                logging.debug(f"[blue][歌词][/] 不支持的音频格式: {file}")
    except Exception as e:
        logging.error(f"[blue][歌词][/] 处理 {file.name} 失败: {e}", exc_info=True)
