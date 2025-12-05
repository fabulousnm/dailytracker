from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty,
    StringProperty, BooleanProperty, ListProperty
)
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
import random
import math

# 游戏常量
MAX_SPEED = 15.0  # 最大速度限制
WINNING_SCORE = 11  # 获胜所需分数
SPEED_INCREASE_RATE = 1.02  # 碰撞后速度增长系数


class PongPaddle(Widget):
    """乒乓球拍类"""
    score = NumericProperty(0)  # 球员得分
    matches_won = NumericProperty(0)  # 赢得的局数（大比分）
    paddle_color = ListProperty([0.2, 0.6, 1, 1])  # 球拍颜色属性

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化球拍属性
        self.contact_zone = 0  # 接触区域（用于更真实的碰撞）

    def bounce_ball(self, ball):
        """处理球与球拍的碰撞"""
        if self.collide_widget(ball):
            # 计算接触点相对于球拍中心的位置（-1到1之间）
            relative_contact = (ball.center_y - self.center_y) / (self.height / 2)

            # 限制接触点范围，防止过于极端的角度
            relative_contact = max(-0.9, min(0.9, relative_contact))

            # 保存接触区域用于更真实的反弹
            self.contact_zone = relative_contact

            # 获取球的速度
            vx, vy = ball.velocity

            # 计算反弹后的基本速度（反向x方向，保持y方向）
            bounced = Vector(-vx, vy)

            # 应用速度增长（但不超过最大速度）
            new_vel = bounced * SPEED_INCREASE_RATE

            # 根据接触点调整反弹角度
            # 球拍上部击球会使球向上弹，下部击球会使球向下弹
            angle_adjustment = relative_contact * 2.5

            # 设置新的速度，考虑最大速度限制
            new_speed = Vector(new_vel.x, new_vel.y + angle_adjustment)

            # 应用速度上限
            if abs(new_speed.x) > MAX_SPEED:
                new_speed.x = MAX_SPEED if new_speed.x > 0 else -MAX_SPEED
            if abs(new_speed.y) > MAX_SPEED:
                new_speed.y = MAX_SPEED if new_speed.y > 0 else -MAX_SPEED

            # 确保最小速度，防止游戏太慢
            min_speed = 2.0
            if abs(new_speed.x) < min_speed:
                new_speed.x = min_speed if new_speed.x > 0 else -min_speed

            # 更新球的速度
            ball.velocity = new_speed.x, new_speed.y

            return True
        return False


class PongBall(Widget):
    """乒乓球类"""
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        """移动球的位置"""
        self.pos = Vector(*self.velocity) + self.pos


class GameMenu(ModalView):
    """游戏菜单（开始/暂停/结束）"""
    menu_type = StringProperty("main")  # 菜单类型：main, pause, game_over

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_dismiss = False
        self.size_hint = (0.8, 0.8)
        self.background_color = (0, 0, 0, 0.8)

    def create_menu(self, game_instance=None):
        """创建菜单内容"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        if self.menu_type == "main":

            start_btn = Button(text="开始游戏", size_hint=(1, 0.2),font_name='simsun.ttc')
            start_btn.bind(on_press=self.start_game)

            layout.add_widget(start_btn)

        elif self.menu_type == "pause":
            title = Label(text="游戏暂停", font_size=40, color=(1, 1, 1, 1),font_name='simsun.ttc')
            resume_btn = Button(text="继续游戏", size_hint=(1, 0.2),font_name='simsun.ttc')
            restart_btn = Button(text="重新开始", size_hint=(1, 0.2),font_name='simsun.ttc')
            main_menu_btn = Button(text="返回主菜单", size_hint=(1, 0.2),font_name='simsun.ttc')

            resume_btn.bind(on_press=self.resume_game)
            restart_btn.bind(on_press=self.restart_game)
            main_menu_btn.bind(on_press=self.return_to_main)

            layout.add_widget(title)
            layout.add_widget(resume_btn)
            layout.add_widget(restart_btn)
            layout.add_widget(main_menu_btn)

        elif self.menu_type == "game_over":
            if game_instance:
                winner = "玩家1" if game_instance.player1.score >= WINNING_SCORE else "玩家2"
                title = Label(text=f"{winner} 获胜！", font_size=40, color=(1, 1, 1, 1),font_name='simsun.ttc')
                score_text = f"比分: {game_instance.player1.score} - {game_instance.player2.score}"
                score_label = Label(text=score_text, font_size=30, color=(1, 1, 1, 1),font_name='simsun.ttc')
            else:
                title = Label(text="游戏结束", font_size=40, color=(1, 1, 1, 1),font_name='simsun.ttc')
                score_label = Label(text="", font_size=30, color=(1, 1, 1, 1))

            restart_btn = Button(text="再来一局", size_hint=(1, 0.2),font_name='simsun.ttc')
            main_menu_btn = Button(text="返回主菜单", size_hint=(1, 0.2),font_name='simsun.ttc')

            restart_btn.bind(on_press=self.restart_game)
            main_menu_btn.bind(on_press=self.return_to_main)

            layout.add_widget(title)
            layout.add_widget(score_label)
            layout.add_widget(restart_btn)
            layout.add_widget(main_menu_btn)

        self.add_widget(layout)

    def start_game(self, instance):
        """开始游戏"""
        self.dismiss()
        if hasattr(self, 'on_start'):
            self.on_start()

    def resume_game(self, instance):
        """继续游戏"""
        self.dismiss()
        if hasattr(self, 'on_resume'):
            self.on_resume()

    def restart_game(self, instance):
        """重新开始游戏"""
        self.dismiss()
        if hasattr(self, 'on_restart'):
            self.on_restart()

    def return_to_main(self, instance):
        """返回主菜单"""
        self.dismiss()
        if hasattr(self, 'on_main_menu'):
            self.on_main_menu()


class PongGame(Widget):
    """主游戏类"""
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)
    game_active = BooleanProperty(False)  # 游戏是否进行中
    game_paused = BooleanProperty(False)  # 游戏是否暂停

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化菜单
        self.main_menu = GameMenu(menu_type="main")
        self.pause_menu = GameMenu(menu_type="pause")
        self.game_over_menu = GameMenu(menu_type="game_over")

        # 绑定菜单事件
        self.main_menu.on_start = self.start_game
        self.pause_menu.on_resume = self.resume_game
        self.pause_menu.on_restart = self.reset_game
        self.pause_menu.on_main_menu = self.show_main_menu
        self.game_over_menu.on_restart = self.reset_game
        self.game_over_menu.on_main_menu = self.show_main_menu

        # 显示主菜单
        Clock.schedule_once(lambda dt: self.show_main_menu(), 0.5)

    def show_main_menu(self):
        """显示主菜单"""
        self.game_active = False
        self.main_menu.create_menu()
        self.main_menu.open()

    def show_pause_menu(self):
        """显示暂停菜单"""
        self.game_paused = True
        self.pause_menu.create_menu()
        self.pause_menu.open()

    def show_game_over_menu(self):
        """显示游戏结束菜单"""
        self.game_active = False
        self.game_over_menu.create_menu(self)
        self.game_over_menu.open()

    def start_game(self):
        """开始新游戏"""
        self.reset_game()
        self.game_active = True
        self.game_paused = False

    def resume_game(self):
        """继续游戏"""
        self.game_paused = False

    def reset_game(self):
        """重置游戏状态"""
        self.player1.score = 0
        self.player2.score = 0
        # 设置球拍颜色
        self.player1.paddle_color = [0.13, 0.59, 0.95, 1]  # 蓝色
        self.player2.paddle_color = [1, 0.34, 0.13, 1]  # 橙色
        self.serve_ball()
        self.game_active = True
        self.game_paused = False

    def serve_ball(self):
        """发球"""
        self.ball.center = self.center

        # 随机发球方向
        direction = 1 if random.random() > 0.5 else -1
        # 随机发球角度（-30到30度之间）
        angle = random.uniform(-30, 30) * math.pi / 180

        # 初始速度
        speed = 7.0
        vel_x = direction * speed * math.cos(angle)
        vel_y = speed * math.sin(angle)

        self.ball.velocity = vel_x, vel_y

    def update(self, dt):
        """游戏更新循环"""
        if not self.game_active or self.game_paused:
            return

        # 移动球
        self.ball.move()

        # 与球拍碰撞检测
        self.player1.bounce_ball(self.ball)
        self.player2.bounce_ball(self.ball)

        # 与上下边界碰撞
        if (self.ball.y < self.y) or (self.ball.top > self.top):
            self.ball.velocity_y *= -1

        # 检查是否得分
        if self.ball.x < self.x:
            # 球出左边界，玩家2得分
            self.player2.score += 1
            self.check_win_condition()
            if self.game_active:
                self.serve_ball()

        if self.ball.right > self.width:
            # 球出右边界，玩家1得分
            self.player1.score += 1
            self.check_win_condition()
            if self.game_active:
                self.serve_ball()

    def check_win_condition(self):
        """检查获胜条件"""
        if self.player1.score >= WINNING_SCORE or self.player2.score >= WINNING_SCORE:
            self.game_active = False
            # 延迟显示游戏结束菜单，让玩家看到最终比分
            Clock.schedule_once(lambda dt: self.show_game_over_menu(), 1.0)

    def on_touch_move(self, touch):
        """触摸移动控制球拍"""
        if not self.game_active or self.game_paused:
            return

        # 玩家1控制左球拍（屏幕左1/3区域）
        if touch.x < self.width / 3:
            self.player1.center_y = touch.y

        # 玩家2控制右球拍（屏幕右1/3区域）
        if touch.x > self.width - self.width / 3:
            self.player2.center_y = touch.y

    def on_key_down(self, window, key, *args):
        """键盘事件处理"""
        # 按ESC键暂停/继续游戏
        if key == 27:  # ESC键
            if self.game_active:
                if self.game_paused:
                    self.resume_game()
                else:
                    self.show_pause_menu()
            return True

        # 按R键重新开始游戏
        if key == 114:  # R键
            self.reset_game()
            return True

        # 按M键返回主菜单
        if key == 109:  # M键
            self.show_main_menu()
            return True

        return False


class PongApp(App):
    """主应用类"""

    def build(self):
        """构建应用界面"""
        # 设置窗口大小
        Window.size = (800, 600)

        # 创建游戏实例
        game = PongGame()

        # 绑定键盘事件
        Window.bind(on_key_down=game.on_key_down)

        # 启动游戏循环（60fps）
        Clock.schedule_interval(game.update, 1.0 / 60.0)

        return game

    def on_stop(self):
        """应用停止时的清理工作"""
        # 这里可以添加保存游戏状态等操作
        pass


if __name__ == '__main__':
    PongApp().run()