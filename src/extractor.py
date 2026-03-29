import time
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from . import config

class VideoExtractor:
    def __init__(self):
        self.pw = None
        self.context = None
        self._initialize_browser()

    def _initialize_browser(self):
        if self.pw:
            try: self.pw.stop()
            except: pass
        self.pw = sync_playwright().start()
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        user_data_path = os.path.join(base_path, "user_data")
        has_session = os.path.exists(os.path.join(user_data_path, "Default"))
        current_headless = config.HEADLESS_MODE
        
        self.context = self.pw.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            headless=current_headless,
            user_agent=config.USER_AGENT,
            viewport={'width': 1280, 'height': 720},
            args=["--no-sandbox", "--disable-setuid-sandbox", "--mute-audio"]
        )
        print(f"[Extractor] 준비 완료 (Headless: {current_headless})")

    def extract_mp4(self, url, initial_title):
        page = None
        try:
            try:
                page = self.context.new_page()
            except:
                self._initialize_browser()
                page = self.context.new_page()

            detected_urls = []
            final_title = initial_title

            def handle_request(request):
                u = request.url
                if "mkamp.kakao.com" in u or "log" in u: return
                
                if "clip.mp4" in u and "play.kakao.com" in u and "SEEK" not in u:
                    if "cp=http" in u:
                        match = re.search(r"cp=(https?%3A%2F%2F.+?\.mp4)", u)
                        if match:
                            decoded_u = match.group(1).replace("%3A", ":").replace("%2F", "/")
                            detected_urls.append(decoded_u)
                            return
                    detected_urls.append(u.strip().rstrip('.'))

            page.on("request", handle_request)
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            try:
                page.wait_for_selector("#playerVod", timeout=10000)
            except: pass

            page.mouse.click(640, 360)
            time.sleep(1.0)
            
            for i in range(30):
                if detected_urls:
                    time.sleep(1.5)
                    break
                if i % 10 == 0: page.mouse.click(640, 360)
                time.sleep(0.5)

            best_url = None
            if detected_urls:
                for q in ["1080P", "720P", "HIGH"]:
                    matches = [u for u in detected_urls if q in u]
                    if matches:
                        best_url = matches[-1]
                        print(f"[Extractor] 영상 화질: {q}")
                        break
                if not best_url:
                    best_url = detected_urls[-1]
            
            if best_url:
                best_url = best_url.strip().rstrip('.')

            return best_url, final_title

        except Exception as e:
            print(f"[Extractor] 에러 발생: {e}")
            return None, initial_title
        finally:
            if page:
                try: page.close()
                except: pass