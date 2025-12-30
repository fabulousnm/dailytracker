# english_main.py - Complete version with splash screen
import os
import sys
import json
import datetime
import random
from datetime import datetime

# ========== Import Kivy and other modules ==========
from kivy import platform  # 检测当前平台(Android/iOS/桌面)
from kivy.app import App  # Kivy应用基类
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem  # 选项卡式界面组件
from kivy.core.window import Window  # 窗口管理
from kivy.utils import get_color_from_hex  # 颜色工具
from kivy.clock import Clock  # 定时器/调度器
from kivy.properties import ObjectProperty, StringProperty, NumericProperty  # 属性绑定
from kivy.uix.boxlayout import BoxLayout  # 盒子布局
from kivy.uix.label import Label  # 文本标签
from kivy.uix.button import Button  # 按钮
from kivy.uix.scrollview import ScrollView  # 滚动视图
from kivy.uix.gridlayout import GridLayout  # 网格布局
from kivy.uix.slider import Slider  # 滑块
from kivy.uix.spinner import Spinner  # 下拉选择器
from kivy.uix.popup import Popup  # 弹出窗口
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition  # 屏幕管理器
from kivy.animation import Animation  # 动画

# ========== 每日一言数据库 ==========
DAILY_QUOTES = [
    # ... 你原来的名言保持不变 ...

    # 添加的生僻忧伤哲理诗词
    {"text": "人生到处知何似，应似飞鸿踏雪泥。", "author": "苏轼《和子由渑池怀旧》"},
    {"text": "世事短如春梦，人情薄似秋云。。", "author": "朱敦儒《西江月》"},
    {"text": "人生自是有情痴，此恨不关风与月。", "author": "欧阳修《玉楼春》"},
    {"text": "欲买桂花同载酒，终不似，少年游。", "author": "刘过《唐多令》"},
    {"text": "大都好物不坚牢，彩云易散琉璃脆。", "author": "白居易《简简吟》"},
    {"text": "人生无根蒂，飘如陌上尘。分散逐风转，此已非常身。", "author": "陶渊明《杂诗》"},
    {"text": "世事一场大梦，人生几度秋凉。", "author": "苏轼《西江月》"},
    {"text": "而今听雨僧庐下，鬓已星星也。悲欢离合总无情，一任阶前点滴到天明。", "author": "蒋捷《虞美人·听雨》"},
    {"text": "此情可待成追忆，只是当时已惘然。", "author": "李商隐《锦瑟》"},
    {"text": "人生似幻化，终当归空无。", "author": "陶渊明《归园田居》"},
    {"text": "明月多情应笑我，笑我如今。辜负春心，独自闲行独自吟。", "author": "纳兰性德《采桑子》"},
    {"text": "世路如今已惯，此心到处悠然。", "author": "张孝祥《西江月》"},
    {"text": "浮生若梦，为欢几何？", "author": "李白《春夜宴从弟桃花园序》"},
    {"text": "人生如逆旅，我亦是行人。", "author": "苏轼《临江仙》"},
    {"text": "年年岁岁花相似，岁岁年年人不同。", "author": "刘希夷《代悲白头翁》"},
    {"text": "惆怅东栏一株雪，人生看得几清明。", "author": "苏轼《东栏梨花》"},
    {"text": "草木有本心，何求美人折。", "author": "张九龄《感遇》"},
    {"text": "人生有酒须当醉，一滴何曾到九泉。", "author": "高翥《清明日对酒》"},
    {"text": "谁教岁岁红莲夜，两处沉吟各自知。", "author": "姜夔《鹧鸪天·元夕有所梦》"},
    {"text": "一往情深深几许？深山夕照深秋雨。", "author": "纳兰性德《蝶恋花》"},
    {"text": "世事漫随流水，算来一梦浮生。", "author": "李煜《乌夜啼》"},
    {"text": "人生天地间，忽如远行客。", "author": "《古诗十九首》"},
    {"text": "似此星辰非昨夜，为谁风露立中宵。", "author": "黄景仁《绮怀》"},
    {"text": "君埋泉下泥销骨，我寄人间雪满头。", "author": "白居易《梦微之》"},
    {"text": "人生不相见，动如参与商。今夕复何夕，共此灯烛光。", "author": "杜甫《赠卫八处士》"},
    {"text": "人生代代无穷已，江月年年望相似。", "author": "张若虚《春江花月夜》"},
    {"text": "花开堪折直须折，莫待无花空折枝。", "author": "杜秋娘《金缕衣》"},
    {"text": "壮年听雨客舟中，江阔云低，断雁叫西风。", "author": "蒋捷《虞美人·听雨》"},
    {"text": "满目山河空念远，落花风雨更伤春。不如怜取眼前人。", "author": "晏殊《浣溪沙》"},
    {"text": "自是人生长恨水长东。", "author": "李煜《相见欢》"}
]


# ========== 开屏界面类 ==========
class SplashScreen(Screen):
    """开屏动画界面"""
    quote_text = StringProperty("")  # 名言文本
    quote_author = StringProperty("")  # 名言作者
    current_time = StringProperty("")  # 当前时间
    date_display = StringProperty("")  # 当前日期
    opacity_date = NumericProperty(0)  # 日期透明度
    opacity_quote = NumericProperty(0)  # 名言透明度
    opacity_hint = NumericProperty(0)  # 提示文本透明度

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 设置初始透明度为0（完全透明）
        self.opacity_date = 0
        self.opacity_quote = 0
        self.opacity_hint = 0
        # 设置窗口背景为白色
        Window.clearcolor = (1, 1, 1, 1)

    def on_enter(self):
        """进入界面时触发"""
        # 更新时间和日期
        self.update_time_date()
        # 随机选择一句名言
        self.select_random_quote()
        # 开始渐入动画
        self.start_animation()
        # 每秒更新时间
        Clock.schedule_interval(self.update_time_date, 1)

    def update_time_date(self, *args):
        """更新时间和日期显示"""
        now = datetime.now()
        # 格式化时间：HH:MM:SS
        self.current_time = now.strftime("%H:%M:%S")
        # 格式化日期：YYYY年MM月DD日 星期X
        self.date_display = now.strftime("%Y.%m.%d %a").replace("星期", "星期")

    def select_random_quote(self):
        """随机选择一句名言"""
        quote = random.choice(DAILY_QUOTES)
        self.quote_text = quote["text"]
        self.quote_author = f"—— {quote['author']}——"

    def start_animation(self):
        """开始渐入动画序列"""
        # 重置所有透明度
        self.opacity_date = 0.8
        self.opacity_quote = 0.5
        self.opacity_hint = 0

        # 创建动画序列
        # 1. 日期时间渐入（0.5秒）
        anim_date = Animation(opacity_date=1, duration=0.2)

        # 2. 名言渐入（0.8秒，延迟0.3秒）
        anim_quote = Animation(opacity_quote=1, duration=0.2)
        anim_quote.start_delay = 0.1

        # 3. 提示文本渐入（0.6秒，延迟1.0秒）
        anim_hint = Animation(opacity_hint=1, duration=5)
        anim_hint.start_delay = 0.5

        # 按顺序播放动画
        anim_date.start(self)
        anim_quote.start(self)
        anim_hint.start(self)

    def on_touch_down(self, touch):
        """点击任意位置进入主应用"""
        # 切换到主界面
        if self.manager:
            self.manager.current = 'main'
        return True


# ========== 主界面类 ==========
class MainScreen(Screen):
    """主应用界面"""
    daily_tracker = ObjectProperty(None)  # 主应用实例

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建主应用实例
        self.daily_tracker = DailyTracker()
        self.add_widget(self.daily_tracker)

    def on_enter(self):
        """进入主界面时触发"""
        # 如果从开屏界面切换过来，确保主题正确
        if hasattr(self.daily_tracker, 'current_theme'):
            Clock.schedule_once(lambda dt: self.daily_tracker.update_theme(self.daily_tracker.current_theme), 0.1)


# ========== 原来的DailyTracker类（保持所有功能） ==========
class DailyTracker(TabbedPanel):
    """主应用类，继承自Kivy的TabbedPanel"""
    # 定义属性用于访问各个标签页
    schedule_tab = ObjectProperty(None)  # 计划标签页
    tracking_tab = ObjectProperty(None)  # 跟踪标签页
    personalization_tab = ObjectProperty(None)  # 设置标签页

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False  # 不使用默认标签
        self.tab_pos = 'top_mid'  # 标签位置在顶部中间

        # ========== 主题颜色配置 ==========
        self.theme_colors = {
            'sunny': {  # 晴天主题
                'primary': '#FFD700',  # 主色 - 亮黄
                'secondary': '#32CD32',  # 辅色 - 青柠绿
                'background': '#FFFAF0'  # 背景 - 浅黄
            },
            'cloudy': {  # 多云主题
                'primary': '#696969',  # 主色 - 暗灰
                'secondary': '#8A2BE2',  # 辅色 - 紫罗兰
                'background': '#F8F8FF'  # 背景 - 浅紫
            },
            'rainy': {  # 雨天主题
                'primary': '#1E90FF',  # 主色 - 道奇蓝
                'secondary': '#2F4F4F',  # 辅色 - 深石板灰
                'background': '#F0F8FF'  # 背景 - 浅蓝
            }
        }
        self.current_theme = 'sunny'  # 当前主题默认晴天

        # ========== 初始化数据文件 ==========
        self.data_file = "user_data.json"  # 用户数据存储文件
        self.load_user_data()  # 加载用户数据

        # 创建标签页
        self.create_tabs()

        # 延迟1秒启动服务（等待UI初始化完成）
        Clock.schedule_once(self.init_services, 1)

    def create_tabs(self):
        """创建应用程序的标签页"""
        # ========== 尝试导入组件 ==========
        try:
            # 尝试从组件模块导入各功能标签页
            from components.schedule_tab import ScheduleTab
            from components.tracking_tab import TrackingTab
            from components.personalization_tab import PersonalizationTab

            COMPONENTS_AVAILABLE = True  # 标记组件可用
            print("Components imported successfully")
        except ImportError as e:
            print(f"Component import failed: {e}")
            COMPONENTS_AVAILABLE = False  # 标记组件不可用

            # ========== 组件不可用时使用回退实现 ==========
            class ScheduleTab(BoxLayout):
                """计划标签页的回退实现"""

                def __init__(self, **kwargs):
                    super().__init__(**kwargs)
                    self.orientation = 'vertical'
                    self.padding = 20
                    self.spacing = 10

                def update_alarm_display(self):
                    """更新闹钟显示（空实现）"""
                    pass

                def update_theme(self, weather_type):
                    """应用主题颜色（空实现）"""
                    pass

            class TrackingTab(BoxLayout):
                """跟踪标签页的回退实现"""

                def __init__(self, **kwargs):
                    super().__init__(**kwargs)
                    self.orientation = 'vertical'
                    self.padding = 10
                    self.spacing = 10

                def update_theme(self, colors):
                    """应用主题颜色（空实现）"""
                    pass

            class PersonalizationTab(BoxLayout):
                """个性化设置标签页的回退实现"""

                def __init__(self, **kwargs):
                    super().__init__(**kwargs)
                    self.orientation = 'vertical'
                    self.padding = 20
                    self.spacing = 15

                def update_theme(self, colors):
                    """应用主题颜色（空实现）"""
                    pass

                def customize_color(self, module):
                    """自定义颜色（空实现）"""
                    print(f"Customize color: {module}")

                def change_theme(self, theme_name):
                    """更改主题（空实现）"""
                    print(f"Change theme: {theme_name}")

                def show_message(self, message):
                    """显示消息（空实现）"""
                    print(f"Message: {message}")

        # ========== 计划标签页 ==========
        if COMPONENTS_AVAILABLE:
            self.schedule_tab = ScheduleTab()  # 使用组件实现
        else:
            self.schedule_tab = ScheduleTab()  # 使用回退实现
        self.schedule_tab.app = self  # 设置对主应用的引用
        tab1 = TabbedPanelItem(text='Schedule')  # 创建标签项
        tab1.add_widget(self.schedule_tab)  # 将标签页添加到标签项
        self.add_widget(tab1)  # 将标签项添加到主面板

        # ========== 跟踪标签页 ==========
        if COMPONENTS_AVAILABLE:
            self.tracking_tab = TrackingTab()
        else:
            self.tracking_tab = TrackingTab()
        self.tracking_tab.app = self
        tab2 = TabbedPanelItem(text='Tracking')
        tab2.add_widget(self.tracking_tab)
        self.add_widget(tab2)

        # ========== 设置标签页 ==========
        if COMPONENTS_AVAILABLE:
            self.personalization_tab = PersonalizationTab()
        else:
            self.personalization_tab = PersonalizationTab()
        self.personalization_tab.app = self
        tab3 = TabbedPanelItem(text='Settings')
        tab3.add_widget(self.personalization_tab)
        self.add_widget(tab3)

    def init_services(self, dt):
        """初始化所有服务"""
        print("Initializing application services...")

        # ========== 初始化天气服务 ==========
        try:
            from utils.weather_api import WeatherManager
            self.weather_manager = WeatherManager()  # 创建天气管理器实例
            self.update_weather_theme()  # 获取天气并更新主题
        except Exception as e:
            print(f"Weather service initialization failed: {e}")
            # 使用默认主题
            self.update_theme('sunny')

        # ========== Android平台特定服务 ==========
        if platform == 'android':
            try:
                from utils.location_manager import LocationManager
                from utils.alarm_reader import AlarmReader

                # 创建位置管理器和闹钟读取器
                self.location_manager = LocationManager(self)
                self.alarm_reader = AlarmReader()

                # 启动位置跟踪
                self.location_manager.start_tracking()
                print("Location tracking service started")

                # 读取闹钟数据
                self.update_alarm_info()

            except Exception as e:
                print(f"Android service initialization failed: {e}")
        else:
            # ========== 非Android平台使用模拟数据 ==========
            print("Non-Android platform, using simulation data")
            self.setup_desktop_simulation()

    def setup_desktop_simulation(self):
        """桌面环境模拟数据设置"""
        try:
            # 更新UI显示
            if hasattr(self, 'schedule_tab'):
                Clock.schedule_once(lambda dt: self.schedule_tab.update_alarm_display(), 0.5)

        except Exception as e:
            print(f"Desktop simulation setup failed: {e}")

    def load_user_data(self):
        """加载用户数据"""
        try:
            if os.path.exists(self.data_file):
                # 从文件读取JSON数据
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                print("User data loaded successfully")
            else:
                # 文件不存在则创建默认数据
                self.create_default_data()
        except Exception as e:
            print(f"Failed to load user data: {e}")
            self.create_default_data()

    def create_default_data(self):
        """创建默认用户数据"""
        self.user_data = {
            'sleep_time': "23:00",  # 默认睡眠时间
            'wake_time': "07:00",  # 默认唤醒时间
            'locations': {  # 预设位置数据
                'home': {
                    'name': 'Home',
                    'events': ['Rest', 'Sleep', 'Gaming'],
                    'coords': [31.0258, 121.4376]  # 上海交大坐标
                },
                'canteen': {
                    'name': 'Cafeteria',
                    'events': ['Eating'],
                    'coords': [31.0260, 121.4380]
                },
                'classroom': {
                    'name': 'Classroom',
                    'events': ['Studying'],
                    'coords': [31.0255, 121.4370]
                },
                'library': {
                    'name': 'Library',
                    'events': ['Learning', 'Rest'],
                    'coords': [31.0262, 121.4378]
                },
                'sports': {
                    'name': 'Sports Field',
                    'events': ['Exercise', 'Running'],
                    'coords': [31.0268, 121.4390]
                }
            },
            'speed_threshold': 5.0,  # 移动速度阈值(m/s)
            'running_threshold': 3.0,  # 跑步速度阈值(m/s)
            'stay_threshold': 60,  # 停留时间阈值(秒)
            'personalization': {},  # 个性化设置
            'notes': [],  # 笔记列表
            'activities': []  # 活动列表
        }
        self.save_user_data()  # 保存默认数据
        print("Default user data created")

    def save_user_data(self):
        """保存用户数据到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save user data: {e}")

    def update_alarm_info(self):
        """更新闹钟信息"""
        if hasattr(self, 'alarm_reader'):
            try:
                # 获取所有闹钟
                alarms = self.alarm_reader.get_alarms()
                if alarms:
                    # 使用最早闹钟作为唤醒时间
                    self.user_data['wake_time'] = min(alarms)
                    # 使用最晚闹钟作为睡眠时间
                    self.user_data['sleep_time'] = max(alarms)
                    self.save_user_data()  # 保存更新

                    # 更新UI显示
                    if hasattr(self, 'schedule_tab'):
                        self.schedule_tab.update_alarm_display()

                    print(
                        f"Alarm data updated: Wake up {self.user_data['wake_time']}, Sleep {self.user_data['sleep_time']}")
            except Exception as e:
                print(f"Failed to read alarms: {e}")

    def update_theme(self, weather_type):
        """应用主题颜色（带视觉反馈效果）"""
        try:
            print(f"=== Applying theme: {weather_type} ===")

            # 保存当前主题
            self.current_theme = weather_type

            # 第一步：短暂变白（闪屏效果）
            original_color = Window.clearcolor  # 保存当前颜色
            Window.clearcolor = (1, 1, 1, 1)  # 设置为白色

            # 第二步：延迟应用最终主题颜色
            Clock.schedule_once(
                lambda dt: self.apply_final_theme(weather_type, self.theme_colors[weather_type]),
                0.2
            )

        except Exception as e:
            print(f"Failed to apply theme: {e}")

    def update_weather_theme(self):
        """根据天气更新主题"""
        try:
            if hasattr(self, 'weather_manager'):
                # 获取当前天气信息（使用上海交大坐标）
                weather_data = self.weather_manager.get_current_weather(31.0258, 121.4376)
                weather_type = weather_data.get('weather', 'sunny')
                print(f"Weather data received: {weather_type}")

                # 天气类型到主题的映射
                weather_map = {
                    'clear': 'sunny',
                    'sunny': 'sunny',
                    'cloudy': 'cloudy',
                    'overcast': 'cloudy',
                    'rain': 'rainy',
                    'rainy': 'rainy',
                    'snow': 'rainy'
                }

                # 获取对应的主题
                theme = weather_map.get(weather_type, 'sunny')
                print(f"Weather {weather_type} mapped to theme: {theme}")
                self.update_theme(theme)  # 应用主题

            else:
                print("Weather manager not available, using default theme")
                self.update_theme('sunny')

        except Exception as e:
            print(f"Weather update error: {e}")
            self.update_theme('sunny')  # 出错时使用默认主题

    def apply_final_theme(self, weather_type, colors):
        """在视觉反馈后应用最终主题颜色"""
        try:
            # 应用最终背景色
            bg_color = get_color_from_hex(colors['background'])
            Window.clearcolor = bg_color
            print(f"Final background color: {colors['background']}")

            # 强制窗口重绘
            Window.canvas.ask_update()

            # 通知所有标签页更新主题
            if hasattr(self, 'schedule_tab'):
                self.schedule_tab.update_theme(colors)
            if hasattr(self, 'tracking_tab'):
                self.tracking_tab.update_theme(colors)
            if hasattr(self, 'personalization_tab'):
                self.personalization_tab.update_theme(colors)

            print(f"Theme {weather_type} applied successfully with visual feedback!")

        except Exception as e:
            print(f"Failed to apply final theme: {e}")

    def add_note(self, activity_data, text, image_path=None):
        """添加活动笔记"""
        try:
            # 创建笔记对象
            note = {
                'timestamp': datetime.datetime.now().isoformat(),  # ISO格式时间戳
                'activity': activity_data,  # 活动数据
                'text': text,  # 笔记文本
                'image': image_path  # 图片路径(可选)
            }

            # 确保notes列表存在
            if 'notes' not in self.user_data:
                self.user_data['notes'] = []

            # 添加笔记并保存
            self.user_data['notes'].append(note)
            self.save_user_data()
            print("Note added successfully")

        except Exception as e:
            print(f"Failed to add note: {e}")

    def customize_color(self, module):
        """自定义模块颜色（委托给设置标签页）"""
        if hasattr(self, 'personalization_tab'):
            self.personalization_tab.customize_color(module)

    def change_theme(self, theme_name):
        """更改主题（委托给设置标签页）"""
        if hasattr(self, 'personalization_tab'):
            self.personalization_tab.change_theme(theme_name)

    def update_speed_threshold(self, value):
        """更新移动速度阈值"""
        try:
            # 更新数据并保存
            self.user_data['speed_threshold'] = float(value)
            self.save_user_data()

            # 更新位置管理器
            if hasattr(self, 'location_manager'):
                self.location_manager.speed_threshold = float(value)

            # 更新跟踪标签页
            if hasattr(self, 'tracking_tab'):
                self.tracking_tab.speed_threshold = float(value)

            print(f"Speed threshold updated: {value} m/s")

        except Exception as e:
            print(f"Failed to update speed threshold: {e}")

    def save_settings(self):
        """保存所有设置"""
        try:
            self.save_user_data()
            print("Settings saved successfully")

            # 在设置标签页显示成功消息
            if hasattr(self, 'personalization_tab'):
                self.personalization_tab.show_message("Settings saved successfully!")

        except Exception as e:
            print(f"Failed to save settings: {e}")

    def reset_settings(self):
        """重置设置为默认值"""
        try:
            # 创建默认数据
            self.create_default_data()

            # 重新加载主题
            self.update_theme('sunny')

            # 更新所有标签页
            if hasattr(self, 'schedule_tab'):
                self.schedule_tab.update_alarm_display()  # 更新闹钟显示
                # 清除活动数据（如果组件支持）
                if hasattr(self.schedule_tab, 'clear_activities'):
                    self.schedule_tab.clear_activities()

            if hasattr(self, 'tracking_tab'):
                # 清除日志（如果组件支持）
                if hasattr(self.tracking_tab, 'clear_logs'):
                    self.tracking_tab.clear_logs()

            print("Settings reset to default")

            # 在设置标签页显示成功消息
            if hasattr(self, 'personalization_tab'):
                self.personalization_tab.show_message("Settings reset to default!")

        except Exception as e:
            print(f"Failed to reset settings: {e}")


# ========== 修改应用类 ==========
class DailyTrackerApp(App):
    """Kivy应用类"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "DailyTracker - SJTU"  # 应用标题
        self.icon = self.get_icon_path()  # 应用图标
        self.screen_manager = None

    def get_icon_path(self):
        """获取图标路径"""
        # 可能的图标路径列表
        icon_paths = [
            'assets/icon.png',  # 首选路径
            'icon.png',  # 备选路径
            './assets/icon.png',
            './icon.png'
        ]

        # 检查路径是否存在
        for path in icon_paths:
            if os.path.exists(path):
                print(f"Icon file found: {path}")
                return path

        print("Icon file not found")
        return None

    def build(self):
        """构建应用界面"""
        print("Starting DailyTracker application...")
        print(f"Application icon: {self.icon}")

        # 设置初始窗口大小（桌面测试用）
        Window.size = (400, 700)

        # 创建屏幕管理器
        self.screen_manager = ScreenManager(transition=FadeTransition(duration=0.5))

        # 添加开屏界面
        splash_screen = SplashScreen(name='splash')
        self.screen_manager.add_widget(splash_screen)

        # 添加主界面
        main_screen = MainScreen(name='main')
        self.screen_manager.add_widget(main_screen)

        # 设置当前屏幕为开屏界面
        self.screen_manager.current = 'splash'

        return self.screen_manager

    def on_pause(self):
        """应用暂停时调用（Android特有）"""
        try:
            # 保存用户数据
            if hasattr(self, 'root'):
                if self.screen_manager and self.screen_manager.current == 'main':
                    main_screen = self.screen_manager.get_screen('main')
                    if main_screen and hasattr(main_screen, 'daily_tracker'):
                        main_screen.daily_tracker.save_user_data()
            print("Application paused, data saved")
            return True  # 允许应用暂停
        except Exception as e:
            print(f"Pause handling failed: {e}")
            return True

    def on_resume(self):
        """应用恢复时调用（Android特有）"""
        try:
            if self.screen_manager and self.screen_manager.current == 'main':
                main_screen = self.screen_manager.get_screen('main')
                if main_screen and hasattr(main_screen, 'daily_tracker'):
                    # 更新闹钟信息和天气主题
                    main_screen.daily_tracker.update_alarm_info()
                    main_screen.daily_tracker.update_weather_theme()
            print("Application resumed, data updated")
        except Exception as e:
            print(f"Resume handling failed: {e}")

    def on_stop(self):
        """应用停止时调用"""
        try:
            # 保存用户数据
            if hasattr(self, 'root'):
                if self.screen_manager and self.screen_manager.current == 'main':
                    main_screen = self.screen_manager.get_screen('main')
                    if main_screen and hasattr(main_screen, 'daily_tracker'):
                        main_screen.daily_tracker.save_user_data()
            print("Application stopped, data saved")
        except Exception as e:
            print(f"Stop handling failed: {e}")


# ========== 应用入口 ==========
if __name__ == '__main__':
    try:
        # 创建并运行应用
        DailyTrackerApp().run()
    except Exception as e:
        print(f"Application startup failed: {e}")
        # 打印完整错误堆栈
        import traceback

        traceback.print_exc()