import os
import sys
from io import BytesIO
from typing import IO, TextIO

import httpx
from PIL import Image
from PIL._typing import StrOrBytesPath
from qrcode import QRCode


def truncate(file_name: str, file_suffix: str, max_length: int = 255) -> str:
    """截断文件名主体部分以适应文件系统最大长度限制.

    自动处理UTF-8编码字节边界问题,确保不会产生解码错误.最终文件名格式为:
    [截断后的文件名主体][省略号][文件后缀]

    Args:
        file_name: 文件名主体部分(不包含后缀)
        file_suffix: 文件后缀(包含点号，如".txt")
        max_length: 允许的最大字节长度(包含后缀部分)

    Returns:
        处理后的完整文件名，保证字节长度不超过max_length

    Raises:
        ValueError: 当max_length不足以容纳最小有效内容时
    """
    # 计算后缀的字节长度
    suffix_bytes = file_suffix.encode()
    max_name_bytes = max_length - len(suffix_bytes)

    # 处理极端情况:当长度限制小于后缀长度时
    if max_name_bytes < 0:
        if max_length >= 0:
            return suffix_bytes[:max_length].decode(errors="ignore") or "unnamed"
        raise ValueError("Invalid max_length value")

    # 准备省略号(占3个字节)
    ellipsis = "…"
    ellipsis_bytes = ellipsis.encode()
    max_name_part_bytes = max_name_bytes - len(ellipsis_bytes)

    # 处理长度不足的情况
    if max_name_part_bytes <= 0:
        return f"{ellipsis}{file_suffix}" if max_name_bytes >= 3 else file_suffix

    # 执行截断操作
    encoded_name = file_name.encode()
    if len(encoded_name) <= max_name_bytes:
        return f"{file_name}{file_suffix}"

    # 渐进式截断确保有效解码
    truncated_bytes = encoded_name[:max_name_part_bytes]
    while truncated_bytes:
        try:
            truncated_name = truncated_bytes.decode("utf-8")
            return f"{truncated_name}{ellipsis}{file_suffix}"
        except UnicodeDecodeError:
            truncated_bytes = truncated_bytes[:-1]

    return f"{ellipsis}{file_suffix}"


def safe_filename(file_full_name: str, max_length: int = 255) -> str:
    """生成符合文件系统规范的安全文件名

    处理流程：
    1. 替换路径分隔符等非法字符为全角字符
    2. 转换所有空白字符为普通空格
    3. 移除不可打印字符
    4. 自动截断超长文件名

    Args:
        file_full_name: 原始文件名(可能包含非法字符和空格)
        max_length: 允许的最大字节长度，默认255字节

    Returns:
        符合规范的安全文件名

    Examples:
        >>> safe_filename("a/b:\x00*.txt", 10)
        'a／b：　．.txt'
    """
    # 定义需要替换的非法字符集合(包含空字符)
    illegal_chars = {"\x00", "\\", "/", ":", "*", "?", '"', "<", ">", "|"}
    file_name, file_suffix = os.path.splitext(file_full_name)
    
    processed = []
    for char in file_name:
        # 替换非法字符为全角
        if char in illegal_chars:
            processed.append(chr(ord(char) + 0xFEE0))
        # 标准化空白字符
        elif char.isspace():
            processed.append(" ")
        # 过滤不可打印字符
        elif char.isprintable():
            processed.append(char)
    
    # 构建处理后的文件名主体
    processed_name = "".join(processed).strip()
    if not processed_name:
        processed_name = "unnamed"
    
    # 执行长度截断
    return truncate(processed_name, file_suffix, max_length)


async def get_real_url(url: str) -> str | None:
    """获取跳转后的URL.

    Args:
        url: URL
    """
    async with httpx.AsyncClient(http2=True,timeout=15) as client:
        resp = await client.get(url)
        return resp.headers.get("Location", None)


def show_qrcode(
    path: StrOrBytesPath | IO[bytes],
    out: TextIO = sys.stdout,
    tty: bool = False,
    invert: bool = False,
    border: int = 4,
) -> bool:
    """
    输出二维码的 ASCII 或通过备用方案显示/保存

    Args:
        path: 二维码文件路径或文件对象
        out: 输出流 (默认 stdout)
        tty: 是否使用 TTY 颜色代码
        invert: 是否反转颜色
        border: 二维码边界大小
    """
    try:
        from pyzbar.pyzbar import decode

        if isinstance(path, bytes):
            path = BytesIO(path)

        img = Image.open(path)
        decoded = decode(img)

        if decoded:
            url = decoded[0].data.decode("utf-8")
            qr = QRCode(border=border)
            qr.add_data(url)
            qr.print_ascii(out=out, tty=tty, invert=invert)
            return True
        return False
    except Exception:
        return False
