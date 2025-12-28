"""
DailyTracker - 最终版（完整功能）
- 顶部图片优先来自百度热搜首页首条（若该条含缩略图），回退到新闻第一页面的图片
- Playwright 增强图片抓取（已安装时启用）以提高图片抓取成功率
- 关键词最小长度 KEYWORD_MIN_LEN = 7（去空格后）
- 热搜排序优化：原第1项标为TOP，原第2项升为第1，后续依次上移
- 保留后端 ignore list 管理接口，前端不暴露管理
- 手动刷新按钮保留；自动刷新后台默认每小时运行
- 新闻与热搜条目不显示来源文本（只显示序号与标题 / 热度）
依赖：
  pip install requests beautifulsoup4 lxml kivy
  pip install playwright  # 可选增强
  python -m playwright install
"""
import os
import re
import threading
import json
import webbrowser
import time
from datetime import datetime
from functools import partial
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty, NumericProperty

# Playwright 增强图片抓取（可选但推荐）
USE_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    USE_PLAYWRIGHT = True
except ImportError as e:
    print(f"Playwright 未安装（可选增强）：{e}")
    print("如需增强图片抓取，请执行：pip install playwright && python -m playwright install")

# 配置常量
KV_FILE = "trackingtab.kv"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".dailytracker_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
NEWS_CACHE = os.path.join(CACHE_DIR, "news_cache.json")
HOT_CACHE = os.path.join(CACHE_DIR, "hot_cache.json")
IGNORE_FILE = os.path.join(CACHE_DIR, "ignore_list.json")
TOP_IMAGE = os.path.join(CACHE_DIR, "top_news.jpg")
BAIDU_HOT_URL = "https://top.baidu.com/board?tab=realtime"

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

# 过滤配置
KEYWORD_MIN_LEN = 7  # 最小关键词长度（去空格后）
DEFAULT_BLACKLIST = [
    "百度", "查看更多", "贴吧", "小说", "邮箱大师", "国内", "国际",
    "首页", "应用", "新闻", "hao123", "地图", "网易", "163", "www",
    "http", "专题", "推荐", "登录", "注册", "下载", "会员", "帮助",
    "意见", "导航", "软件", "视频", "首页图片"
]
NETEASE_NOISE_TOKENS = ["邮箱大师", "国内", "国际", "图片", "评论", "直播", "游戏", "应用", "体育", "娱乐",
                        "王三三", "综合", "中超", "英超", "电影", "电视", "音乐"]

# 图片下载限制
MAX_IMAGE_BYTES = 600 * 1024  # 600 KB
IMAGE_TIMEOUT = 15  # 秒
DOWNLOAD_TIMEOUT = 15


def ensure_absolute_link(link, base):
    """确保链接为绝对路径"""
    if not link:
        return link
    link = link.strip()
    if link.startswith("//"):
        return "https:" + link
    if link.startswith(("http://", "https://")):
        return link
    try:
        return urljoin(base, link)
    except Exception:
        return link


def ensure_absolute(url, base):
    """增强版绝对路径处理（兼容更多场景）"""
    if not url:
        return url
    u = url.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith(("http://", "https://")):
        return u
    return urljoin(base, u)


def download_image(url, dst_path, referer=None):
    """增强版图片下载（带大小限制和Referer）"""
    try:
        if not url:
            return False

        # 清理URL并确保绝对路径
        url = ensure_absolute(url, BAIDU_HOT_URL)
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        headers = HEADERS.copy()
        if referer:
            headers["Referer"] = referer

        print(f"下载图片: {url}")
        r = requests.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT)

        if r.status_code != 200:
            print(f"图片下载失败: HTTP {r.status_code}")
            return False

        # 验证内容类型
        ct = r.headers.get("Content-Type", "")
        if not ct or not ct.startswith("image"):
            print(f"非图片类型: {ct}")
            return False

        # 分块下载并限制大小
        total = 0
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(4096):
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    print("图片过大，终止下载")
                    f.close()
                    os.remove(dst_path)
                    return False
                f.write(chunk)

        if total == 0:
            os.remove(dst_path)
            return False

        print(f"图片保存至: {dst_path} (大小: {total/1024:.1f}KB)")
        return True

    except Exception as e:
        print(f"图片下载错误: {e}")
        if os.path.exists(dst_path):
            os.remove(dst_path)
        return False


def extract_img_from_element(page, el, base_url):
    """从DOM元素提取图片URL（支持多种属性和背景图）"""
    try:
        # 优先提取img标签
        img = el.query_selector("img")
        if img:
            # 尝试多种图片属性
            for attr in ("src", "data-src", "data-original", "data-lazy-src", "data-ks-lazyload"):
                val = img.get_attribute(attr)
                if val and val.strip():
                    return ensure_absolute(val, base_url)
            # 处理srcset
            srcset = img.get_attribute("srcset")
            if srcset:
                m = re.split(r',\s*', srcset)[0]
                url_part = m.split()[0] if m else None
                if url_part:
                    return ensure_absolute(url_part, base_url)
    except Exception:
        pass

    # 尝试元素自身的data属性
    try:
        for attr in ("data-src", "data-original", "data-lazy-src"):
            v = el.get_attribute(attr)
            if v and v.strip():
                return ensure_absolute(v, base_url)
    except Exception:
        pass

    # 提取背景图
    try:
        style = el.get_attribute("style") or ""
        m = re.search(r'url\(([^)]+)\)', style)
        if m:
            candidate = m.group(1).strip(" '\"")
            if candidate:
                return ensure_absolute(candidate, base_url)
    except Exception:
        pass

    # 通过JS获取计算后的背景图
    try:
        js = """(el) => {
            const nodes = el.querySelectorAll('*');
            for (let n of nodes) {
                const s = window.getComputedStyle(n);
                const bg = s.getPropertyValue('background-image');
                if (bg && bg !== 'none') return bg;
            }
            return null;
        }"""
        bg = page.evaluate(js, el)
        if bg:
            m = re.search(r'url\\(([^)]+)\\)', bg) or re.search(r'url\\(([^)]+)\\)', bg.strip())
            if m:
                candidate = m.group(1).strip(" '\"")
                if candidate:
                    return ensure_absolute(candidate, base_url)
    except Exception:
        pass

    return None


def find_first_item_element(page):
    """精准定位百度热搜第一条元素"""
    # 1. 优先查找data-pos="1"
    try:
        el = page.query_selector('[data-pos="1"]')
        if el:
            return el
    except Exception:
        pass

    # 2. 查找所有data-pos元素，找值为1或0的
    try:
        el_all = page.query_selector_all('[data-pos]')
        if el_all:
            for e in el_all:
                try:
                    v = e.get_attribute("data-pos")
                    if v and v.strip() in ("1", "0"):
                        return e
                except Exception:
                    continue
            return el_all[0]
    except Exception:
        pass

    # 3. 查找包含数字1徽章的元素
    try:
        anchors = page.query_selector_all("a")
        for a in anchors[:300]:
            try:
                children = a.query_selector_all("*")
                for c in children:
                    try:
                        ctxt = c.inner_text().strip()
                        if ctxt == "1":
                            # 向上查找容器元素
                            parent = a
                            for _ in range(6):
                                parent = parent.evaluate_handle("el => el.parentElement")
                                if not parent:
                                    break
                                tag = parent.evaluate("el => el.tagName.toLowerCase()")
                                if tag in ("li", "div"):
                                    cls = parent.get_attribute("class") or ""
                                    if any(k in cls for k in ("hot-list", "board-wrapper", "list-table")):
                                        return parent
                            return a
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass

    return None


def fetch_first_baidu_image_playwright():
    """使用Playwright抓取百度热搜首条图片"""
    img_url = None
    first_link = None

    if not USE_PLAYWRIGHT:
        return None, None

    try:
        with sync_playwright() as pw:
            # 启动浏览器（无头模式）
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])

            try:
                # 加载页面
                page.goto(BAIDU_HOT_URL, timeout=20000, wait_until="networkidle")
            except PlaywrightTimeoutError:
                print("页面加载超时，继续使用已有DOM")
                page.wait_for_load_state(timeout=8000)

            # 小幅度滚动触发懒加载
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight*0.05)")
                time.sleep(0.6)
            except Exception:
                pass

            # 定位第一条热搜元素
            first_el = find_first_item_element(page)

            if first_el:
                print("找到第一条热搜元素")
                img_candidate = None

                # 检查图片尺寸（严格模式）
                try:
                    img_el = first_el.query_selector("img")
                    if img_el:
                        wh = page.evaluate("(img)=>[img.naturalWidth||0, img.naturalHeight||0]", img_el)
                        w, h = int(wh[0]), int(wh[1])
                        print(f"图片自然尺寸: {w}x{h}")

                        # 严格模式：200x120以上
                        if w >= 200 and h >= 120:
                            img_candidate = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                        # 宽松模式：100x80以上
                        elif w >= 100 and h >= 80:
                            img_candidate = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                except Exception as e:
                    print(f"检查图片尺寸失败: {e}")

                # 通用提取
                if not img_candidate:
                    img_candidate = extract_img_from_element(page, first_el, BAIDU_HOT_URL)

                # 获取第一条链接
                try:
                    a = first_el.query_selector("a")
                    if a:
                        href = a.get_attribute("href")
                        first_link = ensure_absolute(href, BAIDU_HOT_URL) if href else None
                except Exception:
                    pass

                if img_candidate:
                    img_url = ensure_absolute(img_candidate, BAIDU_HOT_URL)

            # 备用方案：扫描所有列表项找合适图片
            if not img_url:
                print("备用方案：扫描列表项找图片")
                candidate_selectors = [
                    ".category-wrap .hot-list li",
                    ".category-wrap ul li",
                    ".board-wrapper li",
                    ".list-table tr",
                    ".hot-list-item",
                    "[data-pos]"
                ]

                for sel in candidate_selectors:
                    try:
                        nodes = page.query_selector_all(sel)
                    except Exception:
                        nodes = []

                    for node in nodes:
                        try:
                            text = node.inner_text().strip() or ""
                            if len(re.sub(r'\s+', '', text)) < 7:
                                continue

                            img_el = node.query_selector("img")
                            if not img_el:
                                continue

                            wh = page.evaluate("(img)=>[img.naturalWidth||0, img.naturalHeight||0]", img_el)
                            w, h = int(wh[0]), int(wh[1])

                            if w >= 100 and h >= 80:
                                src = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                                if src:
                                    img_url = ensure_absolute(src, BAIDU_HOT_URL)
                                    first_link = node.query_selector("a").get_attribute("href") if node.query_selector("a") else None
                                    browser.close()
                                    return img_url, first_link
                        except Exception:
                            continue

            # 最终备用：打开链接找og:image
            if not img_url:
                print("最终备用：打开链接找og:image")
                candidate_links = []
                for sel in [".category-wrap .hot-list li a", ".board-wrapper li a", "[data-pos] a"]:
                    try:
                        anchors = page.query_selector_all(sel)
                        for a in anchors:
                            txt = a.inner_text().strip() or ""
                            if len(re.sub(r'\s+', '', txt)) >= 7 and "hao123" not in txt.lower():
                                href = a.get_attribute("href")
                                if href:
                                    candidate_links.append(ensure_absolute(href, BAIDU_HOT_URL))
                        if candidate_links:
                            break
                    except Exception:
                        continue

                for link in candidate_links[:3]:
                    try:
                        p2 = browser.new_page(user_agent=HEADERS["User-Agent"])
                        p2.goto(link, timeout=15000, wait_until="networkidle")

                        # 查找og:image
                        og = p2.query_selector('meta[property="og:image"]')
                        if og:
                            v = og.get_attribute("content")
                            if v:
                                img_url = ensure_absolute(v, link)
                                first_link = link
                                p2.close()
                                browser.close()
                                return img_url, first_link

                        # 查找twitter:image
                        tw = p2.query_selector('meta[name="twitter:image"]') or p2.query_selector('meta[property="twitter:image"]')
                        if tw:
                            v = tw.get_attribute("content")
                            if v:
                                img_url = ensure_absolute(v, link)
                                first_link = link
                                p2.close()
                                browser.close()
                                return img_url, first_link

                        p2.close()
                    except Exception:
                        continue

            browser.close()

    except Exception as e:
        print(f"Playwright图片抓取失败: {e}")

    return img_url, first_link


class TrackingTab(BoxLayout):
    app = ObjectProperty(None)
    news_status = StringProperty("正在加载今日新闻（新浪 & 网易）...")
    hot_status = StringProperty("正在加载热搜（百度 & 知乎）...")
    local_html_path = StringProperty("")
    top_image_link = StringProperty("")    # 百度首条链接
    auto_refresh_enabled = BooleanProperty(True)
    auto_refresh_interval = NumericProperty(3600)  # 1小时
    top_hot_item = ObjectProperty(None)    # 标记为TOP的热搜项

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 默认本地 html 路径
        self.local_html_path = r"C:\Users\admin\PycharmProjects\dailytracker\utils\location+weather.html"
        # 加载忽略列表
        self.ignore_list = self._load_ignore_list()
        # 启动时立即开始抓取
        Clock.schedule_once(lambda dt: self.start_fetching(), 0.2)
        # 启动自动刷新
        Clock.schedule_once(lambda dt: self._ensure_auto_refresh(), 1.0)

    # ---------------- 热搜排序重排逻辑 ----------------
    def reorder_hot_list(self, hot_items):
        """
        重排热搜列表：
        - 原第1项 → 标记为top（保留原排名1，添加特殊标记）
        - 原第2项 → 新第1名
        - 原第3项 → 新第2名，以此类推
        返回 (top_item, reordered_items)，无数据时返回 (None, [])
        """
        if not isinstance(hot_items, list) or len(hot_items) == 0:
            return None, []

        reordered = []
        top_item = None

        for idx, item in enumerate(hot_items):
            # 深拷贝避免修改原数据
            new_item = item.copy()

            if idx == 0:
                # 原第1项 → 标记为top，保留原排名
                top_item = new_item
                top_item["is_top"] = True  # 添加top标记
                top_item["display_rank"] = "TOP"  # 显示用排名
                top_item["original_rank"] = item.get("rank", "1")  # 记录原排名
            else:
                # 原第2项及以后 → 排名=原排名-1
                original_rank = item.get("rank", str(idx+1))
                new_rank = str(int(original_rank)-1) if original_rank.isdigit() else str(idx)
                new_item["rank"] = new_rank
                new_item["display_rank"] = new_rank  # 显示用排名
                new_item["is_top"] = False  # 普通项标记
                new_item["original_rank"] = original_rank  # 记录原排名
                reordered.append(new_item)

        return top_item, reordered

    # ---------------- 自动刷新（仅后台） ----------------
    def _ensure_auto_refresh(self):
        if hasattr(self, "_auto_ev") and self._auto_ev:
            try:
                self._auto_ev.cancel()
            except Exception:
                pass
        if self.auto_refresh_enabled and self.auto_refresh_interval > 0:
            self._auto_ev = Clock.schedule_interval(lambda dt: self.start_fetching(), self.auto_refresh_interval)

    def set_auto_refresh(self, enabled: bool, interval_seconds: int = None):
        self.auto_refresh_enabled = enabled
        if interval_seconds is not None:
            self.auto_refresh_interval = interval_seconds
        self._ensure_auto_refresh()

    # ---------------- 忽略列表管理（后端） ----------------
    def _load_ignore_list(self):
        try:
            if os.path.exists(IGNORE_FILE):
                with open(IGNORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged = list(dict.fromkeys(DEFAULT_BLACKLIST + data))
                        return merged
            return list(DEFAULT_BLACKLIST)
        except Exception:
            return list(DEFAULT_BLACKLIST)

    def _save_ignore_list(self):
        try:
            with open(IGNORE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.ignore_list, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_ignore_keyword(self, keyword: str):
        k = keyword.strip()
        if k and k not in self.ignore_list:
            self.ignore_list.insert(0, k)
            self._save_ignore_list()

    def remove_ignore_keyword(self, keyword: str):
        try:
            self.ignore_list = [k for k in self.ignore_list if k != keyword]
            self._save_ignore_list()
        except Exception:
            pass

    # ---------------- 抓取控制 ----------------
    def start_fetching(self, *_):
        th = threading.Thread(target=self.fetch_all, daemon=True)
        th.start()

    def fetch_all(self):
        # 1) 优先使用Playwright抓取百度热搜首图
        baidu_first_img_url = None
        baidu_first_link = None

        try:
            # 先尝试Playwright增强抓取
            img_url, link = fetch_first_baidu_image_playwright()
            if img_url:
                baidu_first_img_url = img_url
                baidu_first_link = link
                print(f"Playwright找到首图: {img_url}")
        except Exception as e:
            print(f"Playwright抓取失败: {e}")

        # 2) 备用方案：常规方法抓取百度热搜
        try:
            baidu_list, fallback_img_url, fallback_link = self.fetch_baidu_hot_enhanced()
            # 如果Playwright没抓到，使用备用方案的图片
            if not baidu_first_img_url and fallback_img_url:
                baidu_first_img_url = fallback_img_url
                baidu_first_link = fallback_link
        except Exception:
            baidu_list, baidu_first_img_url, baidu_first_link = [], "", ""

        # 3) 下载并更新顶部图片
        if baidu_first_img_url:
            # 使用增强版下载函数
            success = download_image(baidu_first_img_url, TOP_IMAGE, referer=BAIDU_HOT_URL)
            if not success and baidu_first_link:
                # 重试，添加Referer
                success = download_image(baidu_first_img_url, TOP_IMAGE, referer=baidu_first_link)

            if success and os.path.exists(TOP_IMAGE):
                Clock.schedule_once(partial(self.update_top_image_ui, TOP_IMAGE, baidu_first_link), 0)

        # 4) 抓取新闻
        try:
            news_items = self.fetch_news()
            Clock.schedule_once(partial(self.update_news_ui, news_items), 0)
        except Exception as e:
            news_items = self.read_cache(NEWS_CACHE) or []
            Clock.schedule_once(partial(self.update_news_ui, news_items, str(e)), 0)

        # 5) 抓取知乎热搜并处理排序
        try:
            zhihu_list = self.fetch_zhihu_hot()
            hot_items = baidu_list + zhihu_list

            # 新增：调用重排函数，分离top项和普通项
            self.top_hot_item, reordered_hot_items = self.reorder_hot_list(hot_items)

            Clock.schedule_once(partial(self.update_hot_ui, reordered_hot_items), 0)
        except Exception as e:
            hot_items = self.read_cache(HOT_CACHE) or []
            self.top_hot_item, reordered_hot_items = self.reorder_hot_list(hot_items)
            Clock.schedule_once(partial(self.update_hot_ui, reordered_hot_items, str(e)), 0)

    # ---------------- 关键词过滤 ----------------
    def _clean_keyword(self, s: str) -> str:
        if not s:
            return ""
        s = s.strip()
        s = re.sub(r'[>\s]+$', '', s)
        s = re.sub(r'^\s*\d+[\.\、\)]\s*', '', s)
        return s

    def is_valid_keyword(self, k: str) -> bool:
        """关键词有效性检查"""
        if not k:
            return False
        s = self._clean_keyword(k)
        if not s or re.fullmatch(r'[\W_]+', s):
            return False

        s_no_space = re.sub(r'\s+', '', s)
        if len(s_no_space) < KEYWORD_MIN_LEN:
            return False

        lower = s.lower()
        if re.search(r'(http|www\.|\.com|\.cn)', lower):
            return False

        for token in self.ignore_list:
            if token and token.lower() in lower:
                return False

        for t in NETEASE_NOISE_TOKENS:
            if s == t or s.lower() == t.lower():
                return False

        chinese_groups = re.findall(r'[\u4e00-\u9fff]+', s)
        if chinese_groups:
            chlen = sum(len(g) for g in chinese_groups)
            if chlen < 2:
                return False
        else:
            if len(s_no_space) < 6:
                return False

        if re.fullmatch(r'\d+', s_no_space):
            return False

        return True

    # ---------------- 新闻抓取 ----------------
    def fetch_news(self):
        items = []
        items += self.fetch_sina_news()
        items += self.fetch_163_news()
        dedup = []
        seen = set()
        for it in items:
            link = it.get("link") or it.get("url") or ""
            base = link or "https://news.sina.com.cn"
            link = ensure_absolute_link(link, base)
            it["link"] = link
            key = link or it.get("title", "")
            if key in seen:
                continue
            seen.add(key)
            dedup.append(it)
            if len(dedup) >= 30:
                break
        self.write_cache(NEWS_CACHE, {"fetched_at": datetime.utcnow().isoformat(), "items": dedup})
        return dedup

    def fetch_sina_news(self):
        results = []
        rss_candidates = [
            "https://feed.sina.cn/?/feed/sina_news_top.xml",
            "http://rss.sina.com.cn/news/china/focus15.xml",
            "http://rss.sina.com.cn/roll/sina_roll.xml",
        ]
        for rss in rss_candidates:
            try:
                r = requests.get(rss, headers=HEADERS, timeout=8)
                if r.status_code == 200 and r.content:
                    try:
                        root = ET.fromstring(r.content)
                        for item in root.findall(".//item")[:15]:
                            title = item.findtext("title") or ""
                            link = item.findtext("link") or ""
                            if self.is_valid_keyword(title):
                                results.append({"title": title.strip(), "link": link.strip()})
                        if results:
                            return results
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            r = requests.get("https://news.sina.com.cn/", headers=HEADERS, timeout=8)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            candidates = soup.select("div#blk_hd a") + soup.select(".feed-card-item a") + soup.select(".news-item a")
            if not candidates:
                candidates = soup.find_all("a", href=True)[:60]
            for a in candidates:
                title = a.get_text(strip=True)
                link = a.get("href")
                if title and link and self.is_valid_keyword(title):
                    link = ensure_absolute_link(link, "https://news.sina.com.cn")
                    results.append({"title": title, "link": link})
            return results[:18]
        except Exception:
            return results

    def fetch_163_news(self):
        results = []
        try:
            r = requests.get("https://news.163.com/", headers=HEADERS, timeout=8)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            selectors = [
                "div#newsFocus a",
                ".data_row a",
                ".focusList a",
                ".news-top a",
                ".ns-left a",
                ".ns-right a"
            ]
            nodes = []
            for sel in selectors:
                found = soup.select(sel)
                if found:
                    nodes = found
                    break
            if not nodes:
                nodes = soup.find_all("a", href=True)[:80]
            for a in nodes:
                title_raw = a.get_text(strip=True)
                title = self._clean_keyword(title_raw)
                link = a.get("href")
                if not title or not link:
                    continue
                if not self.is_valid_keyword(title):
                    continue
                link = ensure_absolute_link(link, "https://news.163.com")
                results.append({"title": title, "link": link})
                if len(results) >= 18:
                    break
            return results
        except Exception:
            return results

    # ---------------- 百度热搜（含常规图片提取） ----------------
    def fetch_baidu_hot_enhanced(self):
        """常规方法抓取百度热搜（备用方案）"""
        url = BAIDU_HOT_URL
        items = []
        first_img_url = ""
        first_link = ""
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            selectors = [
                ".category-wrap .hot-list li",
                ".category-wrap ul li",
                ".board-wrapper li",
                ".list-table tr",
                ".hot-list-item",
            ]
            rows = []
            for sel in selectors:
                found = soup.select(sel)
                if found:
                    rows = found
                    break
            if not rows:
                rows = soup.select("[data-pos]") or []
            rank = 0
            for node in rows:
                a = node.find("a")
                if not a:
                    a = node.select_one(".keyword") or node.select_one(".title") or node.select_one(".c-single-text-ellipsis")
                if not a:
                    continue
                keyword_raw = a.get_text(strip=True)
                keyword = self._clean_keyword(keyword_raw)
                if not self.is_valid_keyword(keyword):
                    continue
                rank += 1
                link = a.get("href") or ""
                link = ensure_absolute_link(link, url)
                hot = ""
                hot_node = node.select_one(".last") or node.select_one(".hot-index") or node.select_one(".index") or node.find("span")
                if hot_node:
                    hot = hot_node.get_text(strip=True) or ""
                # 提取图片
                img_tag = node.find("img")
                img_url = ""
                if img_tag and img_tag.get("src"):
                    img_url = ensure_absolute_link(img_tag.get("src"), url)
                if rank == 1:
                    first_link = link
                    if img_url:
                        first_img_url = img_url
                items.append({"rank": str(rank), "keyword": keyword, "link": link, "hot": hot})
                if rank >= 30:
                    break
            if not items:
                for a in soup.select("a[href]")[:200]:
                    txt = a.get_text(strip=True)
                    if self.is_valid_keyword(txt):
                        items.append({"rank": str(len(items) + 1), "keyword": txt, "link": ensure_absolute_link(a['href'], url), "hot": ""})
                        if len(items) >= 20:
                            break
            return items, first_img_url, first_link
        except Exception as e:
            print(f"常规百度热搜抓取失败: {e}")
            return [], "", ""

    # ---------------- 知乎热搜 ----------------
    def fetch_zhihu_hot(self):
        results = []
        url = "https://www.zhihu.com/hot"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            r.raise_for_status()
            text = r.text
            m = re.search(r'\"hotList\"\s*:\s*(\[[^\]]+\])', text)
            if m:
                try:
                    arr = json.loads(m.group(1))
                    rank = 0
                    for it in arr:
                        rank += 1
                        title = it.get("title") or it.get("query") or it.get("target", "")
                        if self.is_valid_keyword(title):
                            results.append({"rank": str(rank), "keyword": title, "link": "https://www.zhihu.com/hot", "hot": ""})
                        if rank >= 30:
                            break
                    return results
                except Exception:
                    pass
            soup = BeautifulSoup(text, "lxml")
            nodes = soup.select(".HotList-list .HotList-item") or soup.select(".hot-list li") or soup.select(".HotItem")
            rank = 0
            for n in nodes:
                rank += 1
                a = n.select_one("a") or n.select_one(".HotItem-title")
                keyword = a.get_text(strip=True) if a else n.get_text(strip=True)
                if self.is_valid_keyword(keyword):
                    results.append({"rank": str(rank), "keyword": keyword, "link": "https://www.zhihu.com/hot", "hot": ""})
                if rank >= 30:
                    break
            return results
        except Exception:
            return results

    # ---------------- UI更新 ----------------
    def update_top_image_ui(self, img_path, baidu_first_link, dt=0):
        """更新顶部图片UI"""
        img_widget = self.ids.get("top_image")
        if img_widget:
            if img_path and os.path.exists(img_path):
                img_widget.source = img_path
                img_widget.reload()
                self.top_image_link = baidu_first_link or ""
                print(f"顶部图片已更新: {img_path}")
            else:
                # 使用占位图
                placeholder = 'assets/images/top_placeholder.jpg'
                if os.path.exists(placeholder):
                    img_widget.source = placeholder
                else:
                    img_widget.source = ""
                self.top_image_link = ""

        # 更新状态文本
        self.news_status = f"今日新闻 · 上次更新 {datetime.now().strftime('%H:%M:%S')}"

    def update_news_ui(self, items, err_msg=None, dt=0):
        container = self.ids.get("news_list")
        status_label = self.ids.get("news_status_label")
        container.clear_widgets()
        if not items:
            status_label.text = "无法获取新闻" + (f"：{err_msg}" if err_msg else "")
            return
        status_label.text = f"今日新闻 · 上次更新 {datetime.now().strftime('%H:%M:%S')}"

        for idx, it in enumerate(items, start=1):
            title = it.get("title") or it.get("keyword") or ""
            link = it.get("link") or ""
            txt = f"[b]{idx}. {title}[/b]"
            btn = Button(
                text=txt,
                size_hint_y=None,
                height=80,
                markup=True,
                font_name="simsun.ttc",
                background_normal="",
                background_color=(1,1,1,0.06),
                color=(0.06,0.06,0.06,1),
                font_size='15sp'
            )
            if link:
                btn.bind(on_release=partial(webbrowser.open, link))
            container.add_widget(btn)

    def update_hot_ui(self, items, err_msg=None, dt=0):
        """更新热搜UI（TOP项+重排后的普通项）"""
        container = self.ids.get("hot_list")
        status_label = self.ids.get("hot_status_label")
        container.clear_widgets()

        if not items and not self.top_hot_item:
            status_label.text = "无法获取热搜" + (f"：{err_msg}" if err_msg else "")
            return

        status_label.text = f"热搜 · 上次更新 {datetime.now().strftime('%H:%M:%S')}"

        # 第一步：渲染TOP项（原第1项）- 特殊样式
        if self.top_hot_item:
            top_item = self.top_hot_item
            keyword = top_item.get("keyword", "")
            link = top_item.get("link", "")
            hot = top_item.get("hot", "")

            # TOP项特殊样式：浅红色渐变背景+白色文字+TOP标记
            top_btn = Button(
                text=f"[b][color=#FFFFFF]🔥 TOP {keyword}[/color][/b]\n[color=#FFEEEE]{hot}[/color]",
                size_hint_y=None,
                height=90,
                markup=True,
                font_name="simsun.ttc",
                background_normal="",
                background_color=(0.98, 0.3, 0.3, 0.5),  # 浅红色背景
                color=(1, 1, 1, 1)  # 白色文字
                ,bold=True,
                font_size='18sp'
            )
            if link:
                top_btn.bind(on_release=partial(webbrowser.open, link))
            container.add_widget(top_btn)

            # 注释：这里的分隔线已被删除

        # 第二步：渲染重排后的普通项（原第2项→新第1项，依次类推）
        for it in items:
            rank = it.get("display_rank", it.get("rank", ""))
            keyword = it.get("keyword", "")
            link = it.get("link", "")
            hot = it.get("hot", "")

            # 普通项样式
            btn = Button(
                text=f"[b]{rank}. {keyword}[/b]\n{hot}",
                size_hint_y=None,
                height=70,
                markup=True,
                font_name="simsun.ttc",
                background_normal="",
                background_color=(1, 0.98, 0.95, 0.02),
                color=(0.06, 0.06, 0.06, 1),
                font_size='15sp'
            )
            if link:
                btn.bind(on_release=partial(webbrowser.open, link))
            container.add_widget(btn)

        # 缓存重排后的数据（仅普通项，TOP项单独存储）
        cache_data = {"fetched_at": datetime.utcnow().isoformat(), "items": items, "top_item": self.top_hot_item}
        self.write_cache(HOT_CACHE, cache_data)

    # ---------------- 缓存管理 ----------------
    def write_cache(self, path, obj):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False)
        except Exception:
            pass

    def read_cache(self, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    items = obj.get("items", obj)

                    # 热搜缓存需要重排处理
                    if path == HOT_CACHE:
                        # 读取TOP项
                        self.top_hot_item = obj.get("top_item") or None
                        # 重排普通项
                        if items:
                            _, reordered = self.reorder_hot_list(items)
                            return reordered

                    return items
        except Exception:
            return None
        return None

    # ---------------- 辅助功能 ----------------
    def open_local_html(self, instance=None):
        """打开本地天气HTML文件"""
        path = self.local_html_path
        if not path:
            return
        if not os.path.exists(path):
            return
        url = f"file:///{path.replace('\\', '/')}"
        webbrowser.open(url)

    def open_top_image(self):
        """点击顶部图片打开链接"""
        if self.top_image_link:
            webbrowser.open(self.top_image_link)

    def on_manual_refresh(self, instance=None):
        """手动刷新按钮回调"""
        self.news_status = "手动刷新中：新闻..."
        self.hot_status = "手动刷新中：热搜..."
        self.start_fetching()


