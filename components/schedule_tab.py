from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
import datetime
import json
import os

from kivy.properties import StringProperty, NumericProperty

class ActivityItem(BoxLayout):
    content = StringProperty("")  # 简化后的单一字符串属性

    def __init__(self, content="", **kwargs):
        super().__init__(**kwargs)
        self.content = content


class ScheduleTab(BoxLayout):
    app = ObjectProperty(None)  # 添加 app 属性

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.activities = []
        Clock.schedule_once(self._post_init)

    def _post_init(self, dt):
        """初始化显示"""
        self.load_activities()
        self.display_activities()

    def load_activities(self):
        """优化后的加载方法"""
        try:
            if os.path.exists('activities.json'):
                with open('activities.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 支持两种格式：直接字符串数组或带logs键的字典
                    self.activities = data.get('logs', data) if isinstance(data, dict) else data
            else:
                self.activities = [
                    "09:00-10:30 教室上课",
                    "12:00-13:00 一餐厅用餐",
                    "15:00-16:30 图书馆学习"
                ]
                self._save_activities()
        except Exception as e:
            print(f"加载失败: {str(e)}")
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
                    sleep_label.text = self.app.user_data.get('sleep_time', '12:00')
            except Exception as e:
                print(f"fail: {e}")

    def display_activities(self):
        """优化显示方法"""
        if hasattr(self, 'ids'):
            try:
                container = self.ids.activity_container
                container.clear_widgets()

                # 添加日期分隔线示例
                today = datetime.date.today().strftime("%Y-%m-%d")
                container.add_widget(ActivityItem(content=f"                  === {today} === \n\n              今天也是活力满满的一天喵！"))

                for activity in sorted(self.activities[-20:]):  # 限制显示数量
                    if isinstance(activity, dict):  # 处理字典格式数据
                        text = f"       {activity.get('time'," ")}   不要忘记   {activity.get('event', '')}"
                    else:
                        text = str(activity)
                    container.add_widget(ActivityItem(content=text))
            except Exception as e:
                print(f"显示失败: {str(e)}")

    def add_log_entry(self, content):
        """添加新条目的优化方法"""
        if content:
            self.activities.append(content)
            self._save_activities()
            self.display_activities()
    def _save_activities(self):
        """保存活动数据到JSON文件"""
        try:
            with open('activities.json', 'w', encoding='utf-8') as f:
                json.dump({"logs": self.activities}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存活动数据失败: {e}")
