import asyncio
import logging
import logging.handlers
import socket

import websockets
from websockets.asyncio.server import serve
from pynput.keyboard import Controller, Key, KeyCode
from pynput import keyboard


# -----------------------
# ロギング設定
# -----------------------
LOG_FILE = "server.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3

logger = logging.getLogger("ws_key_server")
logger.setLevel(logging.DEBUG)  # 必要に応じて DEBUG/INFO に変更

# コンソール出力
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# ローテーティングファイル出力
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


class KeyEventHandler:
    """キーイベントを処理するクラス"""

    def __init__(self):
        self.keyboard_controller: Controller = keyboard.Controller()
        self.special_keys: dict[str, Key] = {
            "space": Key.space,
            "enter": Key.enter,
            "return": Key.enter,
            "escape": Key.esc,
            "esc": Key.esc,
            "tab": Key.tab,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "cmd": Key.cmd,
            "option": Key.alt,
            "alt": Key.alt,
            "delete": Key.delete,
            "backspace": Key.backspace,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "home": Key.home,
            "end": Key.end,
            "page_up": Key.page_up,
            "page_down": Key.page_down,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,
        }

    def parse_key_combination(self, key_string: str) -> list[Key | KeyCode]:
        """
        キー組み合わせ文字列を解析
        例: "cmd+c", "ctrl+shift+a", "space"
        """
        if not key_string:
            return []

        parts = key_string.lower().split("+")
        keys: list[Key | KeyCode] = []

        for part in parts:
            part = part.strip()
            if part in self.special_keys:
                keys.append(self.special_keys[part])
            elif len(part) == 1:
                keys.append(KeyCode.from_char(part))
            else:
                # 認識できないキーの場合は文字として扱う
                for char in part:
                    keys.append(KeyCode.from_char(char))

        logger.debug("Parsed key string '%s' -> %s", key_string, keys)
        return keys

    def send_key_event(self, key_string: str) -> bool:
        """
        キーイベントを送信
        戻り値: 成功時True, 失敗時False
        """
        try:
            keys = self.parse_key_combination(key_string)
            if not keys:
                logger.warning("Empty or invalid key string received: %r", key_string)
                return False

            # キー組み合わせの場合（複数キー）
            if len(keys) > 1:
                # 修飾キーを押下
                for key in keys[:-1]:
                    logger.debug("Press: %r", key)
                    self.keyboard_controller.press(key)

                # 最後のキーを押下・離上
                logger.debug("Press & release: %r", keys[-1])
                self.keyboard_controller.press(keys[-1])
                self.keyboard_controller.release(keys[-1])

                # 修飾キーを離上（逆順）
                for key in reversed(keys[:-1]):
                    logger.debug("Release: %r", key)
                    self.keyboard_controller.release(key)
            else:
                # 単一キーの場合
                logger.debug("Press & release single key: %r", keys[0])
                self.keyboard_controller.press(keys[0])
                self.keyboard_controller.release(keys[0])

            logger.info("Dispatched key event for: %r", key_string)
            return True

        except Exception:
            logger.exception("Failed to dispatch key event for: %r", key_string)
            return False


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        logger.info("Local IP detected: %s", ip)
        return ip
    except Exception:
        logger.exception("Failed to detect local IP")
        return "Unknown"


async def echo(websocket, keyhandler: KeyEventHandler):
    peer = websocket.remote_address
    logger.info("Connection from %s", peer)

    try:
        async for message in websocket:
            logger.info("Received from %s: %r", peer, message)
            success = keyhandler.send_key_event(message)
            if not success:
                logger.warning(
                    "Key event handling failed for message from %s: %r", peer, message
                )

            try:
                await websocket.send(message)
                logger.debug("Echoed back to %s: %r", peer, message)
            except Exception:
                logger.exception("Failed to send echo to %s", peer)
                # 続行して接続を閉じる
                break

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(
            "Connection closed %s: code=%s, reason=%s",
            peer,
            getattr(e, "code", None),
            getattr(e, "reason", None),
        )
    except Exception:
        logger.exception("Unexpected error in connection handler for %s", peer)
    finally:
        logger.info("Disconnected %s", peer)


async def main():
    ip = "0.0.0.0"
    port = 8765
    logger.info("Server starting at %s:%s", ip, port)

    keyhandler = KeyEventHandler()

    handler = lambda ws: echo(ws, keyhandler)

    # serve は context manager を返す
    async with serve(handler, ip, port):
        logger.info("WebSocket server serving on %s:%s", ip, port)
        # 永久に待機（Ctrl+C で終了）
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down server (KeyboardInterrupt)")
    except Exception:
        logger.exception("Server terminated with unexpected exception")
