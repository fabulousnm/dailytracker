# twenty48.py - 主Python文件
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.properties import (
    NumericProperty, StringProperty, ListProperty,
    BooleanProperty, ObjectProperty
)
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle, RoundedRectangle
import random
import json
import os


class Tile(ButtonBehavior, Label):
    """游戏格子类"""
    value = NumericProperty(0)  # 格子中的数字
    bg_color = ListProperty([0.78, 0.73, 0.66, 1])  # 背景颜色
    text_color = ListProperty([0.47, 0.43, 0.39, 1])  # 文字颜色
    is_new = BooleanProperty(False)  # 是否是新生成的格子
    is_merged = BooleanProperty(False)  # 是否是合并产生的格子

    def __init__(self, value=0, **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.update_colors()

    def update_colors(self):
        """根据数字值更新颜色"""
        # 数字对应的颜色映射
        color_map = {
            0: [0.78, 0.73, 0.66, 0.35],  # 空格子
            2: [0.93, 0.89, 0.85, 1],
            4: [0.93, 0.88, 0.78, 1],
            8: [0.95, 0.69, 0.47, 1],
            16: [0.96, 0.58, 0.39, 1],
            32: [0.96, 0.49, 0.37, 1],
            64: [0.96, 0.37, 0.23, 1],
            128: [0.93, 0.81, 0.45, 1],
            256: [0.93, 0.80, 0.38, 1],
            512: [0.93, 0.78, 0.31, 1],
            1024: [0.93, 0.77, 0.25, 1],
            2048: [0.93, 0.75, 0.19, 1],
            4096: [0.24, 0.22, 0.19, 1],
            8192: [0.24, 0.22, 0.19, 1]
        }

        # 文字颜色映射
        text_color_map = {
            0: [0.47, 0.43, 0.39, 0],
            2: [0.47, 0.43, 0.39, 1],
            4: [0.47, 0.43, 0.39, 1],
            8: [0.97, 0.96, 0.95, 1],
            16: [0.97, 0.96, 0.95, 1],
            32: [0.97, 0.96, 0.95, 1],
            64: [0.97, 0.96, 0.95, 1],
            128: [0.97, 0.96, 0.95, 1],
            256: [0.97, 0.96, 0.95, 1],
            512: [0.97, 0.96, 0.95, 1],
            1024: [0.97, 0.96, 0.95, 1],
            2048: [0.97, 0.96, 0.95, 1],
            4096: [0.97, 0.96, 0.95, 1],
            8192: [0.97, 0.96, 0.95, 1]
        }

        self.bg_color = color_map.get(self.value, [0.24, 0.22, 0.19, 1])
        self.text_color = text_color_map.get(self.value, [0.97, 0.96, 0.95, 1])

        # 更新文字显示
        self.text = str(self.value) if self.value > 0 else ""

        # 根据数字大小调整字体大小
        if self.value < 100:
            self.font_size = '40sp'
        elif self.value < 1000:
            self.font_size = '35sp'
        elif self.value < 10000:
            self.font_size = '28sp'
        else:
            self.font_size = '22sp'


class GameBoard(GridLayout):
    """游戏主网格"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 4
        self.rows = 4
        self.spacing = [10, 10]
        self.padding = [10, 10, 10, 10]
        self.size_hint = (None, None)
        self.size = (370, 370)

        # 初始化所有格子
        self.tiles = []
        for i in range(16):
            tile = Tile(value=0)
            self.tiles.append(tile)
            self.add_widget(tile)

    def get_tile(self, row, col):
        """获取指定位置的格子"""
        index = row * 4 + col
        if 0 <= index < 16:
            return self.tiles[index]
        return None

    def set_tile_value(self, row, col, value):
        """设置指定位置的格子值"""
        tile = self.get_tile(row, col)
        if tile:
            tile.value = value
            tile.update_colors()
            return tile
        return None


class GameGrid(BoxLayout):
    """游戏主界面"""
    score = NumericProperty(0)
    best_score = NumericProperty(0)
    game_over = BooleanProperty(False)
    game_won = BooleanProperty(False)
    grid_size = NumericProperty(4)  # 添加grid_size属性

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = 20
        self.padding = [20, 20, 20, 20]

        # 游戏网格逻辑
        self.tile_values = [[0 for _ in range(self.grid_size)]
                            for _ in range(self.grid_size)]

        # 加载最高分
        self.load_best_score()

        # 绑定键盘事件
        Window.bind(on_key_down=self.on_key_down)

        # 延迟初始化游戏
        Clock.schedule_once(lambda dt: self.reset_game(), 0.1)

    def load_best_score(self):
        """加载最高分"""
        try:
            if os.path.exists('2048_best_score.json'):
                with open('2048_best_score.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.best_score = data.get('best_score', 0)
        except:
            self.best_score = 0

    def save_best_score(self):
        """保存最高分"""
        try:
            with open('2048_best_score.json', 'w', encoding='utf-8') as f:
                json.dump({'best_score': self.best_score}, f, ensure_ascii=False)
        except:
            pass

    def reset_game(self):
        """重置游戏"""
        # 重置分数和状态
        self.score = 0
        self.game_over = False
        self.game_won = False

        # 清空所有格子
        self.tile_values = [[0 for _ in range(self.grid_size)]
                            for _ in range(self.grid_size)]

        # 更新显示
        self.update_board()

        # 生成初始的两个数字
        self.add_random_tile()
        self.add_random_tile()

    def update_board(self):
        """更新游戏板显示"""
        if hasattr(self, 'ids') and 'game_board' in self.ids:
            game_board = self.ids.game_board
            for i in range(self.grid_size):
                for j in range(self.grid_size):
                    tile = game_board.get_tile(i, j)
                    if tile:
                        tile.value = self.tile_values[i][j]
                        tile.update_colors()

    def add_random_tile(self):
        """在随机空位置添加一个数字"""
        empty_cells = []

        # 找出所有空位置
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.tile_values[i][j] == 0:
                    empty_cells.append((i, j))

        if empty_cells:
            # 随机选择一个空位置
            row, col = random.choice(empty_cells)

            # 随机生成数字（90%概率为2，10%概率为4）
            value = 2 if random.random() < 0.9 else 4

            # 设置格子值
            self.tile_values[row][col] = value
            self.update_board()

            # 标记为新格子
            if hasattr(self, 'ids') and 'game_board' in self.ids:
                game_board = self.ids.game_board
                tile = game_board.get_tile(row, col)
                if tile:
                    tile.is_new = True
                    Clock.schedule_once(lambda dt: setattr(tile, 'is_new', False), 0.3)

    def move_tiles(self, direction):
        """移动格子"""
        if self.game_over:
            return False

        # 复制当前状态以检测是否有移动
        old_values = [row[:] for row in self.tile_values]
        moved = False
        size = self.grid_size

        if direction == 'left':
            for row in range(size):
                moved = self.move_row_left(row) or moved
        elif direction == 'right':
            for row in range(size):
                moved = self.move_row_right(row) or moved
        elif direction == 'up':
            for col in range(size):
                moved = self.move_col_up(col) or moved
        elif direction == 'down':
            for col in range(size):
                moved = self.move_col_down(col) or moved

        # 检查是否有移动
        if old_values != self.tile_values:
            moved = True

        # 如果有移动，添加新数字并检查游戏状态
        if moved:
            self.add_random_tile()
            self.check_game_state()
            self.update_board()

            # 更新最高分
            if self.score > self.best_score:
                self.best_score = self.score
                self.save_best_score()

        return moved

    def move_row_left(self, row):
        """向左移动一行"""
        moved = False
        size = self.grid_size

        # 合并相邻的相同数字
        for col in range(size - 1):
            current_val = self.tile_values[row][col]
            if current_val == 0:
                continue

            for next_col in range(col + 1, size):
                next_val = self.tile_values[row][next_col]
                if next_val == 0:
                    continue

                if current_val == next_val:
                    # 合并
                    new_val = current_val * 2
                    self.tile_values[row][col] = new_val
                    self.tile_values[row][next_col] = 0
                    self.score += new_val
                    moved = True

                    # 标记合并效果
                    if hasattr(self, 'ids') and 'game_board' in self.ids:
                        game_board = self.ids.game_board
                        tile = game_board.get_tile(row, col)
                        if tile:
                            tile.is_merged = True
                            Clock.schedule_once(lambda dt: setattr(tile, 'is_merged', False), 0.3)
                    break
                else:
                    break

        # 移动格子填补空隙
        for col in range(size):
            if self.tile_values[row][col] == 0:
                for next_col in range(col + 1, size):
                    if self.tile_values[row][next_col] != 0:
                        self.tile_values[row][col] = self.tile_values[row][next_col]
                        self.tile_values[row][next_col] = 0
                        moved = True
                        break

        return moved

    def move_row_right(self, row):
        """向右移动一行"""
        moved = False
        size = self.grid_size

        for col in range(size - 1, 0, -1):
            current_val = self.tile_values[row][col]
            if current_val == 0:
                continue

            for prev_col in range(col - 1, -1, -1):
                prev_val = self.tile_values[row][prev_col]
                if prev_val == 0:
                    continue

                if current_val == prev_val:
                    new_val = current_val * 2
                    self.tile_values[row][col] = new_val
                    self.tile_values[row][prev_col] = 0
                    self.score += new_val
                    moved = True

                    if hasattr(self, 'ids') and 'game_board' in self.ids:
                        game_board = self.ids.game_board
                        tile = game_board.get_tile(row, col)
                        if tile:
                            tile.is_merged = True
                            Clock.schedule_once(lambda dt: setattr(tile, 'is_merged', False), 0.3)
                    break
                else:
                    break

        for col in range(size - 1, -1, -1):
            if self.tile_values[row][col] == 0:
                for prev_col in range(col - 1, -1, -1):
                    if self.tile_values[row][prev_col] != 0:
                        self.tile_values[row][col] = self.tile_values[row][prev_col]
                        self.tile_values[row][prev_col] = 0
                        moved = True
                        break

        return moved

    def move_col_up(self, col):
        """向上移动一列"""
        moved = False
        size = self.grid_size

        for row in range(size - 1):
            current_val = self.tile_values[row][col]
            if current_val == 0:
                continue

            for next_row in range(row + 1, size):
                next_val = self.tile_values[next_row][col]
                if next_val == 0:
                    continue

                if current_val == next_val:
                    new_val = current_val * 2
                    self.tile_values[row][col] = new_val
                    self.tile_values[next_row][col] = 0
                    self.score += new_val
                    moved = True

                    if hasattr(self, 'ids') and 'game_board' in self.ids:
                        game_board = self.ids.game_board
                        tile = game_board.get_tile(row, col)
                        if tile:
                            tile.is_merged = True
                            Clock.schedule_once(lambda dt: setattr(tile, 'is_merged', False), 0.3)
                    break
                else:
                    break

        for row in range(size):
            if self.tile_values[row][col] == 0:
                for next_row in range(row + 1, size):
                    if self.tile_values[next_row][col] != 0:
                        self.tile_values[row][col] = self.tile_values[next_row][col]
                        self.tile_values[next_row][col] = 0
                        moved = True
                        break

        return moved

    def move_col_down(self, col):
        """向下移动一列"""
        moved = False
        size = self.grid_size

        for row in range(size - 1, 0, -1):
            current_val = self.tile_values[row][col]
            if current_val == 0:
                continue

            for prev_row in range(row - 1, -1, -1):
                prev_val = self.tile_values[prev_row][col]
                if prev_val == 0:
                    continue

                if current_val == prev_val:
                    new_val = current_val * 2
                    self.tile_values[row][col] = new_val
                    self.tile_values[prev_row][col] = 0
                    self.score += new_val
                    moved = True

                    if hasattr(self, 'ids') and 'game_board' in self.ids:
                        game_board = self.ids.game_board
                        tile = game_board.get_tile(row, col)
                        if tile:
                            tile.is_merged = True
                            Clock.schedule_once(lambda dt: setattr(tile, 'is_merged', False), 0.3)
                    break
                else:
                    break

        for row in range(size - 1, -1, -1):
            if self.tile_values[row][col] == 0:
                for prev_row in range(row - 1, -1, -1):
                    if self.tile_values[prev_row][col] != 0:
                        self.tile_values[row][col] = self.tile_values[prev_row][col]
                        self.tile_values[prev_row][col] = 0
                        moved = True
                        break

        return moved

    def has_possible_moves(self):
        """检查是否还有可能的移动"""
        size = self.grid_size

        # 检查是否有空位置
        for i in range(size):
            for j in range(size):
                if self.tile_values[i][j] == 0:
                    return True

        # 检查是否有相邻的相同数字
        for i in range(size):
            for j in range(size):
                current = self.tile_values[i][j]
                if current == 0:
                    continue

                if j < size - 1 and self.tile_values[i][j + 1] == current:
                    return True

                if i < size - 1 and self.tile_values[i + 1][j] == current:
                    return True

        return False

    def check_game_state(self):
        """检查游戏状态"""
        # 检查是否达到2048
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.tile_values[i][j] == 2048 and not self.game_won:
                    self.game_won = True

        # 检查游戏是否结束
        if not self.has_possible_moves():
            self.game_over = True

    def on_key_down(self, window, key, *args):
        """处理键盘事件"""
        if key == 273 or key == 119:  # 上箭头或W键
            self.move_tiles('up')
        elif key == 274 or key == 115:  # 下箭头或S键
            self.move_tiles('down')
        elif key == 275 or key == 100:  # 右箭头或D键
            self.move_tiles('right')
        elif key == 276 or key == 97:  # 左箭头或A键
            self.move_tiles('left')
        elif key == 114:  # R键 - 重新开始
            self.reset_game()
        return True

    def show_instructions(self):
        """显示操作说明"""
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # 标题
        title = Label(
            text='游戏说明',
            font_size='28sp',
            font_name='simsun.ttc',

            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=50
        )
        content.add_widget(title)

        # 滚动区域
        scroll = ScrollView()
        instructions_text = """       游戏目标：
 通过移动格子，合并相同的数字，最终创造出
 2048这个数字。

 操作方法：
 • 方向键 ↑ ↓ ← → 移动格子
 • WASD 键也可以移动
 • R 键重新开始游戏

 游戏规则：
 1. 每次移动时，所有格子会朝移动方向滑动
 2. 相同数字的格子相撞时会合并
 3. 每次移动后会在空位置随机生成一个新数字（2或4）
 4. 当没有空位置且无法合并时游戏结束

 提示：
 • 尽量保持最大的数字在角落
 • 避免随意移动，要有策略地合并
 • 尝试预测新数字出现的位置
"""
        instructions = Label(
            text=instructions_text,
            font_size='15sp',
            font_name='simsun.ttc',
            color=(1, 1,1, 1),
            size_hint_y=None,
            text_size=(400, None),
            valign='top',
            halign='left'
        )
        instructions.bind(texture_size=instructions.setter('size'))
        scroll.add_widget(instructions)
        content.add_widget(scroll)

        # 关闭按钮
        close_btn = Button(
            text='关闭',
            font_name='simsun.ttc',
            font_size='20sp',
            size_hint_y=None,
            height=50,
            background_color=(0.56, 0.48, 0.4, 1),
            color=(1, 1, 1, 1)
        )

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.8),
            auto_dismiss=False,
            separator_height=0
        )

        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)

        popup.open()


class Twenty48App(App):
    """2048游戏主应用"""

    def build(self):
        # 设置窗口大小
        Window.size = (450, 650)
        Window.clearcolor = (0.98, 0.97, 0.95, 1)

        # 创建主游戏界面
        return GameGrid()

    def show_instructions(self):
        """显示操作说明"""
        if hasattr(self.root, 'show_instructions'):
            self.root.show_instructions()


if __name__ == '__main__':
    Twenty48App().run()