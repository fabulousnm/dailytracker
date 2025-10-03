# main.py - Complete English Version with Component Integration
import os
import sys
import json
import datetime

# ========== Import Kivy and other modules ==========
from kivy import platform
from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup

# ========== Import Components ==========
try:
    from components.schedule_tab import ScheduleTab
    from components.tracking_tab import TrackingTab
    from components.personalization_tab import PersonalizationTab

    COMPONENTS_AVAILABLE = True
    print("Components imported successfully")
except ImportError as e:
    print(f"Component import failed: {e}")
    COMPONENTS_AVAILABLE = False


    # Fallback component definitions
    class ScheduleTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 20
            self.spacing = 10
            self.add_widget(Label(text='Daily Schedule', font_size='24sp', bold=True))
            self.add_widget(Label(text='Wake Up: 07:00', font_size='18sp'))
            self.add_widget(Label(text='Sleep Time: 23:00', font_size='18sp'))

        def update_alarm_display(self):
            pass

        def update_theme(self, weather_type):
            """Apply theme colors"""
            try:
                print(f"=== Applying theme: {weather_type} ===")

                self.current_theme = weather_type
                colors = self.theme_colors[weather_type]

                # 更明显地设置窗口背景色
                bg_color = get_color_from_hex(colors['background'])
                Window.clearcolor = bg_color
                print(f"Window background set to: {colors['background']} -> {bg_color}")

                # 强制窗口重绘
                Window.canvas.ask_update()

                # 通知所有标签更新主题
                if hasattr(self, 'schedule_tab'):
                    self.schedule_tab.update_theme(colors)
                if hasattr(self, 'tracking_tab'):
                    self.tracking_tab.update_theme(colors)
                if hasattr(self, 'personalization_tab'):
                    self.personalization_tab.update_theme(colors)

                print(f"Theme {weather_type} applied successfully!")

            except Exception as e:
                print(f"Failed to apply theme: {e}")

    class TrackingTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 10
            self.spacing = 10
            self.add_widget(Label(text='Daily Tracking', font_size='24sp', bold=True))
            self.add_widget(Label(text='Location Tracking', font_size='16sp'))

        def update_theme(self, colors):
            pass


    class PersonalizationTab(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 20
            self.spacing = 15
            self.add_widget(Label(text='Personalization', font_size='24sp', bold=True))
            self.add_widget(Label(text='SJTU - Manage Your Time!', font_size='14sp', italic=True))

        def update_theme(self, colors):
            pass

        def customize_color(self, module):
            print(f"Customize color: {module}")

        def change_theme(self, theme_name):
            print(f"Change theme: {theme_name}")

        def show_message(self, message):
            print(f"Message: {message}")


class DailyTracker(TabbedPanel):
    # Define properties for component access
    schedule_tab = ObjectProperty(None)
    tracking_tab = ObjectProperty(None)
    personalization_tab = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.tab_pos = 'top_mid'

        # Theme color configuration
        self.theme_colors = {
            'sunny': {
                'primary': '#FFD700',  # Bright Yellow
                'secondary': '#32CD32',  # Lime Green
                'background': '#FFFAF0'  # Very Light Yellow (Floral White)
            },
            'cloudy': {
                'primary': '#696969',  # Dim Gray
                'secondary': '#8A2BE2',  # Bright Purple (Blue Violet)
                'background': '#F8F8FF'  # Very Light Purple (Ghost White)
            },
            'rainy': {
                'primary': '#1E90FF',  # Bright Blue (Dodger Blue)
                'secondary': '#2F4F4F',  # Dark Slate Gray
                'background': '#F0F8FF'  # Very Light Blue (Alice Blue)
            }
        }
        self.current_theme = 'sunny'

        # Initialize data file
        self.data_file = "user_data.json"
        self.load_user_data()

        # Create tabs with components
        self.create_tabs()

        # Start services
        Clock.schedule_once(self.init_services, 1)

    def create_tabs(self):
        """Create application tabs with components"""
        # Schedule Tab
        if COMPONENTS_AVAILABLE:
            self.schedule_tab = ScheduleTab()
        else:
            self.schedule_tab = ScheduleTab()
        self.schedule_tab.app = self  # Ensure app reference is set
        # ... same for other tabs
        tab1 = TabbedPanelItem(text='Schedule')
        tab1.add_widget(self.schedule_tab)
        self.add_widget(tab1)

        # Tracking Tab
        if COMPONENTS_AVAILABLE:
            self.tracking_tab = TrackingTab()
        else:
            self.tracking_tab = TrackingTab()
        self.tracking_tab.app = self
        tab2 = TabbedPanelItem(text='Tracking')
        tab2.add_widget(self.tracking_tab)
        self.add_widget(tab2)

        # Personalization Tab
        if COMPONENTS_AVAILABLE:
            self.personalization_tab = PersonalizationTab()
        else:
            self.personalization_tab = PersonalizationTab()
        self.personalization_tab.app = self
        tab3 = TabbedPanelItem(text='Settings')
        tab3.add_widget(self.personalization_tab)
        self.add_widget(tab3)

    def init_services(self, dt):
        """Initialize all services"""
        print("Initializing application services...")

        # Initialize weather service
        try:
            from utils.weather_api import WeatherManager
            self.weather_manager = WeatherManager()
            # Get current weather and update theme
            self.update_weather_theme()
        except Exception as e:
            print(f"Weather service initialization failed: {e}")
            # Use default theme
            self.update_theme('sunny')

        # Initialize Android specific services
        if platform == 'android':
            try:
                from utils.location_manager import LocationManager
                from utils.alarm_reader import AlarmReader

                self.location_manager = LocationManager(self)
                self.alarm_reader = AlarmReader()

                # Start location tracking
                self.location_manager.start_tracking()
                print("Location tracking service started")

                # Read alarm data
                self.update_alarm_info()

            except Exception as e:
                print(f"Android service initialization failed: {e}")
        else:
            print("Non-Android platform, using simulation data")
            self.setup_desktop_simulation()

    def setup_desktop_simulation(self):
        """Setup desktop environment simulation data"""
        try:
            # Update UI display
            if hasattr(self, 'schedule_tab'):
                Clock.schedule_once(lambda dt: self.schedule_tab.update_alarm_display(), 0.5)

        except Exception as e:
            print(f"Desktop simulation setup failed: {e}")

    def load_user_data(self):
        """Load user data"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                print("User data loaded successfully")
            else:
                self.create_default_data()
        except Exception as e:
            print(f"Failed to load user data: {e}")
            self.create_default_data()

    def create_default_data(self):
        """Create default user data"""
        self.user_data = {
            'sleep_time': "23:00",
            'wake_time': "07:00",
            'locations': {
                'home': {
                    'name': 'Home',
                    'events': ['Rest', 'Sleep', 'Gaming'],
                    'coords': [31.0258, 121.4376]
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
            'speed_threshold': 5.0,
            'running_threshold': 3.0,
            'stay_threshold': 60,
            'personalization': {},
            'notes': [],
            'activities': []
        }
        self.save_user_data()
        print("Default user data created")

    def save_user_data(self):
        """Save user data"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save user data: {e}")

    def update_alarm_info(self):
        """Update alarm information"""
        if hasattr(self, 'alarm_reader'):
            try:
                alarms = self.alarm_reader.get_alarms()
                if alarms:
                    self.user_data['wake_time'] = min(alarms)
                    self.user_data['sleep_time'] = max(alarms)
                    self.save_user_data()

                    # Update UI display
                    if hasattr(self, 'schedule_tab'):
                        self.schedule_tab.update_alarm_display()

                    print(
                        f"Alarm data updated: Wake up {self.user_data['wake_time']}, Sleep {self.user_data['sleep_time']}")
            except Exception as e:
                print(f"Failed to read alarms: {e}")

    def update_theme(self, weather_type):
        """Apply theme colors with visual feedback"""
        try:
            print(f"=== Applying theme: {weather_type} ===")

            # 保存当前主题
            self.current_theme = weather_type
            colors = self.theme_colors[weather_type]

            # 第一步：短暂变白（闪屏效果）
            original_color = Window.clearcolor
            Window.clearcolor = (1, 1, 1, 1)  # 白色

            # 第二步：延迟应用最终主题颜色
            Clock.schedule_once(lambda dt: self.apply_final_theme(weather_type, colors), 0.2)

        except Exception as e:
            print(f"Failed to apply theme: {e}")

    def update_weather_theme(self):
        """Update theme based on weather"""
        try:
            if hasattr(self, 'weather_manager'):
                # Get weather information
                weather_data = self.weather_manager.get_current_weather(31.0258, 121.4376)
                weather_type = weather_data.get('weather', 'sunny')

                print(f"Weather data received: {weather_type}")

                # Map weather type to theme
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
                print(f"Weather {weather_type} mapped to theme: {theme}")
                self.update_theme(theme)

            else:
                print("Weather manager not available, using default theme")
                self.update_theme('sunny')

        except Exception as e:
            print(f"Weather update error: {e}")
            self.update_theme('sunny')

    def apply_final_theme(self, weather_type, colors):
        """Apply the final theme colors after visual feedback"""
        try:
            # 应用最终背景色
            bg_color = get_color_from_hex(colors['background'])
            Window.clearcolor = bg_color
            print(f"Final background color: {colors['background']}")

            # 强制窗口重绘
            Window.canvas.ask_update()

            # 通知所有标签更新主题
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
        """Add activity note"""
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
            print("Note added successfully")

        except Exception as e:
            print(f"Failed to add note: {e}")

    def customize_color(self, module):
        """Customize module color"""
        if hasattr(self, 'personalization_tab'):
            self.personalization_tab.customize_color(module)

    def change_theme(self, theme_name):
        """Change theme"""
        if hasattr(self, 'personalization_tab'):
            self.personalization_tab.change_theme(theme_name)

    def update_speed_threshold(self, value):
        """Update speed threshold"""
        try:
            self.user_data['speed_threshold'] = float(value)
            self.save_user_data()

            if hasattr(self, 'location_manager'):
                self.location_manager.speed_threshold = float(value)

            if hasattr(self, 'tracking_tab'):
                self.tracking_tab.speed_threshold = float(value)

            print(f"Speed threshold updated: {value} m/s")

        except Exception as e:
            print(f"Failed to update speed threshold: {e}")

    def save_settings(self):
        """Save all settings"""
        try:
            self.save_user_data()
            print("Settings saved successfully")

            # Show success message
            if hasattr(self, 'personalization_tab'):
                self.personalization_tab.show_message("Settings saved successfully!")

        except Exception as e:
            print(f"Failed to save settings: {e}")

    def reset_settings(self):
        """Reset settings to default"""
        try:
            self.create_default_data()

            # Reload theme
            self.update_theme('sunny')

            # Update all tabs
            if hasattr(self, 'schedule_tab'):
                self.schedule_tab.update_alarm_display()
                if hasattr(self.schedule_tab, 'clear_activities'):
                    self.schedule_tab.clear_activities()

            if hasattr(self, 'tracking_tab'):
                if hasattr(self.tracking_tab, 'clear_logs'):
                    self.tracking_tab.clear_logs()

            print("Settings reset to default")

            if hasattr(self, 'personalization_tab'):
                self.personalization_tab.show_message("Settings reset to default!")

        except Exception as e:
            print(f"Failed to reset settings: {e}")


class DailyTrackerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "DailyTracker - SJTU"
        self.icon = self.get_icon_path()

    def get_icon_path(self):
        """Get icon path"""
        icon_paths = [
            'assets/icon.png',
            'icon.png',
            './assets/icon.png',
            './icon.png'
        ]

        for path in icon_paths:
            if os.path.exists(path):
                print(f"Icon file found: {path}")
                return path

        print("Icon file not found")
        return None

    def build(self):
        print("Starting DailyTracker application...")
        print(f"Application icon: {self.icon}")
        # Set initial window size (for desktop testing)
        Window.size = (400, 700)
        return DailyTracker()

    def on_pause(self):
        """Called when application pauses"""
        try:
            if hasattr(self, 'root'):
                self.root.save_user_data()
            print("Application paused, data saved")
            return True
        except Exception as e:
            print(f"Pause handling failed: {e}")
            return True

    def on_resume(self):
        """Called when application resumes"""
        try:
            if hasattr(self, 'root'):
                self.root.update_alarm_info()
                self.root.update_weather_theme()
            print("Application resumed, data updated")
        except Exception as e:
            print(f"Resume handling failed: {e}")

    def on_stop(self):
        """Called when application stops"""
        try:
            if hasattr(self, 'root'):
                self.root.save_user_data()
            print("Application stopped, data saved")
        except Exception as e:
            print(f"Stop handling failed: {e}")


if __name__ == '__main__':
    try:
        DailyTrackerApp().run()
    except Exception as e:
        print(f"Application startup failed: {e}")
        import traceback

        traceback.print_exc()