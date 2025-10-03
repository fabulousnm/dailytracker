# main.py - 完整修改版
import os
import sys
import locale


# ========== 强制中文字体配置 ==========
def init_chinese_support():
    """强制初始化中文支持"""
    print("=== 初始化中文支持 ===")

    # 1. 设置系统编码
    try:
        if hasattr(sys, 'setdefaultencoding'):
            sys.setdefaultencoding('utf-8')
    except:
        pass

    # 2. 设置locale
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'chinese')
        except:
            print("警告: 无法设置中文locale")

    # 3. 强制注册中文字体
    from kivy.core.text import LabelBase
    from kivy.config import Config

    # Windows 11 字体优先级列表
    font_priority = [
        ('MicrosoftYaHei', 'C:/Windows/Fonts/msyh.ttc'),  # 微软雅黑
        ('SimHei', 'C:/Windows/Fonts/simhei.ttf'),  # 黑体
        ('DengXian', 'C:/Windows/Fonts/Deng.ttf'),  # 等线
        ('SimSun', 'C:/Windows/Fonts/simsun.ttc'),  # 宋体
    ]

    registered_font = None
    for font_name, font_path in font_priority:
        if os.path.exists(font_path):
            try:
                LabelBase.register(font_name, font_path)
                print(f"✅ 成功注册字体: {font_name}")
                registered_font = font_name
                break
            except Exception as e:
                print(f"❌ 注册字体失败 {font_name}: {e}")

    # 4. 强制设置默认字体
    if registered_font:
        Config.set('kivy', 'default_font', [registered_font])
        print(f"✅ 设置默认字体为: {registered_font}")
    else:
        print("❌ 未找到可用的中文字体")

    # 5. 设置文本渲染选项
    Config.set('graphics', 'maxfps', 60)
    Config.set('kivy', 'log_level', 'info')


# 在导入Kivy之前调用字体初始化
init_chinese_support()

# ========== 正常导入Kivy和其他模块 ==========
from kivy import platform
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
import json
import datetime
import os

# 其余代码保持不变...

# 其余代码保持不变...
# 尝试导入组件
try:
    from components.schedule_tab import ScheduleTab
    from components.tracking_tab import TrackingTab
    from components.personalization_tab import PersonalizationTab

    COMPONENTS_AVAILABLE = True
    print("组件导入成功")
except ImportError as e:
    print(f"组件导入失败: {e}")
    COMPONENTS_AVAILABLE = False


    # 定义简单的备用组件
    class ScheduleTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 20
            self.spacing = 10
            self.add_widget(Label(text='每日行程', font_size='24sp', bold=True))
            self.add_widget(Label(text='起床时间: 07:00', font_size='18sp'))
            self.add_widget(Label(text='睡觉时间: 23:00', font_size='18sp'))

        def update_alarm_display(self):
            pass

        def update_theme(self, colors):
            pass


    class TrackingTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 10
            self.spacing = 10
            self.add_widget(Label(text='每日踪迹', font_size='24sp', bold=True))
            self.add_widget(Label(text='位置跟踪功能', font_size='16sp'))

        def update_theme(self, colors):
            pass


    class PersonalizationTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 20
            self.spacing = 15
            self.add_widget(Label(text='个性化设置', font_size='24sp', bold=True))
            self.add_widget(Label(text='SJTU - 设定你的时间，管理你的一天！', font_size='14sp', italic=True))

        def update_theme(self, colors):
            pass

        def customize_color(self, module):
            print(f"自定义颜色: {module}")

        def change_theme(self, theme_name):
            print(f"更改主题: {theme_name}")

        def show_message(self, message):
            print(f"消息: {message}")


class DailyTracker(TabbedPanel):
    # 定义属性以便在KV中访问
    schedule_tab = ObjectProperty(None)
    tracking_tab = ObjectProperty(None)
    personalization_tab = ObjectProperty(None)

    # 用于显示品牌信息
    brand_name = StringProperty("SJTU DailyTracker")
    slogan = StringProperty("设定你的时间，管理你的一天！")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.tab_pos = 'top_mid'

        # 主题颜色配置
        self.theme_colors = {
            'sunny': {
                'primary': '#FFD700',  # 黄色
                'secondary': '#32CD32',  # 绿色
                'background': '#FFFFFF'  # 白色
            },
            'cloudy': {
                'primary': '#808080',  # 灰色
                'secondary': '#800080',  # 紫色
                'background': '#F5F5F5'  # 浅灰
            },
            'rainy': {
                'primary': '#0000FF',  # 蓝色
                'secondary': '#000000',  # 黑色
                'background': '#E8E8E8'  # 浅灰
            }
        }
        self.current_theme = 'sunny'

        # 初始化数据文件
        self.data_file = "user_data.json"
        self.load_user_data()

        # 启动服务
        Clock.schedule_once(self.init_services, 1)

    def init_services(self, dt):
        """初始化所有服务"""
        print("初始化应用服务...")

        # 初始化天气服务
        try:
            from utils.weather_api import WeatherManager
            self.weather_manager = WeatherManager()
            # 获取当前天气并更新主题
            self.update_weather_theme()
        except Exception as e:
            print(f"天气服务初始化失败: {e}")
            # 使用默认主题
            self.update_theme('sunny')

        # 初始化Android特定服务
        if platform == 'android':
            try:
                from utils.location_manager import LocationManager
                from utils.alarm_reader import AlarmReader

                self.location_manager = LocationManager(self)
                self.alarm_reader = AlarmReader()

                # 开始位置跟踪
                self.location_manager.start_tracking()
                print("位置跟踪服务已启动")

                # 读取闹钟数据
                self.update_alarm_info()

            except Exception as e:
                print(f"Android服务初始化失败: {e}")
        else:
            print("非Android平台，使用模拟数据")
            self.setup_desktop_simulation()

    def setup_desktop_simulation(self):
        """设置桌面环境模拟数据"""
        try:
            # 模拟闹钟数据
            self.user_data['wake_time'] = "07:30"
            self.user_data['sleep_time'] = "23:30"
            self.save_user_data()

            # 更新UI显示
            if self.schedule_tab:
                Clock.schedule_once(lambda dt: self.schedule_tab.update_alarm_display(), 0.5)

        except Exception as e:
            print(f"桌面模拟设置失败: {e}")

    def load_user_data(self):
        """加载用户数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                print("用户数据加载成功")
            else:
                self.create_default_data()
        except Exception as e:
            print(f"加载用户数据失败: {e}")
            self.create_default_data()

    def create_default_data(self):
        """创建默认用户数据"""
        self.user_data = {
            'sleep_time': "23:00",
            'wake_time': "07:00",
            'locations': {
                'home': {
                    'name': '家',
                    'events': ['休息', '睡觉', '打游戏'],
                    'coords': [31.0258, 121.4376]
                },
                'canteen': {
                    'name': '食堂',
                    'events': ['吃饭'],
                    'coords': [31.0260, 121.4380]
                },
                'classroom': {
                    'name': '教室',
                    'events': ['上课'],
                    'coords': [31.0255, 121.4370]
                },
                'library': {
                    'name': '图书馆',
                    'events': ['学习', '休息'],
                    'coords': [31.0262, 121.4378]
                },
                'sports': {
                    'name': '操场',
                    'events': ['运动', '跑步'],
                    'coords': [31.0268, 121.4390]
                }
            },
            'speed_threshold': 5.0,
            'running_threshold': 3.0,
            'stay_threshold': 60,
            'personalization': {},
            'notes': [],
            'activities': []
        }
        self.save_user_data()
        print("默认用户数据已创建")

    def save_user_data(self):
        """保存用户数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存用户数据失败: {e}")

    def update_alarm_info(self):
        """更新闹钟信息"""
        if hasattr(self, 'alarm_reader'):
            try:
                alarms = self.alarm_reader.get_alarms()
                if alarms:
                    self.user_data['wake_time'] = min(alarms)
                    self.user_data['sleep_time'] = max(alarms)
                    self.save_user_data()

                    # 更新UI显示
                    if self.schedule_tab:
                        self.schedule_tab.update_alarm_display()

                    print(f"闹钟数据更新: 起床 {self.user_data['wake_time']}, 睡觉 {self.user_data['sleep_time']}")
            except Exception as e:
                print(f"读取闹钟错误: {e}")

    def update_weather_theme(self):
        """根据天气更新主题"""
        try:
            if hasattr(self, 'weather_manager'):
                # 获取天气信息（使用上海交通大学的坐标）
                weather_data = self.weather_manager.get_current_weather(31.0258, 121.4376)
                weather_type = weather_data.get('weather', 'sunny')

                # 映射天气类型到主题
                weather_map = {
                    'clear': 'sunny',
                    'sunny': 'sunny',
                    'cloudy': 'cloudy',
                    'overcast': 'cloudy',
                    'rain': 'rainy',
                    'rainy': 'rainy',
                    'snow': 'rainy'
                }

                theme = weather_map.get(weather_type, 'sunny')
                self.update_theme(theme)
                print(f"天气主题已更新: {weather_type} -> {theme}")

        except Exception as e:
            print(f"天气更新错误: {e}")
            self.update_theme('sunny')

    def update_theme(self, weather_type):
        """应用主题颜色"""
        try:
            self.current_theme = weather_type
            colors = self.theme_colors[weather_type]

            # 更新窗口背景色
            Window.clearcolor = get_color_from_hex(colors['background'])

            # 通知所有标签页更新主题
            if self.schedule_tab:
                self.schedule_tab.update_theme(colors)
            if self.tracking_tab:
                self.tracking_tab.update_theme(colors)
            if self.personalization_tab:
                self.personalization_tab.update_theme(colors)

            print(f"主题已应用: {weather_type}")

        except Exception as e:
            print(f"应用主题失败: {e}")

    def add_note(self, activity_data, text, image_path=None):
        """添加活动备注"""
        try:
            note = {
                'timestamp': datetime.datetime.now().isoformat(),
                'activity': activity_data,
                'text': text,
                'image': image_path
            }

            if 'notes' not in self.user_data:
                self.user_data['notes'] = []

            self.user_data['notes'].append(note)
            self.save_user_data()
            print("备注已添加")

        except Exception as e:
            print(f"添加备注失败: {e}")

    def customize_color(self, module):
        """自定义模块颜色"""
        if self.personalization_tab:
            self.personalization_tab.customize_color(module)

    def change_theme(self, theme_name):
        """更改主题"""
        if self.personalization_tab:
            self.personalization_tab.change_theme(theme_name)

    def update_speed_threshold(self, value):
        """更新速度阈值"""
        try:
            self.user_data['speed_threshold'] = float(value)
            self.save_user_data()

            if hasattr(self, 'location_manager'):
                self.location_manager.speed_threshold = float(value)

            if self.tracking_tab:
                self.tracking_tab.speed_threshold = float(value)

            print(f"速度阈值已更新: {value} m/s")

        except Exception as e:
            print(f"更新速度阈值失败: {e}")

    def save_settings(self):
        """保存所有设置"""
        try:
            self.save_user_data()
            print("设置已保存")

            # 显示保存成功消息
            if self.personalization_tab:
                self.personalization_tab.show_message("设置保存成功！")

        except Exception as e:
            print(f"保存设置失败: {e}")

    def reset_settings(self):
        """重置设置为默认值"""
        try:
            self.create_default_data()

            # 重新加载主题
            self.update_theme('sunny')

            # 更新所有标签页
            if self.schedule_tab:
                self.schedule_tab.update_alarm_display()
                if hasattr(self.schedule_tab, 'clear_activities'):
                    self.schedule_tab.clear_activities()

            if self.tracking_tab:
                if hasattr(self.tracking_tab, 'clear_logs'):
                    self.tracking_tab.clear_logs()

            print("设置已重置为默认值")

            if self.personalization_tab:
                self.personalization_tab.show_message("设置已重置为默认值！")

        except Exception as e:
            print(f"重置设置失败: {e}")


class DailyTrackerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "DailyTracker - SJTU"

    def build(self):
        print("启动 DailyTracker 应用...")
        # 设置初始窗口大小（便于桌面测试）
        Window.size = (400, 700)
        return DailyTracker()

    def on_pause(self):
        """应用暂停时调用"""
        try:
            if hasattr(self, 'root'):
                self.root.save_user_data()
            print("应用暂停，数据已保存")
            return True
        except Exception as e:
            print(f"应用暂停处理失败: {e}")
            return True

    def on_resume(self):
        """应用恢复时调用"""
        try:
            if hasattr(self, 'root'):
                self.root.update_alarm_info()
                self.root.update_weather_theme()
            print("应用恢复，数据已更新")
        except Exception as e:
            print(f"应用恢复处理失败: {e}")

    def on_stop(self):
        """应用停止时调用"""
        try:
            if hasattr(self, 'root'):
                self.root.save_user_data()
            print("应用停止，数据已保存")
        except Exception as e:
            print(f"应用停止处理失败: {e}")


class DailyTrackerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "DailyTracker - SJTU"
        self.icon = self.get_icon_path()

    def get_icon_path(self):
        """获取图标路径"""
        icon_paths = [
            'assets/icon.png',
            'icon.png',
            './assets/icon.png',
            './icon.png'
        ]

        for path in icon_paths:
            if os.path.exists(path):
                print(f"✅ 找到图标文件: {path}")
                return path

        print("❌ 未找到图标文件")
        return None

    def build(self):
        print("启动 DailyTracker 应用...")
        print(f"应用图标: {self.icon}")
        # 设置初始窗口大小（便于桌面测试）
        Window.size = (400, 700)
        return DailyTracker()


if __name__ == '__main__':
    try:
        DailyTrackerApp().run()
    except Exception as e:
        print(f"应用启动失败: {e}")
        import traceback

        traceback.print_exc()