#!/usr/bin/env python3
"""
更稳健的 Baidu 首条热搜图片抓取测试脚本（使用 Playwright）
- 优先通过 data-pos="1" 或含排名角标为 "1" 的元素定位第一条热搜
- 分层图片阈值：严格 -> 宽容 -> 回退到首条链接的 og:image / 最大图
输出：
 - baidu_hot_test.png
 - baidu_first_image.jpg (若找到)
"""
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception as e:
    print("Playwright not available:", e)
    sys.exit(2)

PAGE_URL = "https://top.baidu.com/board?tab=realtime"
SCREENSHOT_FILE = "baidu_hot_test.png"
OUTPUT_IMAGE_FILE = "baidu_first_image.jpg"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"}
MAX_IMAGE_BYTES = 600 * 1024
DOWNLOAD_TIMEOUT = 15


def ensure_absolute(url, base):
    if not url:
        return url
    u = url.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(base, u)


def download_image(url, dst_path, referer=None):
    try:
        if not url:
            return False
        url = ensure_absolute(url, PAGE_URL)
        headers = HEADERS.copy()
        if referer:
            headers["Referer"] = referer
        print("Downloading:", url)
        r = requests.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT)
        if r.status_code != 200:
            print("HTTP", r.status_code)
            return False
        ct = r.headers.get("Content-Type", "")
        if not ct.startswith("image"):
            print("Not an image:", ct)
            return False
        total = 0
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(4096):
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    print("Image too large, abort")
                    try:
                        f.close()
                        os.remove(dst_path)
                    except Exception:
                        pass
                    return False
                f.write(chunk)
        print("Saved image to", dst_path)
        return True
    except Exception as e:
        print("Download error:", e)
        return False


def extract_img_from_element(page, el, base_url):
    """从元素尝试提取图片 URL（img attrs / style / data-attrs / computed background）"""
    try:
        img = el.query_selector("img")
        if img:
            for attr in ("src", "data-src", "data-original", "data-lazy-src", "data-ks-lazyload"):
                val = img.get_attribute(attr)
                if val and val.strip():
                    return ensure_absolute(val, base_url)
            srcset = img.get_attribute("srcset")
            if srcset:
                m = re.split(r',\s*', srcset)[0]
                url_part = m.split()[0] if m else None
                if url_part:
                    return ensure_absolute(url_part, base_url)
    except Exception:
        pass

    try:
        for attr in ("data-src", "data-original", "data-lazy-src"):
            v = el.get_attribute(attr)
            if v and v.strip():
                return ensure_absolute(v, base_url)
    except Exception:
        pass

    try:
        style = el.get_attribute("style") or ""
        m = re.search(r'url\(([^)]+)\)', style)
        if m:
            candidate = m.group(1).strip(" '\"")
            if candidate:
                return ensure_absolute(candidate, base_url)
    except Exception:
        pass

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
    """
    更确定地定位第一页“第1条热搜”的 DOM 元素：
    - 优先查找 [data-pos="1"] 或类似标识
    - 其次查找含排名角标文本为 "1" 的元素（badge）
    - 返回 element handle 或 None
    """
    # 1) try data-pos="1" (some layouts use data-pos starting at 1)
    try:
        el = page.query_selector('[data-pos="1"]')
        if el:
            return el
    except Exception:
        pass
    # 2) sometimes data-pos starts from 0 or different structure: try first [data-pos]
    try:
        el_all = page.query_selector_all('[data-pos]')
        if el_all and len(el_all) > 0:
            # find the one whose attribute == '1' if any, else take the first
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
    # 3) try find badge element that indicates rank "1" inside list nodes
    # look for elements that have descendant with inner_text '1' and a sibling/title text -> likely rank badge
    try:
        # a simple heuristic using XPath-like text match via page.locator("text='1'")
        # But we need the parent list item; iterate anchors and check for a child with text '1'
        anchors = page.query_selector_all("a")
        for a in anchors[:300]:
            try:
                txt = a.inner_text().strip()
                # quick filter: if anchor contains '1' at start in a small segment (badge)
                # check for substring '1' in a short child text
                # We'll check child nodes' inner text lengths
                children = a.query_selector_all("*")
                for c in children:
                    try:
                        ctxt = c.inner_text().strip()
                        if ctxt == "1":
                            # return parent list item if possible
                            # climb up to nearest <li> or container
                            parent = a
                            for _ in range(6):
                                parent = parent.evaluate_handle("el => el.parentElement")
                                if not parent:
                                    break
                                # try to detect li or item container
                                tag = parent.evaluate("el => el.tagName.toLowerCase()")
                                if tag and tag.lower() == "li":
                                    return parent
                                # if container has class 'hot-list' or 'board-wrapper' etc., return parent
                                cls = parent.get_attribute("class") or ""
                                if any(k in cls for k in ("hot-list", "board-wrapper", "list-table", "hot-list-item", "category-wrap")):
                                    return parent
                            # fallback: return anchor itself
                            return a
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return None


def fetch_first_baidu_image():
    print("Launching Playwright and loading page...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        try:
            page.goto(PAGE_URL, timeout=20000, wait_until="networkidle")
        except PlaywrightTimeoutError:
            print("Warning: networkidle timeout, proceeding with available DOM")
            try:
                page.wait_for_load_state(timeout=8000)
            except Exception:
                pass

        # save screenshot for debugging
        try:
            page.screenshot(path=SCREENSHOT_FILE, full_page=False)
            print("Saved screenshot:", SCREENSHOT_FILE)
        except Exception as e:
            print("Screenshot failed:", e)

        # small scroll to trigger lazy load
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight*0.05)")
            time.sleep(0.6)
        except Exception:
            pass

        # 1) locate first item element more deterministically
        first_el = find_first_item_element(page)
        if first_el:
            print("Located first-item element via data-pos/badge.")
            # attempt to extract image with stricter then looser thresholds
            # try strict natural size check (>=200x120)
            img_candidate = None
            try:
                img_el = first_el.query_selector("img")
                if img_el:
                    wh = page.evaluate("(img)=>[img.naturalWidth||0, img.naturalHeight||0]", img_el)
                    w, h = int(wh[0]), int(wh[1])
                    print("Found img in first-el natural size:", w, h)
                    if w >= 200 and h >= 120:
                        img_candidate = img_el.get_attribute("src") or img_el.get_attribute("data-src") or img_el.get_attribute("data-original")
                # if not strict, try looser threshold
                if not img_candidate and img_el:
                    try:
                        if w >= 100 and h >= 80:
                            img_candidate = img_el.get_attribute("src") or img_el.get_attribute("data-src") or img_el.get_attribute("data-original")
                    except Exception:
                        pass
            except Exception:
                pass
            # if still nothing, attempt generic extraction (style, data-attrs)
            if not img_candidate:
                img_candidate = extract_img_from_element(page, first_el, PAGE_URL)
            # try to get a link
            first_link = None
            try:
                a = first_el.query_selector("a")
                if a:
                    href = a.get_attribute("href")
                    first_link = ensure_absolute(href, PAGE_URL) if href else None
            except Exception:
                first_link = None

            if img_candidate:
                return ensure_absolute(img_candidate, PAGE_URL), first_link

        # 2) fallback: scan list nodes and find any node whose keyword seems legitimate and has a sizable image
        print("Fallback: scanning list nodes for sizable images...")
        candidate_selectors = [
            ".category-wrap .hot-list li",
            ".category-wrap ul li",
            ".board-wrapper li",
            ".list-table tr",
            ".hot-list-item",
            "[data-pos] li",
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
                    # lightweight keyword check: length and not just site name
                    if not text or len(re.sub(r'\s+', '', text)) < 7:
                        continue
                    # look for image child and size
                    img_el = node.query_selector("img")
                    if not img_el:
                        continue
                    try:
                        wh = page.evaluate("(img)=>[img.naturalWidth||0, img.naturalHeight||0]", img_el)
                        w, h = int(wh[0]), int(wh[1])
                    except Exception:
                        w, h = 0, 0
                    if w >= 100 and h >= 80:
                        src = img_el.get_attribute("src") or img_el.get_attribute("data-src") or img_el.get_attribute("data-original")
                        if src:
                            # we prefer the topmost candidate
                            return ensure_absolute(src, PAGE_URL), (node.query_selector("a").get_attribute("href") if node.query_selector("a") else None)
                except Exception:
                    continue

        # 3) final fallback: collect candidate links whose text looks like real keywords and open them for og:image
        print("Final fallback: open candidate article pages for og:image...")
        candidate_links = []
        for sel in [".category-wrap .hot-list li a", ".board-wrapper li a", ".list-table tr a", "[data-pos] a", ".hot-list-item a"]:
            try:
                anchors = page.query_selector_all(sel)
            except Exception:
                anchors = []
            for a in anchors:
                try:
                    txt = a.inner_text().strip() or ""
                    if len(re.sub(r'\s+', '', txt)) >= 7 and "hao123" not in txt.lower():
                        href = a.get_attribute("href")
                        if href:
                            candidate_links.append(ensure_absolute(href, PAGE_URL))
                except Exception:
                    continue
            if candidate_links:
                break

        for link in candidate_links[:3]:
            try:
                print("Opening candidate link:", link)
                p2 = browser.new_page(user_agent=HEADERS["User-Agent"])
                try:
                    p2.goto(link, timeout=15000, wait_until="networkidle")
                except PlaywrightTimeoutError:
                    try:
                        p2.wait_for_load_state(timeout=8000)
                    except Exception:
                        pass
                og = p2.query_selector('meta[property="og:image"]')
                if og:
                    v = og.get_attribute("content")
                    if v:
                        try:
                            p2.close()
                        except Exception:
                            pass
                        browser.close()
                        return ensure_absolute(v, link), link
                # twitter
                tw = p2.query_selector('meta[name="twitter:image"]') or p2.query_selector('meta[property="twitter:image"]')
                if tw:
                    v = tw.get_attribute("content")
                    if v:
                        try:
                            p2.close()
                        except Exception:
                            pass
                        browser.close()
                        return ensure_absolute(v, link), link
                # try largest image
                imgs = p2.query_selector_all("img")
                best = None
                best_area = 0
                for im in imgs:
                    try:
                        src = im.get_attribute("src") or im.get_attribute("data-src") or im.get_attribute("data-original")
                        if not src:
                            continue
                        wh = p2.evaluate("(el)=>[el.naturalWidth||0, el.naturalHeight||0]", im)
                        w, h = int(wh[0]), int(wh[1])
                        area = w * h
                        if area > best_area and w >= 100 and h >= 80:
                            best_area = area
                            best = src
                    except Exception:
                        continue
                try:
                    p2.close()
                except Exception:
                    pass
                if best:
                    browser.close()
                    return ensure_absolute(best, link), link
            except Exception:
                continue

        try:
            browser.close()
        except Exception:
            pass
        return None, None


def main():
    img_url, first_link = fetch_first_baidu_image()
    if not img_url:
        print("No suitable first-hot image found. Check baidu_hot_test.png for page structure and post it if you'd like help.")
        sys.exit(1)

    print("Found image URL:", img_url)
    print("Associated first-link (if any):", first_link)
    ok = download_image(img_url, OUTPUT_IMAGE_FILE, referer=PAGE_URL)
    if not ok:
        print("Download failed. Retrying with Referer header may help.")
        HEADERS["Referer"] = PAGE_URL
        if download_image(img_url, OUTPUT_IMAGE_FILE, referer=PAGE_URL):
            print("Downloaded with Referer.")
            sys.exit(0)
        print("Final download attempt failed.")
        sys.exit(2)

    print("Success: saved top hot image as", OUTPUT_IMAGE_FILE)
    sys.exit(0)


if __name__ == "__main__":
    main()