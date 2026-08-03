import argparse
import sys
import time
import random
import math
from pathlib import Path

try:
    import numpy as np
    import pyautogui
    import pygetwindow as gw
except ImportError:
    print("Missing required packages. Install with: pip install pyautogui pygetwindow numpy")
    sys.exit(1)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from PIL import Image

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


def human_click(precision: bool = False):
    time.sleep(random.uniform(0.15, 0.30))
    pre_range = 1 if precision else 3
    post_range = 1 if precision else 2
    dx = random.randint(-pre_range, pre_range)
    dy = random.randint(-pre_range, pre_range)
    if dx != 0 or dy != 0:
        pyautogui.moveRel(dx, dy, _pause=False)
        time.sleep(random.uniform(0.01, 0.03))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.03, 0.08))
    pyautogui.mouseUp()
    # Post-click slip: finger lifting off causes slight movement
    time.sleep(random.uniform(0.02, 0.05))
    dx = random.randint(-post_range, post_range)
    dy = random.randint(-post_range, post_range)
    if dx != 0 or dy != 0:
        pyautogui.moveRel(dx, dy, _pause=False)


def human_write(text: str):
    """Type with Gaussian delays, word pauses, and occasional typo correction."""
    for char in text:
        delay = max(0.015, min(0.18, random.gauss(0.055, 0.035)))
        pyautogui.write(char, _pause=False)
        time.sleep(delay)
        if char == " ":
            time.sleep(random.uniform(0.1, 0.35))
    if random.random() < 0.1 and len(text) > 3:
        fix_len = random.randint(1, min(3, len(text)))
        suffix = text[-fix_len:]
        for _ in range(fix_len):
            pyautogui.press("backspace")
            time.sleep(random.uniform(0.06, 0.15))
        time.sleep(random.uniform(0.2, 0.5))
        for char in suffix:
            delay = max(0.03, min(0.2, random.gauss(0.08, 0.04)))
            pyautogui.write(char, _pause=False)
            time.sleep(delay)


def human_select_all():
    """Ctrl+A with human-like key press delay."""
    pyautogui.keyDown("ctrl")
    time.sleep(random.uniform(0.03, 0.08))
    pyautogui.press("a")
    time.sleep(random.uniform(0.03, 0.08))
    pyautogui.keyUp("ctrl")


def reading_pause():
    """Random pause simulating reading the page between major actions."""
    if random.random() < 0.6:
        time.sleep(random.uniform(3.0, 8.0))


def micro_move():
    if random.random() < 0.5:
        dx = random.randint(-5, 5)
        dy = random.randint(-5, 5)
        pyautogui.moveRel(dx, dy, _pause=False)
        time.sleep(random.uniform(0.02, 0.06))


def rand_sleep(base: float, variance: float = 0.4):
    """Log-normal distributed sleep for human-like timing variability."""
    sigma = 0.35
    mu = math.log(base) - sigma * sigma / 2
    delay = math.exp(random.gauss(mu, sigma))
    delay = max(base * 0.3, min(base * 3.0, delay))
    time.sleep(delay)


def human_move_to(x: int, y: int):
    """Move mouse along bezier curve with ease-in-out speed, occasional pauses, and overshoot."""
    start_x, start_y = pyautogui.position()

    # Control point for bezier curve with random offset
    cx = start_x + (x - start_x) * random.uniform(0.3, 0.7)
    cy = start_y + (y - start_y) * random.uniform(0.3, 0.7) + random.randint(-30, 30)

    # Occasional overshoot: aim past target then correct (20% chance)
    overshoot = random.random() < 0.2
    if overshoot:
        ox = x + random.randint(-15, 15)
        oy = y + random.randint(-15, 15)
    else:
        ox, oy = x, y

    steps = random.randint(15, 25)

    # Occasional mid-movement pause with micro-correction (25% chance)
    pause_at = random.randint(steps // 3, 2 * steps // 3) if random.random() < 0.25 else -1

    for i in range(1, steps + 1):
        t = i / steps
        # Ease-in-out: slow start → fast middle → slow end
        eased = 0.5 - 0.5 * math.cos(t * math.pi)

        px = int((1 - eased) ** 2 * start_x + 2 * (1 - eased) * eased * cx + eased ** 2 * ox)
        py = int((1 - eased) ** 2 * start_y + 2 * (1 - eased) * eased * cy + eased ** 2 * oy)
        px += int(random.gauss(0, 1.2))
        py += int(random.gauss(0, 1.2))
        pyautogui.moveTo(px, py, _pause=False)

        # Variable speed: slower at start/end, faster in middle
        if i < steps * 0.2 or i > steps * 0.8:
            time.sleep(random.uniform(0.020, 0.040))
        else:
            time.sleep(random.uniform(0.012, 0.025))

        # Mid-movement pause with direction twitch
        if i == pause_at:
            twitch_x = random.randint(-8, 8)
            twitch_y = random.randint(-8, 8)
            pyautogui.moveRel(twitch_x, twitch_y, _pause=False)
            time.sleep(random.uniform(0.05, 0.15))
            pyautogui.moveRel(-twitch_x, -twitch_y, _pause=False)

    # If overshot, correct back to actual target with small steps
    if overshoot:
        time.sleep(random.uniform(0.02, 0.06))
        correct_steps = random.randint(3, 6)
        for i in range(1, correct_steps + 1):
            t = i / correct_steps
            px = int(ox + (x - ox) * t + int(random.gauss(0, 0.8)))
            py = int(oy + (y - oy) * t + int(random.gauss(0, 0.8)))
            pyautogui.moveTo(px, py, _pause=False)
            time.sleep(random.uniform(0.005, 0.012))

    pyautogui.moveTo(x, y, _pause=False)
    for _ in range(3):
        time.sleep(0.05)
        cx, cy = pyautogui.position()
        if abs(cx - x) <= 2 and abs(cy - y) <= 2:
            break
        pyautogui.moveTo(x, y, _pause=False)


WINDOW_TITLE_KEYWORDS = ["quickbooks", "payment links", "get paid", "quickbooks.com", "sunbrowser"]
DEFAULT_WINDOW_INDEX = 3
ACTIVE_WINDOW = None
USE_IMAGE_MODE = False
IMAGE_DIR = Path(__file__).parent / "button_images"

IMAGE_FILE_NAMES = {
    "login_detect": "login_detect.png",
    "login_account": "login_account.png",
    "login_password": "login_password.png",
    "login_signin": "login_signin.png",
    "session_continue": "session_continue.png",
    "home": "home.png",
    "sales_paid": "sales_paid.png",
    "payment_links_nav": "payment_links_nav.png",
    "nav_create": "nav_create.png",
    "risk_check": "risk_check.png",
    "bot_check": "bot_check.png",
    "bot_continue": "bot_continue.png",
}

def load_coordinates(config_path: Path) -> dict:
    """Load button coordinates from config file. Format: - name: `x, y`"""
    coords = {}
    if not config_path.exists():
        return coords
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("` ").replace(" ", "")
        if "," in value:
            parts = value.split(",")
            if len(parts) == 2:
                try:
                    coords[key] = (int(parts[0]), int(parts[1]))
                except ValueError:
                    pass
    return coords


# Window-relative coordinates — defaults, overridden by setup.md
_COORD_DEFAULTS = {
    "login_account": (800, 300),
    "login_password": (850, 450),
    "login_signin": (1000, 550),
    "session_continue": (960, 540),
    "home": (150, 300),
    "sales_paid": (800, 60),
    "payment_links_nav": (150, 500),
    "nav_create": (0, 0),
}
COORDINATES = dict(_COORD_DEFAULTS)
_setup = Path(__file__).resolve().parent / "setup.md"
_coords = load_coordinates(_setup)
if "login_password_coord" in _coords:
    _coords["login_password"] = _coords.pop("login_password_coord")
COORDINATES.update(_coords)

# Per-button match threshold override (default 0.80)
def load_thresholds(config_path: Path) -> dict:
    th = {}
    if not config_path.exists():
        return th
    for line in config_path.read_text(encoding="utf-8").splitlines():
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
        if key.startswith("th_"):
            try:
                th[key[3:]] = float(value)
            except ValueError:
                pass
    return th


COORDINATES = dict(_COORD_DEFAULTS)
_setup = Path(__file__).resolve().parent / "setup.md"
_coords = load_coordinates(_setup)
if "login_password_coord" in _coords:
    _coords["login_password"] = _coords.pop("login_password_coord")
COORDINATES.update(_coords)
BUTTON_THRESHOLDS = load_thresholds(_setup)


def load_waits(config_path: Path) -> dict:
    w = {}
    if not config_path.exists():
        return w
    for line in config_path.read_text(encoding="utf-8").splitlines():
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
        if key.startswith("wait_"):
            try:
                w[key[5:]] = float(value)
            except ValueError:
                pass
    return w


WAITS = load_waits(_setup)

# Small buttons that need precise clicking (narrower jitter)
SMALL_BUTTONS = {"payment_links_nav"}

# Coordinate fallback tracking
_consecutive_fallback = 0
_risk_check_count = 0
_bot_check_count = 0
CONSECUTIVE_FALLBACK_LIMIT = 3

DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent / "setup.md"


def load_setup_config(path: Path) -> dict:
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


def find_quickbooks_window(index: int):
    matches = []
    for w in gw.getAllWindows():
        if not w.title:
            continue
        if "sunbrowser" in w.title.lower():
            matches.append(w)
    if not matches:
        raise RuntimeError("No SunBrowser window found.")
    if len(matches) < index:
        titles = [w.title for w in matches]
        raise RuntimeError(
            f"Found {len(matches)} SunBrowser windows, but requested index {index}.\n"
            f"Available titles: {titles}"
        )
    win = matches[index - 1]
    print(f"Using SunBrowser window: {win.title}")
    return win


def activate_window(window):
    window.activate()
    time.sleep(1.5)


def image_path(name: str):
    return IMAGE_DIR / IMAGE_FILE_NAMES[name]


def image_button_exists(name: str):
    return image_path(name).exists()


def get_window_screenshot():
    if ACTIVE_WINDOW is None:
        return np.array(pyautogui.screenshot())
    left, top = ACTIVE_WINDOW.left, ACTIVE_WINDOW.top
    width, height = ACTIVE_WINDOW.width, ACTIVE_WINDOW.height
    return np.array(pyautogui.screenshot(region=(left, top, width, height)))


def fatal_stop(reason: str) -> None:
    """Stop all actions, update customerAccount status=1, and exit."""
    print(f"\nFATAL: 图像识别失败 - {reason}")
    print("停止所有动作。")

    mysql_config_path = Path(__file__).resolve().parent / "mysql_config.md"
    mysql_config = load_setup_config(mysql_config_path)
    setup_config_path = Path(__file__).resolve().parent / "setup.md"
    setup_config = load_setup_config(setup_config_path)
    platform_id = setup_config.get("platform_id", "")

    if platform_id and mysql_config:
        try:
            import mysql.connector
            conn = mysql.connector.connect(use_pure=True,
                host=mysql_config.get("host", "127.0.0.1"),
                port=int(mysql_config.get("port", 3306)),
                user=mysql_config.get("user"),
                password=mysql_config.get("password"),
                database=mysql_config.get("database", "links"),
            )
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE customeraccount SET status = 1 WHERE platform_id = %s",
                (platform_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()
            print(f"已更新 customerAccount 表中 platform_id={platform_id} 的 status 为 1")
        except Exception as e:
            print(f"更新数据库失败: {e}")

    sys.exit(1)


def locate_button_image(name: str):
    if not CV2_AVAILABLE:
        raise RuntimeError("Image search requires OpenCV. Install with: pip install opencv-python")
    path = image_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Template image not found: {path}")
    print(f"Locating image for '{name}' using {path}")
    try:
        pil_template = Image.open(path)
        template = cv2.cvtColor(np.array(pil_template), cv2.COLOR_RGB2GRAY)
    except Exception as exc:
        raise RuntimeError(f"Failed to open template image for '{name}': {exc}")

    screen = get_window_screenshot()
    screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    threshold = BUTTON_THRESHOLDS.get(name, 0.80)
    print(f"Template match: '{name}' max_val={max_val:.3f} @({max_loc[0]},{max_loc[1]}) threshold={threshold:.2f}")

    if max_val < threshold:
        # Retry screenshot once (may return stale data)
        time.sleep(0.3)
        screen = get_window_screenshot()
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val2, _, max_loc2 = cv2.minMaxLoc(result)
        print(f"Retry match: '{name}' max_val={max_val2:.3f} @({max_loc2[0]},{max_loc2[1]}) (was {max_val:.3f})")
        if max_val2 < threshold:
            return None
        max_val, max_loc = max_val2, max_loc2

    top_left = max_loc
    template_h, template_w = template.shape
    center_x = top_left[0] + template_w // 2
    center_y = top_left[1] + template_h // 2
    if ACTIVE_WINDOW is not None:
        center_x += ACTIVE_WINDOW.left
        center_y += ACTIVE_WINDOW.top
    return center_x, center_y


def is_logged_out() -> bool:
    """Check if login page is showing. Defaults to True (logged out) when detection is unavailable."""
    if not USE_IMAGE_MODE or not image_button_exists("login_detect"):
        print("无法检测登录状态: login_detect.png 不存在或未启用 image-mode，默认按已登出处理")
        return True
    result = locate_button_image("login_detect")
    if result is not None:
        print("检测到登录页面 — 已退出登录")
        return True
    print("未检测到登录页面 — 仍在登录状态")
    return False


def is_session_expired() -> bool:
    """Check if session timeout popup ('Are you still there?') is showing."""
    if not USE_IMAGE_MODE or not image_button_exists("session_continue"):
        print("无法检测会话超时弹窗: session_continue.png 不存在或未启用 image-mode")
        return False
    result = locate_button_image("session_continue")
    if result is not None:
        print("检测到会话超时弹窗 — 需要点击继续使用")
        return True
    print("未检测到会话超时弹窗")
    return False


def handle_session_expired() -> None:
    """Click 'Continue' button on session timeout popup."""
    print("处理会话超时弹窗，点击继续使用...")
    if USE_IMAGE_MODE and image_button_exists("session_continue"):
        wait_for_image("session_continue", timeout=8)
    click_at("session_continue", sleep_after=WAITS.get("session_continue", 5.0))
    print("已点击继续使用，等待页面恢复 (5~8秒)...")
    rand_sleep(6, 2)


def wait_for_image(name: str, timeout: int = 12):
    print(f"Waiting for image '{name}' to appear on screen...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            time.sleep(0.1)  # buffer to reduce screenshot API stress
            result = locate_button_image(name)
            if result is not None:
                x, y = result
                print(f"Found '{name}' at ({x}, {y})")
                return x, y
        except Exception:
            pass
        time.sleep(random.uniform(0.3, 0.7))
    fatal_stop(f"等待 '{name}' 按钮超时 ({timeout}秒)")


def get_click_position(name: str):
    if USE_IMAGE_MODE and image_button_exists(name):
        result = locate_button_image(name)
        if result is not None:
            x, y = result
            print(f"Found '{name}' by image at ({x}, {y})")
            return x, y
        fatal_stop(f"无法在屏幕上定位 '{name}' 按钮")
    if ACTIVE_WINDOW is None:
        raise RuntimeError("ACTIVE_WINDOW is not set.")
    x, y = COORDINATES[name]
    return ACTIVE_WINDOW.left + x, ACTIVE_WINDOW.top + y


def click_at(name: str, sleep_after: float = 5.0):
    if name not in COORDINATES:
        raise KeyError(f"Unknown coordinate key: {name}")
    if ACTIVE_WINDOW is None:
        raise RuntimeError("ACTIVE_WINDOW is not set.")
    try:
        ACTIVE_WINDOW.activate()
    except:
        pass
    abs_x, abs_y = get_click_position(name)
    precise = name in SMALL_BUTTONS
    jitter = 1 if precise else 3
    abs_x += random.randint(-jitter, jitter)
    abs_y += random.randint(-jitter, jitter)
    print(f"Clicking {name} at screen ({abs_x}, {abs_y}){' [precision]' if precise else ''}")
    human_move_to(abs_x, abs_y)
    # Pre-click hesitation: 70% chance of brief pause (reading/confirming target)
    if random.random() < 0.7:
        time.sleep(random.uniform(0.3, 1.5))
    human_click(precision=precise)
    micro_move()
    rand_sleep(sleep_after, sleep_after * 0.2)


def do_login(password: str) -> None:
    """Login: select account → enter password → sign in."""
    print("开始登录...")
    # Step 1: Click to select the account
    if USE_IMAGE_MODE and image_button_exists("login_account"):
        wait_for_image("login_account", timeout=8)
    click_at("login_account", sleep_after=WAITS.get("login_account", 5.0))
    print("已选择账号。")
    reading_pause()
    # Step 2: Enter password
    if USE_IMAGE_MODE and image_button_exists("login_password"):
        wait_for_image("login_password", timeout=8)
    click_at("login_password", sleep_after=WAITS.get("login_password", 5.0))
    human_select_all()
    time.sleep(random.uniform(0.1, 0.3))
    human_write(password)
    rand_sleep(0.5, 0.3)
    reading_pause()
    # Step 3: Click Sign In
    if USE_IMAGE_MODE and image_button_exists("login_signin"):
        wait_for_image("login_signin", timeout=8)
    click_at("login_signin", sleep_after=WAITS.get("login_signin", 5.0))
    print("已点击 Sign In，等待登录完成...")
    time.sleep(random.uniform(4.0, 6.0))
    # Check for bot verification after clicking Sign In
    global _bot_check_count
    if USE_IMAGE_MODE and image_button_exists("bot_check"):
        result = locate_button_image("bot_check")
        if result is not None:
            _bot_check_count += 1
            print(f"检测到机器人验证 (连续 {_bot_check_count}/2)")
            if _bot_check_count >= 2:
                fatal_stop("连续 2 次检测到机器人验证，需要人工处理")
            print("点击 I am not a bot 复选框...")
            bx, by = result
            bx += random.randint(-1, 1)
            by += random.randint(-1, 1)
            human_move_to(bx, by)
            time.sleep(random.uniform(0.3, 1.5))
            human_click()
            if USE_IMAGE_MODE and image_button_exists("bot_continue"):
                result2 = locate_button_image("bot_continue")
                if result2 is not None:
                    cx, cy = result2
                    cx += random.randint(-1, 1)
                    cy += random.randint(-1, 1)
                    human_move_to(cx, cy)
                    time.sleep(random.uniform(0.3, 1.5))
                    human_click()
            print("刷新页面，重新登录...")
            pyautogui.hotkey("ctrl", "r")
            time.sleep(random.uniform(3.0, 5.0))
            do_login(password)
            return
    _bot_check_count = 0
    # Check for account risk verification page after clicking Sign In
    global _risk_check_count
    if USE_IMAGE_MODE and image_button_exists("risk_check"):
        if locate_button_image("risk_check") is not None:
            _risk_check_count += 1
            print(f"检测到账户风险认证页面 (连续 {_risk_check_count}/2)")
            if _risk_check_count >= 2:
                fatal_stop("连续 2 次检测到账户风险认证页面，需要人工处理")
            print("刷新页面，重新登录...")
            pyautogui.hotkey("ctrl", "r")
            time.sleep(random.uniform(3.0, 5.0))
            do_login(password)
            return
    _risk_check_count = 0
    time.sleep(random.uniform(16, 18))


def navigate_to_payment_links() -> None:
    """导航步骤已注释，假设已位于 Payment links 页面。"""
    # cx, cy = COORDINATES["nav_create"]
    # ...
    print("导航: 已跳过（假设已在 Payment links 页面）。")


def capture_button_template(name: str, width: int = 200, height: int = 80):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    x, y = pyautogui.position()
    left = max(0, x - width // 2)
    top = max(0, y - height // 2)
    image = pyautogui.screenshot(region=(left, top, width, height))
    path = image_path(name)
    image.save(path)
    print(f"Captured template for '{name}' to {path}")
    return path


def capture_template_prompt(name: str):
    print(f"请将鼠标移动到 '{name}' 按钮上，然后按回车键截取。")
    input("准备好后按 Enter... ")
    path = capture_button_template(name)
    print(f"已保存模板：{path}\n")


def calibrate_mouse():
    print("Calibration mode: 将鼠标移动到目标按钮上，按 Ctrl-C 停止。")
    print("坐标将以 x,y 形式实时打印。")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"{x},{y}", end="\r")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n已停止校准。")


def check_and_login(password: str, window_index: int, dry_run: bool = False) -> bool:
    """Return True if login was performed (was logged out), False if already logged in."""
    global ACTIVE_WINDOW
    target_window = find_quickbooks_window(window_index)
    print(f"Activating window #{window_index}: {target_window.title}")
    activate_window(target_window)
    ACTIVE_WINDOW = target_window

    if dry_run:
        print("DRY RUN: 检测登录状态...")
        if USE_IMAGE_MODE:
            print("  - 检查 login_detect.png ...")
        print("  (不会实际执行登录)")
        return False

    if not is_logged_out():
        if is_session_expired():
            print("检测到会话超时，点击继续使用...")
            handle_session_expired()
            print("会话已恢复。")
            return True
        print("仍在登录状态，无需操作。")
        return False

    print("检测到已登出，开始重新登录...")
    do_login(password)

    if USE_IMAGE_MODE and image_button_exists("home"):
        wait_for_image("home", timeout=15)
    navigate_to_payment_links()
    print("登录并导航完成。")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检测登录状态，如登出则自动登录并导航到 Payment links 页面。")
    parser.add_argument("--window-index", type=int, default=DEFAULT_WINDOW_INDEX, help="浏览器窗口匹配索引")
    parser.add_argument("--config-file", default=str(DEFAULT_CONFIG_FILE), help="配置文件路径，默认 setup.md")
    parser.add_argument("--password", default=None, help="登录密码（优先使用 setup.md 中的 login_password）")
    parser.add_argument("--dry-run", action="store_true", help="仅检测状态，不实际登录")
    parser.add_argument("--image-mode", action="store_true", help="使用模板图片识别按钮位置")
    parser.add_argument("--image-dir", default=None, help="按钮模板图片目录")
    parser.add_argument("--list-windows", action="store_true", help="列出匹配的浏览器窗口")
    parser.add_argument("--calibrate", action="store_true", help="实时显示鼠标坐标")
    parser.add_argument("--capture-template", nargs="+", choices=list(IMAGE_FILE_NAMES.keys()), help="截取按钮模板")
    parser.add_argument("--capture-all", action="store_true", help="交互式截取所有按钮模板")
    parser.add_argument("--test-fatal", action="store_true", help="测试 fatal_stop 数据库更新功能")
    args = parser.parse_args()

    if args.test_fatal:
        print("测试 fatal_stop 数据库更新功能...")
        fatal_stop("测试：验证 customeraccount 表 status 更新")

    if args.list_windows:
        windows = []
        for w in gw.getAllWindows():
            if not w.title:
                continue
            if any(keyword in w.title.lower() for keyword in WINDOW_TITLE_KEYWORDS):
                windows.append(w)
        if not windows:
            print(f"No windows containing any of {WINDOW_TITLE_KEYWORDS} found.")
            sys.exit(1)
        for idx, window in enumerate(windows, start=1):
            print(f"{idx}: {window.title}")
        sys.exit(0)

    if args.calibrate:
        calibrate_mouse()
        sys.exit(0)

    if args.capture_template:
        if args.image_dir:
            IMAGE_DIR = Path(args.image_dir)
        for name in args.capture_template:
            capture_template_prompt(name)
        sys.exit(0)

    if args.capture_all:
        if args.image_dir:
            IMAGE_DIR = Path(args.image_dir)
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        print("开始捕获所有按钮模板。")
        for name in IMAGE_FILE_NAMES:
            capture_template_prompt(name)
        print("所有模板已捕获完成。")
        sys.exit(0)

    if args.image_dir:
        IMAGE_DIR = Path(args.image_dir)

    if args.image_mode:
        USE_IMAGE_MODE = True
        print(f"Image mode enabled. Searching templates in: {IMAGE_DIR}")
        if not CV2_AVAILABLE:
            print("Warning: OpenCV not installed. Install with: pip install opencv-python")
    else:
        if CV2_AVAILABLE and image_button_exists("login_detect"):
            USE_IMAGE_MODE = True
            print(f"Found button templates in {IMAGE_DIR}. Automatically enabling image mode.")

    # Load password
    config = load_setup_config(Path(args.config_file))
    password = args.password or config.get("login_password", "")
    if not args.dry_run and (not password or password == "your_password_here"):
        print("登录密码未设置。请在 setup.md 中设置 login_password 或通过 --password 指定。")
        sys.exit(1)

    try:
        performed = check_and_login(password, args.window_index, dry_run=args.dry_run)
        if performed:
            print("RESULT: LOGGED_IN")
        else:
            print("RESULT: ALREADY_LOGGED_IN")
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
