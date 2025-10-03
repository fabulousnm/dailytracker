from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
import datetime
import json


class ScheduleTab(BoxLayout):
    app = ObjectProperty(None)  # 添加 app 属性

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.activities = []
        self.current_activity = None
        self.activity_start_time = None

        # 初始化活动数据
        self.load_activities()

        # 延迟更新显示，确保界面已加载
        Clock.schedule_once(self.update_alarm_display, 0.1)
        Clock.schedule_once(self.update_activities_display, 0.2)

    def load_activities(self):
        """加载活动数据"""
        try:
            with open('activities.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.activities = data.get('activities', [])
        except FileNotFoundError:
            self.activities = []
        except Exception as e:
            print(f"fail: {e}")
            self.activities = []

    def save_activities(self):
        """保存活动数据"""
        try:
            with open('activities.json', 'w', encoding='utf-8') as f:
                json.dump({'activities': self.activities}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"fail: {e}")

    def update_alarm_display(self, dt=None):
        """更新闹钟显示"""
        if hasattr(self, 'ids') and hasattr(self, 'app'):
            try:
                wake_label = self.ids.get('wake_time_label')
                sleep_label = self.ids.get('sleep_time_label')
                if wake_label and sleep_label:
                    wake_label.text = self.app.user_data.get('wake_time', '07:00')
                    sleep_label.text = self.app.user_data.get('sleep_time', '23:00')
            except Exception as e:
                print(f"fail: {e}")

    def update_activities_display(self, dt=None):
        """更新活动显示"""
        if hasattr(self, 'ids'):
            try:
                activity_container = self.ids.get('activity_container')
                if activity_container:
                    # 清空现有活动显示
                    activity_container.clear_widgets()

                    # 添加今天的活动记录（按时间倒序）
                    today = datetime.datetime.now().strftime('%Y-%m-%d')
                    today_activities = [a for a in self.activities if a.get('date', '') == today]
                    today_activities.sort(key=lambda x: x.get('start_time', ''), reverse=True)

                    for activity in today_activities[:10]:  # 只显示最近10条
                        self.add_activity_to_display(activity)
            except Exception as e:
                print(f"更新活动显示失败: {e}")

    def add_activity_to_display(self, activity):
        """添加活动记录到显示"""
        if hasattr(self, 'ids'):
            try:
                activity_container = self.ids.get('activity_container')
                if activity_container:
                    # 创建活动项
                    activity_item = ActivityItem(
                        location=activity.get('location', 'unknown'),
                        event_type=activity.get('event_type', 'unknown'),
                        start_time=activity.get('start_time', '--:--'),
                        end_time=activity.get('end_time', '--:--'),
                        duration=activity.get('duration', 0)
                    )
                    activity_container.add_widget(activity_item)
            except Exception as e:
                print(f"fail: {e}")

    def record_activity(self, location, event_type, duration):
        """记录活动"""
        try:
            activity_record = {
                'location': location,
                'event_type': event_type,
                'start_time': (datetime.datetime.now() - datetime.timedelta(seconds=duration)).strftime('%H:%M'),
                'end_time': datetime.datetime.now().strftime('%H:%M'),
                'duration': duration,
                'date': datetime.datetime.now().strftime('%Y-%m-%d')
            }

            self.activities.append(activity_record)
            self.save_activities()

            # 更新显示
            self.update_activities_display()

            print(f"记录活动: at{location} {event_type} for{duration} seconds")

        except Exception as e:
            print(f"fail: {e}")

    def clear_activities(self):
        """清空活动"""
        self.activities = []
        self.save_activities()
        self.update_activities_display()

    def update_theme(self, colors):
        """Update theme"""
        try:
            print(f"🎨 ScheduleTab applying theme: {colors['background']}")

            # 清除现有canvas
            self.canvas.before.clear()

            # 使用更明显的背景色
            with self.canvas.before:
                from kivy.graphics import Color, Rectangle
                bg_color = get_color_from_hex(colors['background'])
                Color(*bg_color)
                # 确保覆盖整个区域
                Rectangle(pos=(0, 0), size=Window.size)

            # 强制重绘
            self.canvas.ask_update()

        except Exception as e:
            print(f"ScheduleTab theme update failed: {e}")

class ActivityItem(BoxLayout):
    def __init__(self, location="", event_type="", start_time="", end_time="", duration=0, **kwargs):
        super().__init__(**kwargs)
        self.location = location
        self.event_type = event_type
        self.start_time = start_time

        self.end_time = end_time
        self.duration = duration