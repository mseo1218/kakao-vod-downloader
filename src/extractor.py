import time
import re
import os
from playwright.sync_api import sync_playwright
import config


class VideoExtractor:
    def __init__(self):
        self.pw = None
        self.context = None
        self.job_count = 0
        self._initialize_browser()

    def _initialize_browser(self):
        if self.pw:
            try:
                self.pw.stop()
            except:
                pass

        self.pw = sync_playwright().start()

        launch_options = {
            "user_data_dir": os.path.join(config.BASE_DIR, "data", "user_data"),
            "headless": config.HEADLESS_MODE,
            "user_agent": config.USER_AGENT,
            "viewport": {'width': 1280, 'height': 720},
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--mute-audio",
                "--disable-blink-features=AutomationControlled"
            ]
        }

        if config.CHROME_EXE_PATH:
            launch_options["executable_path"] = config.CHROME_EXE_PATH

        try:
            self.context = self.pw.chromium.launch_persistent_context(**launch_options)
            # print(f"\n준비 완료 (Headless: {config.HEADLESS_MODE})")
        except Exception as e:
            print(f"\n[!] 브라우저 실행 실패: {e}")

    def extract_mp4(self, url, initial_title):
        page = None
        try:
            try:
                page = self.context.new_page()
            except:
                # 🔥 컨텍스트 문제 시 복구
                self._initialize_browser()
                page = self.context.new_page()

            detected_urls = []
            final_title = initial_title

            # ✅ 🔥 기존 패킷 감지 로직 그대로 유지
            def handle_request(request):
                u = request.url

                if "mkamp.kakao.com" in u or "log" in u:
                    return

                # 1순위 clip.mp4
                if "clip.mp4" in u and "play.kakao.com" in u and "SEEK" not in u:
                    target_u = u
                    if "cp=http" in u:
                        match = re.search(r"cp=(https?%3A%2F%2F.+?\.mp4)", u)
                        if match:
                            decoded_u = match.group(1).replace("%3A", ":").replace("%2F", "/")
                            target_u = decoded_u.strip().rstrip('.')

                    if target_u not in detected_urls:
                        detected_urls.insert(0, target_u)
                    return

                # 2순위 일반 mp4
                if "play.kakao.com" in u and ".mp4" in u:
                    if any(q in u.upper() for q in ["1080", "720", "720P"]):
                        if u not in detected_urls:
                            detected_urls.append(u)

            page.on("request", handle_request)

            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            try:
                page.wait_for_selector("#playerVod", timeout=10000)
                page.mouse.click(640, 360)
                time.sleep(1.0)
            except:
                pass

            # 🔥 화질 변경 로직 유지
            try:
                player_frame = page.frame(name="player_iframe") or page.frame(url=re.compile(r"tv.kakao.com/embed"))

                if player_frame:
                    video_container = player_frame.locator("#player")
                    video_container.hover()
                    video_container.click(force=True)
                    time.sleep(1.0)

                    setting_btn = player_frame.locator("#settingBtn")
                    setting_btn.wait_for(state="visible", timeout=5000)
                    setting_btn.click(force=True)

                    quality_menu = player_frame.locator("button.btn_quality")
                    quality_menu.wait_for(state="visible", timeout=3000)
                    quality_menu.click(force=True)
                    time.sleep(1.0)

                    target_1080 = player_frame.locator('button[data-profile="HIGH4"]').first
                    target_720 = player_frame.locator('button[data-profile="HIGH"]').first

                    if target_1080.count() > 0:
                        target_1080.click(force=True)
                    elif target_720.count() > 0:
                        target_720.click(force=True)

                    time.sleep(4)
            except Exception as fe:
                print(f"\n[!] 화질 변경 오류: {fe}")

            # 🔥 패킷 대기
            for _ in range(30):
                if detected_urls:
                    break
                time.sleep(0.5)

            # 🔥 선택 로직 그대로 유지
            best_url = None
            if detected_urls:
                for q in ["1080", "720"]:
                    matches = [u for u in detected_urls if q in u.upper()]
                    if matches:
                        best_url = matches[0]
                        break

                if not best_url:
                    best_url = detected_urls[0]

            return best_url, final_title

        except Exception as e:
            print(f"\n[Extractor] 에러 발생: {e}")
            return None, initial_title

        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

            # ✅ 🔥 핵심 개선: 주기적 브라우저 리셋
            self.job_count += 1
            if self.job_count % 20 == 0:
                print(f"\n[Extractor] 브라우저 리셋")
                self._initialize_browser()