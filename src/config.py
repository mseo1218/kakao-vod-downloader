import os

# --- 기본 경로 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

LINK_FILE = os.path.join(DATA_DIR, "links.txt")
TITLE_FILE = os.path.join(DATA_DIR, "titles.txt")
DONE_FILE = os.path.join(DATA_DIR, "done.txt")
FAILED_FILE = os.path.join(DATA_DIR, "failed.txt")

# 다운로드 저장 경로
DOWNLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "videos"))

# --- 성능 및 작업 설정 ---
EXTRACTOR_WORKER_COUNT = 1 
DOWNLOAD_WORKER_COUNT = 8

# --- 브라우저 설정 ---
HEADLESS_MODE = True
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- 환경 초기화 함수 ---
def init_directories():
    """필요한 폴더와 파일이 없으면 생성"""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    for f in [LINK_FILE, DATA_DIR, TITLE_FILE, DONE_FILE, FAILED_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as file:
                pass