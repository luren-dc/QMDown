import logging

from rich.console import Console
from rich.logging import RichHandler

__version__ = "0.2.3"
__prog_name__ = "QMDown"

console = Console()

logging.getLogger("httpx").propagate = False
logging.getLogger("httpcore").propagate = False

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            console=console,
        )
    ],
)
