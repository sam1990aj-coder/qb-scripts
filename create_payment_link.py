import argparse
import sys
import time
import os
import random
import math
from pathlib import Path
from PIL import Image

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
CURRENT_WINDOW_INDEX = DEFAULT_WINDOW_INDEX
ACTIVE_WINDOW = None
USE_IMAGE_MODE = False
IMAGE_DIR = Path(__file__).parent / "button_images"
IMAGE_FILE_NAMES = {
    "new_link": "new_link.png",
    "multi_use": "multi_use.png",
    "next": "next.png",
    "amount": "amount.png",
    "note": "note.png",
    "create": "create.png",
    "copy": "copy.png",
    "done": "done.png",
    "new_link_page": "new_link_page.png",
    "new_link_page2": "new_link_page2.png",
    "nav_create": "nav_create.png",
    "payment_links_nav": "payment_links_nav.png",
}

# Optional per-button search region (window-relative: left, top, width, height).
# When set, cv2.matchTemplate only searches within this area,
# avoiding false matches on similar UI elements elsewhere.
# Example: {"multi_use": (1300, 500, 250, 150)}
SEARCH_REGIONS = {}

# Debug logging: saves annotated screenshots and click logs for troubleshooting
DEBUG_DIR = Path(__file__).parent / "debug_logs"
DEBUG_ENABLED = True

# Small buttons that need precise clicking (narrower jitter)
SMALL_BUTTONS = {"multi_use", "copy"}

# Coordinate fallback tracking
_consecutive_fallback = 0
CONSECUTIVE_FALLBACK_LIMIT = 3
_next_fail_count = 0
_amount_fail_count = 0

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


_COORD_DEFAULTS = {
    "new_link": (1877, 224),
    "multi_use": (1420, 569),
    "next": (1749, 976),
    "amount": (850, 420),
    "note": (850, 500),
    "create": (1300, 860),
    "copy": (1841, 466),
    "done": (1850, 997),
    "new_link_page": (500, 200),
    "new_link_page2": (500, 200),
    "nav_create": (0, 0),
    "payment_links_nav": (0, 0),
}
def load_thresholds(config_path: Path) -> dict:
    """Load per-button thresholds from config. Format: - th_button: `0.45`"""
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
COORDINATES.update(load_coordinates(_setup))
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
    if not window.isActive:
        raise RuntimeError("Failed to activate the target window. Please make sure adsPower is running and the window is visible.")


def refresh_active_window():
    global ACTIVE_WINDOW
    if CURRENT_WINDOW_INDEX is None:
        return
    ACTIVE_WINDOW = find_quickbooks_window(CURRENT_WINDOW_INDEX)
    return ACTIVE_WINDOW


def log_click_event(name: str, event_type: str, details: str):
    """Append a timestamped entry to the daily debug log."""
    if not DEBUG_ENABLED:
        return
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_file = DEBUG_DIR / f"click_log_{time.strftime('%Y%m%d')}.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {event_type:10s} | {name:18s} | {details}\n")
    except Exception:
        pass  # never let logging break the main flow


def save_debug_screenshot(name: str, screen_np, match_loc, template_shape, search_region=None):
    """Save annotated screenshot showing where the match was found (green rect + red crosshair)."""
    if not DEBUG_ENABLED:
        return
    try:
        import copy
        annotated = copy.deepcopy(screen_np)
        # Convert grayscale back to BGR for color drawing
        if len(annotated.shape) == 2:
            annotated = cv2.cvtColor(annotated, cv2.COLOR_GRAY2BGR)

        th, tw = template_shape
        mx, my = match_loc
        # Green rectangle around matched area
        cv2.rectangle(annotated, (mx, my), (mx + tw, my + th), (0, 255, 0), 2)
        # Red crosshair at click center
        cx, cy = mx + tw // 2, my + th // 2
        cv2.line(annotated, (cx - 10, cy), (cx + 10, cy), (0, 0, 255), 2)
        cv2.line(annotated, (cx, cy - 10), (cx, cy + 10), (0, 0, 255), 2)
        # Label with button name
        cv2.putText(annotated, name, (mx, max(my - 8, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        # ROI dashed border if search_region was used
        if search_region:
            rx, ry, rw, rh = search_region
            cv2.rectangle(annotated, (rx, ry), (rx + rw, ry + rh), (255, 255, 0), 1)

        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%H%M%S")
        filename = f"{ts}_{name}.png"
        cv2.imwrite(str(DEBUG_DIR / filename), annotated)
        log_click_event(name, "DEBUG_IMG", f"saved {filename}")
    except Exception:
        pass


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
    mysql_config = {}
    if mysql_config_path.exists():
        for line in mysql_config_path.read_text(encoding="utf-8").splitlines():
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
                mysql_config[key] = value

    setup_config_path = Path(__file__).resolve().parent / "setup.md"
    setup_config = {}
    if setup_config_path.exists():
        for line in setup_config_path.read_text(encoding="utf-8").splitlines():
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
                setup_config[key] = value

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


def locate_button_image(name: str, search_region=None):
    if not CV2_AVAILABLE:
        raise RuntimeError("Image search requires OpenCV. Install with: pip install opencv-python")
    path = image_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"Template image not found: {path}. Place a screenshot of the '{name}' button there."
        )
    print(f"Locating image for '{name}' using {path}")
    try:
        pil_template = Image.open(path)
        template = cv2.cvtColor(np.array(pil_template), cv2.COLOR_RGB2GRAY)
    except Exception as exc:
        raise RuntimeError(f"Failed to open template image for '{name}': {exc}")

    screen = get_window_screenshot()
    screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

    if search_region:
        rx, ry, rw, rh = search_region
        h, w = screen_gray.shape
        rx = max(0, rx)
        ry = max(0, ry)
        rw = min(rw, w - rx)
        rh = min(rh, h - ry)
        if rw <= 0 or rh <= 0:
            raise RuntimeError(f"Search region for '{name}' is outside the window bounds")
        screen_gray = screen_gray[ry:ry+rh, rx:rx+rw]
        print(f"  ROI search: region=({rx},{ry},{rw},{rh})")

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    threshold = BUTTON_THRESHOLDS.get(name, 0.80)
    print(f"Template match: '{name}' max_val={max_val:.3f} @({max_loc[0]},{max_loc[1]}) threshold={threshold:.2f}")

    if max_val < threshold:
        # Retry screenshot once (may return stale data)
        time.sleep(0.3)
        screen = get_window_screenshot()
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        if search_region:
            rx, ry, rw, rh = search_region
            h, w = screen_gray.shape
            rx = max(0, rx)
            ry = max(0, ry)
            rw = min(rw, w - rx)
            rh = min(rh, h - ry)
            if rw > 0 and rh > 0:
                screen_gray = screen_gray[ry:ry+rh, rx:rx+rw]
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val2, _, max_loc2 = cv2.minMaxLoc(result)
        print(f"Retry match: '{name}' max_val={max_val2:.3f} @({max_loc2[0]},{max_loc2[1]}) (was {max_val:.3f})")
        if max_val2 >= threshold:
            max_val, max_loc = max_val2, max_loc2
        else:
            raise RuntimeError(f"Template match too weak for '{name}'. max_val={max_val2:.3f} threshold={threshold:.2f}")

    top_left = max_loc
    if search_region:
        top_left = (top_left[0] + search_region[0], top_left[1] + search_region[1])
    template_h, template_w = template.shape
    center_x = top_left[0] + template_w // 2
    center_y = top_left[1] + template_h // 2

    # Log and save debug screenshot
    roi_str = f"ROI=({search_region[0]},{search_region[1]},{search_region[2]},{search_region[3]})" if search_region else "ROI=fullscreen"
    log_click_event(name, "MATCH_OK", f"conf={max_val:.3f} center=({center_x},{center_y}) {roi_str}")
    save_debug_screenshot(name, screen, top_left, (template_h, template_w), search_region)

    if ACTIVE_WINDOW is not None:
        center_x += ACTIVE_WINDOW.left
        center_y += ACTIVE_WINDOW.top
    return center_x, center_y


def wait_for_image(name: str, timeout: int = 12):
    print(f"Waiting for image '{name}' to appear on screen...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            time.sleep(0.1)  # buffer to reduce screenshot API stress
            x, y = locate_button_image(name)
            print(f"Found '{name}' at ({x}, {y})")
            return x, y
        except Exception:
            time.sleep(random.uniform(0.3, 0.7))
    fatal_stop(f"等待 '{name}' 按钮超时 ({timeout}秒)")


def capture_button_template(name: str, width: int = 200, height: int = 80):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    x, y = pyautogui.position()
    left = max(0, x - width // 2)
    top = max(0, y - height // 2)
    region = (left, top, width, height)
    image = pyautogui.screenshot(region=region)
    path = image_path(name)
    image.save(path)
    print(f"Captured template for '{name}' to {path}")
    return path


def get_click_position(name: str, force_coordinate: bool = False, absolute: bool = False):
    if not force_coordinate and USE_IMAGE_MODE and image_button_exists(name):
        try:
            region = SEARCH_REGIONS.get(name)
            x, y = locate_button_image(name, search_region=region)
            print(f"Found '{name}' by image at ({x}, {y})")
            return x, y
        except Exception as exc:
            print(f"Image lookup failed for '{name}': {exc}")
            log_click_event(name, "FATAL", f"Image lookup failed: {exc}")
            fatal_stop(f"无法在屏幕上定位 '{name}' 按钮")
    if absolute:
        return COORDINATES[name]
    if ACTIVE_WINDOW is None:
        raise RuntimeError("ACTIVE_WINDOW is not set. Cannot compute relative coordinates.")
    x, y = COORDINATES[name]
    return ACTIVE_WINDOW.left + x, ACTIVE_WINDOW.top + y


def capture_template_prompt(name: str):
    print(f"请将鼠标移动到 '{name}' 按钮上，然后按回车键开始截取。")
    input("准备好后按 Enter... ")
    path = capture_button_template(name)
    print(f"已保存模板：{path}\n")


def capture_all_templates():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("开始捕获所有按钮模板。")
    print("注意：请依次移动鼠标至按钮位置，并按 Enter。")
    for name in IMAGE_FILE_NAMES:
        capture_template_prompt(name)
    print("所有模板已捕获完成。")


def click_at(name: str, force_coordinate: bool = False, absolute: bool = False, sleep_after: float = 2.0):
    if name not in COORDINATES:
        raise KeyError(f"Unknown coordinate key: {name}")
    if not absolute and ACTIVE_WINDOW is None:
        raise RuntimeError("ACTIVE_WINDOW is not set. Cannot compute relative coordinates.")
    if not absolute:
        refresh_active_window()
        try:
            ACTIVE_WINDOW.activate()
        except:
            pass
    abs_x, abs_y = get_click_position(name, force_coordinate=force_coordinate, absolute=absolute)
    precise = name in SMALL_BUTTONS
    jitter = 1 if precise else 3
    abs_x += random.randint(-jitter, jitter)
    abs_y += random.randint(-jitter, jitter)
    print(f"Clicking {name} at absolute ({abs_x}, {abs_y}){' [precision]' if precise else ''}")
    log_click_event(name, "CLICK", f"screen=({abs_x},{abs_y}) precise={precise} window_offset=({ACTIVE_WINDOW.left if ACTIVE_WINDOW else 'N/A'},{ACTIVE_WINDOW.top if ACTIVE_WINDOW else 'N/A'})")
    human_move_to(abs_x, abs_y)
    # Pre-click hesitation: 70% chance of brief pause (reading/confirming target)
    if random.random() < 0.7:
        time.sleep(random.uniform(0.3, 1.5))
    human_click(precision=precise)
    micro_move()
    rand_sleep(sleep_after, sleep_after * 0.25)


def fill_field(text: str):
    # Vary the input approach to mimic natural human behavior
    r = random.random()
    if r < 0.3:
        # Occasionally select-all first (clearing pre-existing content)
        human_select_all()
        time.sleep(random.uniform(0.1, 0.3))
    elif r < 0.7:
        # Most of the time just type directly (field was just clicked, cursor is there)
        pass
    else:
        # Sometimes hit backspace a few times (simulating correcting old content)
        for _ in range(random.randint(1, 4)):
            pyautogui.press("backspace")
            time.sleep(random.uniform(0.05, 0.12))
    human_write(text)
    time.sleep(0.5)


def calibrate_mouse():
    print("Calibration mode: 将鼠标移动到目标按钮上，按 Ctrl-C 停止。")
    print("当前鼠标位置将以 x,y 形式实时打印。")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"{x},{y}", end="\r")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n已停止校准。")


def create_payment_link(amount: str, note: str, dry_run: bool = False):
    if dry_run:
        print("DRY RUN: would perform these actions:")
        for step in ["new_link", "multi_use", "next", "amount", "note", "create", "copy", "done"]:
            print(f"  - {step} at {COORDINATES[step]}")
        return

    # Navigate to Payment links + verify (max 2 attempts)
    max_nav_attempts = 2
    for nav_attempt in range(max_nav_attempts):
        cx, cy = COORDINATES["nav_create"]
        if USE_IMAGE_MODE and image_button_exists("nav_create"):
            try:
                result = locate_button_image("nav_create")
                if result is not None:
                    cx, cy = result
                    print(f"导航: 识图找到 Create 按钮 ({cx}, {cy})")
                else:
                    print(f"导航: 识图未找到 Create，使用坐标 ({cx}, {cy})")
            except Exception:
                print(f"导航: 识图异常，使用坐标 ({cx}, {cy})")
        else:
            print(f"导航: 使用坐标移动到 Create 按钮 ({cx}, {cy})")
        hx = cx + random.randint(-3, 3)
        hy = cy + random.randint(-3, 3)
        human_move_to(hx, hy)
        micro_move()
        time.sleep(random.uniform(3.0, 4.0))

        drift = random.randint(40, 50)
        print(f"导航: 向右移动 {drift} 像素...")
        hx2 = cx + drift + random.randint(-3, 3)
        hy2 = cy + random.randint(-3, 3)
        human_move_to(hx2, hy2)
        micro_move()

        px, py = COORDINATES["payment_links_nav"]
        if USE_IMAGE_MODE and image_button_exists("payment_links_nav"):
            try:
                result = locate_button_image("payment_links_nav")
                if result is not None:
                    px, py = result
                    print(f"导航: 识图找到 Payment links 按钮 ({px}, {py})")
                else:
                    print(f"导航: 识图未找到 Payment links，使用坐标 ({px}, {py})")
            except Exception:
                print(f"导航: 识图异常，使用坐标 ({px}, {py})")
        else:
            print(f"导航: 使用坐标点击 Payment links 按钮 ({px}, {py})")
        human_move_to(px, py)
        time.sleep(random.uniform(0.8, 1.2))
        human_click()
        micro_move()
        print("已进入 Payment links 页面。")
        time.sleep(random.uniform(10.0, 12.0))

        # === Steps after navigation are inside the retry loop ===

        click_at("multi_use", sleep_after=WAITS.get("multi_use", 4.0))
        print("Multi-use payment link selected. 等待选项加载...")

        # Pre-check next button; track consecutive failures
        global _next_fail_count
        if USE_IMAGE_MODE and image_button_exists("next"):
            try:
                if locate_button_image("next") is None:
                    _next_fail_count += 1
                    print(f"Next 按钮识图失败 (连续 {_next_fail_count}/3)，重新导航...")
                    if _next_fail_count >= 3:
                        fatal_stop("Next 按钮连续 3 次识图失败")
                    continue
                _next_fail_count = 0
            except Exception:
                _next_fail_count += 1
                print(f"Next 识图异常 (连续 {_next_fail_count}/3)，重新导航...")
                if _next_fail_count >= 3:
                    fatal_stop("Next 按钮连续 3 次识图失败")
                continue
        click_at("next", sleep_after=WAITS.get("next", 4.5))
        reading_pause()

        # Pre-check amount; track consecutive failures
        global _amount_fail_count
        if USE_IMAGE_MODE and image_button_exists("amount"):
            try:
                if locate_button_image("amount") is None:
                    _amount_fail_count += 1
                    print(f"Amount 按钮识图失败 (连续 {_amount_fail_count}/3)，重新导航...")
                    if _amount_fail_count >= 3:
                        fatal_stop("Amount 按钮连续 3 次识图失败")
                    continue
                _amount_fail_count = 0
            except Exception:
                _amount_fail_count += 1
                print(f"Amount 识图异常 (连续 {_amount_fail_count}/3)，重新导航...")
                if _amount_fail_count >= 3:
                    fatal_stop("Amount 按钮连续 3 次识图失败")
                continue
        click_at("amount", sleep_after=WAITS.get("amount", 2.5))
        fill_field(amount)
        click_at("note", sleep_after=WAITS.get("note", 2.5))
        fill_field(note)
        reading_pause()
        click_at("create", sleep_after=WAITS.get("create", 5.5))

        print("等待收款链接生成...")

        click_at("copy", absolute=True, sleep_after=WAITS.get("copy", 2.5))
        print("已点击 Copy，链接已复制到剪贴板。")

        if USE_IMAGE_MODE and image_button_exists("done"):
            wait_for_image("done", timeout=10)
        click_at("done", sleep_after=WAITS.get("done", 2.5))
        print("已点击 Done。")
        break  # success
    else:
        fatal_stop("连续 2 次无法打开 Payment links 页面")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a QuickBooks payment link in adsPower browser window #3."
    )
    parser.add_argument("amount", nargs="?", help="Payment amount")
    parser.add_argument("note", nargs="?", help="Payment note or remark")
    parser.add_argument(
        "--window-index",
        type=int,
        default=DEFAULT_WINDOW_INDEX,
        help="adsPower browser window match index (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned UI actions without clicking anything.",
    )
    parser.add_argument(
        "--list-windows",
        action="store_true",
        help="List matching QuickBooks windows and exit.",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Print mouse coordinates so you can calibrate button positions.",
    )
    parser.add_argument(
        "--image-mode",
        action="store_true",
        help="Locate buttons using template images instead of fixed coordinates.",
    )
    parser.add_argument(
        "--image-dir",
        default=None,
        help="Directory containing button template images.",
    )
    parser.add_argument(
        "--capture-template",
        nargs="+",
        choices=list(IMAGE_FILE_NAMES.keys()),
        help="Capture screenshot region(s) around the current mouse position as button template(s).",
    )
    parser.add_argument(
        "--capture-all",
        action="store_true",
        help="Capture template images for all buttons interactively.",
    )
    args = parser.parse_args()

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
        capture_all_templates()
        sys.exit(0)

    if not args.amount or not args.note:
        parser.error("amount and note are required unless using --capture-all, --capture-template, --calibrate, or --list-windows")

    if args.image_dir:
        IMAGE_DIR = Path(args.image_dir)

    if args.image_mode:
        USE_IMAGE_MODE = True
        print(f"Image mode enabled. Searching templates in: {IMAGE_DIR}")
        if not CV2_AVAILABLE:
            print("Warning: OpenCV is not installed. Install with: pip install opencv-python for image matching.")
    else:
        if CV2_AVAILABLE and image_button_exists("next"):
            USE_IMAGE_MODE = True
            print(f"Found button templates in {IMAGE_DIR}. Automatically enabling image mode.")

    try:
        target_window = find_quickbooks_window(args.window_index)
        print(f"Activating window #{args.window_index}: {target_window.title}")
        activate_window(target_window)
        globals()["CURRENT_WINDOW_INDEX"] = args.window_index
        globals()["ACTIVE_WINDOW"] = target_window
        create_payment_link(args.amount, args.note, dry_run=args.dry_run)
        if not args.dry_run:
            print("已执行创建流程，请检查浏览器中生成的收款链接。")
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
