#!/usr/bin/env python3
"""Auto-updater: check remote version, download updates, run Find_task."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request

# ===== 配置 =====
# 远程更新源 URL（末尾带 /）
UPDATE_BASE = "https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/"

# 需要更新的脚本文件列表
UPDATE_FILES = [
    "Find_task.py",
    "Find_task_mac.py",
    "check_login.py",
    "check_login_mac.py",
    "create_payment_link.py",
    "create_payment_link_mac.py",
    "update_link.py",
    "updater.py",
]

# 从不覆盖的本地配置文件（即使远程有同名的也不会下载）
PROTECTED_FILES = [
    "setup.md",
    "mysql_config.md",
]

SCRIPT_DIR = Path(__file__).resolve().parent
VERSION_FILE = SCRIPT_DIR / "version.txt"


def get_remote_version() -> str:
    """Fetch remote version string."""
    try:
        url = UPDATE_BASE + "version.txt"
        req = Request(url, headers={"User-Agent": "script-updater/1.0"})
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as e:
        print(f"无法获取远程版本: {e}")
        return ""


def get_local_version() -> str:
    """Read local version string."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0"


def save_local_version(version: str) -> None:
    VERSION_FILE.write_text(version, encoding="utf-8")


def download_file(filename: str) -> bool:
    """Download a single file from remote. Returns True on success."""
    if filename in PROTECTED_FILES:
        print(f"  跳过受保护文件: {filename}")
        return True
    try:
        url = UPDATE_BASE + filename
        req = Request(url, headers={"User-Agent": "script-updater/1.0"})
        with urlopen(req, timeout=30) as resp:
            content = resp.read()
        dest = SCRIPT_DIR / filename
        dest.write_bytes(content)
        return True
    except Exception as e:
        print(f"  下载失败 {filename}: {e}")
        return False


def update_all() -> bool:
    """Download all update files. Returns True if all succeeded."""
    print(f"下载更新文件 ({len(UPDATE_FILES)} 个)...")
    ok, fail = 0, 0
    for f in UPDATE_FILES:
        if download_file(f):
            ok += 1
        else:
            fail += 1
    print(f"完成: {ok} 成功, {fail} 失败")
    return fail == 0


def check_and_update() -> bool:
    """Check for updates and apply if needed. Returns True if scripts are ready."""
    remote_ver = get_remote_version()
    if not remote_ver:
        print("跳过更新检查（无法连接远程）。")
        return True  # continue with local scripts

    local_ver = get_local_version()
    print(f"远程版本: {remote_ver}  本地版本: {local_ver}")

    if remote_ver != local_ver:
        print("发现新版本，开始更新...")
        if update_all():
            save_local_version(remote_ver)
            print(f"已更新到版本 {remote_ver}")
        else:
            print("部分文件更新失败，继续使用现有脚本。")
    else:
        print("已是最新版本。")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="自动更新并启动 Find_task 轮询脚本"
    )
    parser.add_argument("--process", action="store_true", help="执行处理模式")
    parser.add_argument("--show-only", action="store_true", help="仅显示模式")
    parser.add_argument("--window-index", type=int, default=None, help="浏览器窗口索引")
    parser.add_argument("--poll-interval", type=int, default=None, help="轮询间隔秒数")
    parser.add_argument("--image-mode", action="store_true", help="启用图片识别")
    parser.add_argument("--skip-update", action="store_true", help="跳过更新检查")
    parser.add_argument("--update-url", default=None, help="覆盖远程更新源 URL")
    args = parser.parse_args()

    global UPDATE_BASE
    if args.update_url:
        UPDATE_BASE = args.update_url

    # Check and apply updates
    if not args.skip_update:
        print("=== 检查更新 ===")
        check_and_update()
        print()

    # Determine which Find_task script to run
    if sys.platform == "darwin":
        script = "Find_task_mac.py"
    else:
        script = "Find_task.py"

    # Build command
    cmd = [sys.executable, str(SCRIPT_DIR / script)]
    if args.process:
        cmd.append("--process")
    else:
        cmd.append("--show-only")
    if args.window_index is not None:
        cmd.extend(["--window-index", str(args.window_index)])
    if args.poll_interval is not None:
        cmd.extend(["--poll-interval", str(args.poll_interval)])
    if args.image_mode:
        cmd.append("--image-mode")

    print(f"启动: {' '.join(cmd)}")
    sys.stdout.flush()

    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
