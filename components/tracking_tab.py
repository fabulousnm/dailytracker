from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
import datetime
import math


class LocationLogEntry(BoxLayout):
    location_text = StringProperty("")
    duration_text = StringProperty("")
    activity_text = StringProperty("")

    def __init__(self, location_text="", duration_text="", activity_text="", **kwargs):
        super().__init__(**kwargs)
        self.location_text = location_text
        self.duration_text = duration_text
        self.activity_text = activity_text


class TrackingTab(BoxLayout):
    app = ObjectProperty(None)  # 添加 app 属性

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tracking_data = []
        self.current_speed = 0.0
        self.running_start_time = None
        self.current_location = None
        self.location_start_time = None
        self.speed_threshold = 5.0

        # 延迟初始化
        Clock.schedule_once(self.initialize_display, 0.1)

    def initialize_display(self, dt=None):
        """初始化显示"""
        if hasattr(self, 'ids') and hasattr(self, 'app'):
            try:
                # 设置速度阈值滑块
                speed_slider = self.ids.get('speed_slider')
                if speed_slider:
                    speed_slider.value = self.app.user_data.get('speed_threshold', 5.0)
                    self.speed_threshold = speed_slider.value

                # 更新速度显示
                self.update_current_speed(0.0)

                # 添加一些示例日志
                self.add_sample_logs()

            except Exception as e:
                print(f"fail: {e}")

    def update_current_speed(self, speed):
        """更新当前速度显示"""
        self.current_speed = speed
        if hasattr(self, 'ids'):
            try:
                speed_label = self.ids.get('current_speed_label')
                if speed_label:
                    speed_label.text = f'{speed:.1f} m/s'
                    # 根据速度阈值改变颜色
                    if speed > self.speed_threshold:
                        speed_label.color = (0.8, 0.2, 0.2, 1)  # 红色
                    else:
                        speed_label.color = (0.2, 0.8, 0.2, 1)  # 绿色
            except Exception as e:
                print(f"fail: {e}")

    def add_running_start_log(self, speed):
        """添加跑步开始日志"""
        try:
            log_entry = LocationLogEntry(
                location_text="Start running",
                duration_text="",
                activity_text=f"speed: {speed:.1f} m/s"
            )
            self.add_log_entry(log_entry)
        except Exception as e:
            print(f"fail: {e}")

    def add_running_end_log(self, duration, speed):
        """添加跑步结束日志"""
        try:
            log_entry = LocationLogEntry(
                location_text="finish running",
                duration_text=f"duration: {int(duration)}秒",
                activity_text=f"average speed: {speed:.1f} m/s"
            )
            self.add_log_entry(log_entry)
        except Exception as e:
            print(f"fail: {e}")

    def add_location_log(self, location, duration, activity=""):
        """添加位置停留日志"""
        try:
            log_entry = LocationLogEntry(
                location_text=f"at{location} ",
                duration_text=f": {int(duration)}seconds",
                activity_text=activity if activity else "you are moving"
            )
            self.add_log_entry(log_entry)
        except Exception as e:
            print(f"fail: {e}")

    def add_log_entry(self, log_entry):
        """添加日志条目"""
        if hasattr(self, 'ids'):
            try:
                location_logs = self.ids.get('location_logs')
                if location_logs:
                    # 限制日志数量
                    if len(location_logs.children) > 20:
                        location_logs.remove_widget(location_logs.children[-1])

                    location_logs.add_widget(log_entry)
            except Exception as e:
                print(f"fail: {e}")

    def clear_logs(self):
        """清空日志"""
        if hasattr(self, 'ids'):
            try:
                location_logs = self.ids.get('location_logs')
                if location_logs:
                    location_logs.clear_widgets()
            except Exception as e:
                print(f"fail: {e}")

    def add_sample_logs(self):
        """添加示例日志（用于测试）"""
        try:
            sample_logs = [
                LocationLogEntry("classrooom", "duration: 5400 sed", "at class"),
                LocationLogEntry("dinning hall", "duration: 2700 sed", "at meal"),
                LocationLogEntry("start running", "", "speed: 4.5 m/s"),
                LocationLogEntry("finish running", "duration: 1200 sed", "average speed: 4.2 m/s"),
                LocationLogEntry("library", "duration: 7200 sed", "reading")
            ]

            for log in sample_logs:
                self.add_log_entry(log)

        except Exception as e:
            print(f"fail: {e}")

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