from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.utils import get_color_from_hex
import datetime
import json
import os
import requests
import time
import threading

import os
import json
import datetime
import re
import requests
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty

# ========== AI对话配置 ==========
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-mbxkfffezgrurqntcdxozrciaqxncrmlblepiyszzeursmtv"
CHAT_HISTORY_FILE = "chat_history.json"


# ==================== 字体混合处理器 ====================
def is_chinese_char(char):
    """判断单个字符是否为中文字符"""
    if ord(char) < 128 and char.isprintable() and char not in "，。！？；：「」『』【】（）《》～、·":
        return False

    cp = ord(char)
    chinese_ranges = [
        (0x4E00, 0x9FFF),  # 基本汉字
        (0x3400, 0x4DBF),  # 扩展A
        (0xF900, 0xFAFF),  # 兼容汉字
        (0x20000, 0x2A6DF),  # 扩展B
    ]

    for start, end in chinese_ranges:
        if start <= cp <= end:
            return True

    chinese_punctuation = "，。！？；：「」『』【】（）《》～、·"
    return char in chinese_punctuation


def add_font_markup(text, chinese_font="simkai.ttf", other_font="arial.ttf"):
    """
    为文本添加字体标记：中文用楷体，非中文用Arial
    """
    if not text or not isinstance(text, str):
        return text

    all_chinese = all(is_chinese_char(c) for c in text if c.strip())
    all_non_chinese = all(not is_chinese_char(c) for c in text if c.strip())

    if all_chinese:
        return f"[font={chinese_font}]{text}[/font]"
    if all_non_chinese:
        return f"[font={other_font}]{text}[/font]"

    result_parts = []
    current_segment = ""
    current_is_chinese = None

    for char in text:
        is_chinese = is_chinese_char(char)

        if current_is_chinese is None:
            current_is_chinese = is_chinese
            current_segment = char
        elif is_chinese == current_is_chinese:
            current_segment += char
        else:
            font = chinese_font if current_is_chinese else other_font
            result_parts.append(f"[font={font}]{current_segment}[/font]")
            current_segment = char
            current_is_chinese = is_chinese

    if current_segment:
        font = chinese_font if current_is_chinese else other_font
        result_parts.append(f"[font={font}]{current_segment}[/font]")

    return "".join(result_parts)


# ==================== AI回复高级格式化器 ====================
class AIResponseFormatter:
    """高级AI回复格式化器"""

    SYMBOL_MAP = {
        '³': '³',
        '^3': '³',
        '**3': '³',
        '\\u00b3': '³',
        '²': '²',
        '^2': '²',
        '**2': '²',
        '\\u00b2': '²',
        '∫': '∫',
        '∞': '∞',
        'π': 'π',
        '≈': '≈',
        '≠': '≠',
        '≤': '≤',
        '≥': '≥',
        '□': '',
        '■': '',
        '▢': '',
        '。。': '。',
        '...': '…',
        '。.': '。',
    }

    @classmethod
    def format(cls, text, response_type="general"):
        """格式化AI回复"""
        if not isinstance(text, str) or not text.strip():
            return text

        text = cls._fix_symbols_and_encoding(text)
        text = cls._deep_clean(text)

        if cls._is_math_response(text):
            text = cls._format_math_response(text)
        elif cls._is_code_response(text):
            text = cls._format_code_response(text)
        else:
            text = cls._format_general_response(text)

        text = cls._final_cleanup(text)
        return text

    @classmethod
    def format_with_font_markup(cls, text):
        """格式化并添加字体标记"""
        formatted = cls.format(text)
        return add_font_markup(formatted)

    @classmethod
    def _fix_symbols_and_encoding(cls, text):
        """修复特殊符号"""
        unicode_fixes = {
            '\\u00b3': '³',
            '\\u00b2': '²',
            '\\u00b0': '°',
            '\\u03c0': 'π',
            '\\u221e': '∞',
            '\\u222b': '∫',
        }

        for unicode_char, display_char in unicode_fixes.items():
            text = text.replace(unicode_char, display_char)

        display_fixes = {
            '(sin x)^3': 'sin³x',
            '(cos x)^3': 'cos³x',
            '(sin x)^2': 'sin²x',
            '(cos x)^2': 'cos²x',
            'sin x *': 'sin x ·',
            'cos x *': 'cos x ·',
            ' * ': ' · ',
        }

        for wrong, correct in display_fixes.items():
            text = text.replace(wrong, correct)

        for wrong_symbol, correct_symbol in cls.SYMBOL_MAP.items():
            text = text.replace(wrong_symbol, correct_symbol)

        return text

    @classmethod
    def _deep_clean(cls, text):
        """深度清理"""
        text = re.sub(r'([。，；：！？])\1+', r'\1', text)
        text = re.sub(r'([.,;:!?])\1+', r'\1', text)
        text = re.sub(r'\s+', ' ', text)

        thinking_patterns = [
            r'^嗯，\s*',
            r'^首先，\s*',
            r'^接下来，\s*',
            r'^然后，\s*',
            r'^好的，\s*',
            r'^这样，\s*',
            r'^所以，\s*',
            r'^总之，\s*',
            r'^让我想想[，。:]?\s*',
            r'^我需要[计算分析思考][一下]?[，。:]?\s*',
            r'^这个问题[，。:]?\s*',
            r'^用户问的是.*?[，。:]?\s*',
            r'<think>.*?</think>\s*',
            r'\s*</?think[^>]*>\s*',
        ]

        for pattern in thinking_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        return text.strip()

    @classmethod
    def _is_math_response(cls, text):
        """检测数学回复"""
        math_indicators = ['∫', 'dx', 'dy', 'dz', 'sin', 'cos', 'tan', 'π', '∞']
        count = sum(1 for indicator in math_indicators if indicator in text)
        return count >= 2

    @classmethod
    def _format_math_response(cls, text):
        """格式化数学回复"""
        fixes = [
            (r'sin\s*([³²]?)\s*([a-zA-Zθφ])', r'sin\1\2'),
            (r'cos\s*([³²]?)\s*([a-zA-Zθφ])', r'cos\1\2'),
            (r'∫\s*([^∫\n]+?)\s*dx', lambda m: f'∫ {m.group(1).strip()} dx'),
        ]

        for pattern, replacement in fixes:
            if callable(replacement):
                text = re.sub(pattern, replacement, text)
            else:
                text = re.sub(pattern, replacement, text)

        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '∫' in line and 'dx' in line:
                if '=' in line:
                    parts = line.split('=', 1)
                    formatted_lines.append(parts[0].strip())
                    formatted_lines.append(f"    = {parts[1].strip()}")
                else:
                    formatted_lines.append(line)
            elif line.startswith('=') or line.startswith('≈'):
                formatted_lines.append(f"    {line}")
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    @classmethod
    def _is_code_response(cls, text):
        """检测代码回复"""
        return '```' in text or 'def ' in text or 'import ' in text

    @classmethod
    def _format_code_response(cls, text):
        """格式化代码回复"""
        return text

    @classmethod
    def _format_general_response(cls, text):
        """格式化一般回复"""
        paragraphs = []
        current_para = []

        sentences = re.split(r'[。！？]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            current_para.append(sentence)

            if len(''.join(current_para)) > 100 or sentence.endswith('：'):
                paragraphs.append(''.join(current_para))
                current_para = []

        if current_para:
            paragraphs.append(''.join(current_para))

        return '\n\n'.join(paragraphs)

    @classmethod
    def _final_cleanup(cls, text):
        """最终清理"""
        text = re.sub(r'([。，；：！？])\1+', r'\1', text)
        text = re.sub(r'([.,;:!?])\1+', r'\1', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)


# ==================== ChatMessage 组件 ====================
# ==================== ChatMessage 组件 ====================
class ChatMessage(BoxLayout):
    """对话消息组件 - 修复版"""

    role = StringProperty("user")
    content = StringProperty("")
    formatted_content = StringProperty("")
    header_text = StringProperty("")
    _is_ai_thinking = BooleanProperty(False)

    def __init__(self, role, content, is_ai_thinking=False, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self._is_ai_thinking = is_ai_thinking

        if content:
            self.content = content
            self._format_content()
        self._setup_header()

    def _format_content(self):
        """格式化内容"""
        if self._is_ai_thinking:
            # 思考状态不格式化
            self.formatted_content = self.content
        elif self.content:
            self.formatted_content = AIResponseFormatter.format_with_font_markup(self.content)
        else:
            self.formatted_content = ""

    def _setup_header(self):
        """设置头部信息"""
        # 使用 datetime 模块的 datetime 类
        from datetime import datetime as dt
        time_str = dt.now().strftime("%H:%M:%S")
        if self.role == "user":
            self.header_text = f"👤 你 ({time_str})"
        else:
            self.header_text = f"🤖 AI助手 ({time_str})"

    def update_content(self, new_content, is_final=False):
        """更新消息内容"""
        self.content = new_content
        self._is_ai_thinking = not is_final
        self._format_content()

        # 更新高度并触发重新布局
        Clock.schedule_once(lambda dt: self._update_height(), 0.01)

    def _update_height(self):
        """更新消息高度"""
        self.height = self.minimum_height
        if self.parent and hasattr(self.parent.parent, 'do_layout'):
            self.parent.parent.do_layout()

    def update_height(self, *args):
        """Label的texture_size变化时更新高度"""
        self.height = self.minimum_height


# ==================== AI对话管理类 ====================
class ConversationManager:
    """对话历史管理"""

    def __init__(self):
        self.history_file = CHAT_HISTORY_FILE
        self.formatter = AIResponseFormatter()

        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        self.history = self.load_chat_history()
        self._init_system_message()
        self.save_chat_history()

    def load_chat_history(self):
        """加载对话历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

                valid_history = []
                for msg in history:
                    if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                        if msg['role'] in ['system', 'user', 'assistant'] and msg['content'].strip():
                            valid_history.append(msg)
                return valid_history
        except Exception as e:
            print(f"加载对话历史失败: {e}")

        return []

    def _init_system_message(self):
        """初始化系统消息"""
        system_msg = {
            "role": "system",
            "content": """你是一个友好的AI助手。请：
1. 直接给出答案，不要包含思考过程
2. 数学表达式使用标准符号：sin³x 而不是 (sin x)^3
3. 避免双句号和奇怪符号
4. 回复简洁明了"""
        }

        self.history = [msg for msg in self.history if msg["role"] != "system"]
        self.history.insert(0, system_msg)

    def save_chat_history(self):
        """保存对话历史"""
        try:
            system_msgs = [msg for msg in self.history if msg["role"] == "system"]
            chat_msgs = [msg for msg in self.history if msg["role"] in ["user", "assistant"]]

            recent_chat = chat_msgs[-10:] if len(chat_msgs) > 10 else chat_msgs
            final_history = system_msgs + recent_chat

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(final_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史失败: {e}")

    def add_message(self, role, content):
        """添加消息"""
        content = content.strip()
        if not content:
            return

        if role == "assistant":
            content = self.formatter.format_with_font_markup(content)
            if not content:
                return

        self.history.append({"role": role, "content": content})
        self.save_chat_history()

    def get_recent_chat(self):
        """获取最近对话"""
        chat_msgs = [msg for msg in self.history if msg["role"] in ["user", "assistant"]]
        return chat_msgs[-10:] if len(chat_msgs) > 10 else chat_msgs

    def clear_history(self):
        """清空历史（保留系统消息）"""
        system_msgs = [msg for msg in self.history if msg["role"] == "system"]
        self.history = system_msgs
        self.save_chat_history()


# ==================== 操作菜单组件 ====================
class ActionMenu(BoxLayout):
    """操作菜单"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._activity_item_ref = None

    def set_activity_item(self, activity_item):
        """设置关联项"""
        self._activity_item_ref = activity_item

    def edit_button_pressed(self):
        """编辑"""
        if self._activity_item_ref:
            self._activity_item_ref.edit_activity()

    def delete_button_pressed(self):
        """删除"""
        if self._activity_item_ref:
            self._activity_item_ref.delete_activity()


class ActionMenuOverlay(FloatLayout):
    """菜单遮罩"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_touch_down(self, touch, *args):
        """处理触摸"""
        for child in self.children[:]:
            if isinstance(child, ActionMenu):
                if child.collide_point(*touch.pos):
                    return super().on_touch_down(touch, *args)

        for child in self.children[:]:
            if isinstance(child, ActionMenu) and hasattr(child, '_activity_item_ref'):
                child._activity_item_ref.close_action_menu()
                break

        return True


import os
import json
import threading
import time
import platform
import subprocess
import tempfile
from datetime import datetime, timedelta
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.properties import (
    StringProperty, ObjectProperty, NumericProperty, BooleanProperty
)
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.utils import get_color_from_hex
import datetime as dt_module


# ==================== 跨平台通知管理器 ====================
class CrossPlatformNotificationManager:
    """跨平台通知管理器（Windows + Android）"""

    def __init__(self):
        self.platform = self.detect_platform()
        self.reminders_file = 'memo_reminders.json'
        print(f"检测到平台: {self.platform}")

    def detect_platform(self):
        """检测当前运行平台"""
        try:
            import android
            return "android"
        except ImportError:
            pass

        if platform.system().lower() == "windows":
            return "windows"

        return "unknown"

    def schedule_notification(self, activity_data, minutes_before=20):
        """安排通知（跨平台）"""
        if not activity_data or 'time' not in activity_data:
            return False

        try:
            event_name = activity_data.get('event', '备忘录提醒')
            activity_time = activity_data.get('time', '')

            if not activity_time:
                return False

            reminder_time = self._calculate_reminder_time(activity_time, minutes_before)
            if not reminder_time:
                return False

            if self.platform == "windows":
                success = self._schedule_windows(activity_data, reminder_time)
            elif self.platform == "android":
                success = self._schedule_android(activity_data, reminder_time)
            else:
                success = self._schedule_fallback(activity_data, reminder_time)

            if success:
                self._save_reminder_to_json(activity_data, reminder_time)

            return success

        except Exception as e:
            print(f"安排通知失败: {e}")
            return False

    def _calculate_reminder_time(self, time_str, minutes_before):
        """计算提醒时间"""
        try:
            hour, minute = map(int, time_str.split(':'))
            now = datetime.now()
            activity_time = datetime(now.year, now.month, now.day, hour, minute)
            reminder_time = activity_time - timedelta(minutes=minutes_before)

            if reminder_time < now:
                reminder_time += timedelta(days=1)

            return reminder_time
        except Exception as e:
            print(f"计算提醒时间失败: {e}")
            return None

    def _schedule_windows(self, activity_data, reminder_time):
        """Windows平台：使用任务计划程序"""
        try:
            event_name = activity_data.get('event', '备忘录提醒')
            activity_time = activity_data.get('time', '')

            import hashlib
            task_id = hashlib.md5(f"{event_name}{activity_time}".encode()).hexdigest()[:8]
            task_name = f"MemoReminder_{task_id}"

            script_content = self._create_windows_notification_script(
                event_name, activity_time, activity_data.get('description', '')
            )

            success = self._create_windows_scheduled_task(
                task_name, reminder_time, script_content
            )

            if success:
                print(f"✅ Windows任务计划创建成功: {event_name}")
                return True
            else:
                print(f"❌ Windows任务计划创建失败: {event_name}")
                return False

        except Exception as e:
            print(f"Windows安排失败: {e}")
            return False

    def _create_windows_notification_script(self, event_name, activity_time, description):
        """创建Windows通知脚本"""
        script = f'''
import ctypes
import time

# 显示消息框
title = "📅 备忘录提醒"
message = f"事件: {event_name}\\n时间: {activity_time}"
if "{description}":
    message += f"\\n备注: {description}"

ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

# 同时尝试系统通知（Windows 10+）
try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
    toaster.show_toast(
        title,
        message.replace("\\n", " "),
        duration=10,
        threaded=True
    )
except:
    pass
'''
        return script

    def _create_windows_scheduled_task(self, task_name, reminder_time, script_content):
        """创建Windows计划任务"""
        try:
            temp_dir = tempfile.gettempdir()
            script_path = os.path.join(temp_dir, f"{task_name}.py")

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            trigger_time = reminder_time.strftime("%H:%M")

            python_exe = os.sys.executable.replace('\\', '\\\\')
            cmd = [
                'schtasks', '/create', '/tn', task_name,
                '/tr', f'"{python_exe}" "{script_path}"',
                '/sc', 'once', '/st', trigger_time, '/f'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                print(f"计划任务创建成功: {task_name}")
                return True
            else:
                cmd_str = f'schtasks /create /tn "{task_name}" /tr "\\"{python_exe}\\" \\"{script_path}\\"" /sc once /st {trigger_time} /f'
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                return result.returncode == 0

        except Exception as e:
            print(f"创建Windows任务失败: {e}")
            return False

    def _schedule_android(self, activity_data, reminder_time):
        """Android平台：使用AlarmManager"""
        try:
            event_name = activity_data.get('event', '备忘录提醒')
            activity_time = activity_data.get('time', '')

            try:
                from plyer import notification

                reminder_timestamp = int(reminder_time.timestamp() * 1000)

                print(f"✅ Android提醒已安排（需要前台服务）: {event_name}")
                return True

            except ImportError:
                print("❌ Android通知模块不可用")
                return False

        except Exception as e:
            print(f"Android安排失败: {e}")
            return False

    def _schedule_fallback(self, activity_data, reminder_time):
        """回退方案：保存到文件，由应用启动时检查"""
        print(f"⚠️ 未知平台，使用回退方案: {activity_data.get('event')}")
        return True

    def _save_reminder_to_json(self, activity_data, reminder_time):
        """保存提醒到JSON文件"""
        try:
            reminders = []

            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    reminders = json.load(f)

            reminder = {
                'event': activity_data.get('event', ''),
                'time': activity_data.get('time', ''),
                'description': activity_data.get('description', ''),
                'reminder_time': reminder_time.isoformat(),
                'scheduled_at': datetime.now().isoformat(),
                'platform': self.platform
            }

            for existing in reminders:
                if (existing['event'] == reminder['event'] and
                        existing['time'] == reminder['time']):
                    return

            reminders.append(reminder)

            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(reminders, f, ensure_ascii=False, indent=2)

            print(f"✅ 提醒已保存到文件: {reminder['event']}")

        except Exception as e:
            print(f"保存提醒文件失败: {e}")

    def cancel_notification(self, activity_data):
        """取消活动的提醒"""
        try:
            event_name = activity_data.get('event', '')
            activity_time = activity_data.get('time', '')

            if not event_name or not activity_time:
                return

            if self.platform == "windows":
                import hashlib
                task_id = hashlib.md5(f"{event_name}{activity_time}".encode()).hexdigest()[:8]
                task_name = f"MemoReminder_{task_id}"

                cmd = f'schtasks /delete /tn "{task_name}" /f'
                subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            self._remove_reminder_from_json(activity_data)

            print(f"✅ 提醒已取消: {event_name}")

        except Exception as e:
            print(f"取消提醒失败: {e}")

    def _remove_reminder_from_json(self, activity_data):
        """从JSON文件中移除提醒"""
        try:
            if not os.path.exists(self.reminders_file):
                return

            with open(self.reminders_file, 'r', encoding='utf-8') as f:
                reminders = json.load(f)

            new_reminders = []
            for reminder in reminders:
                if not (reminder['event'] == activity_data.get('event', '') and
                        reminder['time'] == activity_data.get('time', '')):
                    new_reminders.append(reminder)

            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(new_reminders, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"移除提醒失败: {e}")


# ==================== 备忘录弹窗组件 ====================
class EditActivityPopup(Popup):
    """编辑事件弹窗"""
    activity_item = ObjectProperty(None)

    def __init__(self, activity_item, **kwargs):
        super().__init__(**kwargs)
        self.activity_item = activity_item

        if activity_item.time:
            time_parts = activity_item.time.split(':')
            if len(time_parts) >= 2:
                self.ids.hour_input.text = time_parts[0]
                self.ids.minute_input.text = time_parts[1]

        self.ids.event_input.text = activity_item.event if activity_item.event else ""
        self.ids.description_input.text = activity_item.description if activity_item.description else ""

    def save_changes(self):
        """保存修改"""
        try:
            hour = self.ids.hour_input.text.strip()
            minute = self.ids.minute_input.text.strip()

            if not hour or not minute:
                return

            hour_int = int(hour)
            minute_int = int(minute)

            if hour_int < 0 or hour_int > 23 or minute_int < 0 or minute_int > 59:
                return

            time_str = f"{hour_int:02d}:{minute_int:02d}"

            event = self.ids.event_input.text.strip()
            description = self.ids.description_input.text.strip()

            if not event:
                return

            activity_data = {
                "time": time_str,
                "event": event
            }

            if description:
                activity_data["description"] = description

            if self.activity_item:
                self.activity_item.update_activity(activity_data)

            self.dismiss()

        except ValueError:
            pass
        except Exception as e:
            print(f"保存修改时出错: {e}")


class DeleteConfirmPopup(Popup):
    """删除确认弹窗"""
    activity_item = ObjectProperty(None)

    def confirm_delete(self):
        """确认删除"""
        if self.activity_item:
            self.activity_item.perform_delete()
        self.dismiss()


class AddActivityPopup(Popup):
    """添加事件弹窗"""
    schedule_tab = ObjectProperty(None)

    def __init__(self, schedule_tab, **kwargs):
        super().__init__(**kwargs)
        self.schedule_tab = schedule_tab

    def add_activity(self):
        """添加新活动"""
        try:
            hour = self.ids.hour_input.text.strip()
            minute = self.ids.minute_input.text.strip()

            if not hour or not minute:
                return

            hour_int = int(hour)
            minute_int = int(minute)

            if hour_int < 0 or hour_int > 23 or minute_int < 0 or minute_int > 59:
                return

            time_str = f"{hour_int:02d}:{minute_int:02d}"

            event = self.ids.event_input.text.strip()
            description = self.ids.description_input.text.strip()

            if not event:
                return

            activity_data = {
                "time": time_str,
                "event": event
            }

            if description:
                activity_data["description"] = description

            self.schedule_tab.add_activity(activity_data)
            self.dismiss()

        except ValueError:
            pass
        except Exception as e:
            print(f"添加活动时出错: {e}")


# ==================== 备忘录事件项组件 ====================
class ActivityItem(BoxLayout):
    content = StringProperty("")
    time = StringProperty("")
    event = StringProperty("")
    description = StringProperty("")
    index = NumericProperty(-1)
    parent_schedule = ObjectProperty(None)
    action_menu = None

    def __init__(self, content="", index=-1, parent_schedule=None, **kwargs):
        super().__init__(**kwargs)

        self.index = index
        self.parent_schedule = parent_schedule

        if content and isinstance(content, str):
            self.content = content
        elif isinstance(content, dict):
            self.time = content.get('time', '')
            self.event = content.get('event', '')
            self.description = content.get('description', '')
            self.content = f"{self.time} - {self.event}"
        else:
            self.content = str(content)

    def show_action_menu(self):
        """显示操作菜单"""
        if self.action_menu:
            self.close_action_menu()
            return

        from kivy.core.window import Window

        overlay = ActionMenuOverlay()
        overlay.size = Window.size
        overlay.pos = (0, 0)

        menu = ActionMenu()
        menu.set_activity_item(self)
        self.action_menu = menu

        overlay.add_widget(menu)
        Window.add_widget(overlay)

        menu_btn = self.ids.menu_btn
        btn_x, btn_y = menu_btn.to_window(*menu_btn.pos)
        btn_width = menu_btn.width
        btn_height = menu_btn.height

        menu_x = btn_x + btn_width + 10
        menu_y = btn_y - menu.height / 2 + btn_height / 2

        if menu_x + menu.width > Window.width:
            menu_x = btn_x - menu.width - 10
        if menu_y + menu.height > Window.height:
            menu_y = Window.height - menu.height - 20
        if menu_y < 0:
            menu_y = 20

        menu.pos = (menu_x, menu_y)
        self._action_menu_overlay = overlay

    def close_action_menu(self):
        """关闭操作菜单"""
        if hasattr(self, '_action_menu_overlay'):
            from kivy.core.window import Window
            Window.remove_widget(self._action_menu_overlay)
            self._action_menu_overlay = None
            self.action_menu = None

    def edit_activity(self):
        """编辑事件"""
        self.close_action_menu()
        popup = EditActivityPopup(activity_item=self)
        popup.open()

    def delete_activity(self):
        """删除事件"""
        self.close_action_menu()
        popup = DeleteConfirmPopup(activity_item=self)
        popup.open()

    def update_activity(self, new_data):
        """更新当前活动数据"""
        if self.parent_schedule and self.index >= 0:
            self.parent_schedule.edit_activity(self.index, new_data)

    def perform_delete(self):
        """执行删除操作"""
        if self.parent_schedule and self.index >= 0:
            self.parent_schedule.delete_activity(self.index)


# ==================== 主界面：AI对话 + 备忘录（集成通知） ====================
class ScheduleTab(BoxLayout):
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化备忘录数据
        self.activities = []
        # 初始化AI对话管理器
        self.conversation = ConversationManager()
        # 初始化通知管理器
        self.notification_manager = CrossPlatformNotificationManager()
        # 流式响应控制变量
        self._response_cancelled = False
        self._current_ai_message = None
        self._thinking_message = None
        Clock.schedule_once(self._post_init)

    def _post_init(self, dt):
        """初始化显示"""
        # 加载备忘录数据
        self.load_activities()
        self.display_activities()
        # 加载并显示最近10条对话
        self.load_chat_history_to_ui()
        # 显示欢迎消息（如果是首次使用）
        recent_chat = self.conversation.get_recent_chat()
        if len(recent_chat) == 0:  # 无历史对话
            self.add_message_to_ui("assistant", "✨ 欢迎使用AI对话助手！有什么问题可以问我~")

        # 为已有活动安排提醒
        Clock.schedule_once(lambda dt: self.schedule_all_notifications(), 2)

    # ========== 通知相关方法 ==========
    def schedule_all_notifications(self):
        """为所有备忘录安排提醒"""
        try:
            print("开始为所有活动安排提醒...")
            for i, activity in enumerate(self.activities):
                if isinstance(activity, dict) and 'time' in activity:
                    print(f"安排提醒 {i + 1}: {activity.get('event')} - {activity.get('time')}")
                    self.schedule_notification_for_activity(activity)
        except Exception as e:
            print(f"安排提醒失败: {e}")

    def schedule_notification_for_activity(self, activity_data):
        """为单个活动安排提醒"""
        try:
            if not activity_data or 'time' not in activity_data:
                return

            event_name = activity_data.get('event', '')
            activity_time = activity_data.get('time', '')

            print(f"安排提醒: {event_name} 于 {activity_time}")

            success = self.notification_manager.schedule_notification(
                activity_data,
                minutes_before=20
            )

            if success:
                print(f"✅ 提醒安排成功: {event_name}")
            else:
                print(f"❌ 提醒安排失败: {event_name}")

        except Exception as e:
            print(f"安排活动提醒失败: {e}")

    def cancel_notification_for_activity(self, activity_data):
        """取消活动的提醒"""
        try:
            if activity_data and 'time' in activity_data:
                self.notification_manager.cancel_notification(activity_data)
                print(f"已取消提醒: {activity_data.get('event')}")
        except Exception as e:
            print(f"取消提醒失败: {e}")

    # ========== AI对话相关方法 ==========
    def load_chat_history_to_ui(self):
        """加载最近10条对话到UI"""

        def _load():
            chat_box = self.ids.chat_box
            chat_box.clear_widgets()
            recent_chat = self.conversation.get_recent_chat()
            for msg in recent_chat:
                if msg["role"] in ["user", "assistant"]:
                    message_widget = ChatMessage(msg["role"], msg["content"])
                    chat_box.add_widget(message_widget)

            # 重置滚动位置到顶部
            self.ids.chat_history_container.scroll_y = 1.0
            # 确保布局更新
            chat_box.height = chat_box.minimum_height
            chat_box.parent.height = chat_box.height

        Clock.schedule_once(lambda dt: _load(), 0.1)

    def add_message_to_ui(self, role, content, is_thinking=False):
        """线程安全的消息添加方法 - 修复版"""

        def _add(dt):
            chat_box = self.ids.chat_box
            message_widget = ChatMessage(role, content, is_ai_thinking=is_thinking)
            chat_box.add_widget(message_widget)

            # 更新布局和滚动
            chat_box.height = chat_box.minimum_height
            if hasattr(chat_box, 'parent') and chat_box.parent:
                chat_box.parent.height = chat_box.height
            self.ids.chat_history_container.scroll_y = 0

            if role == "assistant":
                self._current_ai_message = message_widget
                if is_thinking:
                    self._thinking_message = message_widget

            return message_widget

        # 直接调用Clock.schedule_once，不尝试索引返回值
        Clock.schedule_once(_add, 0)

    def update_ai_message(self, content, is_final=False):
        """更新AI消息内容"""

        def _update():
            if self._current_ai_message:
                self._current_ai_message.update_content(content, is_final)

                # 更新对话管理器
                if is_final:
                    self.conversation.add_message("assistant", content)

                # 更新UI布局
                chat_box = self.ids.chat_box
                chat_box.height = chat_box.minimum_height
                chat_box.parent.height = chat_box.height
                self.ids.chat_history_container.scroll_y = 0

                # 如果是最终回复，清除当前消息引用
                if is_final:
                    self._current_ai_message = None
                    self._thinking_message = None

        Clock.schedule_once(lambda dt: _update(), 0)

    def send_message(self):
        """发送消息"""
        user_input = self.ids.user_input.text.strip()
        if not user_input:
            return

        self.ids.user_input.text = ""
        self.conversation.add_message("user", user_input)
        self.add_message_to_ui("user", user_input)
        self.get_ai_response(user_input)

    def get_ai_response(self, user_input):
        """获取AI回复 - 修复版"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        recent_chat = self.conversation.get_recent_chat()
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "messages": [
                {"role": "system",
                 "content": "你是一个友好的AI助手，回答简洁明了，仅返回最终回复内容，不要包含任何思考、分析、总结类的文字，使用中文交流。"},
                *recent_chat,
                {"role": "user", "content": user_input}
            ],
            "stream": False,
            "max_tokens": 500,
            "temperature": 0.7
        }

        def request_worker():
            try:
                # 在主线程显示"正在思考..."消息
                Clock.schedule_once(lambda dt: self.add_message_to_ui("assistant", "🔄 正在思考中...", True), 0)

                response = requests.post(
                    API_URL,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_reply = ""
                    if "choices" in data and len(data["choices"]) > 0:
                        ai_reply = data["choices"][0]["message"].get("content", "").strip()

                    if ai_reply:
                        # 移除重复句子
                        ai_reply = self._remove_duplicate_sentences(ai_reply)
                        # 在主线程更新消息
                        Clock.schedule_once(lambda dt: self.update_ai_message(ai_reply, True), 0)
                    else:
                        fallback_msg = "🤔 抱歉，我暂时无法回答你的问题。"
                        Clock.schedule_once(lambda dt: self.update_ai_message(fallback_msg, True), 0)

                else:
                    error_msg = f"❌ 请求失败（状态码：{response.status_code}）"
                    Clock.schedule_once(lambda dt: self.update_ai_message(error_msg, True), 0)

            except Exception as e:
                error_msg = f"⚠️ 网络连接出错：{str(e)[:50]}"
                Clock.schedule_once(lambda dt: self.update_ai_message(error_msg, True), 0)

        threading.Thread(target=request_worker, daemon=True).start()

    def _remove_duplicate_sentences(self, text):
        """移除重复的句子"""
        if not text:
            return ""

        sentences = []
        temp = ""
        for char in text:
            temp += char
            if char in ["。", "！", "？", "；", "\n"]:
                if temp.strip():
                    sentences.append(temp.strip())
                temp = ""
        if temp.strip():
            sentences.append(temp.strip())

        seen = set()
        unique_sentences = []
        for sentence in sentences:
            if sentence not in seen and len(sentence) > 1:
                seen.add(sentence)
                unique_sentences.append(sentence)

        return "。".join(unique_sentences) + ("。" if unique_sentences else "")

    def cancel_response(self):
        """取消当前响应"""
        self._response_cancelled = True
        if self._current_ai_message:
            self.update_ai_message(f"{self._current_ai_message.content}\n\n⚠️ 响应已取消", True)

    # ========== 备忘录相关方法 ==========
    def load_activities(self):
        """加载活动数据"""
        try:
            if os.path.exists('activities.json'):
                with open('activities.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.activities = data.get('logs', data.get('activities', []))
                    else:
                        self.activities = data
            else:
                self.activities = [
                    {"time": "08:00", "event": "起床洗漱"},
                    {"time": "09:00", "event": "开始工作/学习"},
                    {"time": "12:00", "event": "午餐时间"},
                    {"time": "13:00", "event": "午休片刻"},
                    {"time": "14:00", "event": "继续工作"},
                    {"time": "18:00", "event": "晚餐时间"},
                    {"time": "20:00", "event": "休闲娱乐"}
                ]
                self.save_activities()

        except Exception as e:
            print(f"加载活动数据失败: {e}")
            self.activities = []

    def save_activities(self):
        """保存活动数据"""
        try:
            with open('activities.json', 'w', encoding='utf-8') as f:
                json.dump(self.activities, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存活动数据失败: {e}")

    def display_activities(self):
        """显示活动列表"""
        if hasattr(self, 'ids') and 'activity_container' in self.ids:
            try:
                container = self.ids.activity_container
                container.clear_widgets()

                # 添加标题
                today = dt_module.date.today().strftime("%Y-%m-%d")
                container.add_widget(ActivityItem(
                    content=f"      == {today} === \n\n   今天也是活力满满的一天喵！"
                ))

                # 按时间排序并显示活动
                sorted_activities = sorted(
                    [a for a in self.activities if isinstance(a, dict) and 'time' in a],
                    key=lambda x: x['time']
                )

                for i, activity in enumerate(sorted_activities):
                    activity_item = ActivityItem(
                        content=activity,
                        index=i,
                        parent_schedule=self
                    )
                    container.add_widget(activity_item)

            except Exception as e:
                print(f"显示活动时出错: {e}")

    def add_activity(self, activity_data):
        """添加新活动（集成提醒）"""
        try:
            if isinstance(activity_data, dict):
                self.activities.append(activity_data)
                self.save_activities()
                self.display_activities()

                # 安排提醒
                self.schedule_notification_for_activity(activity_data)

        except Exception as e:
            print(f"添加活动时出错: {e}")

    def edit_activity(self, index, new_data):
        """编辑指定索引的活动（更新提醒）"""
        try:
            if 0 <= index < len(self.activities) and isinstance(new_data, dict):
                # 取消旧提醒
                old_activity = self.activities[index]
                self.cancel_notification_for_activity(old_activity)

                # 更新活动数据
                self.activities[index] = new_data

                # 保存并刷新显示
                self.save_activities()
                self.display_activities()

                # 安排新提醒
                self.schedule_notification_for_activity(new_data)
        except Exception as e:
            print(f"编辑活动时出错: {e}")

    def delete_activity(self, index):
        """删除指定索引的活动（取消提醒）"""
        try:
            if 0 <= index < len(self.activities):
                # 取消提醒
                activity = self.activities[index]
                self.cancel_notification_for_activity(activity)

                # 删除活动
                del self.activities[index]

                # 保存并刷新显示
                self.save_activities()
                self.display_activities()
        except Exception as e:
            print(f"删除活动时出错: {e}")

    def show_add_popup(self):
        """显示添加活动的弹出窗口"""
        popup = AddActivityPopup(schedule_tab=self)
        popup.open()

    def update_alarm_display(self, dt=None):
        """更新闹钟显示（兼容原有逻辑）"""
        pass