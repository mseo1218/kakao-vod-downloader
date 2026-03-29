import time
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
import config

class VideoExtractor:
    def __init__(self):
        self.pw = None
        self.context = None
        self._initialize_browser()

    def _initialize_browser(self):
            # 1. 기존 Playwright 인스턴스 정리
            if self.pw:
                try:
                    self.pw.stop()
                except:
                    pass
            
            self.pw = sync_playwright().start()

            # 2. 브라우저 실행 옵션 설정
            launch_options = {
                "user_data_dir": os.path.join(config.BASE_DIR, "src", "user_data"),
                "headless": config.HEADLESS_MODE,
                "user_agent": config.USER_AGENT,
                "viewport": {'width': 1280, 'height': 720},
                "args": ["--no-sandbox", "--disable-setuid-sandbox", "--mute-audio", "--disable-blink-features=AutomationControlled"]
            }

            # 3. bin 폴더에 전용 크롬이 있을 때만 경로 추가
            # config.CHROME_EXE_PATH가 None이면 Playwright가 시스템에 설치된 브라우저를 알아서 찾습니다.
            if config.CHROME_EXE_PATH:
                launch_options["executable_path"] = config.CHROME_EXE_PATH
                print(f"[*] 전용 브라우저 사용: {config.CHROME_EXE_PATH}")
            else:
                print("[*] 시스템 브라우저 사용 (bin 폴더 미발견)")

            # 4. 설정된 옵션으로 브라우저 실행 (**는 딕셔너리를 인자로 풀어주는 문법)
            try:
                self.context = self.pw.chromium.launch_persistent_context(**launch_options)
                print(f"[Extractor] 준비 완료 (Headless: {config.HEADLESS_MODE})")
            except Exception as e:
                print(f"[!] 브라우저 실행 실패: {e}")
                # 만약 실행 실패 시 추가적인 예외 처리가 필요할 수 있습니다.

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