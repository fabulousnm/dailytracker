from kivy.clock import Clock
from kivy.garden.mapview import MapView, MapMarker
import time
from math import sqrt, radians, sin, cos, atan2


class LocationManager:
    def __init__(self, app):
        self.app = app
        self.locations = []
        self.current_location = None
        self.last_location = None
        self.last_location_time = None
        self.current_stay = None
        self.stay_start_time = None
        self.running_start_time = None

        # 从用户数据获取阈值
        self.speed_threshold = app.user_data.get('speed_threshold', 5.0)
        self.running_threshold = app.user_data.get('running_threshold', 3.0)
        self.stay_threshold = app.user_data.get('stay_threshold', 60)

    def start_tracking(self):
        """开始位置跟踪"""
        try:
            # 对于Android设备
            if self.is_android():
                from plyer import gps
                gps.configure(on_location=self.on_gps_location)
                gps.start()
            else:
                # 桌面模拟
                Clock.schedule_interval(self.simulate_location, 10)
        except Exception as e:
            print(f"fail: {e}")
            # 使用模拟数据
            Clock.schedule_interval(self.simulate_location, 10)

    def is_android(self):
        """检查是否是Android平台"""
        try:
            import plyer
            return True
        except:
            return False

    def on_gps_location(self, **kwargs):
        """处理真实GPS位置"""
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        speed = kwargs.get('speed', 0)

        if lat and lon:
            self.process_new_location(lat, lon, speed)

    def simulate_location(self, dt):
        """模拟位置数据（用于测试）"""
        # 模拟上海交通大学周围的坐标
        import random
        base_lat, base_lon = 31.0258, 121.4376
        lat = base_lat + random.uniform(-0.001, 0.001)
        lon = base_lon + random.uniform(-0.001, 0.001)
        speed = random.uniform(0, 8)  # 0-8 m/s

        self.process_new_location(lat, lon, speed)

    def process_new_location(self, lat, lon, speed):
        """处理新位置数据"""
        current_time = time.time()
        new_location = (lat, lon, speed, current_time)

        # 添加到位置历史
        self.locations.append(new_location)
        if len(self.locations) > 1000:
            self.locations = self.locations[-1000:]

        # 更新当前速度
        if self.app.tracking_tab:
            self.app.tracking_tab.update_current_speed(speed)

        # 检查位置停留
        self.check_location_stay(lat, lon, current_time)

        # 检查跑步状态
        self.check_running_status(speed, current_time)

        # 更新最后位置
        self.last_location = (lat, lon)
        self.last_location_time = current_time

    def check_location_stay(self, lat, lon, current_time):
        """检查位置停留"""
        predefined_locations = self.app.user_data['locations']
        nearest_location = self.find_nearest_location(lat, lon, predefined_locations)

        if nearest_location and self.is_within_radius(lat, lon, nearest_location['coords'], 10):
            # 在预定义地点附近
            if self.current_stay != nearest_location['name']:
                # 新地点停留开始
                self.current_stay = nearest_location['name']
                self.stay_start_time = current_time
            else:
                # 继续在同一地点停留
                stay_duration = current_time - self.stay_start_time
                if stay_duration >= self.stay_threshold:
                    # 停留时间超过阈值，记录活动
                    self.record_stay_activity(nearest_location, stay_duration)
        else:
            # 不在预定义地点或离开地点
            if self.current_stay:
                # 结束当前停留
                stay_duration = current_time - self.stay_start_time
                if stay_duration >= self.stay_threshold:
                    self.record_leave_activity(self.current_stay, stay_duration)
                self.current_stay = None
                self.stay_start_time = None

    def find_nearest_location(self, lat, lon, locations):
        """查找最近的定义位置"""
        nearest = None
        min_distance = float('inf')

        for loc_id, loc_data in locations.items():
            if 'coords' in loc_data:
                loc_lat, loc_lon = loc_data['coords']
                distance = self.calculate_distance(lat, lon, loc_lat, loc_lon)
                if distance < min_distance:
                    min_distance = distance
                    nearest = loc_data
                    nearest['id'] = loc_id

        return nearest if min_distance <= 100 else None  # 100米范围内

    def is_within_radius(self, lat1, lon1, coords2, radius_meters):
        """检查是否在指定半径内"""
        lat2, lon2 = coords2
        distance = self.calculate_distance(lat1, lon1, lat2, lon2)
        return distance <= radius_meters

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """计算两点间距离（米）"""
        R = 6371000  # 地球半径

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = (sin(delta_lat / 2) * sin(delta_lat / 2) +
             cos(lat1_rad) * cos(lat2_rad) *
             sin(delta_lon / 2) * sin(delta_lon / 2))
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def check_running_status(self, speed, current_time):
        """检查跑步状态"""
        if speed > self.running_threshold:
            if self.running_start_time is None:
                # 开始跑步
                self.running_start_time = current_time
                if self.app.tracking_tab:
                    self.app.tracking_tab.add_running_start_log(speed)
        else:
            if self.running_start_time is not None:
                # 结束跑步
                duration = current_time - self.running_start_time
                if self.app.tracking_tab:
                    self.app.tracking_tab.add_running_end_log(duration, speed)
                self.running_start_time = None

    def record_stay_activity(self, location, duration):
        """记录停留活动"""
        if self.app.schedule_tab:
            # 自动选择第一个可用事件类型
            events = location.get('events', ['stay'])
            event_type = events[0]

            self.app.schedule_tab.record_activity(
                location['name'],
                event_type,
                int(duration)
            )