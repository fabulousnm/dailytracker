import os
import time
import math
from datetime import datetime, timedelta
import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.garden.mapview import MapView, MapMarker
from plyer import gps


class GPSTrackerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trajectory_data = []
        self.speed_threshold = 3.0  # m/s
        self.today_date = datetime.now().strftime("%Y%m%d")
        self.current_map_file = None
        self.is_tracking = False

    def build(self):
        # 创建主布局
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 状态显示
        self.status_label = Label(
            text='GPS轨迹跟踪系统\n点击"开始跟踪"启动',
            size_hint_y=None,
            height=100,
            text_size=(400, None)
        )
        layout.add_widget(self.status_label)

        # 控制按钮
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)

        start_btn = Button(text='开始跟踪')
        start_btn.bind(on_press=self.start_tracking)
        btn_layout.add_widget(start_btn)

        stop_btn = Button(text='停止跟踪')
        stop_btn.bind(on_press=self.stop_tracking)
        btn_layout.add_widget(stop_btn)

        layout.add_widget(btn_layout)

        # 地图视图
        self.mapview = MapView(zoom=15, lat=31.2304, lon=121.4737)  # 默认上海坐标
        layout.add_widget(self.mapview)

        return layout

    def start_tracking(self, instance):
        """开始GPS跟踪"""
        try:
            # 请求GPS权限并启动
            gps.configure(on_location=self.on_location)
            gps.start()
            self.is_tracking = True
            self.status_label.text = "GPS跟踪已启动\n等待定位数据..."

            # 启动定时任务
            Clock.schedule_interval(self.check_tracking_time, 5)  # 每5秒检查

        except Exception as e:
            self.status_label.text = f"GPS启动失败: {str(e)}"

    def stop_tracking(self, instance):
        """停止GPS跟踪"""
        try:
            gps.stop()
            self.is_tracking = False
            self.status_label.text = "GPS跟踪已停止"
        except Exception as e:
            self.status_label.text = f"停止GPS失败: {str(e)}"

    def on_location(self, **kwargs):
        """GPS位置更新回调"""
        try:
            lat = kwargs.get('lat')
            lon = kwargs.get('lon')

            if lat is not None and lon is not None:
                current_time = datetime.now()

                # 计算速度
                speed = 0.0
                if self.trajectory_data:
                    last_point = self.trajectory_data[-1]
                    speed = self.calculate_speed(
                        (last_point[0], last_point[1], last_point[2]),
                        (lat, lon, current_time)
                    )

                # 添加轨迹点
                self.trajectory_data.append((lat, lon, current_time, speed))

                # 更新状态
                self.update_status_display(lat, lon, speed)

                # 生成轨迹地图
                self.generate_trajectory_map()

        except Exception as e:
            print(f"位置处理错误: {e}")

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """计算两点间距离（米）"""
        R = 6371000  # 地球半径（米）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def calculate_speed(self, point1, point2):
        """计算两点间的平均速度 (m/s)"""
        lat1, lon1, time1 = point1
        lat2, lon2, time2 = point2

        distance = self.calculate_distance(lat1, lon1, lat2, lon2)
        time_diff = (time2 - time1).total_seconds()

        if time_diff > 0:
            return distance / time_diff
        return 0.0

    def update_status_display(self, lat, lon, speed):
        """更新状态显示"""
        status_text = f"📍 实时位置\n"
        status_text += f"纬度: {lat:.6f}\n"
        status_text += f"经度: {lon:.6f}\n"
        status_text += f"速度: {speed:.2f} m/s\n"
        status_text += f"轨迹点: {len(self.trajectory_data)}\n"
        status_text += f"时间: {datetime.now().strftime('%H:%M:%S')}"

        self.status_label.text = status_text

        # 更新地图中心
        self.mapview.center_on(lat, lon)

    def generate_trajectory_map(self):
        """生成高精度轨迹地图"""
        try:
            if len(self.trajectory_data) < 2:
                return

            # 使用百度地图API生成静态图
            baidu_ak = "YOUR_BAIDU_MAP_AK"  # 需要替换为你的百度地图AK

            last_lat, last_lon, _, _ = self.trajectory_data[-1]

            # 构建轨迹线
            paths = []
            for i in range(len(self.trajectory_data) - 1):
                lat1, lon1, _, speed = self.trajectory_data[i]
                lat2, lon2, _, _ = self.trajectory_data[i + 1]

                # 根据速度选择颜色
                color = "0xFF0000" if speed > self.speed_threshold else "0x00FF00"
                path = f"{lon1},{lat1};{lon2},{lat2}"
                paths.append(f"{path}|0x000000,5,,|0x000000,0,{color},0.8,1")

            url = "http://api.map.baidu.com/staticimage/v2"
            params = {
                'ak': baidu_ak,
                'center': f"{last_lon},{last_lat}",
                'width': 1000,
                'height': 800,
                'zoom': 18,  # 高精度
                'paths': ",".join(paths),
                'copyright': 1
            }

            response = requests.get(url, params=params, timeout=10)

            # 保存地图
            filename = f"gps_trajectory_{self.today_date}.png"
            with open(filename, 'wb') as f:
                f.write(response.content)

            self.current_map_file = filename
            print(f"地图已更新: {filename}")

        except Exception as e:
            print(f"生成地图失败: {e}")

    def check_tracking_time(self, dt):
        """检查跟踪时间"""
        current_time = datetime.now()

        # 检查是否到达停止时间
        if self.should_stop_tracking():
            self.stop_tracking(None)
            self.save_final_map()

        # 检查是否是新的一天
        if self.is_new_day():
            self.save_final_map()
            self.trajectory_data = []
            self.today_date = datetime.now().strftime("%Y%m%d")

    def should_stop_tracking(self):
        """检查是否到达停止时间"""
        now = datetime.now()
        stop_time = now.replace(hour=23, minute=30, second=0, microsecond=0)
        return now >= stop_time

    def is_new_day(self):
        """检查是否是新的一天"""
        current_date = datetime.now().strftime("%Y%m%d")
        return current_date != self.today_date

    def save_final_map(self):
        """保存最终地图"""
        if self.current_map_file and os.path.exists(self.current_map_file):
            final_filename = f"{self.today_date}.png"
            os.rename(self.current_map_file, final_filename)
            print(f"最终地图已保存: {final_filename}")


if __name__ == '__main__':
    GPSTrackerApp().run()