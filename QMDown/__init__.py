import gettext
import logging
import os
import pathlib
from typing import Final

from rich.console import Console

__version__ = "0.2.3"
__prog_name__ = "QMDown"

# 控制台实例
console = Console()

# 禁用第三方库的日志传播
DISABLED_LOGGERS: Final = ["httpx", "httpcore", "hpack", "aiocache"]
for logger_name in DISABLED_LOGGERS:
    logging.getLogger(logger_name).propagate = False

# 国际化配置
LANG: Final = "zh_CN"
os.environ["LANGUAGE"] = LANG
LOCALE_DIR: Final = pathlib.Path(__file__).parent / "languages"
gettext.bindtextdomain(LANG, LOCALE_DIR)
gettext.textdomain(LANG)
t = gettext.translation(
    LANG,
    localedir=LOCALE_DIR,
    languages=[LANG],
)
t.install()
