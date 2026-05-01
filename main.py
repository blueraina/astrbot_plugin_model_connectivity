import asyncio
import base64
import io
import json
import os
import random
import re
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register


PLUGIN_NAME = "astrbot_plugin_model_connectivity"


@dataclass
class ProbeTarget:
    provider: Any
    provider_id: str
    provider_group_id: str
    provider_type: str
    provider_name: str
    provider_group_name: str
    current_model: str
    model: str
    provider_logo: str = ""

PROVIDER_ICONS = {
    'openai': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/openai.svg',
    'azure': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/azure.svg',
    'xai': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/xai.svg',
    'anthropic': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/anthropic.svg',
    'ollama': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/ollama.svg',
    'google': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/gemini-color.svg',
    'deepseek': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/deepseek.svg',
    'modelscope': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/modelscope.svg',
    'zhipu': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/zhipu.svg',
    'nvidia': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/nvidia-color.svg',
    'siliconflow': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/siliconcloud.svg',
    'moonshot': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/kimi.svg',
    'kimi': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/kimi.svg',
    'kimi-code': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/kimi.svg',
    'longcat': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/longcat-color.svg',
    'ppio': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/ppio.svg',
    'dify': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/dify-color.svg',
    'coze': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@1.66.0/icons/coze.svg',
    'dashscope': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/alibabacloud-color.svg',
    'deerflow': 'https://cdn.jsdelivr.net/gh/bytedance/deer-flow@main/frontend/public/images/deer.svg',
    'fastgpt': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/fastgpt-color.svg',
    'lm_studio': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/lmstudio.svg',
    'fishaudio': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/fishaudio.svg',
    'minimax': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/minimax.svg',
    'minimax-token-plan': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/minimax.svg',
    'mimo': 'https://platform.xiaomimimo.com/favicon.874c9507.png',
    '302ai': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@1.53.0/icons/ai302-color.svg',
    'microsoft': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/microsoft.svg',
    'vllm': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/vllm.svg',
    'groq': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/groq.svg',
    'aihubmix': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/aihubmix-color.svg',
    'openrouter': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/openrouter.svg',
    'tokenpony': 'https://tokenpony.cn/tokenpony-web/logo.png',
    'compshare': 'https://compshare.cn/favicon.ico',
    'xinference': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/xinference-color.svg',
    'bailian': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/bailian-color.svg',
    'volcengine': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/volcengine-color.svg',
}


@register(
    PLUGIN_NAME,
    "Codex",
    "检测 WebUI 已打开的模型连通性，并发送状态看板图片。",
    "1.4.2",
)
class ModelConnectivityPlugin(Star):
    def __init__(self, context: Context, config: Optional[dict] = None):
        super().__init__(context)
        self.config = config or {}
        self._check_lock = asyncio.Lock()
        self._auto_check_task: Optional[asyncio.Task] = None
        self._auto_status_send_task: Optional[asyncio.Task] = None
        self._skip_model_options_refresh_task: Optional[asyncio.Task] = None
        self._provider_icons = self._load_provider_icons()
        self._provider_icon_cache: dict[tuple[str, str, int], Any] = {}
        self._refresh_skip_model_options()
        self._start_skip_model_options_refresh_task()
        self._start_auto_check_task()
        self._start_auto_status_send_task()

    @filter.command("modeltest")
    async def modeltest(self, event):
        """检测 WebUI 已打开模型的连通性。"""
        async for result in self._handle_connectivity_check(event):
            yield result

    @filter.command("模型连通性")
    async def model_connectivity_cn(self, event):
        """检测 WebUI 已打开模型的连通性。"""
        async for result in self._handle_connectivity_check(event):
            yield result

    @filter.command("modelstatus")
    async def modelstatus(self, event):
        """发送最近一次模型连通性状态图，不触发新的检测。"""
        async for result in self._handle_latest_status(event):
            yield result

    @filter.command("模型状态")
    async def model_status_cn(self, event):
        """发送最近一次模型连通性状态图，不触发新的检测。"""
        async for result in self._handle_latest_status(event):
            yield result

    @filter.command("modelstatusoff")
    async def modelstatusoff(self, event):
        """取消当前会话的定时状态图推送。"""
        async for result in self._handle_status_push_unsubscribe(event):
            yield result

    @filter.command("取消模型状态推送")
    async def model_status_push_off_cn(self, event):
        """取消当前会话的定时状态图推送。"""
        async for result in self._handle_status_push_unsubscribe(event):
            yield result

    @filter.command("modelskiprefresh")
    async def modelskiprefresh(self, event):
        """刷新跳过模型的 WebUI 候选项。"""
        async for result in self._handle_skip_model_options_refresh(event):
            yield result

    @filter.command("刷新模型候选")
    async def refresh_model_candidates_cn(self, event):
        """刷新跳过模型的 WebUI 候选项。"""
        async for result in self._handle_skip_model_options_refresh(event):
            yield result

    async def _handle_connectivity_check(self, event):
        started_at = time.perf_counter()
        await self._remember_status_send_target_from_event(event)
        yield event.plain_result("正在检测 WebUI 已打开模型的连通性，请稍等...")

        try:
            report = await self._run_connectivity_check()
            if report is None:
                yield event.plain_result("没有发现 WebUI 中已打开的聊天模型。")
                return

            try:
                image_path = await self._render_report_image(report)
                yield event.image_result(image_path)
            except Exception as render_exc:
                logger.exception("Model connectivity image rendering failed")
                yield event.plain_result(
                    "模型检测完成，但图片渲染失败："
                    f"{render_exc}\n\n{self._format_text_report(report)}"
                )
        except Exception as exc:
            logger.exception("Model connectivity check failed")
            yield event.plain_result(f"模型连通性检测失败：{exc}")

    async def _handle_latest_status(self, event):
        await self._remember_status_send_target_from_event(event)
        report = await self._load_latest_report()
        if report is None:
            yield event.plain_result(
                "还没有可发送的模型状态图，请先执行 /modeltest 或开启定时自动检测。"
            )
            return

        try:
            image_path = await self._render_report_image(self._snapshot_report_for_render(report))
            yield event.image_result(image_path)
        except Exception as exc:
            logger.exception("Latest model status image rendering failed")
            yield event.plain_result(f"发送最近状态图失败：{exc}")

    async def _handle_status_push_unsubscribe(self, event):
        origin = self._event_origin(event)
        if not origin:
            yield event.plain_result("无法识别当前会话，取消自动推送失败。")
            return

        removed = await self._forget_status_send_target(origin)
        if removed:
            yield event.plain_result("已取消当前群聊/私聊的模型状态图自动推送。")
            return

        yield event.plain_result("当前群聊/私聊没有开启模型状态图自动推送。")

    async def _handle_skip_model_options_refresh(self, event):
        try:
            providers = list(self.context.get_all_providers() or [])
        except Exception:
            providers = []

        options = self._configured_skip_model_options(providers) if providers else []
        if not options:
            report = await self._load_latest_report()
            options = self._skip_model_options_from_report(report) if report else []

        if options:
            preview = "\n".join(options[:80])
            suffix = "" if len(options) <= 80 else f"\n... 还有 {len(options) - 80} 个"
            yield event.plain_result(
                "当前可跳过模型候选如下。请把需要跳过的值填入插件配置里的“跳过的模型”，"
                "多个值可用英文逗号或换行分隔：\n"
                f"{preview}{suffix}"
            )
            return

        yield event.plain_result(
            "还没有读到可用模型候选。请确认 WebUI 中模型开关已打开，或先执行一次 /modeltest。"
        )

    async def _run_connectivity_check(self) -> Optional[dict[str, Any]]:
        async with self._check_lock:
            started_at = time.perf_counter()
            targets, provider_errors = await self._collect_probe_targets()
            if not targets:
                return None
            results = await self._probe_targets(targets)
            report = await self._build_report(results, provider_errors, started_at)
            await self._save_latest_report(report)
            self._refresh_skip_model_options_from_report(report)
            return report

    def _start_auto_check_task(self) -> None:
        if self._auto_check_interval_range() is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("Auto model connectivity check was not started: no running event loop")
            return
        self._auto_check_task = loop.create_task(self._auto_check_loop())

    async def _auto_check_loop(self) -> None:
        if self._cfg_bool("auto_check_run_on_start", False):
            await self._run_auto_check_once()

        while True:
            interval_range = self._auto_check_interval_range()
            if interval_range is None:
                return
            min_hours, max_hours = interval_range
            interval_hours = random.uniform(min_hours, max_hours)
            logger.info(
                "Next auto model connectivity check in %.2f hour(s)",
                interval_hours,
            )
            await asyncio.sleep(max(60.0, interval_hours * 3600))
            await self._run_auto_check_once()

    async def _run_auto_check_once(self) -> None:
        try:
            report = await self._run_connectivity_check()
            if report is None:
                logger.info("Auto model connectivity check skipped: no enabled models")
                return
            logger.info(
                "Auto model connectivity check finished: ok=%s slow=%s error=%s total=%s",
                report.get("ok_count"),
                report.get("slow_count"),
                report.get("error_count"),
                report.get("total"),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Auto model connectivity check failed: %s", exc)

    def _auto_check_interval_range(self) -> Optional[tuple[float, float]]:
        min_hours = self._cfg_float("auto_check_interval_min_hours", 0.0)
        max_hours = self._cfg_float("auto_check_interval_max_hours", 0.0)

        if min_hours <= 0 and max_hours <= 0:
            legacy_hours = self._cfg_float("auto_check_interval_hours", 0.0)
            min_hours = legacy_hours
            max_hours = legacy_hours
        elif min_hours <= 0:
            min_hours = max_hours
        elif max_hours <= 0:
            max_hours = min_hours

        if max_hours < min_hours:
            min_hours, max_hours = max_hours, min_hours

        if max_hours <= 0:
            return None
        return max(0.0, min_hours), max_hours

    def _auto_check_interval_label(self) -> str:
        interval_range = self._auto_check_interval_range()
        if interval_range is None:
            return "manual"
        min_hours, max_hours = interval_range
        if abs(max_hours - min_hours) < 0.0001:
            return f"{max_hours:g}h"
        return f"{min_hours:g}-{max_hours:g}h"

    def _start_auto_status_send_task(self) -> None:
        if self._cfg_float("auto_status_send_interval_hours", 0.0) <= 0:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("Auto model status sender was not started: no running event loop")
            return
        self._auto_status_send_task = loop.create_task(self._auto_status_send_loop())

    async def _auto_status_send_loop(self) -> None:
        while True:
            interval_hours = self._cfg_float("auto_status_send_interval_hours", 0.0)
            if interval_hours <= 0:
                return
            await asyncio.sleep(max(60.0, interval_hours * 3600))
            await self._run_auto_status_send_once()

    async def _run_auto_status_send_once(self) -> None:
        try:
            report = await self._load_latest_report()
            if report is None:
                logger.info("Auto model status send skipped: no latest report")
                return

            targets = await self._status_send_targets()
            if not targets:
                logger.info("Auto model status send skipped: no target session")
                return

            image_path = await self._render_report_image(
                self._snapshot_report_for_render(report)
            )
            for target in targets:
                try:
                    chain = self._image_message_chain(image_path)
                    send_result = self.context.send_message(target, chain)
                    if hasattr(send_result, "__await__"):
                        await send_result
                except Exception as exc:
                    logger.warning("Auto model status send failed for %s: %s", target, exc)
            logger.info("Auto model status image sent to %s target(s)", len(targets))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Auto model status send failed: %s", exc)

    async def terminate(self) -> None:
        for task in (
            self._auto_check_task,
            self._auto_status_send_task,
            self._skip_model_options_refresh_task,
        ):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _save_latest_report(self, report: dict[str, Any]) -> None:
        try:
            await self.put_kv_data("latest_report", report)
        except Exception as exc:
            logger.warning("Failed to save latest model connectivity report: %s", exc)

    async def _load_latest_report(self) -> Optional[dict[str, Any]]:
        try:
            data = await self.get_kv_data("latest_report", None)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.warning("Failed to load latest model connectivity report: %s", exc)
            return None

    def _snapshot_report_for_render(self, report: dict[str, Any]) -> dict[str, Any]:
        snapshot = dict(report)
        now = datetime.now()
        theme = self._theme_name(now)
        snapshot["theme"] = theme
        snapshot["theme_label"] = "白天" if theme == "light" else "夜间"
        return snapshot

    async def _remember_status_send_target_from_event(self, event: Any) -> None:
        if not self._cfg_bool("auto_status_remember_command_session", True):
            return
        origin = self._event_origin(event)
        if not origin:
            return

        try:
            targets = await self.get_kv_data("status_send_targets", [])
            if not isinstance(targets, list):
                targets = []
            normalized = [str(item).strip() for item in targets if str(item).strip()]
            if origin not in normalized:
                normalized.append(origin)
                normalized = normalized[-20:]
                await self.put_kv_data("status_send_targets", normalized)
        except Exception as exc:
            logger.warning("Failed to remember model status send target: %s", exc)

    async def _forget_status_send_target(self, origin: str) -> bool:
        origin = str(origin or "").strip()
        if not origin:
            return False

        try:
            targets = await self.get_kv_data("status_send_targets", [])
            if not isinstance(targets, list):
                return False
            normalized = [str(item).strip() for item in targets if str(item).strip()]
            filtered = [target for target in normalized if target != origin]
            if len(filtered) == len(normalized):
                return False
            await self.put_kv_data("status_send_targets", filtered)
            return True
        except Exception as exc:
            logger.warning("Failed to forget model status send target: %s", exc)
            return False

    def _event_origin(self, event: Any) -> str:
        for name in ("unified_msg_origin", "get_unified_msg_origin"):
            value = getattr(event, name, "")
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = ""
            value = str(value or "").strip()
            if value:
                return value
        return ""

    async def _status_send_targets(self) -> list[str]:
        if not self._cfg_bool("auto_status_remember_command_session", True):
            return []

        try:
            remembered = await self.get_kv_data("status_send_targets", [])
            if not isinstance(remembered, list):
                return []
            return self._deduplicate([str(target).strip() for target in remembered if str(target).strip()])
        except Exception as exc:
            logger.warning("Failed to load remembered model status send targets: %s", exc)
            return []

    def _image_message_chain(self, image_path: str) -> Any:
        is_url = image_path.startswith(("http://", "https://"))
        try:
            from astrbot.api.event import MessageChain

            chain = MessageChain()
            if is_url:
                if hasattr(chain, "url_image"):
                    return chain.url_image(image_path)
                raise AttributeError("MessageChain.url_image is not available")
            return chain.file_image(image_path)
        except Exception:
            from astrbot.api import message_components as Comp

            if is_url and hasattr(Comp.Image, "fromURL"):
                return [Comp.Image.fromURL(image_path)]
            return [Comp.Image.fromFileSystem(image_path)]

    async def _render_report_image(self, report: dict[str, Any]) -> str:
        backend = self._cfg_str("render_backend", "local").strip().lower()
        fallback_to_remote = self._cfg_bool("fallback_to_remote_render", True)
        errors: list[str] = []

        if backend in ("local", "pillow", "auto"):
            try:
                return await asyncio.to_thread(self._render_local_report_image, report)
            except Exception as exc:
                logger.warning("Local report image rendering failed: %s", exc)
                errors.append(f"local: {exc}")
                if backend in ("local", "pillow") and not fallback_to_remote:
                    raise

        if backend in ("remote", "html", "auto") or fallback_to_remote:
            try:
                return await self._render_remote_report_image(report)
            except Exception as exc:
                logger.warning("Remote report image rendering failed: %s", exc)
                errors.append(f"remote: {exc}")

        raise RuntimeError("; ".join(errors) or "no image renderer available")

    async def _render_remote_report_image(self, report: dict[str, Any]) -> str:
        # 尝试使用本地 Playwright（通过独立子进程运行，避免 AstrBot 的事件循环冲突）
        try:
            from jinja2 import Template
            import subprocess
            import asyncio
            import sys
            
            template = Template(STATUS_TEMPLATE)
            html_content = template.render(**report)
            
            script = """
import sys, os, uuid, tempfile
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(1)

# 强制使用 utf-8 解码，解决 Windows 下的中文乱码问题
html_content = sys.stdin.buffer.read().decode('utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 860})
    page.set_content(html_content, wait_until="networkidle")
    save_path = os.path.join(tempfile.gettempdir(), f"model_connectivity_pw_{uuid.uuid4().hex}.png")
    page.screenshot(path=save_path, full_page=True)
    browser.close()
    print(save_path, end="")
"""
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-c", script,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=html_content.encode('utf-8'))
            if process.returncode == 0:
                save_path = stdout.decode('utf-8').strip()
                if save_path and save_path.endswith('.png'):
                    return save_path
            else:
                err_msg = stderr.decode('utf-8', errors='ignore')
                logger.warning(f"本地 Playwright 子进程渲染失败: {err_msg}")
        except Exception as e:
            logger.warning(f"本地 Playwright 包装器执行异常: {e}")

        # 兜底使用远端渲染
        return await self.html_render(
            STATUS_TEMPLATE,
            report,
            options={
                "type": "png",
                "full_page": True,
                "timeout": int(self._cfg_float("render_timeout_seconds", 60.0) * 1000),
                "animations": "disabled",
            },
        )

    def _render_local_report_image(self, report: dict[str, Any]) -> str:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise RuntimeError("本地图片渲染需要安装 Pillow") from exc

        scale = self._image_scale()
        width = 1500
        padding = 48
        gap = 22
        header_height = 180
        card_width = (width - padding * 2 - gap) // 2
        theme = self._theme_palette(str(report.get("theme") or "dark"))

        fonts = {
            "title": self._load_pil_font(ImageFont, 64, bold=True),
            "h2": self._load_pil_font(ImageFont, 24, bold=True),
            "body": self._load_pil_font(ImageFont, 16, bold=True),
            "small": self._load_pil_font(ImageFont, 13, bold=True),
            "tiny": self._load_pil_font(ImageFont, 11, bold=True),
        }

        providers = report.get("providers", [])
        cards: list[dict[str, Any]] = []
        for provider in providers:
            model_heights = [self._model_row_height(item) for item in provider["results"]]
            card_height = 88 + 16 + sum(model_heights)
            if model_heights:
                card_height += 12 * (len(model_heights) - 1)
            card_height += 20
            cards.append(
                {
                    "provider": provider,
                    "model_heights": model_heights,
                    "height": card_height,
                }
            )

        positions: list[tuple[int, int, int, int, int]] = []
        column_y = [padding + header_height, padding + header_height]
        for index, card in enumerate(cards):
            column = 0 if column_y[0] <= column_y[1] else 1
            x = padding + column * (card_width + gap)
            y = column_y[column]
            positions.append((index, x, y, card_width, card["height"]))
            column_y[column] += card["height"] + gap

        content_bottom = max(column_y) - gap if cards else padding + header_height

        provider_errors = report.get("provider_errors", [])
        provider_error_height = 0
        if provider_errors:
            provider_error_height = 68 + len(provider_errors) * 24

        error_gap = gap if provider_errors else 0
        height = max(860, content_bottom + error_gap + provider_error_height + padding)
        image = Image.new("RGB", (width, height), theme["bg"])
        draw = ImageDraw.Draw(image)
        self._draw_grid(draw, width, height, theme)
        self._draw_report_header(draw, report, fonts, padding, width, theme)

        for index, x, y, w, h in positions:
            self._draw_provider_card(
                image,
                draw,
                cards[index]["provider"],
                cards[index]["model_heights"],
                x,
                y,
                w,
                h,
                fonts,
                theme,
            )

        if provider_errors:
            self._draw_provider_errors(
                draw,
                provider_errors,
                padding,
                content_bottom + gap,
                width - padding * 2,
                provider_error_height,
                fonts,
                theme,
            )

        output_dir = os.path.join(tempfile.gettempdir(), PLUGIN_NAME)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            f"model_connectivity_{int(time.time() * 1000)}.png",
        )
        if scale != 1:
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
        image.save(output_path, "PNG", optimize=True)
        return output_path

    def _image_scale(self) -> float:
        scale = self._cfg_float("image_scale", 2.0)
        if scale < 1:
            return 1.0
        if scale > 3:
            return 3.0
        return scale

    def _draw_report_header(
        self,
        draw: Any,
        report: dict[str, Any],
        fonts: dict[str, Any],
        padding: int,
        width: int,
        theme: dict[str, Any],
    ) -> None:
        draw.text(
            (padding, 58),
            str(report.get("title") or "模型连通性"),
            font=fonts["title"],
            fill=theme["text"],
        )

        pill_y = 190
        pill_x = padding
        pill_x = self._draw_pill(draw, pill_x, pill_y, f"{report.get('ok_count', 0)} 正常", fonts["small"], "ok", theme)
        pill_x = self._draw_pill(draw, pill_x + 8, pill_y, f"{report.get('slow_count', 0)} 较慢", fonts["small"], "slow", theme)
        pill_x = self._draw_pill(draw, pill_x + 8, pill_y, f"{report.get('error_count', 0)} 错误", fonts["small"], "error", theme)
        pill_x = self._draw_pill(draw, pill_x + 8, pill_y, f"{report.get('provider_count', 0)} 个 Provider", fonts["small"], None, theme)
        self._draw_pill(draw, pill_x + 8, pill_y, f"{report.get('total', 0)} 个模型", fonts["small"], None, theme)

        right_x = width - padding - 340
        self._draw_pill(
            draw,
            right_x + 150,
            118,
            str(report.get("overall_status") or "OPERATIONAL"),
            fonts["small"],
            "ok" if report.get("overall_status") == "OPERATIONAL" else "error",
            theme,
        )
        meta = (
            f"更新于 {report.get('generated_at')} · 耗时 {report.get('elapsed_ms')} ms\n"
            f"全局并发 {report.get('global_concurrency')} · "
            f"单 Provider {report.get('provider_concurrency')} · "
            f"统计 {report.get('stats_window_days')} 天 · "
            f"历史 {report.get('history_size')} 次"
        )
        draw.multiline_text(
            (right_x, 166),
            meta,
            font=fonts["small"],
            fill=theme["muted"],
            spacing=6,
            align="right",
        )

    def _draw_provider_card(
        self,
        image: Any,
        draw: Any,
        provider: dict[str, Any],
        model_heights: list[int],
        x: int,
        y: int,
        w: int,
        h: int,
        fonts: dict[str, Any],
        theme: dict[str, Any],
    ) -> None:
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=16,
            fill=theme["card"],
            outline=theme["outline"],
            width=1,
        )
        draw.line((x, y + 88, x + w, y + 88), fill=theme["line"], width=1)
        draw.rounded_rectangle(
            (x + 20, y + 20, x + 68, y + 68),
            radius=12,
            fill=theme["mark_bg"],
            outline=theme["mark_outline"],
        )
        icon = self._load_provider_icon_image(
            str(provider.get("provider_logo") or ""),
            theme,
            34,
        )
        if icon is not None:
            icon_x = x + 20 + (48 - icon.width) // 2
            icon_y = y + 20 + (48 - icon.height) // 2
            image.paste(icon, (icon_x, icon_y), icon if icon.mode == "RGBA" else None)
        else:
            initial = str(provider.get("provider_name") or "A")[:1].upper()
            initial_w = self._text_width(draw, initial, fonts["body"])
            draw.text((x + 20 + (48 - initial_w) // 2, y + 32), initial, font=fonts["body"], fill=theme["mark_text"])

        title = self._fit_text(
            draw,
            str(provider.get("provider_name") or "Provider"),
            fonts["h2"],
            w - 210,
        )
        draw.text((x + 82, y + 18), title, font=fonts["h2"], fill=theme["text"])
        subtitle = (
            f"{provider.get('provider_type')} · "
            f"{provider.get('provider_id')} · "
            f"{provider.get('model_count')} models"
        )
        subtitle = self._fit_text(draw, subtitle, fonts["small"], w - 210)
        draw.text((x + 82, y + 52), subtitle, font=fonts["small"], fill=theme["muted"])

        self._draw_status_badge(
            draw,
            x + w - 76,
            y + 29,
            str(provider.get("status_label") or ""),
            fonts["tiny"],
            str(provider.get("status") or "ok"),
            theme,
        )

        row_y = y + 104
        for item, row_height in zip(provider["results"], model_heights):
            self._draw_model_row(
                draw,
                item,
                x + 20,
                row_y,
                w - 40,
                row_height,
                fonts,
                theme,
            )
            row_y += row_height + 12

    def _draw_model_row(
        self,
        draw: Any,
        item: dict[str, Any],
        x: int,
        y: int,
        w: int,
        h: int,
        fonts: dict[str, Any],
        theme: dict[str, Any],
    ) -> None:
        status = str(item.get("status_class") or item.get("status") or "ok")
        colors = self._status_colors(status, theme)
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=12,
            fill=theme["panel"],
            outline=theme["outline"],
        )
        draw.ellipse((x + 12, y + 18, x + 20, y + 26), fill=colors["fg"])

        model_name = self._fit_text(
            draw,
            str(item.get("model") or ""),
            fonts["body"],
            w - 150,
        )
        draw.text((x + 28, y + 12), model_name, font=fonts["body"], fill=theme["text"])
        self._draw_status_badge(
            draw,
            x + w - 56,
            y + 12,
            str(item.get("status_label") or ""),
            fonts["tiny"],
            status,
            theme,
        )

        metric_y = y + 50
        metric_gap = 8
        metric_padding = 16
        metric_w = (w - metric_padding * 2 - metric_gap * 3) // 4
        metrics = [
            ("当前延迟", f"{item.get('latency_ms')} ms", theme["text"]),
            ("24h平均", str(item.get("avg_latency_24h") or "N/A"), theme["text"]),
            ("可用性", str(item.get("availability") or "0.00%"), colors["fg"]),
            ("周成功次数", str(item.get("weekly_success_text") or "0/0"), colors["fg"]),
        ]
        for index, (label, value, value_color) in enumerate(metrics):
            mx = x + metric_padding + index * (metric_w + metric_gap)
            draw.rounded_rectangle(
                (mx, metric_y, mx + metric_w, metric_y + 58),
                radius=10,
                fill=theme["metric"],
            )
            draw.text((mx + 10, metric_y + 9), label, font=fonts["tiny"], fill=theme["muted"])
            value = self._fit_text(draw, value, fonts["body"], metric_w - 20)
            draw.text((mx + 10, metric_y + 30), value, font=fonts["body"], fill=value_color)

        curve_y_offset = 124
        if item.get("show_curve_chart"):
            curve_pts = item.get("pillow_curve_points", [])
            if curve_pts:
                cw = w - metric_padding * 2
                ch = 40
                cx = x + metric_padding
                cy = y + 116
                scaled_pts = [(cx + pt[0] * cw / 100, cy + pt[1] * ch / 40) for pt in curve_pts]
                poly_pts = scaled_pts + [(cx + cw, cy + ch), (cx, cy + ch)]
                
                draw.polygon(poly_pts, fill=theme.get("curve_bg", theme["grid"]))
                draw.line(scaled_pts, fill=theme.get("curve_line", theme["outline"]), width=2)
                
                for label in item.get("time_labels", []):
                    lx = cx + (label["x_pct"] / 100) * cw
                    tw = self._text_width(draw, label["text"], fonts["tiny"])
                    lx = max(cx, min(lx - tw / 2, cx + cw - tw))
                    draw.text(
                        (lx, cy + ch + 4),
                        label["text"],
                        font=fonts["tiny"],
                        fill=theme["muted"]
                    )
            curve_y_offset += 76

        self._draw_history(
            draw,
            item.get("history", []),
            x + metric_padding,
            y + curve_y_offset,
            w - metric_padding * 2,
            12,
            theme,
        )

        if item.get("error"):
            error_text = self._fit_text(
                draw,
                str(item["error"]),
                fonts["small"],
                w - metric_padding * 2,
            )
            draw.text((x + metric_padding, y + curve_y_offset + 20), error_text, font=fonts["small"], fill=theme["error_text"])

    def _draw_provider_errors(
        self,
        draw: Any,
        errors: list[dict[str, Any]],
        x: int,
        y: int,
        w: int,
        h: int,
        fonts: dict[str, Any],
        theme: dict[str, Any],
    ) -> None:
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=8,
            fill=theme["error_panel"],
            outline=theme["error_outline"],
        )
        draw.text((x + 20, y + 16), "Provider 枚举异常", font=fonts["body"], fill=theme["error_text"])
        line_y = y + 44
        for item in errors:
            text = f"{item.get('provider_type')} · {item.get('provider_id')}: {item.get('error')}"
            text = self._fit_text(draw, text, fonts["small"], w - 40)
            draw.text((x + 20, line_y), text, font=fonts["small"], fill=theme["error_text"])
            line_y += 24

    def _load_provider_icon_image(
        self,
        logo: str,
        theme: dict[str, Any],
        size: int,
    ) -> Optional[Any]:
        if not logo:
            return None
        theme_name = str(theme.get("name") or "dark")
        cache_key = (logo, theme_name, size)
        cache = getattr(self, "_provider_icon_cache", None)
        if cache is None:
            cache = {}
            self._provider_icon_cache = cache
        if cache_key in cache:
            cached = cache[cache_key]
            return cached.copy() if cached is not None else None

        try:
            from PIL import Image

            data = self._read_provider_icon_bytes(logo, theme_name)
            if not data:
                cache[cache_key] = None
                return None
            if data.lstrip().startswith(b"<svg"):
                cache[cache_key] = None
                return None
            icon = Image.open(io.BytesIO(data)).convert("RGBA")
            icon.thumbnail((size, size), Image.Resampling.LANCZOS)
            cache[cache_key] = icon.copy()
            return icon
        except Exception as exc:
            logger.warning("Failed to load provider icon %s: %s", logo, exc)
            cache[cache_key] = None
            return None

    def _read_provider_icon_bytes(self, logo: str, theme_name: str) -> bytes:
        logo = logo.strip()
        if not logo:
            return b""
        if logo.startswith("data:"):
            return self._read_data_uri(logo)
        if logo.startswith("<svg"):
            return logo.encode("utf-8")

        icon_url = self._local_render_icon_url(logo, theme_name)
        parsed = urllib.parse.urlparse(icon_url)
        if parsed.scheme in ("http", "https"):
            request = urllib.request.Request(
                icon_url,
                headers={"User-Agent": f"{PLUGIN_NAME}/1.4.2"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                return response.read()

        path = Path(icon_url)
        if path.exists():
            return path.read_bytes()
        return b""

    def _read_data_uri(self, value: str) -> bytes:
        try:
            header, payload = value.split(",", 1)
        except ValueError:
            return b""
        if ";base64" in header:
            return base64.b64decode(payload)
        return urllib.parse.unquote_to_bytes(payload)

    def _local_render_icon_url(self, logo: str, theme_name: str) -> str:
        parsed = urllib.parse.urlparse(logo)
        path = parsed.path
        if "@lobehub/icons-static-svg" in logo and "/icons/" in path and path.endswith(".svg"):
            slug = path.rsplit("/", 1)[-1].removesuffix(".svg")
            png_theme = "dark" if theme_name == "dark" else "light"
            return (
                "https://cdn.jsdelivr.net/npm/"
                f"@lobehub/icons-static-png@latest/{png_theme}/{slug}.png"
            )
        return logo

    def _draw_grid(self, draw: Any, width: int, height: int, theme: dict[str, Any]) -> None:
        for x in range(0, width, 38):
            draw.line((x, 0, x, height), fill=theme["grid"], width=1)
        for y in range(0, height, 38):
            draw.line((0, y, width, y), fill=theme["grid"], width=1)

    def _draw_pill(
        self,
        draw: Any,
        x: int,
        y: int,
        text: str,
        font: Any,
        status: Optional[str] = None,
        theme: Optional[dict[str, Any]] = None,
    ) -> int:
        colors = self._status_colors(status or "neutral", theme)
        text_width = self._text_width(draw, text, font)
        pill_width = text_width + (34 if status else 22)
        draw.rounded_rectangle(
            (x, y, x + pill_width, y + 30),
            radius=15,
            fill=colors["bg"],
            outline=(34, 36, 38) if not theme else theme["outline"],
        )
        text_x = x + 12
        if status:
            draw.ellipse((x + 10, y + 11, x + 18, y + 19), fill=colors["fg"])
            text_x = x + 25
        draw.text((text_x, y + 7), text, font=font, fill=colors["fg"])
        return x + pill_width

    def _draw_status_badge(
        self,
        draw: Any,
        x: int,
        y: int,
        text: str,
        font: Any,
        status: str,
        theme: Optional[dict[str, Any]] = None,
    ) -> None:
        colors = self._status_colors(status, theme)
        text_width = self._text_width(draw, text, font)
        width = max(48, text_width + 18)
        draw.rounded_rectangle(
            (x, y, x + width, y + 24),
            radius=12,
            fill=colors["bg"],
            outline=(42, 45, 48) if not theme else theme["outline"],
        )
        draw.text((x + (width - text_width) // 2, y + 6), text, font=font, fill=colors["fg"])

    def _draw_history(
        self,
        draw: Any,
        history: list[str],
        x: int,
        y: int,
        w: int,
        h: int,
        theme: Optional[dict[str, Any]] = None,
    ) -> None:
        if not history:
            return
        gap = 3
        count = len(history)
        bar_width = max(3, int((w - gap * (count - 1)) / count))
        cursor_x = x
        for status in history:
            colors = self._status_colors(str(status), theme)
            draw.rounded_rectangle(
                (cursor_x, y, cursor_x + bar_width, y + h),
                radius=2,
                fill=colors["fg"],
            )
            cursor_x += bar_width + gap

    def _model_row_height(self, item: dict[str, Any]) -> int:
        h = 150
        if item.get("error"):
            h += 30
        if item.get("show_curve_chart"):
            h += 76
        return h

    def _status_colors(
        self,
        status: str,
        theme: Optional[dict[str, Any]] = None,
    ) -> dict[str, tuple[int, int, int]]:
        theme_name = (theme or {}).get("name", "dark")
        if theme_name == "light":
            if status == "ok":
                return {"fg": (0, 153, 100), "bg": (219, 252, 231)}
            if status == "slow":
                return {"fg": (180, 108, 0), "bg": (255, 243, 205)}
            if status == "error":
                return {"fg": (220, 38, 38), "bg": (254, 226, 226)}
            if status == "empty":
                return {"fg": (224, 229, 236), "bg": (224, 229, 236)}
            return {"fg": (55, 65, 81), "bg": (241, 245, 249)}

        if status == "ok":
            return {"fg": (24, 231, 141), "bg": (9, 54, 35)}
        if status == "slow":
            return {"fg": (255, 177, 26), "bg": (62, 44, 12)}
        if status == "error":
            return {"fg": (255, 77, 94), "bg": (62, 18, 25)}
        if status == "empty":
            return {"fg": (32, 34, 36), "bg": (32, 34, 36)}
        return {"fg": (217, 221, 229), "bg": (20, 22, 23)}

    def _theme_name(self, now: Optional[datetime] = None) -> str:
        mode = self._cfg_str("theme_mode", "auto").strip().lower()
        if mode in ("light", "day", "白天"):
            return "light"
        if mode in ("dark", "night", "夜间"):
            return "dark"

        now = now or datetime.now()
        start = self._normalize_hour(self._cfg_int("day_mode_start_hour", 8))
        end = self._normalize_hour(self._cfg_int("day_mode_end_hour", 18))
        current = now.hour + now.minute / 60
        if start == end:
            return "light"
        if start < end:
            return "light" if start <= current < end else "dark"
        return "light" if current >= start or current < end else "dark"

    def _normalize_hour(self, hour: int) -> int:
        return max(0, min(23, int(hour)))

    def _theme_palette(self, theme_name: str) -> dict[str, Any]:
        if theme_name == "light":
            return {
                "name": "light",
                "bg": (248, 250, 252),
                "grid": (226, 232, 240),
                "text": (15, 23, 42),
                "muted": (100, 116, 139),
                "card": (255, 255, 255),
                "panel": (248, 250, 252),
                "metric": (255, 255, 255),
                "outline": (226, 232, 240),
                "line": (226, 232, 240),
                "icon_bg": (15, 23, 42),
                "icon_text": (255, 255, 255),
                "mark_bg": (255, 255, 255),
                "mark_outline": (226, 232, 240),
                "mark_text": (15, 23, 42),
                "error_panel": (254, 242, 242),
                "error_outline": (254, 205, 211),
                "error_text": (159, 18, 57),
                "curve_bg": (224, 231, 255),
                "curve_line": (99, 102, 241),
            }
        return {
            "name": "dark",
            "bg": (10, 11, 12),
            "grid": (25, 28, 31),
            "text": (241, 245, 249),
            "muted": (148, 163, 184),
            "card": (15, 17, 19),
            "panel": (20, 23, 26),
            "metric": (15, 17, 19),
            "outline": (30, 41, 59),
            "line": (30, 41, 59),
            "icon_bg": (241, 245, 249),
            "icon_text": (15, 23, 42),
            "mark_bg": (20, 25, 30),
            "mark_outline": (51, 65, 85),
            "mark_text": (248, 250, 252),
            "error_panel": (60, 15, 20),
            "error_outline": (100, 25, 35),
            "error_text": (254, 163, 170),
            "curve_bg": (30, 27, 75),
            "curve_line": (139, 92, 246),
        }

    def _load_pil_font(self, ImageFont: Any, size: int, *, bold: bool = False) -> Any:
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_candidates = []
        if bold:
            font_candidates.extend(
                [
                    os.path.join(windir, "Fonts", "msyhbd.ttc"),
                    os.path.join(windir, "Fonts", "simhei.ttf"),
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                ]
            )
        font_candidates.extend(
            [
                os.path.join(windir, "Fonts", "msyh.ttc"),
                os.path.join(windir, "Fonts", "simsun.ttc"),
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _text_width(self, draw: Any, text: str, font: Any) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return int(bbox[2] - bbox[0])

    def _fit_text(self, draw: Any, text: str, font: Any, max_width: int) -> str:
        if self._text_width(draw, text, font) <= max_width:
            return text
        if max_width <= 20:
            return ""
        suffix = "..."
        available = max_width - self._text_width(draw, suffix, font)
        value = text
        while value and self._text_width(draw, value, font) > available:
            value = value[:-1]
        return value + suffix if value else suffix

    def _format_text_report(self, report: dict[str, Any]) -> str:
        lines = [
            f"{report.get('title', '模型连通性')}：{report.get('overall_status')}",
            (
                f"正常 {report.get('ok_count', 0)} / "
                f"较慢 {report.get('slow_count', 0)} / "
                f"错误 {report.get('error_count', 0)} / "
                f"总计 {report.get('total', 0)}"
            ),
            f"更新于 {report.get('generated_at')}，耗时 {report.get('elapsed_ms')} ms",
            "",
        ]
        for provider in report.get("providers", []):
            lines.append(
                f"[{provider.get('status_label')}] "
                f"{provider.get('provider_name')} ({provider.get('model_count')} models)"
            )
            for item in provider.get("results", []):
                line = (
                    f"- {item.get('model')}: {item.get('status_label')}, "
                    f"{item.get('latency_ms')} ms, "
                    f"周成功次数 {item.get('weekly_success_text')}, "
                    f"可用性 {item.get('availability')}"
                )
                if item.get("error"):
                    line += f", {item.get('error')}"
                lines.append(line)
            lines.append("")
        return "\n".join(lines).strip()

    async def _collect_probe_targets(self) -> tuple[list[ProbeTarget], list[dict[str, Any]]]:
        providers = list(self.context.get_all_providers() or [])
        self._refresh_skip_model_options(providers)
        skip_models = set(self._cfg_list("skip_models", []))
        provider_icons = self._provider_icon_map()
        provider_errors: list[dict[str, Any]] = []
        targets: list[ProbeTarget] = []
        seen_targets: set[tuple[str, str]] = set()

        for provider in providers:
            try:
                meta = provider.meta()
                provider_id = str(getattr(meta, "id", "") or "default")
                provider_type = str(getattr(meta, "type", "") or "unknown")
                provider_name = self._provider_display_name(provider, provider_type)
                provider_group_id = self._provider_group_id(provider, provider_id)
                provider_group_name = self._provider_group_name(
                    provider,
                    provider_group_id,
                    provider_name,
                )
                provider_logo = ""
                search_keys = [
                    str(provider_id).lower(),
                    str(provider_type).lower(),
                    str(provider_name).lower(),
                    str(provider_group_id).lower()
                ]
                
                # 1. Exact match
                for sk in search_keys:
                    if sk in provider_icons:
                        provider_logo = provider_icons[sk]
                        break
                        
                # 2. Prefix or token match
                if not provider_logo:
                    for sk in search_keys:
                        for icon_k, icon_v in provider_icons.items():
                            if sk.startswith(icon_k) or icon_k in sk.replace('-', '_').split('_'):
                                provider_logo = icon_v
                                break
                        if provider_logo:
                            break

                if not provider_logo:
                    # Fallback to metadata
                    try:
                        if hasattr(provider, "meta"):
                            meta_obj = provider.meta()
                            provider_logo = str(getattr(meta_obj, "logo", getattr(meta_obj, "icon", "")))
                    except Exception:
                        pass

                current_model = str(
                    provider.get_model() or getattr(meta, "model", "") or ""
                ).strip()
                models = await self._get_provider_models(provider, current_model)
                for model in models:
                    if self._is_model_skipped(
                        skip_models,
                        provider_id,
                        provider_group_id,
                        provider_group_name,
                        model,
                    ):
                        continue
                    target_key = (provider_group_id, model)
                    if target_key in seen_targets:
                        continue
                    seen_targets.add(target_key)
                    targets.append(
                        ProbeTarget(
                            provider=provider,
                            provider_id=provider_id,
                            provider_group_id=provider_group_id,
                            provider_type=provider_type,
                            provider_name=provider_name,
                            provider_group_name=provider_group_name,
                            current_model=current_model,
                            model=model,
                            provider_logo=provider_logo,
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to collect models from provider: %s", exc)
                provider_errors.append(
                    {
                        "provider_id": self._safe_provider_id(provider),
                        "provider_type": self._safe_provider_type(provider),
                        "error": self._short_error(exc),
                    }
                )

        return targets, provider_errors

    async def _get_provider_models(self, provider: Any, current_model: str) -> list[str]:
        if self._cfg_bool("detect_enabled_models_only", True):
            models = self._configured_models_from_provider(provider, current_model)
            max_models = self._cfg_int("max_models_per_provider", 0)
            if max_models > 0:
                models = models[:max_models]
            return models

        timeout_seconds = self._cfg_float("model_list_timeout_seconds", 20.0)
        max_models = self._cfg_int("max_models_per_provider", 0)

        models: list[str] = []
        try:
            raw_models = await asyncio.wait_for(provider.get_models(), timeout=timeout_seconds)
            models = [str(item).strip() for item in raw_models or [] if str(item).strip()]
        except Exception as exc:
            logger.warning("Failed to get provider model list, fallback to current model: %s", exc)

        if current_model:
            models.insert(0, current_model)

        models = self._deduplicate(models)
        if max_models > 0:
            models = models[:max_models]

        return models

    def _configured_model_from_provider(self, provider: Any) -> str:
        models = self._configured_models_from_provider(provider)
        return models[0] if models else ""

    def _configured_models_from_provider(
        self,
        provider: Any,
        current_model: str = "",
    ) -> list[str]:
        models: list[str] = []

        def add(value: Any) -> None:
            if value is None or isinstance(value, bool):
                return
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    add(item)
                return
            text = str(value).strip()
            if text:
                models.append(text)

        if current_model:
            add(current_model)

        for attr in ("get_model",):
            getter = getattr(provider, attr, None)
            if callable(getter):
                try:
                    add(getter())
                except Exception:
                    pass

        try:
            meta = provider.meta()
            add(getattr(meta, "model", ""))
        except Exception:
            pass

        for attr in (
            "model",
            "model_id",
            "model_name",
            "model_config",
            "models",
            "enabled_models",
            "configured_models",
            "provider_config",
            "config",
        ):
            try:
                self._collect_model_values(getattr(provider, attr, None), models)
            except Exception:
                continue

        return self._deduplicate(models)

    def _collect_model_values(self, value: Any, output: list[str]) -> None:
        if value is None or isinstance(value, bool):
            return

        if isinstance(value, str):
            text = value.strip()
            if text:
                output.append(text)
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                if isinstance(item, dict):
                    if not self._model_entry_enabled(item):
                        continue
                    for key in ("model", "model_id", "model_name", "id", "name", "value"):
                        candidate = item.get(key)
                        if candidate:
                            self._collect_model_values(candidate, output)
                            break
                else:
                    self._collect_model_values(item, output)
            return

        if not isinstance(value, dict):
            for dumper in ("model_dump", "dict"):
                method = getattr(value, dumper, None)
                if callable(method):
                    try:
                        dumped = method()
                    except Exception:
                        continue
                    if isinstance(dumped, dict):
                        self._collect_model_values(dumped, output)
                        return

            for key in ("model", "model_id", "model_name", "id", "name", "value"):
                try:
                    candidate = getattr(value, key, None)
                except Exception:
                    continue
                if candidate:
                    self._collect_model_values(candidate, output)
                    return
            return

        for key in ("model", "model_id", "model_name"):
            candidate = value.get(key)
            if candidate:
                self._collect_model_values(candidate, output)

        for key in (
            "model_config",
            "model_configs",
            "models",
            "enabled_models",
            "configured_models",
            "available_models",
            "model_list",
        ):
            if key in value:
                self._collect_model_values(value.get(key), output)

    def _model_entry_enabled(self, item: dict[str, Any]) -> bool:
        for key in ("enable", "enabled", "is_enabled", "active", "checked"):
            if key not in item:
                continue
            raw = item.get(key)
            if isinstance(raw, str):
                return raw.lower() in ("1", "true", "yes", "on", "是")
            return bool(raw)
        return True

    def _provider_icon_map(self) -> dict[str, str]:
        icons = getattr(self, "_provider_icons", None)
        if icons is None:
            icons = self._load_provider_icons()
            self._provider_icons = icons
        return icons

    def _load_provider_icons(self) -> dict[str, str]:
        icons = {key.lower(): value for key, value in PROVIDER_ICONS.items()}
        js_path = Path(__file__).with_name("providerUtils.js")
        if not js_path.exists():
            return icons
        try:
            text = js_path.read_text(encoding="utf-8")
            matches = re.findall(
                r"""['"]([^'"]+)['"]\s*:\s*['"]([^'"]+)['"]""",
                text,
            )
            for key, value in matches:
                if value.startswith(("http://", "https://", "data:", "<svg")):
                    icons[key.lower()] = value
        except Exception as exc:
            logger.warning("Failed to load provider icon mapping from providerUtils.js: %s", exc)
        return icons

    def _start_skip_model_options_refresh_task(self) -> None:
        if not self._cfg_bool("auto_refresh_skip_model_options", True):
            return
        if not self._skip_models_field_supports_options():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._skip_model_options_refresh_task = loop.create_task(
            self._delayed_refresh_skip_model_options()
        )

    async def _delayed_refresh_skip_model_options(self) -> None:
        for delay in (3, 10, 30, 60):
            await asyncio.sleep(delay)
            if self._refresh_skip_model_options():
                return

    def _refresh_skip_model_options(self, providers: Optional[list[Any]] = None) -> bool:
        if not self._cfg_bool("auto_refresh_skip_model_options", True):
            return False
        if not self._skip_models_field_supports_options():
            return False

        try:
            if providers is None:
                providers = list(self.context.get_all_providers() or [])
            options = self._configured_skip_model_options(providers)
            if not options:
                logger.info("Skip model options refresh skipped: no configured models found yet")
                return False
            return self._write_skip_model_options(options)
        except Exception as exc:
            logger.warning("Failed to refresh skip model options: %s", exc)
            return False

    def _refresh_skip_model_options_from_report(self, report: dict[str, Any]) -> bool:
        if not self._cfg_bool("auto_refresh_skip_model_options", True):
            return False

        options = self._skip_model_options_from_report(report)
        if not options:
            return False
        return self._write_skip_model_options(options)

    def _skip_model_options_from_report(self, report: dict[str, Any]) -> list[str]:
        options: list[str] = []
        seen: set[str] = set()
        for provider in report.get("providers", []):
            provider_id = str(
                provider.get("provider_id")
                or provider.get("provider_group_id")
                or provider.get("provider_name")
                or ""
            ).strip()
            for item in provider.get("results", []):
                model = str(item.get("model") or "").strip()
                if not model:
                    continue
                value = self._skip_model_option_value(provider_id, model)
                if value in seen:
                    continue
                seen.add(value)
                options.append(value)
        return sorted(options, key=str.lower)

    def _write_skip_model_options(self, options: list[str]) -> bool:
        if not options:
            return False
        schema_path = Path(__file__).with_name("_conf_schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        field = schema.get("skip_models")
        if not isinstance(field, dict):
            return False
        if field.get("type") != "list":
            return False
        if field.get("options") == options and "_special" not in field:
            return True
        field["options"] = options
        field.pop("_special", None)
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Refreshed skip model options: %s model(s)", len(options))
        return True

    def _skip_models_field_supports_options(self) -> bool:
        try:
            schema_path = Path(__file__).with_name("_conf_schema.json")
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            field = schema.get("skip_models")
            return isinstance(field, dict) and field.get("type") == "list"
        except Exception:
            return False

    def _configured_skip_model_options(self, providers: list[Any]) -> list[str]:
        options: list[str] = []
        seen: set[str] = set()
        for provider in providers:
            try:
                meta = provider.meta()
                provider_id = str(getattr(meta, "id", "") or "default")
                provider_group_id = self._provider_group_id(provider, provider_id)
                current_model = str(
                    provider.get_model() or getattr(meta, "model", "") or ""
                ).strip()
                for model in self._configured_models_from_provider(provider, current_model):
                    value = self._skip_model_option_value(provider_group_id, model)
                    if value in seen:
                        continue
                    seen.add(value)
                    options.append(value)
            except Exception:
                continue
        return sorted(options, key=str.lower)

    def _skip_model_option_value(self, provider_group_id: str, model: str) -> str:
        return f"{provider_group_id}/{model}" if provider_group_id else model

    def _is_model_skipped(
        self,
        skip_models: set[str],
        provider_id: str,
        provider_group_id: str,
        provider_group_name: str,
        model: str,
    ) -> bool:
        candidates = {
            model,
            self._skip_model_option_value(provider_group_id, model),
            self._skip_model_option_value(provider_group_name, model),
            self._skip_model_option_value(provider_id, model),
            f"{provider_group_id}::{model}",
            f"{provider_id}::{model}",
        }
        return any(candidate in skip_models for candidate in candidates if candidate)

    async def _probe_targets(self, targets: list[ProbeTarget]) -> list[dict[str, Any]]:
        global_concurrency = max(1, self._cfg_int("concurrency", 3))
        provider_concurrency = self._provider_concurrency_limit(global_concurrency)
        global_semaphore = asyncio.Semaphore(global_concurrency)
        provider_semaphores: dict[str, asyncio.Semaphore] = {}

        async def run_one(target: ProbeTarget) -> dict[str, Any]:
            provider_key = target.provider_group_id
            provider_semaphore = provider_semaphores.setdefault(
                provider_key,
                asyncio.Semaphore(provider_concurrency),
            )
            async with provider_semaphore:
                async with global_semaphore:
                    return await self._probe_one(target)

        gathered = await asyncio.gather(*(run_one(target) for target in targets))
        return list(gathered)

    def _provider_concurrency_limit(self, global_concurrency: int) -> int:
        configured = self._cfg("provider_concurrency", None)
        if configured is None:
            return 1 if self._cfg_bool("same_provider_sequential", True) else global_concurrency

        try:
            provider_concurrency = int(configured)
        except (TypeError, ValueError):
            provider_concurrency = 1

        if provider_concurrency <= 0:
            return 1 if self._cfg_bool("same_provider_sequential", True) else global_concurrency
        return provider_concurrency

    async def _probe_one(self, target: ProbeTarget) -> dict[str, Any]:
        timeout_seconds = self._cfg_float("timeout_seconds", 30.0)
        slow_threshold_ms = self._cfg_int("slow_threshold_ms", 8000)
        prompt = self._cfg_str("probe_prompt", "只回复 OK 两个字母。")
        system_prompt = self._cfg_str(
            "probe_system_prompt",
            "你是一个模型连通性探针。请只回复 OK，不要解释。",
        )

        started = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                target.provider.text_chat(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=target.model,
                ),
                timeout=timeout_seconds,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            completion_text = str(getattr(response, "completion_text", "") or "").strip()
            status = "slow" if latency_ms >= slow_threshold_ms else "ok"
            return self._result_payload(
                target=target,
                status=status,
                latency_ms=latency_ms,
                response_preview=completion_text[:80],
            )
        except asyncio.TimeoutError:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return self._result_payload(
                target=target,
                status="error",
                latency_ms=latency_ms,
                error=f"timeout after {timeout_seconds:g}s",
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return self._result_payload(
                target=target,
                status="error",
                latency_ms=latency_ms,
                error=self._short_error(exc),
            )

    async def _build_report(
        self,
        results: list[dict[str, Any]],
        provider_errors: list[dict[str, Any]],
        started_at: float,
    ) -> dict[str, Any]:
        history_size = max(1, self._cfg_int("history_size", 30))
        stats_days = max(1, self._cfg_int("stats_window_days", 7))
        show_error_detail = self._cfg_bool("show_error_detail", True)
        now = datetime.now()
        theme = self._theme_name(now)
        history = await self._load_history()

        for result in results:
            history_key = result["history_key"]
            history_size = self._cfg_int("history_size", 30)
            show_curve = self._cfg_bool("show_curve_chart", True)
            interval_str = self._auto_check_interval_label()
            
            result["show_curve_chart"] = show_curve
            result["interval_str"] = interval_str

            records = history.get(history_key, [])
            if not isinstance(records, list):
                records = []
            records = self._prune_history_records(
                records,
                now,
                stats_days,
                history_size,
            )
            records.append(
                {
                    "status": result["status"],
                    "latency_ms": result["latency_ms"],
                    "checked_at": now.isoformat(timespec="seconds"),
                }
            )
            records = records[
                -max(history_size, self._cfg_int("max_history_records", 500)) :
            ]
            history[history_key] = records
            result["history"] = self._history_bars(records, history_size)
            
            if show_curve:
                latencies = self._history_latencies(records, history_size)
                svg_line = self._generate_svg_path(latencies, 100, 40)
                result["svg_path_line"] = svg_line
                result["svg_path_area"] = f"{svg_line} L 100,40 L 0,40 Z" if svg_line else ""
                result["pillow_curve_points"] = self._generate_curve_points(latencies, 100, 40)
                result["time_labels"] = self._history_time_labels(records, history_size)
            
            records_24h = self._records_in_hours(records, now, 24)
            valid_lats = [int(rec.get("latency_ms", 0)) for rec in records_24h if rec.get("status") in ("ok", "slow")]
            if valid_lats:
                avg_lat = sum(valid_lats) // len(valid_lats)
                result["avg_latency_24h"] = f"{avg_lat} ms"
            else:
                result["avg_latency_24h"] = "N/A"
            
            window_records = self._records_in_days(records, now, stats_days)
            result["weekly_success_count"], result["weekly_total_count"] = (
                self._success_total_counts(window_records)
            )
            result["weekly_success_text"] = (
                f"{result['weekly_success_count']}/{result['weekly_total_count']}"
            )
            result["availability"] = self._availability(window_records)
            result["status_label"] = self._status_label(result["status"])
            result["status_class"] = result["status"]
            if not show_error_detail:
                result["error"] = ""

        await self._save_history(history)

        grouped: dict[str, dict[str, Any]] = {}
        for result in results:
            key = result["provider_id"]
            if key not in grouped:
                logo = str(result.get("provider_logo") or "")
                grouped[key] = {
                    "provider_id": result["provider_id"],
                    "provider_type": result["provider_type"],
                    "provider_name": result["provider_name"],
                    "provider_logo": self._local_render_icon_url(logo, theme) if logo else "",
                    "current_model": result["current_model"],
                    "results": [],
                    "ok_count": 0,
                    "slow_count": 0,
                    "error_count": 0,
                    "status": "ok",
                    "status_label": "正常",
                }
            provider_group = grouped[key]
            provider_group["results"].append(result)
            provider_group[f"{result['status']}_count"] += 1

        providers = list(grouped.values())
        for provider_group in providers:
            if provider_group["error_count"]:
                provider_group["status"] = "error"
                provider_group["status_label"] = "异常"
            elif provider_group["slow_count"]:
                provider_group["status"] = "slow"
                provider_group["status_label"] = "较慢"
            provider_group["model_count"] = len(provider_group["results"])

        total = len(results)
        ok_count = sum(1 for item in results if item["status"] == "ok")
        slow_count = sum(1 for item in results if item["status"] == "slow")
        error_count = sum(1 for item in results if item["status"] == "error")
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

        return {
            "title": self._cfg_str("dashboard_title", "模型连通性"),
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_ms": elapsed_ms,
            "global_concurrency": max(1, self._cfg_int("concurrency", 3)),
            "provider_concurrency": self._provider_concurrency_limit(
                max(1, self._cfg_int("concurrency", 3))
            ),
            "total": total,
            "ok_count": ok_count,
            "slow_count": slow_count,
            "error_count": error_count,
            "provider_count": len(providers),
            "providers": providers,
            "provider_errors": provider_errors,
            "overall_status": "OPERATIONAL" if error_count == 0 else "DEGRADED",
            "overall_class": "ok" if error_count == 0 else "error",
            "history_size": history_size,
            "stats_window_days": stats_days,
            "theme": theme,
            "theme_label": "白天" if theme == "light" else "夜间",
        }

    def _result_payload(
        self,
        *,
        target: ProbeTarget,
        status: str,
        latency_ms: int,
        response_preview: str = "",
        error: str = "",
    ) -> dict[str, Any]:
        is_current = target.model == target.current_model
        return {
            "provider_id": target.provider_group_id,
            "provider_group_id": target.provider_group_id,
            "provider_type": target.provider_type,
            "provider_name": target.provider_group_name,
            "provider_logo": target.provider_logo,
            "provider_instance_id": target.provider_id,
            "provider_instance_name": target.provider_name,
            "current_model": target.current_model,
            "model": target.model,
            "is_current": is_current,
            "status": status,
            "latency_ms": latency_ms,
            "response_preview": response_preview,
            "error": error,
            "history_key": f"{target.provider_id}::{target.model}",
        }

    async def _load_history(self) -> dict[str, Any]:
        if not self._cfg_bool("enable_history", True):
            return {}
        try:
            data = await self.get_kv_data("probe_history", {})
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("Failed to load probe history: %s", exc)
            return {}

    async def _save_history(self, history: dict[str, Any]) -> None:
        if not self._cfg_bool("enable_history", True):
            return
        try:
            await self.put_kv_data("probe_history", history)
        except Exception as exc:
            logger.warning("Failed to save probe history: %s", exc)

    def _history_bars(self, records: list[dict[str, Any]], history_size: int) -> list[str]:
        statuses = [str(item.get("status") or "unknown") for item in records[-history_size:]]
        padding = ["empty"] * max(0, history_size - len(statuses))
        return padding + statuses

    def _history_latencies(self, records: list[dict[str, Any]], history_size: int) -> list[int]:
        lats = [int(item.get("latency_ms") or 0) for item in records[-history_size:]]
        padding = [0] * max(0, history_size - len(lats))
        return padding + lats

    def _generate_svg_path(self, latencies: list[int], width: int, height: int) -> str:
        if not latencies:
            return ""
        max_lat = max(latencies + [1000])
        max_lat = max(max_lat, 1)
        n = len(latencies)
        if n == 1:
            y = height - (latencies[0] / max_lat * height)
            return f"M 0,{y:.1f} L {width},{y:.1f}"
        step = width / (n - 1)
        points = [(i * step, height - (lat / max_lat * height)) for i, lat in enumerate(latencies)]
        path = [f"M {points[0][0]:.1f},{points[0][1]:.1f}"]
        for i in range(1, n):
            prev = points[i-1]
            curr = points[i]
            cx1 = prev[0] + step / 2
            cx2 = curr[0] - step / 2
            path.append(f"C {cx1:.1f},{prev[1]:.1f} {cx2:.1f},{curr[1]:.1f} {curr[0]:.1f},{curr[1]:.1f}")
        return " ".join(path)

    def _generate_curve_points(self, latencies: list[int], width: int, height: int) -> list[tuple[float, float]]:
        if not latencies:
            return []
        max_lat = max(latencies + [1000])
        max_lat = max(max_lat, 1)
        n = len(latencies)
        if n == 1:
            y = height - (latencies[0] / max_lat * height)
            return [(0, y), (width, y)]
        step = width / (n - 1)
        base = [(i * step, height - (lat / max_lat * height)) for i, lat in enumerate(latencies)]
        
        def sample(p0, p1, p2, p3):
            pts = []
            for i in range(11):
                t = i / 10
                u = 1 - t
                x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
                y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
                pts.append((x, y))
            return pts

        curve = []
        for i in range(1, n):
            p0 = base[i-1]
            p3 = base[i]
            p1 = (p0[0] + step / 2, p0[1])
            p2 = (p3[0] - step / 2, p3[1])
            seg = sample(p0, p1, p2, p3)
            curve.extend(seg if i == 1 else seg[1:])
        return curve

    def _history_time_labels(self, records: list[dict[str, Any]], history_size: int) -> list[dict[str, Any]]:
        actual_records = records[-history_size:]
        n = max(history_size, len(actual_records))
        if n <= 1 or not actual_records:
            return []
            
        pad_len = history_size - len(actual_records)
        labels = []
        num_labels = 4 if len(actual_records) >= 4 else len(actual_records)
        if num_labels <= 1:
            return []
        indices = [int(i * (len(actual_records) - 1) / (num_labels - 1)) for i in range(num_labels)]
        
        last_pct = -100.0
        for i in indices:
            rec = actual_records[i]
            checked_at = self._parse_checked_at(rec.get("checked_at"))
            if not checked_at:
                continue
            x_pct = (pad_len + i) / (n - 1) * 100
            if x_pct - last_pct < 15:
                continue
            last_pct = x_pct
            
            style = f"left: {x_pct}%; transform: translateX(-50%);"
            if x_pct <= 5:
                style = f"left: {x_pct}%;"
            elif x_pct >= 95:
                style = f"right: {100 - x_pct}%;"
                
            labels.append({
                "text": checked_at.strftime("%H:%M"),
                "x_pct": x_pct,
                "style": style
            })
            
        return labels

    def _prune_history_records(
        self,
        records: list[dict[str, Any]],
        now: datetime,
        stats_days: int,
        history_size: int,
    ) -> list[dict[str, Any]]:
        window_start = now - timedelta(days=stats_days)
        max_records = max(history_size, self._cfg_int("max_history_records", 500))
        kept: list[dict[str, Any]] = []
        for record in records:
            checked_at = self._parse_checked_at(record.get("checked_at"))
            if checked_at is None or checked_at >= window_start:
                kept.append(record)
        return kept[-max_records:]

    def _records_in_days(
        self,
        records: list[dict[str, Any]],
        now: datetime,
        days: int,
    ) -> list[dict[str, Any]]:
        window_start = now - timedelta(days=days)
        result: list[dict[str, Any]] = []
        for record in records:
            checked_at = self._parse_checked_at(record.get("checked_at"))
            if checked_at is None or checked_at >= window_start:
                result.append(record)
        return result

    def _records_in_hours(
        self,
        records: list[dict[str, Any]],
        now: datetime,
        hours: int,
    ) -> list[dict[str, Any]]:
        window_start = now - timedelta(hours=hours)
        result: list[dict[str, Any]] = []
        for record in records:
            checked_at = self._parse_checked_at(record.get("checked_at"))
            if checked_at is None or checked_at >= window_start:
                result.append(record)
        return result

    def _parse_checked_at(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _success_total_counts(self, records: list[dict[str, Any]]) -> tuple[int, int]:
        success = sum(1 for item in records if item.get("status") in ("ok", "slow"))
        return success, len(records)

    def _availability(self, records: list[dict[str, Any]]) -> str:
        if not records:
            return "0.00%"
        reachable = sum(1 for item in records if item.get("status") in ("ok", "slow"))
        return f"{reachable / len(records) * 100:.2f}%"

    def _provider_display_name(self, provider: Any, fallback: str) -> str:
        provider_config = getattr(provider, "provider_config", {}) or {}
        for key in ("display_name", "name", "id"):
            value = provider_config.get(key)
            if value:
                return str(value)
        return fallback

    def _provider_group_id(self, provider: Any, provider_id: str) -> str:
        provider_config = getattr(provider, "provider_config", {}) or {}
        value = provider_config.get("provider_source_id")
        return str(value).strip() if value else provider_id

    def _provider_group_name(
        self,
        provider: Any,
        provider_group_id: str,
        provider_name: str,
    ) -> str:
        provider_config = getattr(provider, "provider_config", {}) or {}
        if provider_config.get("provider_source_id"):
            return provider_group_id
        return provider_name

    def _safe_provider_id(self, provider: Any) -> str:
        try:
            return str(provider.meta().id)
        except Exception:
            return "unknown"

    def _safe_provider_type(self, provider: Any) -> str:
        try:
            return str(provider.meta().type)
        except Exception:
            return "unknown"

    def _short_error(self, exc: Exception, limit: int = 120) -> str:
        text = f"{type(exc).__name__}: {exc}".strip()
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "..."

    def _status_label(self, status: str) -> str:
        return {"ok": "正常", "slow": "较慢", "error": "错误"}.get(status, "未知")

    def _deduplicate(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    def _cfg_str(self, key: str, default: str) -> str:
        value = self._cfg(key, default)
        return str(value) if value is not None else default

    def _cfg_int(self, key: str, default: int) -> int:
        try:
            return int(self._cfg(key, default))
        except (TypeError, ValueError):
            return default

    def _cfg_float(self, key: str, default: float) -> float:
        try:
            return float(self._cfg(key, default))
        except (TypeError, ValueError):
            return default

    def _cfg_bool(self, key: str, default: bool) -> bool:
        value = self._cfg(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on", "是")
        return bool(value)

    def _cfg_list(self, key: str, default: list[str]) -> list[str]:
        value = self._cfg(key, default)
        if isinstance(value, list):
            return [str(v).strip() for v in value]
        if isinstance(value, str):
            return [v.strip() for v in re.split(r"[,，;；\n\r]+", value) if v.strip()]
        return default

    def _cfg(self, key: str, default: Any) -> Any:
        try:
            value = self.config.get(key, default)
        except AttributeError:
            return default
        return default if value is None else value


STATUS_TEMPLATE = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap');
    
    * { box-sizing: border-box; }

    body {
      margin: 0;
      width: 1500px;
      min-height: 860px;
      color: #f5f7fb;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: 
        radial-gradient(circle at 15% 50%, rgba(20, 255, 140, 0.08), transparent 30%),
        radial-gradient(circle at 85% 30%, rgba(255, 77, 94, 0.08), transparent 30%),
        radial-gradient(circle at 50% 80%, rgba(26, 177, 255, 0.08), transparent 30%),
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        #0a0b0c;
      background-size: 100% 100%, 100% 100%, 100% 100%, 38px 38px, 38px 38px;
    }

    .page { padding: 48px; }

    .topline {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 40px;
    }

    .eyebrow {
      display: flex;
      align-items: center;
      gap: 12px;
      color: #9499a3;
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    .pulse-icon {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border-radius: 10px;
      color: #000;
      background: linear-gradient(135deg, #fff, #e0e5ec);
      box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15);
      font-size: 16px;
    }

    h1 {
      margin: 16px 0 16px;
      font-size: 64px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: -1px;
      background: linear-gradient(135deg, #ffffff, #a0a5b0);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .summary {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      color: #a7abb2;
      font-size: 14px;
      font-weight: 700;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 14px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(20px) saturate(150%);
      -webkit-backdrop-filter: blur(20px) saturate(150%);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
      color: #d9dde5;
    }

    .pill.ok { color: #18e78d; background: linear-gradient(135deg, rgba(11, 159, 93, 0.2), rgba(11, 159, 93, 0.05)); border-color: rgba(24, 231, 141, 0.3); box-shadow: 0 0 15px rgba(24, 231, 141, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }
    .pill.slow { color: #ffb11a; background: linear-gradient(135deg, rgba(255, 177, 26, 0.2), rgba(255, 177, 26, 0.05)); border-color: rgba(255, 177, 26, 0.3); box-shadow: 0 0 15px rgba(255, 177, 26, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }
    .pill.error { color: #ff4d5e; background: linear-gradient(135deg, rgba(255, 77, 94, 0.2), rgba(255, 77, 94, 0.05)); border-color: rgba(255, 77, 94, 0.3); box-shadow: 0 0 15px rgba(255, 77, 94, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 8px currentColor;
    }

    .right-meta {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 12px;
      padding-top: 80px;
      color: #7d828c;
      font-size: 13px;
      font-weight: 500;
    }

    .overall {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 12px 20px;
      border-radius: 999px;
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(30px) saturate(150%);
      -webkit-backdrop-filter: blur(30px) saturate(150%);
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.5px;
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .overall.ok .dot { color: #18e78d; box-shadow: 0 0 8px #18e78d; }
    .overall.slow .dot { color: #ffb11a; box-shadow: 0 0 8px #ffb11a; }
    .overall.error .dot { color: #ff4d5e; box-shadow: 0 0 8px #ff4d5e; }

    .grid {
      column-count: 2;
      column-gap: 24px;
    }

    .provider-card {
      display: inline-block;
      width: 100%;
      margin: 0 0 24px;
      break-inside: avoid;
      page-break-inside: avoid;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%);
      backdrop-filter: blur(40px) saturate(180%);
      -webkit-backdrop-filter: blur(40px) saturate(180%);
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.1);
      overflow: hidden;
    }

    .provider-head {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(0, 0, 0, 0.15);
    }

    .provider-icon {
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      width: 52px;
      height: 52px;
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.2);
      font-size: 20px;
      font-weight: 800;
    }

    .provider-icon svg {
      width: 24px;
      height: 24px;
      fill: currentColor !important;
    }

    .provider-icon svg path {
      fill: currentColor !important;
    }

    .provider-icon img {
      filter: brightness(0) invert(1);
    }

    .provider-info h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 800;
      color: #f5f7fb;
    }

    .provider-info p {
      margin: 6px 0 0;
      color: #a0a5b0;
      font-size: 13px;
      font-weight: 600;
    }

    .provider-status {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 800;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02));
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .provider-status.ok, .status-badge.ok { color: #18e78d; border-color: rgba(24, 231, 141, 0.4); box-shadow: 0 0 10px rgba(24, 231, 141, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(11, 159, 93, 0.3), rgba(11, 159, 93, 0.1)); }
    .provider-status.slow, .status-badge.slow { color: #ffb11a; border-color: rgba(255, 177, 26, 0.4); box-shadow: 0 0 10px rgba(255, 177, 26, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(255, 177, 26, 0.3), rgba(255, 177, 26, 0.1)); }
    .provider-status.error, .status-badge.error { color: #ff4d5e; border-color: rgba(255, 77, 94, 0.4); box-shadow: 0 0 10px rgba(255, 77, 94, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(255, 77, 94, 0.3), rgba(255, 77, 94, 0.1)); }

    .models {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .model-row {
      position: relative;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
      padding: 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    }

    .curve-container {
      position: relative;
      height: 48px;
      margin-bottom: 24px;
      margin-top: -4px;
    }

    .curve-chart {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      opacity: 0.8;
      pointer-events: none;
      overflow: visible;
    }

    .curve-chart .area { fill: url(#curve-gradient-dark); }
    .curve-chart .line { fill: none; stroke: #8b5cf6; stroke-width: 1.5; vector-effect: non-scaling-stroke; }
    .light .curve-chart .area { fill: url(#curve-gradient-light); }
    .light .curve-chart .line { stroke: #6366f1; vector-effect: non-scaling-stroke; }

    .time-axis {
      position: absolute;
      left: 0;
      right: 0;
      bottom: -16px;
      height: 16px;
    }

    .time-axis span {
      position: absolute;
      transform: translateX(-50%);
      font-size: 10px;
      color: #7d828c;
      font-weight: 600;
      white-space: nowrap;
    }
    
    .light .time-axis span { color: #94a3b8; }

    .model-top, .metric-grid, .history, .error-text {
      position: relative;
      z-index: 1;
      pointer-events: none;
    }

    .model-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .model-name {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 10px;
      font-size: 17px;
      font-weight: 800;
    }

    .model-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex: 0 0 auto;
      box-shadow: 0 0 10px currentColor;
    }

    .model-dot.ok { color: #16d586; background: #16d586; }
    .model-dot.slow { color: #ffb11a; background: #ffb11a; }
    .model-dot.error { color: #ff3048; background: #ff3048; }

    .status-badge {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 800;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02));
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }

    .metric {
      min-width: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 12px 16px;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    }

    .metric label {
      display: block;
      color: #8b9099;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }

    .metric strong {
      display: block;
      color: #ffffff;
      font-size: 18px;
      font-weight: 900;
    }

    .metric strong.availability.ok { color: #18e78d; }
    .metric strong.availability.slow { color: #ffb11a; }
    .metric strong.availability.error { color: #ff4d5e; }

    .history {
      display: flex;
      align-items: flex-end;
      gap: 4px;
      height: 16px;
    }

    .bar {
      flex: 1 1 0;
      min-width: 4px;
      border-radius: 2px;
      background: rgba(255, 255, 255, 0.08);
      transition: height 0.3s ease;
    }

    .bar.ok { height: 100%; background: #10c783; box-shadow: 0 0 6px rgba(16, 199, 131, 0.4); }
    .bar.slow { height: 100%; background: #ffb11a; box-shadow: 0 0 6px rgba(255, 177, 26, 0.4); }
    .bar.error { height: 100%; background: #ff3048; box-shadow: 0 0 6px rgba(255, 48, 72, 0.4); }
    .bar.empty { height: 100%; opacity: 0.3; }

    .error-text {
      margin-top: 12px;
      color: #ff98a2;
      font-size: 13px;
      line-height: 1.5;
      padding: 10px 12px;
      background: rgba(255, 48, 72, 0.08);
      border-radius: 8px;
      border: 1px solid rgba(255, 48, 72, 0.15);
    }

    body.light {
      color: #111827;
      background: 
        radial-gradient(circle at 15% 50%, rgba(20, 255, 140, 0.2), transparent 35%),
        radial-gradient(circle at 85% 30%, rgba(255, 77, 94, 0.2), transparent 35%),
        radial-gradient(circle at 50% 80%, rgba(26, 177, 255, 0.2), transparent 35%),
        linear-gradient(rgba(255, 255, 255, 0.5) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.5) 1px, transparent 1px),
        #f0f4f8;
      background-size: 100% 100%, 100% 100%, 100% 100%, 38px 38px, 38px 38px;
    }

    .light h1 {
      background: linear-gradient(135deg, #111827, #4b5563);
      -webkit-background-clip: text;
    }

    .light .provider-card {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.3) 100%);
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .provider-head {
      background: rgba(255, 255, 255, 0.4);
      border-bottom-color: rgba(0, 0, 0, 0.05);
    }

    .light .provider-icon {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.5) 100%);
      border: 1px solid rgba(255, 255, 255, 1);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), inset 0 1px 2px rgba(255, 255, 255, 1);
      color: #111827;
    }

    .light .provider-icon img {
      filter: brightness(0);
    }

    .light .provider-info h2,
    .light .model-name,
    .light .metric strong { color: #111827; }

    .light .provider-info p,
    .light .right-meta,
    .light .metric label,
    .light .eyebrow { color: #64748b; }

    .light .pill, .light .overall {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.5) 100%);
      color: #334155;
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .pill.ok { color: #059669; border-color: rgba(16, 185, 129, 0.4); background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)); }
    .light .pill.slow { color: #d97706; border-color: rgba(245, 158, 11, 0.4); background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05)); }
    .light .pill.error { color: #e11d48; border-color: rgba(225, 29, 72, 0.4); background: linear-gradient(135deg, rgba(225, 29, 72, 0.15), rgba(225, 29, 72, 0.05)); }
    
    .light .overall.ok .dot { color: #059669; box-shadow: 0 0 8px rgba(5, 150, 105, 0.5); }
    .light .overall.slow .dot { color: #d97706; box-shadow: 0 0 8px rgba(217, 119, 6, 0.5); }
    .light .overall.error .dot { color: #e11d48; box-shadow: 0 0 8px rgba(225, 29, 72, 0.5); }

    .light .model-row {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.6) 0%, rgba(255, 255, 255, 0.3) 100%);
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .metric {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.4) 100%);
      border-color: rgba(255, 255, 255, 0.9);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .bar.empty { background: #e2e8f0; }

    .light .provider-status, .light .status-badge { 
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.4) 100%); 
      border-color: rgba(255, 255, 255, 0.9);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 1);
    }
  </style>
</head>
<body class="{{ theme }}">
  <svg width="0" height="0" style="position:absolute;">
    <defs>
      <linearGradient id="curve-gradient-dark" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="rgba(139, 92, 246, 0.5)" />
        <stop offset="100%" stop-color="rgba(139, 92, 246, 0.0)" />
      </linearGradient>
      <linearGradient id="curve-gradient-light" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="rgba(99, 102, 241, 0.3)" />
        <stop offset="100%" stop-color="rgba(99, 102, 241, 0.0)" />
      </linearGradient>
    </defs>
  </svg>
  <main class="page">
    <section class="topline">
      <div>
        <h1>{{ title }}</h1>
        <div class="summary">
          <span class="pill ok"><span class="dot"></span>{{ ok_count }} 正常</span>
          <span class="pill slow"><span class="dot"></span>{{ slow_count }} 较慢</span>
          <span class="pill error"><span class="dot"></span>{{ error_count }} 错误</span>
          <span class="pill">{{ provider_count }} 个 Provider</span>
          <span class="pill">{{ total }} 个模型</span>
        </div>
      </div>
      <div class="right-meta">
        <div class="overall {{ overall_class }}"><span class="dot"></span>{{ overall_status }}</div>
        <div>更新于 {{ generated_at }} · 耗时 {{ elapsed_ms }} ms</div>
        <div>全局并发 {{ global_concurrency }} · 单 Provider {{ provider_concurrency }} · 统计 {{ stats_window_days }} 天 · 历史 {{ history_size }} 次</div>
      </div>
    </section>

    <section class="grid">
      {% for provider in providers %}
      <article class="provider-card">
        <header class="provider-head">
          <div class="provider-icon">
            {% if provider.provider_logo and provider.provider_logo.startswith('http') %}
              <img src="{{ provider.provider_logo }}" alt="logo" style="width:24px; height:24px; object-fit:contain;" />
            {% elif provider.provider_logo and '<svg' in provider.provider_logo %}
              {{ provider.provider_logo | safe }}
            {% else %}
              {{ provider.provider_name[:1] | upper }}
            {% endif %}
          </div>
          <div class="provider-info">
            <h2>{{ provider.provider_name }}</h2>
            <p>{{ provider.provider_type }} · {{ provider.provider_id }} · {{ provider.model_count }} models</p>
          </div>
          <div class="provider-status {{ provider.status }}">{{ provider.status_label }}</div>
        </header>

        <div class="models">
          {% for item in provider.results %}
          <div class="model-row">
            <div class="model-top">
              <div class="model-name">
                <span class="model-dot {{ item.status_class }}"></span>
                <span>{{ item.model }}</span>
              </div>
              <div class="status-badge {{ item.status_class }}">{{ item.status_label }}</div>
            </div>

            <div class="metric-grid">
              <div class="metric">
                <label>当前延迟</label>
                <strong>{{ item.latency_ms }} ms</strong>
              </div>
              <div class="metric">
                <label>24h平均</label>
                <strong>{{ item.avg_latency_24h }}</strong>
              </div>
              <div class="metric">
                <label>可用性</label>
                <strong class="availability {{ item.status_class }}">{{ item.availability }}</strong>
              </div>
              <div class="metric">
                <label>周成功次数</label>
                <strong class="availability {{ item.status_class }}">{{ item.weekly_success_text }}</strong>
              </div>
            </div>

            {% if item.show_curve_chart %}
            <div class="curve-container">
              <svg class="curve-chart" viewBox="0 0 100 40" preserveAspectRatio="none">
                <path d="{{ item.svg_path_area }}" class="area" />
                <path d="{{ item.svg_path_line }}" class="line" />
              </svg>
              <div class="time-axis">
                {% for label in item.time_labels %}
                <span style="{{ label.style }}">{{ label.text }}</span>
                {% endfor %}
              </div>
            </div>
            {% endif %}

            <div class="history" title="最近 {{ history_size }} 次检测">
              {% for status in item.history %}
              <span class="bar {{ status }}"></span>
              {% endfor %}
            </div>

            {% if item.error %}
            <div class="error-text">{{ item.error }}</div>
            {% endif %}
          </div>
          {% endfor %}
        </div>
      </article>
      {% endfor %}
    </section>

    {% if provider_errors %}
    <section class="provider-errors">
      <h3>Provider 枚举异常</h3>
      {% for item in provider_errors %}
      <p>{{ item.provider_type }} · {{ item.provider_id }}：{{ item.error }}</p>
      {% endfor %}
    </section>
    {% endif %}
  </main>
</body>
</html>
"""
