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

            detected_urls = []
            final_title = initial_title

            # 네트워크 요청 가로채기
            def handle_request(request):
                u = request.url
                if "mkamp.kakao.com" in u or "log" in u: return
                
                if "clip.mp4" in u and "play.kakao.com" in u and "SEEK" not in u:
                    if "cp=http" in u:
                        match = re.search(r"cp=(https?%3A%2F%2F.+?\.mp4)", u)
                        if match:
                            decoded_u = match.group(1).replace("%3A", ":").replace("%2F", "/")
                            detected_u_final = decoded_u.strip().rstrip('.')
                            if detected_u_final not in detected_urls:
                                detected_urls.append(detected_u_final)
                            return
                    
                    final_u = u.strip().rstrip('.')
                    if final_u not in detected_urls:
                        detected_urls.append(final_u)

            page.on("request", handle_request)
            
            # 1. 페이지 이동
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            # 2. 플레이어 영역 대기 및 클릭 (재생/일시정지 유도)
            try:
                page.wait_for_selector("#playerVod", timeout=10000)
                page.mouse.click(640, 360)
                time.sleep(1.0)
            except: 
                pass

            # 3. [핵심] Iframe 관통 화질 변경 로직
            try:
                print("[Extractor] 플레이어 프레임 탐색 중...")
                
                # 'player_iframe' 아이디를 가진 프레임을 직접 타겟팅
                player_frame = page.frame(name="player_iframe") or page.frame(url=re.compile(r"tv.kakao.com/embed"))
                
                if player_frame:
                    print("[Extractor] 플레이어 프레임 진입 성공.")
                    
                    # 3-1. 영상 컨트롤바 활성화 (마우스 오버 및 클릭)
                    video_container = player_frame.locator("#player")
                    video_container.hover()
                    video_container.click(force=True)
                    time.sleep(1.0) 

                    # 3-2. 설정 버튼 (#settingBtn) 클릭
                    setting_btn = player_frame.locator("#settingBtn")
                    setting_btn.wait_for(state="visible", timeout=5000)
                    setting_btn.click(force=True)
                    print("[Extractor] 설정 메뉴 열림.")

                    # 3-3. '화질변경' 버튼 (.btn_quality) 클릭
                    quality_menu = player_frame.locator("button.btn_quality")
                    quality_menu.wait_for(state="visible", timeout=3000)
                    quality_menu.click(force=True)
                    time.sleep(1.0)

                    # 3-4. '1080 HD' 버튼 타격 (data-profile="HIGH4" 사용)
                    # 이미지 분석 결과 1080p는 HIGH4 프로필을 가집니다.
                    target_1080 = player_frame.locator('button[data-profile="HIGH4"], button.link_dp:has-text("1080")').first
                    
                    if target_1080.count() > 0:
                        target_1080.click(force=True)
                        print("[Extractor] 1080p 변경 완료! 패킷을 기다립니다.")
                        time.sleep(4.0) # 화질 전환 대기시간 확보
                    else:
                        print("[Extractor] 1080p 옵션을 찾지 못했습니다.")
                        setting_btn.click(force=True) # 메뉴 닫기
                else:
                    print("[!] 플레이어 프레임을 찾지 못했습니다.")

            except Exception as fe:
                print(f"[!] 화질 변경 로직 실패: {fe}")

            # 4. 패킷 수집 대기 루프
            for i in range(30):
                # 1080이 포함된 URL이 잡혔는지 우선 확인
                if any("1080" in u for u in detected_urls):
                    print("[Extractor] 1080p URL 감지됨!")
                    break
                
                if i % 10 == 0: 
                    page.mouse.click(640, 360)
                time.sleep(0.5)

            # 5. 최적의 화질 선택
            best_url = None
            if detected_urls:
                priority_keywords = ["1080", "720P"]
                
                for q in priority_keywords:
                    matches = [u for u in detected_urls if q in u.upper()]
                    if matches:
                        best_url = matches[0]
                        print(f"[Extractor] 최적 화질 매칭 성공: {q}")
                        break
                        
                if not best_url:
                    best_url = detected_urls[-1]
                    print("[Extractor] 우선순위 매칭 실패, 발견된 마지막 주소 사용")

            return best_url, final_title

        except Exception as e:
            print(f"[Extractor] 에러 발생: {e}")
            return None, initial_title
        finally:
            if page:
                try: 
                    page.close()
                except: 
                    pass