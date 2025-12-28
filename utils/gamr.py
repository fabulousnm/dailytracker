
# 24game_gui.py - 24点小游戏（Kivy图形界面版）
import random
import re
from itertools import permutations, product
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window

# 设置窗口大小
Window.size = (500, 400)

class GameLogic:
    """游戏逻辑封装"""
    @staticmethod
    def generate_valid_numbers():
        """生成有解的4个数字"""
        while True:
            nums = [random.randint(1, 13) for _ in range(4)]
            if GameLogic.has_solution(nums):
                return nums

    @staticmethod
    def has_solution(nums):
        """判断数字组合是否有解"""
        def calc(a, b, op):
            if op == '+':
                return a + b
            elif op == '-':
                return a - b
            elif op == '*':
                return a * b
            elif op == '/':
                if b == 0:
                    return float('inf')
                return a / b

        for num_perm in permutations(nums):
            a, b, c, d = num_perm
            for ops in product(['+', '-', '*', '/'], repeat=3):
                op1, op2, op3 = ops
                # 穷举所有运算顺序
                try:
                    res1 = calc(calc(calc(a, b, op1), c, op2), d, op3)
                    res2 = calc(calc(a, calc(b, c, op2), op1), d, op3)
                    res3 = calc(a, calc(b, calc(c, d, op3), op2), op1)
                    res4 = calc(calc(a, b, op1), calc(c, d, op3), op2)
                    res5 = calc(a, calc(calc(b, c, op2), d, op3), op1)
                    if any(abs(res - 24) < 1e-4 for res in [res1, res2, res3, res4, res5]):
                        return True
                except:
                    continue
        return False

    @staticmethod
    def validate_input(expression, target_nums):
        """验证输入是否合法"""
        # 提取数字并验证
        try:
            expr_nums = sorted([int(num) for num in re.findall(r'\d+', expression)])
            if sorted(target_nums) != expr_nums:
                return False, f"必须且只能使用 {target_nums} 这4个数字，每个数字用一次"

            # 计算结果
            result = eval(expression)
            if abs(result - 24) < 1e-4:
                return True, "恭喜你！答案正确！"
            else:
                return False, "答案错误，再试试吧！"
        except ZeroDivisionError:
            return False, "表达式包含除零错误！"
        except:
            return False, "表达式格式错误！请检查语法（例如：(1+2)*(3+5)）"

class TwentyFourGame(BoxLayout):
    """游戏界面布局"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 15

        # 当前游戏数字
        self.current_nums = []

        # 标题
        self.title_label = Label(
            text="24点小游戏（Kivy版）",
            font_size=24,
            bold=True
        )
        self.add_widget(self.title_label)

        # 数字显示标签
        self.num_label = Label(
            text="点击「新游戏」开始",
            font_size=20
        )
        self.add_widget(self.num_label)

        # 输入框
        self.input_box = TextInput(
            hint_text="输入运算表达式（例如：(1+2)*(3+5)）",
            font_size=18,
            multiline=False
        )
        self.add_widget(self.input_box)

        # 按钮布局
        btn_layout = BoxLayout(spacing=10)

        # 验证按钮
        self.check_btn = Button(
            text="验证答案",
            font_size=18,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.check_btn.bind(on_press=self.check_answer)
        btn_layout.add_widget(self.check_btn)

        # 新游戏按钮
        self.new_game_btn = Button(
            text="新游戏",
            font_size=18,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.new_game_btn.bind(on_press=self.start_new_game)
        btn_layout.add_widget(self.new_game_btn)

        self.add_widget(btn_layout)

        # 初始化新游戏
        self.start_new_game(None)

    def start_new_game(self, instance):
        """开始新游戏"""
        self.current_nums = GameLogic.generate_valid_numbers()
        self.num_label.text = f"当前数字：{self.current_nums}"
        self.input_box.text = ""

    def check_answer(self, instance):
        """验证玩家输入的答案"""
        expression = self.input_box.text.strip()
        if not expression:
            self.show_popup("提示", "请输入运算表达式！")
            return

        # 验证输入
        is_correct, message = GameLogic.validate_input(expression, self.current_nums)
        self.show_popup("结果", message)

        # 如果正确，自动开始新游戏
        if is_correct:
            self.start_new_game(None)

    def show_popup(self, title, content):
        """显示弹窗提示"""
        popup = Popup(
            title=title,
            content=Label(text=content, font_size=18),
            size_hint=(0.7, 0.4)
        )
        popup.open()

class TwentyFourApp(App):
    """Kivy应用主类"""
    def build(self):
        self.title = "24点小游戏"
        return TwentyFourGame()

if __name__ == "__main__":
    TwentyFourApp().run()