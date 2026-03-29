import sys
import os
import shutil
import json

# --- 1. 기본 베이스 경로 설정 ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 2. 주요 폴더 및 파일 경로 ---
DATA_DIR = os.path.join(BASE_DIR, "data")
BIN_PATH = os.path.join(BASE_DIR, "bin")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "videos")

LINK_FILE = os.path.join(DATA_DIR, "links.txt")
TITLE_FILE = os.path.join(DATA_DIR, "titles.txt")
DONE_FILE = os.path.join(DATA_DIR, "done.txt")
FAILED_FILE = os.path.join(DATA_DIR, "failed.txt")

# --- 3. 바이너리 경로 동적 할당 ---

# FFmpeg 설정: bin에 없으면 시스템 환경변수(PATH)의 ffmpeg 사용
FFMPEG_EXE = os.path.join(BIN_PATH, "ffmpeg.exe")
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"  # 시스템 환경변수 이용

# Playwright/Chrome 설정
internal_chrome = os.path.join(
    BIN_PATH, "playwright", "chromium-1208", "chrome-win64", "chrome.exe"
)

if os.path.exists(internal_chrome):
    # 빌드된 환경: bin 내부의 브라우저 사용
    CHROME_EXE_PATH = internal_chrome
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(BIN_PATH, "playwright")
    IS_STRIPPED_MODE = False
else:
    # 스크립트 실행 환경: 시스템에 설치된 playwright 이용 (None 전달 시 자동 탐색)
    CHROME_EXE_PATH = None 
    IS_STRIPPED_MODE = True
    # 여기서 os.environ["PLAYWRIGHT_BROWSERS_PATH"]는 건드리지 않음 (기본값 유지)

# --- 4. 워커 및 브라우저 설정 ---
EXTRACTOR_WORKER_COUNT = 1 
DOWNLOAD_WORKER_COUNT = 16
HEADLESS_MODE = True
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

EXTERNAL_CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")

def load_external_settings():
    """외부 settings.json 파일이 있으면 설정을 덮어씁니다."""
    global EXTRACTOR_WORKER_COUNT, DOWNLOAD_WORKER_COUNT, HEADLESS_MODE
    
    if os.path.exists(EXTERNAL_CONFIG_FILE):
        try:
            with open(EXTERNAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                EXTRACTOR_WORKER_COUNT = user_settings.get("extractor_workers", EXTRACTOR_WORKER_COUNT)
                DOWNLOAD_WORKER_COUNT = user_settings.get("download_workers", DOWNLOAD_WORKER_COUNT)
                HEADLESS_MODE = user_settings.get("headless", HEADLESS_MODE)
                print(f"[*] 외부 설정 로드 완료: {EXTERNAL_CONFIG_FILE}")
        except Exception as e:
            print(f"[!] 설정 파일 읽기 실패 (기본값 사용): {e}")
    else:
        # 파일이 없으면 기본값으로 하나 만들어줍니다 (사용자 편의용)
        default_settings = {
            "extractor_workers": EXTRACTOR_WORKER_COUNT,
            "download_workers": DOWNLOAD_WORKER_COUNT,
            "headless": HEADLESS_MODE,
            "_comment": "설정 변경 후 프로그램을 재시작하세요."
        }
        try:
            with open(EXTERNAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=4, ensure_ascii=False)
        except: pass
        
# --- 5. 환경 초기화 ---
def init_directories():
    load_external_settings()
    
    for d in [DATA_DIR, DOWNLOAD_DIR]:
        os.makedirs(d, exist_ok=True)
    
    for f in [LINK_FILE, TITLE_FILE, DONE_FILE, FAILED_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as file: pass

    if IS_STRIPPED_MODE:
        print("[!] 알림: bin 폴더가 없어 시스템 환경 브라우저를 사용합니다.")