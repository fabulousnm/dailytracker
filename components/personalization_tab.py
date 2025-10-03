from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex



class PersonalizationTab(BoxLayout):
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_settings = {}

        # 延迟添加测试按钮，确保界面已加载
        from kivy.clock import Clock
        Clock.schedule_once(self.add_test_buttons, 0.5)

    def add_test_buttons(self, dt):
        """添加测试主题切换的按钮"""
        try:
            # 创建测试按钮布局
            test_layout = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=50,
                spacing=10
            )

            # 添加测试按钮
            sunny_btn = Button(text='Test Sunny', size_hint_x=0.33)
            sunny_btn.bind(on_press=lambda x: self.change_theme('sunny theme'))

            cloudy_btn = Button(text='Test Cloudy', size_hint_x=0.33)
            cloudy_btn.bind(on_press=lambda x: self.change_theme('cloudy theme'))

            rainy_btn = Button(text='Test Rainy', size_hint_x=0.33)
            rainy_btn.bind(on_press=lambda x: self.change_theme('rainy theme'))

            test_layout.add_widget(sunny_btn)
            test_layout.add_widget(cloudy_btn)
            test_layout.add_widget(rainy_btn)

            # 将测试按钮添加到主布局中
            self.add_widget(test_layout)

        except Exception as e:
            print(f"Failed to add test buttons: {e}")

    def update_theme(self, colors):
        """更新主题"""
        try:
            # 清除现有canvas
            self.canvas.before.clear()

            # 添加背景色
            with self.canvas.before:
                Color(*get_color_from_hex(colors['background']))
                Rectangle(pos=self.pos, size=self.size)
        except Exception as e:
            print(f"fail: {e}")

    def customize_color(self, module):
        """自定义模块颜色"""
        try:
            self.show_message(f"开始自定义 {module} 模块颜色\n(功能开发中)")
        except Exception as e:
            print(f"自定义颜色失败: {e}")

    def change_theme(self, theme_name):
        """Change theme"""
        try:
            print(f"=== User requested theme change: {theme_name} ===")

            if hasattr(self, 'app') and self.app:
                theme_map = {
                    'sunny theme': 'sunny',
                    'cloudy theme': 'cloudy',
                    'rainy theme': 'rainy'
                }
                theme_key = theme_map.get(theme_name, 'sunny')
                print(f"Mapped theme key: {theme_key}")

                # Directly call app's update_theme method
                if hasattr(self.app, 'update_theme'):
                    print("Found app.update_theme method, calling...")
                    self.app.update_theme(theme_key)
                else:
                    print("!!! Error: app does not have update_theme method !!!")

                self.show_message(f"Theme changed to {theme_name} successfully")
            else:
                print("!!! Error: personalization_tab has no app reference !!!")

        except Exception as e:
            print(f"!!! Theme change failed: {e} !!!")

    def show_message(self, message):
        """显示消息提示"""
        try:
            popup = Popup(
                title='tips',
                content=Label(text=message, padding=20),
                size_hint=(0.6, 0.4)
            )
            popup.open()
        except Exception as e:
            print(f"fail: {e}")