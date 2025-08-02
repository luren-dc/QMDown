from qqmusic_api import Credential, Session, album, get_session, singer, song, songlist, top

session: Session | None = None


async def setup(credential: dict[str, str] | None = None):
    """
    初始化 QQ 音乐 API 客户端
    """
    global session
    if session is not None:
        raise RuntimeError("Session already initialized")
    session = get_session()
    session.credential = Credential.from_cookies_dict(credential) if credential else Credential()


async def get_Session() -> Session:
    """
    获取当前的 QQ 音乐 API 会话
    """
    global session
    if session is None:
        raise RuntimeError("Session not initialized, please call setup() first")
    return session


__all__ = [
    "album",
    "get_Session",
    "setup",
    "singer",
    "song",
    "songlist",
    "top",
]
