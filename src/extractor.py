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
            print(f"[*] 전용 브라우저 사용: {config.CHROME_EXE_PATH}")
        else:
            print("[*] 시스템 브라우저 사용 (bin 폴더 미발견)")

        try:
            self.context = self.pw.chromium.launch_persistent_context(**launch_options)
            print(f"[Extractor] 준비 완료 (Headless: {config.HEADLESS_MODE})")
        except Exception as e:
            print(f"[!] 브라우저 실행 실패: {e}")

    def extract_mp4(self, url, initial_title):
        page = None
        try:
            try:
                page = self.context.new_page()
            except:
                self._initialize_browser()
                page = self.context.new_page()

            # 감지된 URL들을 저장 (0번 인덱스에 가까울수록 높은 우선순위)
            detected_urls = []
            final_title = initial_title

            # 네트워크 요청 가로채기 (우선순위 로직 적용)
            def handle_request(request):
                u = request.url
                
                # 0. 불필요한 로그 패킷 필터링
                if "mkamp.kakao.com" in u or "log" in u: return
                
                # 1. [1순위] clip.mp4 패킷 감지
                if "clip.mp4" in u and "play.kakao.com" in u and "SEEK" not in u:
                    target_u = u
                    if "cp=http" in u:
                        match = re.search(r"cp=(https?%3A%2F%2F.+?\.mp4)", u)
                        if match:
                            decoded_u = match.group(1).replace("%3A", ":").replace("%2F", "/")
                            target_u = decoded_u.strip().rstrip('.')
                    
                    if target_u not in detected_urls:
                        # 최우선 순위이므로 리스트 맨 앞에 삽입
                        detected_urls.insert(0, target_u)
                        print(f"[⭐ 1순위 감지] clip.mp4 패킷: {target_u[:60]}...")
                    return

                # 2. [2순위] 일반 mp4 패킷 감지 (사용자 예시 패턴)
                # 'play.kakao.com' 도메인을 포함하고 확장자가 .mp4이며 고화질 키워드가 있는 경우
                if "play.kakao.com" in u and ".mp4" in u:
                    if any(q in u.upper() for q in ["1080", "720", "720P"]):
                        if u not in detected_urls:
                            # 차선책이므로 리스트 뒤에 추가
                            detected_urls.append(u)
                            print(f"[✅ 2순위 감지] 일반 mp4 패킷: {u[:60]}...")

            page.on("request", handle_request)
            
            # 1. 페이지 이동
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            # 2. 플레이어 영역 대기 및 클릭
            try:
                page.wait_for_selector("#playerVod", timeout=10000)
                page.mouse.click(640, 360)
                time.sleep(1.0)
            except: 
                pass

            # 3. Iframe 내부 화질 변경 로직
            try:
                print("[Extractor] 플레이어 프레임 탐색 중...")
                player_frame = page.frame(name="player_iframe") or page.frame(url=re.compile(r"tv.kakao.com/embed"))
                
                if player_frame:
                    # 컨트롤바 활성화
                    video_container = player_frame.locator("#player")
                    video_container.hover()
                    video_container.click(force=True)
                    time.sleep(1.0) 

                    # 설정 -> 화질변경 메뉴 진입
                    setting_btn = player_frame.locator("#settingBtn")
                    setting_btn.wait_for(state="visible", timeout=5000)
                    setting_btn.click(force=True)

                    quality_menu = player_frame.locator("button.btn_quality")
                    quality_menu.wait_for(state="visible", timeout=3000)
                    quality_menu.click(force=True)
                    time.sleep(1.0)

                    # 화질 선택 (1080p 우선 -> 720p 차선)
                    target_1080 = player_frame.locator('button[data-profile="HIGH4"]').first
                    target_720 = player_frame.locator('button[data-profile="HIGH"]').first 
                    
                    if target_1080.count() > 0:
                        target_1080.click(force=True)
                        print("[Extractor] 1080p(HIGH4)로 화질 변경 클릭")
                    elif target_720.count() > 0:
                        target_720.click(force=True)
                        print("[Extractor] 1080p 없음 -> 720p(HIGH)로 화질 변경 클릭")
                    else:
                        print("[Extractor] 고화질 옵션 버튼을 찾지 못함")
                        setting_btn.click(force=True) 

                    # 화질 변경 후 새 패킷이 발생할 때까지 대기
                    time.sleep(5.0) 
            except Exception as fe:
                print(f"[!] 화질 변경 과정 오류: {fe}")

            # 4. 패킷 수집 대기 루프
            print("[Extractor] 최종 패킷 대기 중...")
            for i in range(30):
                # 리스트에 하나라도 잡혔으면 성공
                if detected_urls:
                    break
                time.sleep(0.5)

            # 5. 최적의 화질 선택 로직
            best_url = None
            if detected_urls:
                # 1순위(clip.mp4)가 있다면 insert(0)에 의해 맨 앞에 있을 것임
                # 고화질 키워드 순으로 필터링
                for q in ["1080", "720"]:
                    matches = [u for u in detected_urls if q in u.upper()]
                    if matches:
                        # clip.mp4가 섞여있다면 그중 가장 먼저 잡힌 것(인덱스 앞쪽)을 선택
                        best_url = matches[0]
                        break
                
                if not best_url:
                    best_url = detected_urls[0]

            return best_url, final_title

        except Exception as e:
            print(f"[Extractor] 에러 발생: {e}")
            return None, initial_title
        finally:
            if page:
                try: page.close()
                except: pass