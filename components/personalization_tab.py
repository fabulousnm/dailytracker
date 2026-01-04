# personalization_tab.py 修改后的版本
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Line, RoundedRectangle
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
import shutil
import os
from PIL import Image as PILImage
import io
import subprocess
import sys
import webbrowser


class ImageCropWidget(Widget):
    def __init__(self, source, crop_ratio=(3, 4), **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.crop_ratio = crop_ratio
        self.crop_rect = None
        self.dragging = False
        self.last_touch_pos = None
        self.scale_x = 1
        self.scale_y = 1
        self.display_x = 0
        self.display_y = 0
        self.display_width = 0
        self.display_height = 0
        self.texture = None

        # 加载图片
        self.load_image()

        # 绑定触摸事件
        self.bind(size=self.update_graphics, pos=self.update_graphics)

    def load_image(self):
        """加载图片并计算初始裁剪区域"""
        try:
            # 使用PIL打开图片获取尺寸
            pil_img = PILImage.open(self.source)
            self.original_size = pil_img.size

            # 将PIL图像转换为Kivy纹理 - 修复倒置问题
            pil_img_rgb = pil_img.convert('RGB')

            # 翻转图片以适应Kivy的坐标系
            pil_img_flipped = pil_img_rgb.transpose(PILImage.FLIP_TOP_BOTTOM)
            img_data = pil_img_flipped.tobytes()

            # 创建Kivy纹理
            self.texture = Texture.create(size=pil_img_rgb.size, colorfmt='rgb')
            self.texture.blit_buffer(img_data, colorfmt='rgb', bufferfmt='ubyte')

            pil_img.close()
            pil_img_rgb.close()

            # 计算适合的裁剪区域大小
            img_width, img_height = self.original_size
            ratio_w, ratio_h = self.crop_ratio

            # 根据图片尺寸和比例计算裁剪区域大小
            if img_width / img_height > ratio_w / ratio_h:
                # 图片较宽，以高度为基准
                crop_height = min(img_height, img_width * ratio_h / ratio_w)
                crop_width = crop_height * ratio_w / ratio_h
            else:
                # 图片较高，以宽度为基准
                crop_width = min(img_width, img_height * ratio_w / ratio_h)
                crop_height = crop_width * ratio_h / ratio_w

            self.crop_size = (crop_width, crop_height)

            # 初始裁剪区域居中
            crop_x = (img_width - crop_width) / 2
            crop_y = (img_height - crop_height) / 2
            self.crop_pos = (crop_x, crop_y)

        except Exception as e:
            print(f"加载图片失败: {e}")
            # 使用默认值
            self.original_size = (800, 600)
            self.crop_size = (300, 400)
            # 确保默认值也居中
            self.crop_pos = (250, 100)  # (800-300)/2=250, (600-400)/2=100

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dragging = True
            self.last_touch_pos = touch.pos
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.dragging and self.last_touch_pos:
            # 计算移动距离（转换为图片坐标）
            dx = (touch.x - self.last_touch_pos[0]) / self.scale_x
            dy = (touch.y - self.last_touch_pos[1]) / self.scale_y

            # 更新裁剪区域位置（反向移动，因为我们在移动裁剪框而不是图片）
            new_x = max(0, min(self.original_size[0] - self.crop_size[0], self.crop_pos[0] - dx))
            new_y = max(0, min(self.original_size[1] - self.crop_size[1], self.crop_pos[1] - dy))

            self.crop_pos = (new_x, new_y)
            self.last_touch_pos = touch.pos
            self.update_graphics()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.dragging = False
        self.last_touch_pos = None
        return super().on_touch_up(touch)

    def update_graphics(self, *args):
        """更新图形显示"""
        self.canvas.clear()

        if not hasattr(self, 'original_size'):
            return

        # 计算图片在widget中的显示尺寸和位置
        img_width, img_height = self.original_size
        img_ratio = img_width / img_height
        widget_ratio = self.width / self.height if self.height > 0 else 1

        if img_ratio > widget_ratio:
            # 图片较宽，以宽度为基准
            self.display_width = self.width
            self.display_height = self.width / img_ratio
            self.display_x = 50  # 图片的出现位置
            self.display_y = (self.height - self.display_height)  # 图片的出现位置
        else:
            # 图片较高，以高度为基准
            self.display_height = self.height
            self.display_width = self.height * img_ratio
            self.display_x = (self.width - self.display_width) / 2
            self.display_y = 0

        # 计算缩放比例
        self.scale_x = self.display_width / img_width
        self.scale_y = self.display_height / img_height

        with self.canvas:
            # 绘制背景
            # Color(1, 1, 1, 1)
            # Rectangle(pos=(50, 150), size=(self.width, self.height))#灰色背景位置

            # 绘制完整的图片
            if self.texture:
                Color(1, 1, 1, 1)
                Rectangle(
                    texture=self.texture,
                    pos=(self.display_x, self.display_y),
                    size=(self.display_width, self.display_height)
                )
            else:
                # 如果没有纹理，显示灰色背景
                Color(0.5, 0.5, 0.5, 1)
                Rectangle(pos=(self.display_x, self.display_y),
                          size=(self.display_width, self.display_height))

            # 计算裁剪区域在显示中的位置和大小
            crop_display_x = self.display_x + self.crop_pos[0] * self.scale_x
            crop_display_y = self.display_y + self.crop_pos[1] * self.scale_y
            crop_display_width = self.crop_size[0] * self.scale_x
            crop_display_height = self.crop_size[1] * self.scale_y

            # 绘制裁剪区域内的预览（实际图片部分）
            if self.texture:
                # 计算纹理坐标（归一化）
                tex_x = self.crop_pos[0] / img_width
                tex_y = self.crop_pos[1] / img_height
                tex_width = self.crop_size[0] / img_width
                tex_height = self.crop_size[1] / img_height

                # 创建一个临时纹理来显示裁剪区域（高亮显示）
                Color(1, 1, 1, 0.8)
                Rectangle(
                    texture=self.texture,
                    pos=(crop_display_x, crop_display_y),
                    size=(crop_display_width, crop_display_height),
                    tex_coords=(
                        tex_x, tex_y,  # 左下
                        tex_x + tex_width, tex_y,  # 右下
                        tex_x + tex_width, tex_y + tex_height,  # 右上
                        tex_x, tex_y + tex_height  # 左上
                    )
                )

            # 绘制裁剪区域边框
            Color(1, 0, 0, 1)
            Line(
                rectangle=(crop_display_x, crop_display_y, crop_display_width, crop_display_height),
                width=3
            )

            # 绘制角标记
            corner_size = 15
            # 左上角
            Line(points=[
                crop_display_x, crop_display_y,
                crop_display_x + corner_size, crop_display_y
            ], width=2)
            Line(points=[
                crop_display_x, crop_display_y,
                crop_display_x, crop_display_y + corner_size
            ], width=2)
            # 右上角
            Line(points=[
                crop_display_x + crop_display_width, crop_display_y,
                crop_display_x + crop_display_width - corner_size, crop_display_y
            ], width=2)
            Line(points=[
                crop_display_x + crop_display_width, crop_display_y,
                crop_display_x + crop_display_width, crop_display_y + corner_size
            ], width=2)
            # 左下角
            Line(points=[
                crop_display_x, crop_display_y + crop_display_height,
                                crop_display_x + corner_size, crop_display_y + crop_display_height
            ], width=2)
            Line(points=[
                crop_display_x, crop_display_y + crop_display_height,
                crop_display_x, crop_display_y + crop_display_height - corner_size
            ], width=2)
            # 右下角
            Line(points=[
                crop_display_x + crop_display_width, crop_display_y + crop_display_height,
                crop_display_x + crop_display_width - corner_size, crop_display_y + crop_display_height
            ], width=2)
            Line(points=[
                crop_display_x + crop_display_width, crop_display_y + crop_display_height,
                crop_display_x + crop_display_width, crop_display_y + crop_display_height - corner_size
            ], width=2)

            # 绘制半透明遮罩（非裁剪区域）
            Color(0, 0, 0, 0.6)
            # 上遮罩
            if crop_display_y + crop_display_height < self.display_y + self.display_height:
                Rectangle(
                    pos=(self.display_x, crop_display_y + crop_display_height),
                    size=(self.display_width,
                          self.display_y + self.display_height - crop_display_y - crop_display_height)
                )
            # 下遮罩
            if crop_display_y > self.display_y:
                Rectangle(
                    pos=(self.display_x, self.display_y),
                    size=(self.display_width, crop_display_y - self.display_y)
                )
            # 左遮罩
            if crop_display_x > self.display_x:
                Rectangle(
                    pos=(self.display_x, crop_display_y),
                    size=(crop_display_x - self.display_x, crop_display_height)
                )
            # 右遮罩
            if crop_display_x + crop_display_width < self.display_x + self.display_width:
                Rectangle(
                    pos=(crop_display_x + crop_display_width, crop_display_y),
                    size=(self.display_x + self.display_width - crop_display_x - crop_display_width,
                          crop_display_height)
                )

    def crop_image(self):
        """执行裁剪操作"""
        try:
            # 使用PIL进行裁剪
            pil_img = PILImage.open(self.source)

            # 计算实际裁剪区域（确保在图片范围内）
            x = max(0, min(self.original_size[0] - self.crop_size[0], self.crop_pos[0]))
            y = max(0, min(self.original_size[1] - self.crop_size[1], self.crop_pos[1]))
            width = min(self.crop_size[0], self.original_size[0] - x)
            height = min(self.crop_size[1], self.original_size[1] - y)

            # 执行裁剪
            cropped_img = pil_img.crop((x, y, x + width, y + height))
            pil_img.close()

            return cropped_img

        except Exception as e:
            print(f"裁剪图片失败: {e}")
            return None


class PersonalizationTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 5]
        self.spacing = 10
        self.selected_file_path = None



        # 创建三部分界面
        self.create_interface()

    def update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.95, 0.95, 0.98, 1)
            Rectangle(pos=self.pos, size=self.size)

    def create_interface(self):
        """创建三部分界面"""

        # ===== 第一部分：顶部个性化图片按钮 =====
        top_section = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.15),
            padding=[20, 10],
            spacing=10
        )

        top_title = Label(
            text="个性化设置",
            font_size=28,
            size_hint_y=None,
            height=40,
            font_name='simsun.ttc',
            bold=True,
            color=(0.1, 0.1, 0.3, 1)
        )

        top_button = Button(
            text="                 上传个性化图片",
            size_hint_y=None,
            height=60,
            font_name='simsun.ttc',
            font_size=18,
            bold=True,
            background_color=(1.0, 0.8, 0.8, 0.8),
            color=(1, 1, 1, 1)
        )
        top_button.bind(on_press=self.show_file_chooser)

        top_section.add_widget(top_title)
        top_section.add_widget(top_button)
        self.add_widget(top_section)

        # 添加分隔线


        # ===== 第二部分：大学生帮助按钮 =====
        middle_section = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.12),
            padding=[20, 10],
            spacing=10
        )

        middle_title = Label(
            text="学习帮助",
            font_size=24,
            size_hint_y=None,
            height=30,
            font_name='simsun.ttc',
            bold=True,
            color=(0.1, 0.1, 0.3, 1)
        )

        help_button = Button(
            text="                 大学生帮助文档",
            size_hint_y=None,
            height=70,
            font_name='simsun.ttc',
            font_size=18,
            bold=True,
            background_color=(0.85, 0.95, 0.85, 0.7),
            color=(1, 1, 1, 1)
        )
        help_button.bind(on_press=self.open_student_help)

        middle_section.add_widget(middle_title)
        middle_section.add_widget(help_button)
        self.add_widget(middle_section)

        # ===== 第三部分：游戏专区 =====
        game_section = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.7),
            padding=[10, 5],
            spacing=15
        )

        # 游戏专区标题
        game_title = Label(
            text="🎮 游戏专区",
            font_size=26,
            size_hint_y=None,
            height=40,
            font_name='simsun.ttc',
            bold=True,
            color=(0.1, 0.1, 0.3, 1)
        )
        game_section.add_widget(game_title)

        # 创建可滚动的游戏区域
        scroll_view = ScrollView(size_hint=(1, 1))
        game_container = GridLayout(
            cols=1,
            spacing=15,
            size_hint_y=None,
            padding=[10, 10, 10, 20]
        )
        game_container.bind(minimum_height=game_container.setter('height'))

        # 单人游戏区域
        # 单人游戏区域
        single_player_section = self.create_game_section("单人游戏", [
            ("▶ 俄罗斯方块", "tetris.py", (0.2, 0.6, 0.9, 1)),  # 蓝色
            ("▶ 2048游戏", "twenty48.py", (0.3, 0.7, 0.5, 1)),  # 绿色
            ("📖 数独游戏", "数独.html", (0.9, 0.7, 0.3, 1)),  # 橙色
            ("📖 华容道", "华容道.html", (0.6, 0.8, 0.4, 1)),  # 浅绿色
            ("📖 打砖块", "打砖块.html", (0.9, 0.5, 0.3, 1)),  # 橙红色
            ("📖 扫雷", "扫雷.html", (0.7, 0.5, 0.8, 1)),  # 紫色
            ("📖 推箱子", "推箱子.html", (0.5, 0.7, 0.9, 1)),  # 浅蓝色
            ("📖 贪吃蛇", "贪吃蛇游戏11.html", (0.4, 0.8, 0.6, 1))  # 青色
        ])


        game_container.add_widget(single_player_section)

        # 双人游戏区域
        double_player_section = self.create_game_section("双人游戏", [
            ("▶ 乒乓球", "pingpong.py", (0.9, 0.3, 0.3, 1)),  # 红色
            ("📖 中国象棋", "中国象棋.html", (0.8, 0.5, 0.2, 1)),  # 橙色
            ("📖 五子棋", "五子棋.html", (0.3, 0.3, 0.8, 1))  # 蓝色
        ])
        game_container.add_widget(double_player_section)

        scroll_view.add_widget(game_container)
        game_section.add_widget(scroll_view)
        self.add_widget(game_section)

    def create_game_section(self, title, games):
        """创建游戏区域"""
        section = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=len(games) * 80 + 50,  # 根据游戏数量调整高度
            spacing=10
        )

        # 区域标题
        title_label = Label(
            text=title,
            font_size=22,
            size_hint_y=None,
            height=40,
            font_name='simsun.ttc',
            bold=True,
            color=(0.1, 0.1, 0.3, 1)
        )
        section.add_widget(title_label)

        # 游戏按钮
        for game_name, game_file, color in games:
            btn = Button(
                text=game_name,
                size_hint_y=None,
                height=70,
                font_name='simsun.ttc',
                font_size=18,
                bold=True,
                color=(1, 1, 1, 1),
                background_color=color,  # 直接使用你定义的颜色
                background_normal=''  # 关键：移除默认灰色背景
            )



            # 绑定不同的事件处理函数
            if game_file.endswith('.py'):
                if game_file == 'pingpong.py':
                    btn.bind(on_press=lambda x, f=game_file: self.run_pingpong_game())
                elif game_file == 'tetris.py':
                    btn.bind(on_press=lambda x, f=game_file: self.run_tetris_game())
                elif game_file == 'twenty48.py':
                    btn.bind(on_press=lambda x, f=game_file: self.run_twenty48_game())
            else:
                btn.bind(on_press=lambda x, f=game_file: self.open_html_game(f))

            section.add_widget(btn)

        return section

    def open_student_help(self, instance):
        """打开大学生帮助文档"""
        try:
            # 直接打开网页链接
            help_url = "https://witty-dune-008ad7600.4.azurestaticapps.net/"

            # 使用webbrowser打开网页
            webbrowser.open(help_url)
            self.show_message("提示", "正在打开大学生帮助网站...")

        except Exception as e:
            self.show_message("错误", f"打开网站失败:\n{str(e)}")

    def open_html_game(self, game_file):
        """打开HTML游戏"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            game_path = os.path.join(game_dir, game_file)

            if os.path.exists(game_path):
                webbrowser.open(f'file://{os.path.abspath(game_path)}')

            else:
                self.show_message("错误", f"找不到游戏文件:\n{game_file}")
        except Exception as e:
            self.show_message("错误", f"打开游戏失败:\n{str(e)}")

    def run_pingpong_game(self):
        """运行乒乓球游戏"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            game_path = os.path.join(game_dir, 'pingpong.py')

            if not os.path.exists(game_path):
                self.show_message("错误", f"找不到游戏文件:\n{game_path}")
                return

            # 运行游戏
            if sys.platform == 'win32':
                subprocess.Popen(['python', 'pingpong.py'], cwd=game_dir, shell=True)
            elif sys.platform == 'darwin':
                subprocess.Popen(['python3', 'pingpong.py'], cwd=game_dir)
            else:
                subprocess.Popen(['python3', 'pingpong.py'], cwd=game_dir)



        except Exception as e:
            self.show_message("错误", f"启动游戏失败:\n{str(e)}")

    def run_tetris_game(self):
        """运行俄罗斯方块游戏"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            game_path = os.path.join(game_dir, 'tetris.py')

            if not os.path.exists(game_path):
                self.show_message("错误", f"找不到游戏文件:\n{game_path}")
                return

            # 运行游戏
            if sys.platform == 'win32':
                subprocess.Popen(['python', 'tetris.py'], cwd=game_dir, shell=True)
            elif sys.platform == 'darwin':
                subprocess.Popen(['python3', 'tetris.py'], cwd=game_dir)
            else:
                subprocess.Popen(['python3', 'tetris.py'], cwd=game_dir)



        except Exception as e:
            self.show_message("错误", f"启动游戏失败:\n{str(e)}")

    def run_twenty48_game(self):
        """运行2048游戏"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            game_path = os.path.join(game_dir, 'twenty48.py')

            if not os.path.exists(game_path):
                self.show_message("错误", f"找不到游戏文件:\n{game_path}")
                return

            # 运行游戏
            if sys.platform == 'win32':
                subprocess.Popen(['python', 'twenty48.py'], cwd=game_dir, shell=True)
            elif sys.platform == 'darwin':
                subprocess.Popen(['python3', 'twenty48.py'], cwd=game_dir)
            else:
                subprocess.Popen(['python3', 'twenty48.py'], cwd=game_dir)



        except Exception as e:
            self.show_message("错误", f"启动游戏失败:\n{str(e)}")

    def show_file_chooser(self, instance):
        """显示文件选择器"""
        try:
            popup = self.create_file_chooser_popup()
            popup.open()
        except Exception as e:
            print(f"打开文件选择器失败: {e}")
            self.show_message("错误", "打开文件选择器失败")

    def create_file_chooser_popup(self):
        """创建文件选择器弹窗"""
        # 创建主布局
        main_layout = BoxLayout(orientation='vertical', spacing=10)

        # 创建文件选择器
        file_chooser = FileChooserListView(
            path=os.path.expanduser('~'),
            filters=['*.png', '*.jpg', '*.jpeg'],
            size_hint=(1, 0.8)
        )

        # 创建按钮布局
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10
        )

        confirm_btn = Button(
            text='选择图片',
            font_name='simsun.ttc',
            background_color=(0.8980, 0.9882, 1.0, 1)
        )

        cancel_btn = Button(
            text='取消',
            font_name='simsun.ttc',
            background_color=(0.7725, 0.9020, 0.7137, 1)
        )

        button_layout.add_widget(confirm_btn)
        button_layout.add_widget(cancel_btn)

        # 添加到主布局
        main_layout.add_widget(Label(
            text="选择图片文件",
            size_hint_y=None,
            height=30,
            font_name='simsun.ttc'
        ))
        main_layout.add_widget(file_chooser)
        main_layout.add_widget(button_layout)

        # 创建弹窗
        popup = Popup(
            title='选择图片',
            title_font='simsun.ttc',
            content=main_layout,
            size_hint=(0.8, 0.8),
            auto_dismiss=False
        )

        # 绑定按钮事件
        def on_confirm(instance):
            if file_chooser.selection:
                self.selected_file_path = file_chooser.selection[0]
                popup.dismiss()
                self.show_crop_interface()
            else:
                self.show_message("提示", "请先选择一张图片")

        def on_cancel(instance):
            popup.dismiss()

        confirm_btn.bind(on_press=on_confirm)
        cancel_btn.bind(on_press=on_cancel)

        return popup

    def create_crop_popup(self):
        """创建图片裁剪弹窗"""
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            self.show_message("错误", "图片文件不存在")
            return None

        # 创建主布局
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # 添加说明
        instruction = Label(
            text="拖动图片选择裁剪区域 (3:4比例)\n红色框内为最终显示区域",
            bold=True,
            color=(0.85, 0.85, 0.85, 1),
            size_hint_y=None,
            height=80,
            font_name='STHUPO.ttf',
            font_size=30,
            halign='center'
        )
        instruction.bind(size=instruction.setter('text_size'))
        main_layout.add_widget(instruction)

        # 添加裁剪组件
        crop_widget = ImageCropWidget(
            source=self.selected_file_path,
            crop_ratio=(3, 4),  # 图片比例
            size_hint=(1, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        main_layout.add_widget(crop_widget)

        # 添加按钮布局
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=60,
            spacing=20,
            padding=10
        )

        crop_btn = Button(
            text='确认裁剪',
            font_name='simsun.ttc',
            background_color=(0.6, 0.95, 0.6, 1)
        )

        retry_btn = Button(
            text='重新选择',
            font_name='simsun.ttc',
            background_color=(1.0, 1.0, 0.9, 1)
        )

        cancel_btn = Button(
            text='取消',
            font_name='simsun.ttc',
            background_color=(1.0, 0.75, 0.7, 1)
        )

        button_layout.add_widget(crop_btn)
        button_layout.add_widget(retry_btn)
        button_layout.add_widget(cancel_btn)
        main_layout.add_widget(button_layout)

        # 创建弹窗
        popup = Popup(
            title='裁剪图片',
            title_font='STHUPO.ttf',
            content=main_layout,
            size_hint=(0.9, 0.9),
            auto_dismiss=False,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # 绑定按钮事件
        def on_crop(instance):
            cropped_image = crop_widget.crop_image()
            if cropped_image:
                self.save_cropped_image(cropped_image)
                popup.dismiss()
                self.show_message("提示", "图片裁剪并保存成功！")
            else:
                self.show_message("错误", "裁剪失败，请重试")

        def on_retry(instance):
            popup.dismiss()
            self.show_file_chooser(None)

        def on_cancel(instance):
            popup.dismiss()

        crop_btn.bind(on_press=on_crop)
        retry_btn.bind(on_press=on_retry)
        cancel_btn.bind(on_press=on_cancel)

        return popup

    def show_crop_interface(self):
        """显示图片裁剪界面"""
        try:
            popup = self.create_crop_popup()
            if popup:
                popup.open()
        except Exception as e:
            print(f"显示裁剪界面失败: {e}")
            self.show_message("错误", "裁剪界面加载失败")

    def save_cropped_image(self, cropped_image):
        """保存裁剪后的图片"""
        try:
            # 确保目标目录存在
            target_dir = os.path.join('assets', 'images')
            os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, 'xingye.png')

            # 保存图片
            cropped_image.save(target_path, 'PNG')
            cropped_image.close()

            print(f"图片已保存：{target_path}")

        except Exception as e:
            print(f"保存图片失败: {e}")
            self.show_message("错误", "保存图片失败")

    def show_message(self, title, message):
        """显示消息弹窗"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(Label(
            text=message,
            font_name='simsun.ttc',
            text_size=(280, None)
        ))

        ok_btn = Button(
            text='确定',
            size_hint_y=None,
            height=40,
            font_name='simsun.ttc'
        )
        content.add_widget(ok_btn)

        popup = Popup(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(320, 200),
            auto_dismiss=False
        )

        ok_btn.bind(on_press=popup.dismiss)
        popup.open()