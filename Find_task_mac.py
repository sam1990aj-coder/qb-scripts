import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    import mysql.connector
except ImportError:
    print("Missing required package: mysql-connector-python")
    print("Install with: pip install mysql-connector-python")
    sys.exit(1)

DEFAULT_POLL_INTERVAL = 60
DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent / "mysql_config.md"
DEFAULT_PLATFORM_CONFIG_FILE = Path(__file__).resolve().parent / "setup.md"


def validate_identifier(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Invalid identifier: {name}")
    return name


def load_mysql_config(path: Path) -> dict:
    config = {}
    if not path.exists():
        return config
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("` ")
        if key and value:
            config[key] = value
    return config


def apply_mysql_config(args: argparse.Namespace, config: dict) -> None:
    if args.host is None:
        args.host = config.get("host", "127.0.0.1")
    if args.port is None:
        args.port = int(config.get("port", 3306))
    if args.database is None:
        args.database = config.get("database", "")
    if args.password is None:
        args.password = config.get("password", "")
    if args.user is None:
        args.user = config.get("user")


def load_platform_config(path: Path) -> dict:
    return load_mysql_config(path)


def build_query(
    table: str,
    id_column: str,
    amount_column: str,
    note_column: str,
    status_column: str,
    platform_column: str,
) -> str:
    return (
        f"SELECT `{id_column}`, `{amount_column}`, `{note_column}` "
        f"FROM `{table}` WHERE `{status_column}` = 0 AND `{platform_column}` = %s "
        f"ORDER BY `{id_column}` ASC LIMIT 1"
    )


def build_update_query(
    table: str,
    status_column: str,
    updated_at_column: str,
    id_column: str,
) -> str:
    return (
        f"UPDATE `{table}` SET `{status_column}` = 1, `{updated_at_column}` = NOW() "
        f"WHERE `{id_column}` = %s"
    )


def call_payment_script(script_path: Path, amount: str, note: str, window_index: int, image_mode: bool, dry_run: bool) -> None:
    cmd = [sys.executable, str(script_path), amount, note, "--window-index", str(window_index)]
    if image_mode:
        cmd.append("--image-mode")
    if dry_run:
        cmd.append("--dry-run")
    print(f"调用 create_payment_link_mac.py: {' '.join(cmd)}")
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def read_clipboard() -> str:
    # macOS uses pbpaste to read clipboard
    result = subprocess.run(
        ["pbpaste"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def call_update_link(update_script_path: Path, record_id: int, paylink: str) -> None:
    cmd = [sys.executable, str(update_script_path), str(record_id), paylink]
    print(f"调用 update_link.py: {' '.join(cmd)}")
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def update_record_status(
    cursor,
    config: argparse.Namespace,
    record_id: int,
) -> None:
    update_sql = build_update_query(
        config.table,
        config.status_column,
        config.updated_at_column,
        config.id_column,
    )
    cursor.execute(update_sql, (record_id,))


def scan_database(config: argparse.Namespace) -> None:
    print(f"Starting MySQL polling every {config.poll_interval} seconds")
    print(f"Host={config.host} db={config.database} table={config.table} status_column={config.status_column} platform_column={config.platform_column} platform_id={config.platform_id}")
    print(f"Amount column={config.amount_column} note column={config.note_column}")
    print(f"Mode: {'process' if config.process else 'show-only'}")

    if config.process:
        script_path = Path(__file__).resolve().parent / "create_payment_link_mac.py"
        update_script_path = Path(__file__).resolve().parent / "update_link.py"
        check_login_path = Path(__file__).resolve().parent / "check_login_mac.py"

    # 冷启动时重置 customeraccount 状态为正常
    try:
        conn = mysql.connector.connect(use_pure=True,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
        )
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE customeraccount SET status = 0 WHERE platform_id = %s",
            (config.platform_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f"已重置 customeraccount 表中 platform_id={config.platform_id} 的 status 为 0")
    except Exception as e:
        print(f"重置 customeraccount 状态失败（不影响后续流程）: {e}")

    while True:
        try:
            conn = mysql.connector.connect(use_pure=True,
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
            )
            cursor = conn.cursor()
            query = build_query(
                config.table,
                config.id_column,
                config.amount_column,
                config.note_column,
                config.status_column,
                config.platform_column,
            )
            cursor.execute(query, (config.platform_id,))
            row = cursor.fetchone()
            if row:
                record_id, amount, note = row
                print(f"发现 status=0 且 {config.platform_column}={config.platform_id} 的记录")
                print(f"第一个记录: id={record_id}, amount={amount}, remark_visible={note}")
                if config.process:
                    print(f"执行处理 record_id={record_id} amount={amount} note={note}")
                    # Ensure account is still logged in before creating payment link
                    login_cmd = [sys.executable, str(check_login_path), "--image-mode", "--window-index", str(config.window_index)]
                    try:
                        subprocess.run(login_cmd, capture_output=True, text=True, check=True)
                        print("登录状态检查完成")
                    except Exception as exc:
                        print(f"登录状态检查失败，跳过此记录: {exc}")
                        continue
                    success = False
                    last_exc = None
                    for idx in range(int(config.window_index), 0, -1):
                        try:
                            print(f"尝试使用 window-index={idx}")
                            call_payment_script(
                                script_path,
                                str(amount),
                                str(note),
                                idx,
                                True,
                                config.dry_run,
                            )
                            success = True
                            used_index = idx
                            break
                        except subprocess.CalledProcessError as exc:
                            last_exc = exc
                            out = getattr(exc, 'output', '') or ''
                            err = getattr(exc, 'stderr', '') or ''
                            combined = (out + '\n' + err).strip()
                            print(f"window-index={idx} 失败: {combined or exc}")
                            if "requested window index" not in combined and "Found" not in combined:
                                break
                    if success:
                        try:
                            paylink = read_clipboard()
                            print(f"从剪贴板读取 paylink: {paylink}")
                            call_update_link(update_script_path, record_id, paylink)
                            print(f"记录 {record_id} 的 link 字段已更新为: {paylink}")
                        except Exception as exc:
                            print(f"更新 link 字段失败: {exc}")
                        update_record_status(cursor, config, record_id)
                        conn.commit()
                        print(f"记录 {record_id} 已处理并更新状态 (使用 window-index={used_index})")
                    else:
                        print(f"所有 window-index 重试失败: {last_exc}")
            else:
                print(f"暂无 status=0 且 {config.platform_column}={config.platform_id} 的记录")
            cursor.close()
            conn.close()
        except Exception as exc:
            print(f"轮询出错: {exc}")

        time.sleep(config.poll_interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="轮询 MySQL 数据库 status=0 的记录，可选择显示或处理模式。(macOS)"
    )
    parser.add_argument("--config-file", default=str(DEFAULT_CONFIG_FILE), help="MySQL 配置文件路径，默认 mysql_config.md")
    parser.add_argument("--host", default=None, help="MySQL 主机，优先使用配置文件")
    parser.add_argument("--port", type=int, default=None, help="MySQL 端口，优先使用配置文件")
    parser.add_argument("--user", default=None, help="MySQL 用户名，优先使用配置文件")
    parser.add_argument("--password", default=None, help="MySQL 密码，优先使用配置文件")
    parser.add_argument("--database", default=None, help="MySQL 数据库名称，优先使用配置文件")
    parser.add_argument("--table", default="links", help="要扫描的表名，默认 links")
    parser.add_argument("--id-column", default="id", help="主键字段名称，默认 id")
    parser.add_argument("--amount-column", default="amount", help="金额字段名称，默认 amount")
    parser.add_argument("--note-column", default="remark_visible", help="备注字段名称，默认 remark_visible")
    parser.add_argument("--status-column", default="status", help="处理状态字段名称，默认 status")
    parser.add_argument("--platform-column", default="platform_id", help="平台 id 字段名称，默认 platform_id")
    parser.add_argument("--platform-config", default=str(DEFAULT_PLATFORM_CONFIG_FILE), help="平台配置文件路径，默认 setup.md")
    parser.add_argument("--platform-id", type=str, default=None, help="平台 ID，优先使用配置文件中的 platform_id")
    parser.add_argument(
        "--updated-at-column",
        default="updated_at",
        help="更新时间字段名称，默认 updated_at",
    )
    parser.add_argument("--window-index", type=int, default=1, help="浏览器窗口匹配索引，默认 1")
    parser.add_argument("--image-mode", action="store_true", help="调用 create_payment_link.py 时启用图片识别模式")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--show-only",
        dest="process",
        action="store_false",
        help="仅显示第一条匹配记录，不执行处理。（默认）",
    )
    mode_group.add_argument(
        "--process",
        dest="process",
        action="store_true",
        help="执行处理：调用 create_payment_link.py 并更新状态。",
    )
    parser.set_defaults(process=False)
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL, help="轮询间隔秒数，默认 60")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将调用的命令，不实际点击")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config_values = load_mysql_config(Path(args.config_file))
    apply_mysql_config(args, config_values)

    platform_values = load_platform_config(Path(args.platform_config))
    if args.platform_id is None:
        args.platform_id = platform_values.get("platform_id")

    if args.user is None:
        print("MySQL 用户名未设置，请通过配置文件或 --user 指定。")
        sys.exit(1)
    if not args.database:
        print("MySQL 数据库名未设置，请通过配置文件或 --database 指定。")
        sys.exit(1)
    if args.password is None:
        print("MySQL 密码未设置，请通过配置文件或 --password 指定。")
        sys.exit(1)
    if args.platform_id is None:
        print("平台 ID 未设置，请通过 setup.md 或 --platform-id 指定。")
        sys.exit(1)

    try:
        args.table = validate_identifier(args.table)
        args.id_column = validate_identifier(args.id_column)
        args.amount_column = validate_identifier(args.amount_column)
        args.note_column = validate_identifier(args.note_column)
        args.status_column = validate_identifier(args.status_column)
        args.platform_column = validate_identifier(args.platform_column)
        args.updated_at_column = validate_identifier(args.updated_at_column)
    except ValueError as exc:
        print(f"参数错误: {exc}")
        sys.exit(1)

    scan_database(args)
