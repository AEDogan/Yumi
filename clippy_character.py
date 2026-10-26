"""Original Clippit sprite animation, independent of VRM motion and voice transport."""
import json
import random
import time
from pathlib import Path
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter

ASSETS = Path(__file__).resolve().parent / 'assets' / 'clippy'


class ClippyCharacter:
    def __init__(self):
        self.data = json.loads((ASSETS / 'agent.json').read_text(encoding='utf-8'))
        self.sheet = QImage(str(ASSETS / 'map.png'))
        if self.sheet.isNull():
            raise ValueError('Clippy animasyon görseli açılamadı.')
        self.animations = self.data['animations']
        self.name = 'RestPose'
        self.index = 0
        self.image_positions = [[0, 0]]
        self.deadline = 0.
        self.started = 0.
        self.state = 'idle'
        self.next_idle = 0.
        self.pending = None
        self.play('Greeting')

    def play(self, name, now=None):
        if name not in self.animations:
            return False
        now = time.perf_counter() if now is None else now
        self.name = name
        self.index = 0
        self.started = now
        self.pending = None
        self._frame(now)
        return True

    def _frame(self, now):
        frame = self.animations[self.name]['frames'][self.index]
        # Missing images mean retain the preceding drawing, as in Microsoft Agent.
        if 'images' in frame:
            self.image_positions = frame['images']
        self.deadline = now + max(10, frame.get('duration', 100)) / 1000.

    def advance(self, state='idle', now=None):
        now = time.perf_counter() if now is None else now
        if state != self.state:
            self.state = state
            self.pending = {'speaking': 'Explain', 'thinking': 'Thinking',
                            'listening': 'Hearing_1'}.get(state, 'RestPose')
        if now < self.deadline:
            return
        frames = self.animations[self.name]['frames']
        frame = frames[self.index]
        exiting = self.pending is not None or now - self.started > 12
        if exiting and 'exitBranch' in frame:
            index = frame['exitBranch']
        else:
            index = self.index + 1
            if not exiting:
                roll = random.randrange(100)
                for branch in frame.get('branching', {}).get('branches', []):
                    if roll < branch['weight']:
                        index = branch['frameIndex']
                        break
                    roll -= branch['weight']
        if index >= len(frames):
            target = self.pending
            if target:
                self.play(target, now)
            elif state != 'idle':
                self.play({'speaking': 'Explain', 'thinking': 'Thinking',
                           'listening': 'Hearing_1'}[state], now)
            elif now >= self.next_idle:
                self.next_idle = now + random.uniform(7, 15)
                self.play(random.choice(['Idle1_1', 'IdleEyeBrowRaise',
                                         'IdleHeadScratch', 'LookLeft', 'LookRight',
                                         'IdleFingerTap', 'IdleSideToSide']), now)
            else:
                self.play('RestPose', now)
            return
        self.index = index
        self._frame(now)

    def draw(self, painter, rect):
        width, height = self.data['framesize']
        scale = min(rect.width() / 400, rect.height() / 440) * 2
        target = QRectF((rect.width() - width * scale) / 2,
                        rect.height() - height * scale - 8 * scale,
                        width * scale, height * scale)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        for x, y in self.image_positions:
            painter.drawImage(target, self.sheet, QRectF(x, y, width, height))
