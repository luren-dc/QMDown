from pathlib import Path

import typer
from pydantic import BaseModel, Field

from QMDown import __prog_name__


def get_config_home():
    return Path(typer.get_app_dir(__prog_name__, roaming=True))

class QMDownBasicSettings(BaseModel):
    num_workers: int = Field(8, gt=0)
    max_retries: int = Field(3, gt=0)
    timeout: int = Field(15, gt=0)
    overwrite: bool = Field(False)
    no_color: bool = Field(False)
    no_progress: bool = Field(False)
    debug: bool = Field(False)

class QMDownLoginSettings(BaseModel):
    login_type: str = Field("")
    cookies: str = Field("")
    load_path: Path | None = Field(None)
    save_path: Path | None = Field(None)

class QMDownLyricSettings(BaseModel):
    enabled: bool = Field(False)
    trans: bool = Field(False)
    roma: bool = Field(False)
    embed_lyric: bool = Field(True)
    del_lyric: bool = Field(True)

class QMDownMetadataSettings(BaseModel):
    enabled: bool = Field(True)
    embed_cover: bool = Field(True)

class QMDownSettings(BaseModel):
    basic: QMDownBasicSettings = Field(QMDownBasicSettings())
    login: QMDownLoginSettings = Field(QMDownLoginSettings())
    lyric: QMDownLyricSettings = Field(QMDownLyricSettings())
    metadata: QMDownMetadataSettings = Field(QMDownMetadataSettings())

if __name__ == "__main__":
    print(QMDownSettings().model_dump())