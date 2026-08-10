"""
抖音视频流抓取脚本
通过 Playwright 无头浏览器抓取抖音视频的真实播放地址
"""
import sys, json, time, re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1",
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*"
}

def fetch_douyin_video(video_url: str) -> dict:
    """抓取抖音视频信息，返回 {video_url, title, desc}"""
    from playwright.sync_api import sync_playwright

    result = {"video_url": "", "title": "", "desc": ""}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            viewport={"width": 390, "height": 844},
            locale="zh-CN",
            device_scale_factor=2.75
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        page = context.new_page()
        video_stream_urls = []

        def on_request(request):
            url = request.url
            if 'aweme/v1/play' in url or 'douyinvod.com' in url:
                if url not in video_stream_urls:
                    video_stream_urls.append(url)

        page.on('request', on_request)

        # 先访问首页
        page.goto('https://www.douyin.com/', timeout=15000, wait_until='domcontentloaded')
        time.sleep(1.5)

        # 访问视频页面
        page.goto(video_url, timeout=30000, wait_until='domcontentloaded')
        time.sleep(4)

        # 滚动触发加载
        page.evaluate('window.scrollTo(0, 300)')
        time.sleep(2)

        # 尝试播放视频
        try:
            page.evaluate('document.querySelector("video")?.play()')
            time.sleep(1)
        except:
            pass

        # 获取页面标题
        result["title"] = page.title()

        # 优先从网络请求中找可访问的URL（douyinvod.com）
        for u in video_stream_urls:
            if 'douyinvod.com' in u or 'ixigua.com' in u:
                result["video_url"] = u
                break
        
        # 其次从网络请求中找play URL
        if not result["video_url"]:
            for u in video_stream_urls:
                if 'play' in u and 'aweme/v1/play' in u:
                    result["video_url"] = u
                    break
        
        # 最后才从video标签取（可能为blob URL）
        if not result["video_url"]:
            video_src = page.evaluate('''() => {
                const v = document.querySelector('video');
                return v ? (v.currentSrc || v.src) : '';
            }''')
            if video_src and video_src not in ('', 'about:blank') and not video_src.startswith('blob:'):
                result["video_url"] = video_src
        
        if not result["video_url"] and video_stream_urls:
            result["video_url"] = video_stream_urls[0]

        # 去水印：playwm -> play
        if result["video_url"]:
            result["video_url"] = result["video_url"].replace('playwm', 'play')

        browser.close()

    # 追踪重定向获取最终可访问URL
    if result["video_url"] and not result["video_url"].startswith('http'):
        result["video_url"] = ""
    if result["video_url"]:
        try:
            r = requests.get(result["video_url"], headers=HEADERS, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                result["video_url"] = r.url
            else:
                result["video_url"] = ""
        except:
            result["video_url"] = ""

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "缺少参数"}))
        sys.exit(1)

    url = sys.argv[1]
    try:
        info = fetch_douyin_video(url)
        print(info["video_url"])
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))