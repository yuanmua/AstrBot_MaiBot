#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 桌面版入口
=================
- Windows: PySide6 WebView 双标签页 (AstrBot + NapCatQQ)
- Linux 无桌面: 命令行模式
- 自动启动 NapCatQQ 并获取 Token
- 支持 --dev 模式打开日志终端

NapCatQQ 是否启用由打包时决定（如果构建时配置了 napcat 路径，就会嵌入）
"""

import argparse
import asyncio
import logging
import os
import platform
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

import runtime_bootstrap

runtime_bootstrap.initialize_runtime_bootstrap()

from astrbot.core import LogBroker, LogManager, db_helper, logger  # noqa: E402
from astrbot.core.config.default import VERSION  # noqa: E402
from astrbot.core.initial_loader import InitialLoader  # noqa: E402
from astrbot.core.utils.astrbot_path import (  # noqa: E402
    get_astrbot_config_path,
    get_astrbot_data_path,
    get_astrbot_knowledge_base_path,
    get_astrbot_plugin_path,
    get_astrbot_root,
    get_astrbot_site_packages_path,
    get_astrbot_temp_path,
)
from astrbot.core.utils.io import (  # noqa: E402
    download_dashboard,
    get_dashboard_version,
)
# 将父目录添加到 sys.path
sys.path.append(Path(__file__).parent.as_posix())

logo_tmpl = r"""
     ___           _______.___________..______      .______     ______   .___________.
    /   \         /       |           ||   _  \     |   _  \   /  __  \  |           |
   /  ^  \       |   (----`---|  |----`|  |_)  |    |  |_)  | |  |  |  | `---|  |----`
  /  /_\  \       \   \       |  |     |      /     |   _  <  |  |  |  |     |  |
 /  _____  \  .----)   |      |  |     |  |\  \----.|  |_)  | |  `--'  |     |  |
/__/     \__\ |_______/       |__|     | _| `._____||______/   \______/      |__|

"""
# ============================================================================
# 路径配置
# ============================================================================


def get_base_path() -> Path:
    """获取程序基础路径（打包后为 _MEIPASS）"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


def get_exe_dir() -> Path:
    """获取 exe 所在目录"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


def get_internal_dir() -> Path:
    """获取 _internal 目录（PyInstaller onedir 模式）"""
    return get_exe_dir() / "_internal"


# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(dev_mode: bool = False):
    log_dir = get_exe_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "astrbot.log"

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # 控制台处理器 - 仅 dev 模式显示
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    if dev_mode:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root_logger.addHandler(console_handler)


# ============================================================================
# 路径查找
# ============================================================================


def find_dashboard_dist() -> Optional[Path]:
    """查找 AstrBot Dashboard 目录"""
    internal_dir = get_internal_dir()
    base_path = get_base_path()

    for src_dir in [internal_dir, base_path]:
        dist = src_dir / "dashboard_dist"
        if dist.exists():
            return dist

    # 开发模式
    dev_dist = get_exe_dir().parent / "dashboard" / "dist"
    if dev_dist.exists():
        return dev_dist

    dev_distashboard = src_dir / "dashboard" / "dist"
    if dev_distashboard.exists():
        return dev_distashboard

    return None


def find_napcat_dir() -> Optional[Path]:
    """查找 NapCatQQ 目录"""
    internal_dir = get_internal_dir()
    base_path = get_base_path()

    for check_dir in [internal_dir, base_path]:
        napcat = check_dir / "napcat"
        if napcat.exists() and (napcat / "NapCatWinBootMain.exe").exists():
            return napcat

    return None


def has_napcat_embedded() -> bool:
    """检查是否嵌入了 NapCatQQ"""
    return find_napcat_dir() is not None


# ============================================================================
# NapCatQQ 服务
# ============================================================================


class NapCatService:
    """NapCatQQ 服务"""

    def __init__(self, port: int = 6099, dev_mode: bool = False):
        self.port = port
        self.dev_mode = dev_mode
        self.process: Optional[subprocess.Popen] = None
        self.token: Optional[str] = None

    def find_qq_path(self) -> Optional[Path]:
        """查找 QQNT 安装路径"""
        if platform.system() != "Windows":
            return None

        try:
            result = subprocess.run(
                ["reg", "query", r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\QQ", "/v", "UninstallString"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                match = re.search(r'UninstallString\s+REG_SZ\s+(.+)', result.stdout)
                if match:
                    uninstall_path = match.group(1).strip()
                    qq_path = Path(uninstall_path).parent / "QQ.exe"
                    if qq_path.exists():
                        return qq_path
        except Exception:
            pass

        for p in [
            Path("C:/Program Files/Tencent/QQNT/QQ.exe"),
            Path("C:/Program Files (x86)/Tencent/QQNT/QQ.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/QQNT/QQ.exe",
        ]:
            if p.exists():
                return p
        return None

    def parse_token_from_output(self, output: str) -> Optional[str]:
        """从输出中解析 Token"""
        match = re.search(r'WebUi Token:\s*(\w+)', output)
        if match:
            return match.group(1)
        match = re.search(r'[?&]token=(\w+)', output)
        if match:
            return match.group(1)
        return None

    def start(self, timeout: int = 60) -> bool:
        """启动 NapCatQQ"""
        logger = logging.getLogger("AstrBot-Desktop")
        logger.info("启动 NapCatQQ...")

        napcat_dir = find_napcat_dir()
        if not napcat_dir:
            logger.error("未找到 NapCatQQ 目录")
            return False

        qq_path = self.find_qq_path()
        if not qq_path:
            logger.error("未找到 QQNT，请先安装 QQ")
            return False

        # 设置环境变量
        env = os.environ.copy()
        env["NAPCAT_PATCH_PACKAGE"] = str(napcat_dir / "qqnt.json")
        env["NAPCAT_LOAD_PATH"] = str(napcat_dir / "loadNapCat.js")
        env["NAPCAT_INJECT_PATH"] = str(napcat_dir / "NapCatWinBootHook.dll")
        env["NAPCAT_LAUNCHER_PATH"] = str(napcat_dir / "NapCatWinBootMain.exe")
        env["NAPCAT_MAIN_PATH"] = str(napcat_dir / "napcat.mjs")

        # 生成 loadNapCat.js
        napcat_main_path = env["NAPCAT_MAIN_PATH"].replace("\\", "/")
        load_script = f"(async () => {{await import(\"file:///{napcat_main_path}\")}})()"
        with open(napcat_dir / "loadNapCat.js", "w", encoding="utf-8") as f:
            f.write(load_script)

        loader_path = napcat_dir / "NapCatWinBootMain.exe"
        hook_path = napcat_dir / "NapCatWinBootHook.dll"

        cmd = [str(loader_path), str(qq_path), str(hook_path)]
        logger.info(f"执行命令: {' '.join(cmd)}")

        try:
            if self.dev_mode:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(napcat_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )
            else:
                startupinfo = None
                if platform.system() == "Windows":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE

                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(napcat_dir),
                    startupinfo=startupinfo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )

            logger.info(f"NapCatQQ 进程已启动 (PID: {self.process.pid})")

            # 等待 Token
            logger.info("等待 NapCatQQ 初始化...")
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.process.poll() is not None:
                    logger.error("NapCatQQ 进程已退出")
                    return False
                line = self.process.stdout.readline()
                if line:
                    if self.dev_mode:
                        logger.info(f"[NapCatQQ] {line.strip()}")
                    token = self.parse_token_from_output(line)
                    if token:
                        self.token = token
                        logger.info(f"获取到 Token: {token}")
                        return True
                time.sleep(0.1)

            logger.warning("等待 Token 超时，继续运行...")
            return True

        except Exception as e:
            logger.error(f"启动 NapCatQQ 失败: {e}")
            return False

    def stop(self):
        if self.process:
            logger = logging.getLogger("AstrBot-Desktop")
            logger.info("停止 NapCatQQ...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    @property
    def webui_url(self) -> str:
        if self.token:
            return f"http://127.0.0.1:{self.port}/webui?token={self.token}"
        return f"http://127.0.0.1:{self.port}/webui"


# ============================================================================
# AstrBot 服务（直接在当前进程启动）
# ============================================================================

import mimetypes


class AstrBotRunner:
    """AstrBot 运行器 - 直接在当前进程启动"""

    def __init__(self, port: int = 6185):
        self.port = port
        self._webui_dir: Optional[str] = None

    def check_env(self):
        """初始化环境（从 main.py 移植）"""

        astrbot_root = get_astrbot_root()
        if astrbot_root not in sys.path:
            sys.path.insert(0, astrbot_root)

        site_packages_path = get_astrbot_site_packages_path()
        if site_packages_path not in sys.path:
            sys.path.insert(0, site_packages_path)

        os.makedirs(get_astrbot_config_path(), exist_ok=True)
        os.makedirs(get_astrbot_plugin_path(), exist_ok=True)
        os.makedirs(get_astrbot_temp_path(), exist_ok=True)
        os.makedirs(get_astrbot_knowledge_base_path(), exist_ok=True)
        os.makedirs(site_packages_path, exist_ok=True)

        # 针对 #181 的临时解决方案
        mimetypes.add_type("text/javascript", ".js")
        mimetypes.add_type("text/javascript", ".mjs")
        mimetypes.add_type("application/json", ".json")

    async def run_async(self, webui_dir: Optional[str] = None):
        """异步启动 AstrBot"""
        logger = logging.getLogger("AstrBot-Desktop")

        logger.info("异步启动 AstrBot...")

        # logger = logging.getLogger("AstrBot-Desktop")
        logger.info("启动 AstrBot 服务...")

        self._webui_dir = webui_dir

        try:
            # 初始化运行时
            try:
                import runtime_bootstrap
                runtime_bootstrap.initialize_runtime_bootstrap()
            except Exception as e:
                logger.warning(f"runtime_bootstrap 初始化失败: {e}")

            # 启动 AstrBot 核心
            from astrbot.core import db_helper
            from astrbot.core.initial_loader import InitialLoader
            logger.info(logo_tmpl)

            # 创建默认 log_broker
            from astrbot.core import LogBroker
            log_broker = LogBroker()

            # 启动核心服务
            logger.info("初始化数据库...")
            db = db_helper

            logger.info("创建核心服务...")
            core_lifecycle = InitialLoader(db, log_broker)
            core_lifecycle.webui_dir = webui_dir

            logger.info("启动 AstrBot 核心...")
            await core_lifecycle.start()

        except Exception as e:
            logger.error(f"AstrBot 启动失败: {e}", exc_info=True)
            raise

    def start(self, webui_dir: Optional[str] = None):
        """启动 AstrBot"""
        logger = logging.getLogger("AstrBot-Desktop")

        logger.info("启动 AstrBot...")

        self.check_env()
        logger.info("check_env完成...")

        asyncio.run(self.run_async(webui_dir))

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


# ============================================================================
# PySide6 桌面界面
# ============================================================================


def has_desktop_environment() -> bool:
    """检查是否有桌面环境"""
    system = platform.system()
    if system in ("Windows", "Darwin"):
        return True
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def run_desktop_app(
    astrbot_url: str,
    napcat_service: NapCatService = None,
    napcat_embedded: bool = False,
    window_title: str = "AstrBot 桌面版",
) -> int:
    """运行 PySide6 桌面应用"""

    try:
        from PySide6.QtCore import Qt, QUrl, QTimer
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
            QPushButton, QLabel, QHBoxLayout, QMessageBox,
        )
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except ImportError as e:
        logger = logging.getLogger("AstrBot-Desktop")
        logger.error(f"PySide6 未安装: {e}")
        logger.info("请运行: pip install PySide6")
        return 1

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(window_title)
            self.resize(1280, 800)
            self.napcat_service = napcat_service
            self.napcat_embedded = napcat_embedded

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(0, 0, 0, 0)

            self.tabs = QTabWidget()
            layout.addWidget(self.tabs)

            # AstrBot 标签页
            self.astrbot_view = QWebEngineView()
            self.astrbot_view.setUrl(QUrl(astrbot_url))
            self.tabs.addTab(self.astrbot_view, "AstrBot 管理面板")

            # NapCatQQ 标签页（仅当嵌入时）
            if napcat_embedded:
                self.napcat_view = QWebEngineView()
                if napcat_service:
                    self.napcat_view.setUrl(QUrl(napcat_service.webui_url))
                else:
                    self.napcat_view.setUrl(QUrl(f"http://127.0.0.1:{6099}/webui"))
                self.tabs.addTab(self.napcat_view, "NapCatQQ 管理面板")

            # 工具栏
            toolbar = QHBoxLayout()
            toolbar.setContentsMargins(10, 5, 10, 5)

            toolbar.addWidget(QPushButton("刷新", clicked=self.refresh))
            toolbar.addWidget(QPushButton("在浏览器打开", clicked=self.open_browser))

            if napcat_embedded and napcat_service:
                toolbar.addWidget(QPushButton("重启 NapCatQQ", clicked=self.start_napcat))

            toolbar.addStretch()
            toolbar.addWidget(QLabel(f"AstrBot: {astrbot_url}"))
            layout.addLayout(toolbar)

        def refresh(self):
            current = self.tabs.currentWidget()
            if hasattr(current, 'reload'):
                current.reload()

        def open_browser(self):
            current = self.tabs.currentWidget()
            if hasattr(current, 'url'):
                webbrowser.open(current.url().toString())

        def start_napcat(self):
            if self.napcat_service and self.napcat_service.start():
                QMessageBox.information(
                    self, "NapCatQQ", "NapCatQQ 正在启动...\n启动后自动刷新页面"
                )
                QTimer.singleShot(5000, self.refresh_napcat)

        def refresh_napcat(self):
            if self.napcat_service:
                self.napcat_view.setUrl(QUrl(self.napcat_service.webui_url))
            self.napcat_view.reload()

        def closeEvent(self, event):
            if self.napcat_service:
                self.napcat_service.stop()
            event.accept()

    app = QApplication(sys.argv)
    app.setApplicationName("AstrBot Desktop")
    window = MainWindow()
    window.show()
    return app.exec()


# ============================================================================
# 命令行模式
# ============================================================================


def run_cli_mode(port: int = 6185):
    """命令行模式运行"""

    logger = logging.getLogger("AstrBot-Desktop")
    logger.info("以命令行模式运行...")

    dashboard = find_dashboard_dist()
    runner = AstrBotRunner(port=port)

    try:
        # 直接在当前进程启动
        if dashboard:
            runner.start(dashboard)
        else:
            runner.start()

        logger.info("=" * 50)
        logger.info(f"AstrBot 已启动: {runner.url}")
        logger.info("按 Ctrl+C 停止服务")
        logger.info("=" * 50)

        # 保持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"AstrBot 运行错误: {e}")


# ============================================================================
# 主入口
# ============================================================================


def main():
    # 设置打包版本环境变量

    parser = argparse.ArgumentParser(description="AstrBot 桌面版")
    parser.add_argument("--cli", action="store_true", help="强制命令行模式")
    parser.add_argument("--dev", action="store_true", help="开发模式（显示日志终端）")
    parser.add_argument("--port", type=int, default=6185, help="AstrBot 端口")
    parser.add_argument("--napcat-port", type=int, default=6099, help="NapCatQQ 端口")
    args = parser.parse_args()

    # 初始化日志
    setup_logging(dev_mode=args.dev)
    logger = logging.getLogger("AstrBot-Desktop")

    # 检查 NapCatQQ 是否嵌入
    napcat_embedded = has_napcat_embedded()
    logger.info(f"NapCatQQ 嵌入: {napcat_embedded}")

    # 查找 Dashboard
    dashboard = find_dashboard_dist()
    if dashboard:
        logger.info(f"AstrBot Dashboard: {dashboard}")
    else:
        logger.warning("未找到 AstrBot Dashboard")

    # 判断是否使用桌面模式
    use_desktop = not args.cli and has_desktop_environment()

    if use_desktop:
        logger.info("启动桌面应用...")

        # 直接在当前进程启动 astrbot
        runner = AstrBotRunner(port=args.port)
        logger.info("直接在当前进程启动...")

        # 在后台线程启动 astrbot（因为桌面应用需要主线程）
        def run_astrbot():
            try:
                if dashboard:
                    logger.info("runner.start(dashboard)...")
                    runner.start(dashboard)
                else:
                    runner.start()
            except Exception as e:
                logger.error(f"astrbot 启动失败: {e}")

        astrbot_thread = threading.Thread(target=run_astrbot, daemon=True)
        astrbot_thread.start()

        time.sleep(2)  # 等待 astrbot 启动

        # napcatqq 服务（仅当嵌入时）
        napcat = None
        if napcat_embedded:
            napcat = NapCatService(port=args.napcat_port, dev_mode=args.dev)
            napcat.start()
            time.sleep(3)

        try:
            exit_code = run_desktop_app(
                astrbot_url=runner.url,
                napcat_service=napcat,
                napcat_embedded=napcat_embedded,
            )
        except Exception as e:
            logger.error(f"桌面应用错误: {e}")
            exit_code = 1

        return exit_code
    else:
        run_cli_mode(port=args.port)
        return 0


if __name__ == "__main__":
    sys.exit(main())
