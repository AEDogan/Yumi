"""Windows activity counters, foreground app, DPAPI and a global hotkey.

No key names, key text, window content or screen images leave this module.
"""
from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

import psutil

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
crypt32 = ctypes.windll.crypt32
kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
kernel32.LocalFree.restype = wintypes.HLOCAL


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.UINT), ('dwTime', wintypes.DWORD)]


class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]


class MSG(ctypes.Structure):
    _fields_ = [('hwnd', wintypes.HWND), ('message', wintypes.UINT), ('wParam', wintypes.WPARAM),
                ('lParam', wintypes.LPARAM), ('time', wintypes.DWORD), ('pt_x', wintypes.LONG),
                ('pt_y', wintypes.LONG)]


def idle_seconds() -> float:
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def active_application() -> tuple[str, str]:
    handle = user32.GetForegroundWindow()
    if not handle:
        return '', ''
    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(handle, title, 256)
    try:
        name = psutil.Process(process_id.value).name().lower()
    except (psutil.Error, OSError):
        name = ''
    return name, title.value.lower()


class ActivityCounter:
    def __init__(self):
        self.keys = list(range(48, 91)) + [8, 9, 13, 16, 17, 18, 27, 32, 37, 38, 39, 40, 186, 187, 188, 189, 190, 191]
        self.game_keys = {32, 37, 38, 39, 40, 65, 68, 83, 87}
        self.down = {}
        self.key_count = 0
        self.game_count = 0
        self.last_cursor = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(self.last_cursor))
        self.mouse_count = 0

    def sample(self):
        for key in self.keys:
            pressed = bool(user32.GetAsyncKeyState(key) & 0x8000)
            if pressed and not self.down.get(key, False):
                self.key_count += 1
                if key in self.game_keys:
                    self.game_count += 1
            self.down[key] = pressed
        point = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(point)):
            if abs(point.x - self.last_cursor.x) + abs(point.y - self.last_cursor.y) > 2:
                self.mouse_count += 1
            self.last_cursor = point

    def snapshot(self) -> dict:
        name, title = active_application()
        result = {'name': name, 'title': title, 'idle': idle_seconds(),
                  'keys': self.key_count, 'game_keys': self.game_count, 'mouse': self.mouse_count}
        self.key_count = self.game_count = self.mouse_count = 0
        return result


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def protect(data: bytes) -> bytes:
    incoming, buffer = _blob(data)
    outgoing = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(incoming), None, None, None, None, 0,
                                    ctypes.byref(outgoing)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(outgoing.pbData, wintypes.HLOCAL))


def unprotect(data: bytes) -> bytes:
    incoming, buffer = _blob(data)
    outgoing = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 0,
                                      ctypes.byref(outgoing)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(outgoing.pbData, wintypes.HLOCAL))


class GlobalHotkey:
    def __init__(self, callback):
        self.callback = callback
        self.thread_id = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, 0x0002 | 0x0001, ord('M')):
            return
        message = MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == 0x0312 and message.wParam == 1:
                    self.callback()
        finally:
            user32.UnregisterHotKey(None, 1)

    def close(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
