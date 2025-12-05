from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Line
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
import shutil
import os
from PIL import Image as PILImage
import io
import subprocess
import sys
import os
from kivy.uix.popup import Popup
from kivy.uix.label import Label

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
            self.display_x = 50 #图片的出现位置
            self.display_y = (self.height - self.display_height) #图片的出现位置
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
            #Rectangle(pos=(50, 150), size=(self.width, self.height))#灰色背景位置

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
        self.padding = 20
        self.spacing = 15
        self.selected_file_path = None

        # 添加标题
        title_label = Label(
            text="个性化设置",
            font_size=24,
            size_hint_y=None,
            height=50,
            font_name='simsun.ttc',
            bold=True
        )
        self.add_widget(title_label)

        # 添加上传按钮
        upload_btn = Button(
            text="上传图片",
            size_hint_y=None,
            height=50,
            font_name='simsun.ttc',
            bold=True,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        upload_btn.bind(on_press=self.show_file_chooser)
        self.add_widget(upload_btn)

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

        # 先定义更新函数
        def update_filechooser_bg(instance, value):
            if hasattr(instance, 'background_rect'):  # 添加属性检查
                instance.background_rect.pos = (50,50)
                instance.background_rect.size = instance.size
        with file_chooser.canvas.before:
            from kivy.core.image import Image as CoreImage
            texture = CoreImage('assets/images/back.jpg').texture
            original_width = CoreImage('assets/images/back.jpg').width
            original_height = CoreImage('assets/images/back.jpg').height
            image_ratio = original_width / original_height

            # 计算保持比例的尺寸
            widget_width = file_chooser.width
            widget_height = file_chooser.height
            widget_ratio = widget_width / widget_height

            if image_ratio > widget_ratio:
                # 图片较宽，以宽度为基准
                display_width = widget_width
                display_height = widget_width / image_ratio
                display_x = 0
                display_y = (widget_height - display_height) / 2
            else:
                # 图片较高，以高度为基准
                display_height = widget_height
                display_width = widget_height * image_ratio
                display_x = (widget_width - display_width) / 2
                display_y = 0

            Rectangle(
                texture=texture,
                pos=(display_x, display_y),
                size=(display_width*5.2, display_height*5.7)
            )

        # 同样需要绑定更新函数
        file_chooser.bind(pos=update_filechooser_bg, size=update_filechooser_bg)
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
                self.show_message("请先选择一张图片")

        def on_cancel(instance):
            popup.dismiss()

        confirm_btn.bind(on_press=on_confirm)
        cancel_btn.bind(on_press=on_cancel)

        return popup

    def show_file_chooser(self, instance):
        """显示文件选择器"""
        try:
            popup = self.create_file_chooser_popup()
            popup.open()
        except Exception as e:
            print(f"打开文件选择器失败: {e}")
            self.show_message("打开文件选择器失败")

    def create_crop_popup(self):
        """创建图片裁剪弹窗"""
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            self.show_message("图片文件不存在")
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
            crop_ratio=(3, 4),#图片比例
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
            ,background='assets/images/image.jpg'  # 使用图片作为背景

        )



        # 绑定按钮事件
        def on_crop(instance):
            cropped_image = crop_widget.crop_image()
            if cropped_image:
                self.save_cropped_image(cropped_image)
                popup.dismiss()
                self.show_message("图片裁剪并保存成功！")
            else:
                self.show_message("裁剪失败，请重试")

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
            self.show_message("裁剪界面加载失败")

    def save_cropped_image(self, cropped_image):
        """保存裁剪后的图片"""
        try:
            # 确保目标目录存在
            target_dir = os.path.join('assets', 'images')
            os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, 'img.png')

            # 保存图片
            cropped_image.save(target_path, 'PNG')
            cropped_image.close()

            print(f"图片已保存：{target_path}")

        except Exception as e:
            print(f"保存图片失败: {e}")
            self.show_message("保存图片失败")

    def show_message(self, message):
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
            title='提示',
            content=content,
            size_hint=(None, None),
            size=(320, 200),
            auto_dismiss=False
        )

        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def run_pingpong_game(self):
        """运行乒乓球游戏"""
        try:
            # 获取上一级目录的game文件夹路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            pingpong_path = os.path.join(game_dir, 'pingpong.py')

            # 检查文件是否存在
            if not os.path.exists(pingpong_path):
                self.show_popup("错误", f"找不到游戏文件:\n{pingpong_path}")
                return

            print(f"尝试运行游戏: {pingpong_path}")
            print(f"游戏目录: {game_dir}")

            # 运行游戏
            if sys.platform == 'win32':
                # Windows系统
                subprocess.Popen(['python', 'pingpong.py'], cwd=game_dir, shell=True)
            elif sys.platform == 'darwin':
                # macOS系统
                subprocess.Popen(['python3', 'pingpong.py'], cwd=game_dir)
            else:
                # Linux等其他系统
                subprocess.Popen(['python3', 'pingpong.py'], cwd=game_dir)

            self.show_popup("提示", "正在启动乒乓球游戏...")

        except Exception as e:
            error_msg = f"启动游戏失败:\n{str(e)}"
            print(error_msg)
            self.show_popup("错误", error_msg)

    def show_popup(self, title, message):
        """显示提示弹窗"""
        popup = Popup(
            title=title,
            content=Label(text=message, font_size='16sp',font_name='simsun.ttc'),
            size_hint=(0.7, 0.4)
        )
        popup.open()
    def run_twenty48_game(self):
        """运行乒乓球游戏"""
        try:
            # 获取上一级目录的game文件夹路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            game_dir = os.path.join(parent_dir, 'game')
            twenty48_path = os.path.join(game_dir, 'twenty48.py')

            # 检查文件是否存在
            if not os.path.exists(twenty48_path):
                self.show_popup("错误", f"找不到游戏文件:\n{twenty48_path}")
                return

            print(f"尝试运行游戏: {twenty48_path}")
            print(f"游戏目录: {game_dir}")

            # 运行游戏
            if sys.platform == 'win32':
                # Windows系统
                subprocess.Popen(['python', 'twenty48.py'], cwd=game_dir, shell=True)
            elif sys.platform == 'darwin':
                # macOS系统
                subprocess.Popen(['python3', 'twenty48.py'], cwd=game_dir)
            else:
                # Linux等其他系统
                subprocess.Popen(['python3', 'twenty48.py'], cwd=game_dir)

            self.show_popup("loading....", "正在启动2048游戏...")

        except Exception as e:
            error_msg = f"启动游戏失败:\n{str(e)}"
            print(error_msg)
            self.show_popup("错误", error_msg)

    def show_popup(self, title, message):
        """显示提示弹窗"""
        popup = Popup(
            title=title,
            content=Label(text=message, font_size='16sp',font_name='simsun.ttc'),
            size_hint=(0.7, 0.4)
        )
        popup.open()