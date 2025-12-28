import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

# ---------------------------
# 游戏参数
# ---------------------------
BOARD_W = 10
BOARD_H = 20

# Kivy窗口可自行调
Window.size = (520, 720)

# 方块定义（SRS简化版：仅使用一套旋转表）
# 每个形状用4个相对坐标表示（以(0,0)为参考）
SHAPES = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}

# 颜色（RGB 0~1）
COLORS = {
    "I": (0.2, 0.9, 0.9),
    "O": (0.95, 0.9, 0.2),
    "T": (0.7, 0.3, 0.9),
    "S": (0.3, 0.9, 0.3),
    "Z": (0.95, 0.3, 0.3),
    "J": (0.3, 0.5, 0.95),
    "L": (0.95, 0.6, 0.2),
}

# ---------------------------
# 数据结构
# ---------------------------
@dataclass
class Piece:
    kind: str
    x: int
    y: int
    rotation: int = 0  # 0,1,2,3

    def cells(self) -> List[Tuple[int, int]]:
        """返回当前旋转后的4个格子坐标（相对原点）。"""
        pts = SHAPES[self.kind]
        rot = self.rotation % 4
        if rot == 0:
            return pts[:]
        # 旋转：围绕(1.5,1.5)的简化格点旋转（适合4x4框）
        # 为了简单，这里将点放入4x4格子中旋转： (x,y)->(y, 3-x)
        # 先把所有点按4x4系统旋转
        out = pts[:]
        for _ in range(rot):
            out = [(py, 3 - px) for (px, py) in out]
        return out


# ---------------------------
# 核心游戏逻辑
# ---------------------------
class TetrisGame:
    def __init__(self):
        self.board: List[List[Optional[str]]] = [[None for _ in range(BOARD_W)] for _ in range(BOARD_H)]
        self.score = 0
        self.lines = 0
        self.level = 1

        self.cur: Piece = self._new_piece()
        self.next_kind: str = random.choice(list(SHAPES.keys()))
        self.game_over = False

        # 下落速度（秒）
        self.base_drop_interval = 0.6

    def reset(self):
        self.__init__()

    def _new_piece(self) -> Piece:
        kind = random.choice(list(SHAPES.keys()))
        # 生成在顶部中央附近
        p = Piece(kind=kind, x=BOARD_W // 2 - 2, y=0, rotation=0)
        return p

    def spawn_next(self):
        self.cur = Piece(kind=self.next_kind, x=BOARD_W // 2 - 2, y=0, rotation=0)
        self.next_kind = random.choice(list(SHAPES.keys()))
        if self._collides(self.cur, self.cur.x, self.cur.y, self.cur.rotation):
            self.game_over = True

    def _collides(self, piece: Piece, nx: int, ny: int, nrot: int) -> bool:
        test = Piece(piece.kind, nx, ny, nrot)
        for cx, cy in test.cells():
            bx = nx + cx
            by = ny + cy
            if bx < 0 or bx >= BOARD_W or by < 0 or by >= BOARD_H:
                return True
            if self.board[by][bx] is not None:
                return True
        return False

    def _lock_piece(self):
        for cx, cy in self.cur.cells():
            bx = self.cur.x + cx
            by = self.cur.y + cy
            if 0 <= by < BOARD_H and 0 <= bx < BOARD_W:
                self.board[by][bx] = self.cur.kind
        cleared = self._clear_lines()
        if cleared > 0:
            self.lines += cleared
            # 简单计分：1/2/3/4行分别为100/300/500/800 * level
            add = [0, 100, 300, 500, 800][cleared] * self.level
            self.score += add
            self.level = 1 + self.lines // 10

        self.spawn_next()

    def _clear_lines(self) -> int:
        new_board = []
        cleared = 0
        for row in self.board:
            if all(cell is not None for cell in row):
                cleared += 1
            else:
                new_board.append(row)
        while len(new_board) < BOARD_H:
            new_board.insert(0, [None for _ in range(BOARD_W)])
        self.board = new_board
        return cleared

    def move(self, dx: int, dy: int) -> bool:
        if self.game_over:
            return False
        nx, ny = self.cur.x + dx, self.cur.y + dy
        if not self._collides(self.cur, nx, ny, self.cur.rotation):
            self.cur.x, self.cur.y = nx, ny
            return True
        return False

    def rotate(self, direction: int = 1) -> bool:
        """direction=1 顺时针，-1 逆时针。"""
        if self.game_over:
            return False
        nrot = (self.cur.rotation + direction) % 4

        # 简单墙踢：尝试几个偏移
        kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for kx, ky in kicks:
            nx, ny = self.cur.x + kx, self.cur.y + ky
            if not self._collides(self.cur, nx, ny, nrot):
                self.cur.x, self.cur.y, self.cur.rotation = nx, ny, nrot
                return True
        return False

    def soft_drop(self) -> bool:
        """软降（下移一格）。"""
        if self.move(0, 1):
            self.score += 1  # 软降加分（可选）
            return True
        # 到底锁定
        self._lock_piece()
        return False

    def hard_drop(self):
        """硬降（直接落到底）。"""
        if self.game_over:
            return
        dropped = 0
        while self.move(0, 1):
            dropped += 1
        self.score += 2 * dropped  # 硬降加分（可选）
        self._lock_piece()

    def tick(self):
        """自动下落一次。"""
        if self.game_over:
            return
        moved = self.move(0, 1)
        if not moved:
            self._lock_piece()

    def drop_interval(self) -> float:
        # 随等级加速
        return max(0.08, self.base_drop_interval - 0.04 * (self.level - 1))


# ---------------------------
# Kivy绘制/交互
# ---------------------------
class TetrisBoardWidget(Widget):
    def __init__(self, game: TetrisGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.cell_size = dp(28)
        self.margin = dp(12)
        self.bind(pos=self._redraw, size=self._redraw)

    def board_origin(self) -> Tuple[float, float]:
        # 让棋盘居中
        bw = BOARD_W * self.cell_size
        bh = BOARD_H * self.cell_size
        ox = self.x + (self.width - bw) / 2
        oy = self.y + (self.height - bh) / 2
        return ox, oy

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            ox, oy = self.board_origin()
            bw = BOARD_W * self.cell_size
            bh = BOARD_H * self.cell_size

            # 背景
            Color(0.08, 0.09, 0.11)
            Rectangle(pos=(ox, oy), size=(bw, bh))

            # 网格线
            Color(0.18, 0.2, 0.25)
            for x in range(BOARD_W + 1):
                Line(points=[ox + x * self.cell_size, oy, ox + x * self.cell_size, oy + bh], width=1)
            for y in range(BOARD_H + 1):
                Line(points=[ox, oy + y * self.cell_size, ox + bw, oy + y * self.cell_size], width=1)

            # 固定方块
            for y in range(BOARD_H):
                for x in range(BOARD_W):
                    kind = self.game.board[y][x]
                    if kind:
                        self._draw_cell(ox, oy, x, y, kind, alpha=1.0)

            # 幽灵方块（预览落点）
            if not self.game.game_over:
                ghost_y = self.game.cur.y
                while not self.game._collides(self.game.cur, self.game.cur.x, ghost_y + 1, self.game.cur.rotation):
                    ghost_y += 1
                for cx, cy in self.game.cur.cells():
                    gx = self.game.cur.x + cx
                    gy = ghost_y + cy
                    if 0 <= gx < BOARD_W and 0 <= gy < BOARD_H:
                        self._draw_cell(ox, oy, gx, gy, self.game.cur.kind, alpha=0.25)

            # 当前活动方块
            if not self.game.game_over:
                for cx, cy in self.game.cur.cells():
                    bx = self.game.cur.x + cx
                    by = self.game.cur.y + cy
                    if 0 <= bx < BOARD_W and 0 <= by < BOARD_H:
                        self._draw_cell(ox, oy, bx, by, self.game.cur.kind, alpha=1.0)

            # 游戏结束遮罩
            if self.game.game_over:
                Color(0, 0, 0, 0.55)
                Rectangle(pos=(ox, oy), size=(bw, bh))

    def _draw_cell(self, ox, oy, x, y, kind, alpha=1.0):
        r, g, b = COLORS[kind]
        Color(r, g, b, alpha)
        # y向下增长 -> 屏幕坐标 y向上增长，因此要翻转
        sy = BOARD_H - 1 - y
        px = ox + x * self.cell_size
        py = oy + sy * self.cell_size
        Rectangle(pos=(px + 1, py + 1), size=(self.cell_size - 2, self.cell_size - 2))


class TetrisRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(10), **kwargs)
        self.game = TetrisGame()

        # 顶部信息栏
        self.info = Label(size_hint_y=None, height=dp(40), text=self._info_text(), font_size="18sp")
        self.add_widget(self.info)

        # 棋盘
        self.board = TetrisBoardWidget(self.game, size_hint=(1, 1))
        self.add_widget(self.board)

        # 底部提示
        self.help = Label(
            size_hint_y=None,
            height=dp(70),
            text="操作：←→ 移动 | ↑ 旋转 | ↓ 软降 | 空格 硬降 | R 重开",
            font_size="16sp",
        )
        self.add_widget(self.help)

        # 键盘绑定
        Window.bind(on_key_down=self.on_key_down)

        # 定时器
        self._event = None
        self._reschedule_tick()

        # 刷新绘制
        Clock.schedule_interval(self._ui_refresh, 1 / 30)

    def _info_text(self) -> str:
        status = "（游戏结束，按 R 重开）" if self.game.game_over else ""
        return f"Score: {self.game.score}   Lines: {self.game.lines}   Level: {self.game.level} {status}"

    def _ui_refresh(self, dt):
        self.info.text = self._info_text()
        self.board._redraw()

    def _reschedule_tick(self):
        if self._event is not None:
            self._event.cancel()
        self._event = Clock.schedule_interval(self._tick, self.game.drop_interval())

    def _tick(self, dt):
        old_level = self.game.level
        self.game.tick()
        # 如果等级变化，更新下落速度
        if self.game.level != old_level:
            self._reschedule_tick()

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        if key in (ord("r"), ord("R")):
            self.game.reset()
            self._reschedule_tick()
            return True

        if self.game.game_over:
            return False

        # Kivy keycode: 273 up, 274 down, 275 right, 276 left, 32 space
        if key == 276:  # left
            self.game.move(-1, 0)
            return True
        if key == 275:  # right
            self.game.move(1, 0)
            return True
        if key == 274:  # down
            self.game.soft_drop()
            return True
        if key == 273:  # up
            self.game.rotate(1)
            return True
        if key == 32:  # space
            self.game.hard_drop()
            return True
        return False


class TetrisApp(App):
    def build(self):
        self.title = "Kivy Tetris"
        return TetrisRoot()


if __name__ == "__main__":
    TetrisApp().run()
