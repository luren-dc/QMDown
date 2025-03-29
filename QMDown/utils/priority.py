from enum import Enum

from qqmusic_api.song import SongFileType


class SongFileTypePriority(Enum):
    """音频文件类型优先级枚举"""

    MASTER = 130
    ATMOS_2 = 120
    ATMOS_51 = 110
    FLAC = 100
    OGG_640 = 90
    OGG_320 = 80
    MP3_320 = 70
    OGG_192 = 60
    MP3_128 = 50
    OGG_96 = 40
    ACC_192 = 30
    ACC_96 = 20
    ACC_48 = 10


# 预生成数据结构
_priority_map = {SongFileType[ft.name]: ft.value for ft in SongFileTypePriority}
_sorted_types = sorted(SongFileTypePriority, key=lambda x: (-x.value, x.name))
_priority_order = [SongFileType[ft.name] for ft in _sorted_types]


def get_priority(file_type: SongFileType | int) -> list[SongFileType]:
    """
    获取指定类型允许的音频格式列表
    """
    try:
        threshold = _priority_map[file_type] if isinstance(file_type, SongFileType) else int(file_type)

        return [ft for ft in _priority_order if _priority_map.get(ft, 0) <= threshold]
    except (KeyError, ValueError):
        return [SongFileType.MP3_128]

