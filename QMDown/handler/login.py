import asyncio
from pathlib import Path

import typer
from anyio import open_file
from qqmusic_api import Credential, get_session
from qqmusic_api.login import (
    PhoneLoginEvents,
    QRCodeLoginEvents,
    QRLoginType,
    check_qrcode,
    get_qrcode,
    phone_authorize,
    send_authcode,
)
from typing_extensions import override

from QMDown import console
from QMDown.utils.utils import show_qrcode

from ._abc import Context, Handler


class LoginHandler(Handler):
    @override
    async def process(self, ctx: Context) -> bool:
        settings = ctx.settings.login
        credential: Credential | None = None
        changed = False

        if settings.cookies:
            if parsed := self._parse_cookies(settings.cookies):
                credential, cred_changed = await self._check_and_refresh_credential(parsed)
                changed = changed or cred_changed

        if not credential and settings.login_type:
            credential, login_changed = await self._handle_login_type(settings.login_type)
            changed = changed or login_changed

        if not credential and settings.load_path:
            credential, load_changed = await self._load_credential_from_file(settings.load_path)
            changed = changed or load_changed

        if credential and changed and settings.save_path:
            await self._save_credential_to_file(settings.save_path, credential)

        if credential:
            await self._update_session_credential(credential)

        return False

    async def _check_and_refresh_credential(self, credential: Credential) -> tuple[Credential | None, bool]:
        try:
            if not (credential.has_musicid() and credential.has_musickey()):
                return None, False
            if not await credential.is_expired():
                return credential, False

            self.report_info("[yellow]凭证已过期,尝试刷新...")
            if await credential.refresh():
                self.report_info("[green]凭证刷新成功")
                return credential, True

            self.report_info("[red]凭证刷新失败")
            return None, False

        except Exception as e:
            self.report_info(f"[red]凭证检查异常: {e!s}")
            return None, False

    def _parse_cookies(self, raw_cookies: str) -> Credential | None:
        try:
            if not (parts := raw_cookies.split(":")) or len(parts) != 2:
                raise ValueError("Cookie 格式错误")

            return Credential(musicid=int(parts[0]), musickey=parts[1])

        except ValueError as e:
            self.report_info(f"[red]Cookie 解析失败: {e!s}")
            return None

    async def _handle_login_type(self, login_type: str) -> tuple[Credential | None, bool]:
        match login_type:
            case "wx" | "qq":
                return await self._qrcode_login(QRLoginType(login_type)), True
            case "phone":
                return await self._phone_login(), True
        return None, False

    async def _load_credential_from_file(self, path: Path) -> tuple[Credential | None, bool]:
        try:
            async with await open_file(path) as f:
                cookies_str = await f.read()
            credential = Credential.from_cookies_str(cookies_str)
            return await self._check_and_refresh_credential(credential)
        except Exception as e:
            self.report_info(f"[red]加载凭证文件失败: {e!s}")
            return None, False

    async def _save_credential_to_file(self, path: Path, credential: Credential) -> None:
        try:
            async with await open_file(path, "w") as f:
                await f.write(credential.as_json())
            self.report_info(f"[green]凭证已保存至: {path}")
        except Exception as e:
            self.report_info(f"[red]凭证保存失败: {e!s}")

    async def _update_session_credential(self, credential: Credential | None) -> None:
        if credential:
            get_session().credential = credential
            self.report_info(f"当前登录账号: {credential.musicid}")

    async def _qrcode_login(self, login_type: QRLoginType) -> Credential:
        with console.status("获取二维码中...") as status:
            qrcode = await get_qrcode(login_type=QRLoginType(login_type))
            status.stop()
            show_qrcode(qrcode.data)
            status.update(f"[red]请使用[blue] {login_type.value.upper()} [red]扫描二维码登录")
            status.start()

            while True:
                state, credential = await check_qrcode(qrcode)
                match state:
                    case QRCodeLoginEvents.DONE:
                        status.stop()
                        self.report_info("[green]登录成功")
                        return credential  # type: ignore[reportReturnType]
                    case QRCodeLoginEvents.REFUSE | QRCodeLoginEvents.TIMEOUT:
                        error_msg = "二维码登录被拒绝" if state == QRCodeLoginEvents.REFUSE else "二维码登录超时"
                        self.report_error(f"[yellow]{error_msg}")
                        raise typer.Exit(code=1)
                    case QRCodeLoginEvents.SCAN:
                        await asyncio.sleep(5)
                    case _:
                        await asyncio.sleep(2)

    async def _phone_login(
        self,
    ) -> Credential:
        phone = typer.prompt("请输入手机号", type=int)
        with console.status("获取验证码中...") as status:
            while True:
                state, auth_url = await send_authcode(phone)
                if state == PhoneLoginEvents.SEND:
                    self.report_info("[red]验证码发送成功")
                    break
                if state == PhoneLoginEvents.CAPTCHA:
                    self.report_info("[red]需要滑块验证")
                    if not auth_url:
                        self.report_error("[yellow]获取验证链接失败")
                        raise typer.Exit(code=1)
                    self._console.print(f"[red]请复制链接前往浏览器验证:[/]\n{auth_url}")
                    status.stop()
                    typer.confirm("验证后请回车", prompt_suffix="", show_default=False)
                    status.start()
                else:
                    self.report_error("[yellow]登录失败(未知情况)")
                    raise typer.Exit(code=1)

        code = typer.prompt("请输入验证码", type=int)
        try:
            return await phone_authorize(phone, code)
        except Exception:
            self.report_error("[yellow]验证码错误或已过期")
            raise typer.Exit(code=1)
