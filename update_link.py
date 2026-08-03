import argparse
import sys
from pathlib import Path

try:
    import mysql.connector
except ImportError:
    print("Missing required package: mysql-connector-python")
    print("Install with: python3.exe -m pip install mysql-connector-python")
    sys.exit(1)

DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent / "mysql_config.md"


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


def update_link(record_id: int, paylink: str) -> None:
    config_path = DEFAULT_CONFIG_FILE
    config = load_mysql_config(config_path)

    host = config.get("host", "127.0.0.1")
    port = int(config.get("port", 3306))
    user = config.get("user")
    password = config.get("password")
    database = config.get("database")

    if not user:
        print("MySQL 用户名未设置，请检查 mysql_config.md。")
        sys.exit(1)
    if not password:
        print("MySQL 密码未设置，请检查 mysql_config.md。")
        sys.exit(1)
    if not database:
        print("MySQL 数据库名未设置，请检查 mysql_config.md。")
        sys.exit(1)

    print(f"连接 MySQL: host={host}, port={port}, database={database}, user={user}")

    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        use_pure=True,
    )
    cursor = conn.cursor()

    update_sql = "UPDATE `links` SET `link` = %s WHERE `id` = %s"
    cursor.execute(update_sql, (paylink, record_id))

    if cursor.rowcount == 0:
        print(f"警告: 未找到 id={record_id} 的记录，未更新任何行。")
    else:
        print(f"成功更新 id={record_id} 的记录，link={paylink}")

    conn.commit()
    cursor.close()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="更新 links 表中指定 id 记录的 link 字段。"
    )
    parser.add_argument("record_id", type=int, help="要更新的记录 ID")
    parser.add_argument("paylink", type=str, help="新的 paylink 值")
    args = parser.parse_args()

    update_link(args.record_id, args.paylink)


if __name__ == "__main__":
    main()
