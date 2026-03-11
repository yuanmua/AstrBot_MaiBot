#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 桌面版构建脚本

用法:
    python build.py              # 构建前端 + 打包 EXE (默认)
    python build.py --clean      # 清理构建产物
    python build.py --config     # 显示配置
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BUILD_DIR = PROJECT_ROOT / "build"
CONFIG_FILE = BUILD_DIR / "config" / "build_config.yaml"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_command(cmd, cwd=None, check=True, env=None, shell=False):
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    print(f"[执行] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(cmd, cwd=cwd, check=check, shell=shell or sys.platform == "win32", env=full_env)


def build_astrbot_frontend() -> bool:
    print("\n" + "=" * 50)
    print("构建 AstrBot Dashboard 前端")
    print("=" * 50)

    dashboard_dir = PROJECT_ROOT / "dashboard"
    if not dashboard_dir.exists():
        print(f"[错误] Dashboard 目录不存在: {dashboard_dir}")
        return False

    pnpm_cmd = "pnpm.cmd" if sys.platform == "win32" else "pnpm"

    try:
        run_command([pnpm_cmd, "--version"])
    except FileNotFoundError:
        print("[错误] 未安装 pnpm，请先安装 Node.js")
        return False

    print("\n[1/2] 安装依赖...")
    try:
        run_command([pnpm_cmd, "install", "-y"], cwd=dashboard_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 安装依赖失败: {e}")
        return False

    print("\n[2/2] 构建前端...")
    try:
        run_command([pnpm_cmd, "run", "build"], cwd=dashboard_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 构建失败: {e}")
        return False

    dist_dir = dashboard_dir / "dist"
    target_dir = PROJECT_ROOT / "data" / "dist"

    if dist_dir.exists():
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dist_dir, target_dir)
        print(f"\n[完成] 前端已复制到: {target_dir}")
    else:
        print(f"[警告] 构建产物不存在: {dist_dir}")

    return True


def build_napcat_frontend(napcat_path: str) -> bool:
    """构建 NapCatQQ Shell 包（包含前端 + 加载器）"""
    print("\n" + "=" * 50)
    print("构建 NapCatQQ Shell 包")
    print("=" * 50)

    napcat_dir = Path(napcat_path)
    if not napcat_dir.exists():
        print(f"[错误] NapCatQQ 目录不存在: {napcat_dir}")
        return False

    pnpm_cmd = "pnpm.cmd" if sys.platform == "win32" else "pnpm"

    try:
        run_command([pnpm_cmd, "--version"])
    except FileNotFoundError:
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        print("[信息] pnpm 未安装，尝试安装...")
        try:
            run_command([npm_cmd, "install", "-g", "pnpm"])
        except subprocess.CalledProcessError:
            print("[错误] 无法安装 pnpm")
            return False

    print("\n[1/5] 安装依赖...")
    try:
        run_command([pnpm_cmd, "install"], cwd=napcat_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 安装依赖失败: {e}")
        return False

    print("\n[2/5] 构建 WebUI 前端...")
    try:
        run_command([pnpm_cmd, "--filter", "napcat-webui-frontend", "run", "build"], cwd=napcat_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 构建 WebUI 失败: {e}")
        return False

    print("\n[3/5] 构建 Shell...")
    try:
        run_command([pnpm_cmd, "run", "build:shell"], cwd=napcat_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 构建 Shell 失败: {e}")
        return False

    print("\n[4/5] 构建内置插件...")
    try:
        run_command([pnpm_cmd, "--filter", "napcat-plugin-builtin", "run", "build"], cwd=napcat_dir)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 构建内置插件失败: {e}")
        return False

    print("\n[5/5] 打包...")
    shell_dist = napcat_dir / "packages" / "napcat-shell" / "dist"
    if not shell_dist.exists():
        print(f"[错误] Shell 构建产物不存在: {shell_dist}")
        return False

    # 移动到 shell-dist
    target_dir = napcat_dir / "shell-dist"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(shell_dist, target_dir)

    # 安装依赖（使用 npm，与官方 workflow 一致）
    try:
        run_command(["npm.cmd", "install", "--omit=dev"], cwd=target_dir)
    except subprocess.CalledProcessError as e:
        print(f"[警告] 安装 Shell 依赖失败: {e}")

    # 删除 package-lock.json
    lock_file = target_dir / "package-lock.json"
    if lock_file.exists():
        lock_file.unlink()

    # 复制 WebUI
    webui_dist = napcat_dir / "packages" / "napcat-webui-frontend" / "dist"
    if webui_dist.exists():
        webui_target = target_dir / "webui"
        if webui_target.exists():
            shutil.rmtree(webui_target)
        shutil.copytree(webui_dist, webui_target)
        print(f"  [√] WebUI 已复制")

    print(f"\n[完成] NapCatQQ Shell 包: {target_dir}")
    return True


def build_all_frontends(config: dict) -> bool:
    success = True

    if not build_astrbot_frontend():
        success = False

    frontend_config = config.get("frontend", {})
    napcat_path = frontend_config.get("napcat")

    if napcat_path:
        if not build_napcat_frontend(napcat_path):
            success = False
    else:
        print("\n[跳过] NapCatQQ 未配置（frontend.napcat 未设置）")

    return success


def prepare_build_resources(config: dict) -> bool:
    print("\n" + "=" * 50)
    print("准备构建资源")
    print("=" * 50)

    resources_dir = BUILD_DIR / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    # AstrBot Dashboard
    dashboard_dist = PROJECT_ROOT / "data" / "dist"
    target_dashboard = resources_dir / "dashboard_dist"

    if dashboard_dist.exists():
        if target_dashboard.exists():
            shutil.rmtree(target_dashboard)
        shutil.copytree(dashboard_dist, target_dashboard)
        print(f"  [√] AstrBot Dashboard: {target_dashboard}")
    else:
        print(f"  [×] AstrBot Dashboard 未构建")
        return False

    # NapCatQQ Shell 包（包含加载器和 WebUI）
    frontend_config = config.get("frontend", {})
    napcat_path = frontend_config.get("napcat")

    napcat_dir = None
    if napcat_path:
        # 使用新构建的 shell-dist
        napcat_src = Path(napcat_path) / "shell-dist"
        if napcat_src.exists():
            napcat_dir = resources_dir / "napcat"
            if napcat_dir.exists():
                shutil.rmtree(napcat_dir)
            shutil.copytree(napcat_src, napcat_dir)
            print(f"  [√] NapCatQQ Shell 包: {napcat_dir}")
        else:
            print(f"  [×] NapCatQQ Shell 包未构建: {napcat_src}")
    else:
        print(f"  [-] NapCatQQ 未配置（可选）")

    # 入口文件
    entry_point = PROJECT_ROOT / "desktop_main.py"
    if not entry_point.exists():
        print(f"  [×] 入口文件不存在: {entry_point}")
        return False
    print(f"  [√] 入口文件: {entry_point}")

    return True


def get_pyinstaller_args(config: dict, output_dir: Path) -> list:
    project = config["project"]
    local = config.get("local", {})

    args = [
        "pyinstaller",
        "--name", project.get("name", "AstrBot"),
        "--distpath", str(output_dir),
        "--workpath", str(BUILD_DIR / "build_temp"),
        "--specpath", str(BUILD_DIR),
        "-y",
    ]

    if local.get("one_file", False):
        args.append("--onefile")
    else:
        args.append("--onedir")

    # if not local.get("console", True):
    #     args.append("--noconsole")

    icon = local.get("icon")
    if icon:
        icon_path = PROJECT_ROOT / icon
        if icon_path.exists():
            args.extend(["--icon", str(icon_path)])

    if local.get("upx", False):
        upx_path = local.get("upx_path", "")
        if upx_path:
            args.extend(["--upx-dir", upx_path])
        args.append("--upx")

    for imp in project.get("hidden_imports", []):
        args.extend(["--hidden-import", imp])

    resources_dir = BUILD_DIR / "resources"

    dashboard_dist = resources_dir / "dashboard_dist"
    if dashboard_dist.exists():
        args.extend([ f"--add-data={dashboard_dist}:dashboard_dist"])

    # NapCatQQ Shell 包
    napcat_dir = resources_dir / "napcat"
    if napcat_dir.exists():
        args.extend([f"--add-data={napcat_dir}:napcat"])
    else:
        # 兼容旧版 napcat_webui
        napcat_webui_dir = resources_dir / "napcat_webui"
        if napcat_webui_dir.exists():
            args.extend([f"--add-data={napcat_webui_dir}:napcat_webui"])

    # 打包配置文件到 exe 同目录
    config_file = BUILD_DIR / "config" / "build_config.yaml"
    if config_file.exists():
        args.extend([f"--add-data={config_file}:."])

    # 源码
    astrbot_src = PROJECT_ROOT / "astrbot"
    if astrbot_src.exists():
        args.extend([ f"--add-data={astrbot_src}:astrbot"])

    # main.py 和 runtime_bootstrap.py 放到打包后的 exe 同目录
    for src_file in ["main.py", "runtime_bootstrap.py"]:
        src_path = PROJECT_ROOT / src_file
        if src_path.exists():
            args.extend([f"--add-data={src_path}:."])

    for exc in project.get("excludes", []):
        args.extend(["--exclude-module", exc])

    entry_point = project.get("entry_point", "desktop_main.py")
    args.append(str(PROJECT_ROOT / entry_point))

    return args


def build_local(config: dict) -> bool:
    print("\n" + "=" * 50)
    print("开始打包 EXE")
    print("=" * 50)

    output_dir = PROJECT_ROOT / config.get("local", {}).get("output_dir", "dist")
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_dir.exists():
        print(f"[清理] 删除旧构建: {output_dir}")
        shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)

    try:
        run_command(["pyinstaller", "--version"])
    except FileNotFoundError:
        print("[信息] 未安装 PyInstaller，正在安装...")
        run_command(["pip", "install", "pyinstaller"])

    if not prepare_build_resources(config):
        print("[错误] 准备构建资源失败")
        return False

    args = get_pyinstaller_args(config, output_dir)
    print(f"\n[PyInstaller] {' '.join(args)}")

    try:
        run_command(args, cwd=PROJECT_ROOT)
    except subprocess.CalledProcessError as e:
        print(f"[错误] PyInstaller 构建失败: {e}")
        return False

    print(f"\n[成功] 构建完成，输出目录: {output_dir}")
    return True


def clean_build(config: dict) -> None:
    print("\n[清理] 删除构建产物...")

    dirs_to_clean = [
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / "build" / "build_temp",
        PROJECT_ROOT / "build" / "resources",
    ]

    for d in dirs_to_clean:
        if d.exists():
            if d.is_dir():
                shutil.rmtree(d)
            else:
                d.unlink()
            print(f"  - 已删除: {d}")

    spec_file = BUILD_DIR / f"{config['project'].get('name', 'AstrBot')}.spec"
    if spec_file.exists():
        spec_file.unlink()
        print(f"  - 已删除: {spec_file}")

    print("[完成] 清理完成")


def main():
    parser = argparse.ArgumentParser(description="AstrBot 桌面版构建工具")
    parser.add_argument("--clean", action="store_true", help="清理构建产物")
    parser.add_argument("--noweb", action="store_true", help="不构建前端")
    parser.add_argument("--config", action="store_true", help="显示配置")
    parser.add_argument("--output", type=str, help="输出目录")
    args = parser.parse_args()

    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"[错误] {e}")
        sys.exit(1)

    if args.config:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        sys.exit(0)

    if args.output:
        config.setdefault("local", {})["output_dir"] = args.output

    if args.clean:
        clean_build(config)
    else:
        # 默认：构建前端 + 打包 EXE
        if args.noweb:
            success = build_local(config)
        else:
            success = build_all_frontends(config) and build_local(config)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
