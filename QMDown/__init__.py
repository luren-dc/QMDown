import logging

from rich.console import Console

__version__ = "0.2.3"
__prog_name__ = "QMDown"

console = Console()

logging.getLogger("httpx").propagate = False
logging.getLogger("httpcore").propagate = False
logging.getLogger("hpack").propagate = False
logging.getLogger("aiocache").propagate = False
