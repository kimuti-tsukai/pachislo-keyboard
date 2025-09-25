import asyncio
import websockets
import socket
from websockets.asyncio.server import serve
from pynput.keyboard import Controller, Key, KeyCode
from pynput import keyboard

class KeyEventHandler:
    """キーイベントを処理するクラス"""

    def __init__(self):
        self.keyboard_controller: Controller = keyboard.Controller()
        self.special_keys: dict[str, Key] = {
            'space': Key.space,
            'enter': Key.enter,
            'return': Key.enter,
            'escape': Key.esc,
            'esc': Key.esc,
            'tab': Key.tab,
            'shift': Key.shift,
            'ctrl': Key.ctrl,
            'cmd': Key.cmd,
            'option': Key.alt,
            'alt': Key.alt,
            'delete': Key.delete,
            'backspace': Key.backspace,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'page_up': Key.page_up,
            'page_down': Key.page_down,
            'f1': Key.f1,
            'f2': Key.f2,
            'f3': Key.f3,
            'f4': Key.f4,
            'f5': Key.f5,
            'f6': Key.f6,
            'f7': Key.f7,
            'f8': Key.f8,
            'f9': Key.f9,
            'f10': Key.f10,
            'f11': Key.f11,
            'f12': Key.f12,
        }

    def parse_key_combination(self, key_string: str) -> list[Key | KeyCode]:
        """
        キー組み合わせ文字列を解析
        例: "cmd+c", "ctrl+shift+a", "space"
        """
        if not key_string:
            return []

        parts = key_string.lower().split('+')
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

        return keys

    def send_key_event(self, key_string: str) -> bool:
        """
        キーイベントを送信
        戻り値: 成功時True, 失敗時False
        """
        try:
            keys = self.parse_key_combination(key_string)
            if not keys:
                return False

            # キー組み合わせの場合（複数キー）
            if len(keys) > 1:
                # 修飾キーを押下
                for key in keys[:-1]:
                    self.keyboard_controller.press(key)

                # 最後のキーを押下・離上
                self.keyboard_controller.press(keys[-1])
                self.keyboard_controller.release(keys[-1])

                # 修飾キーを離上（逆順）
                for key in reversed(keys[:-1]):
                    self.keyboard_controller.release(key)
            else:
                # 単一キーの場合
                self.keyboard_controller.press(keys[0])
                self.keyboard_controller.release(keys[0])

            return True

        except Exception as e:
            return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return "Unknown"

async def echo(keyhandler: KeyEventHandler, websocket):
    async for message in websocket:
        print(message)
        keyhandler.send_key_event(message)
        await websocket.send(message)


async def main():
    ip = "0.0.0.0"
    port = 8765
    print(f"Server started at {ip}:{port}")

    keyhandler = KeyEventHandler()

    async with serve(lambda websocket: echo(keyhandler, websocket), ip, port) as server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
