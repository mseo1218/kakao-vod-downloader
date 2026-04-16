import threading
import queue
import time
import os
import sys
import re

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
    
import config
from parser import extract_video_title
from extractor import VideoExtractor
from downloader import download_video

# --- 큐 및 전역 변수 ---
extract_queue = queue.Queue()
download_queue = queue.Queue()
done_set = set()
active_downloads = 0
lock = threading.Lock()

def load_done():
    loaded_set = set()
    if os.path.exists(config.DONE_FILE):
        with open(config.DONE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    loaded_set.add(line.strip())
    return loaded_set

# --- Worker 함수들 (기존과 동일) ---
def title_worker():
    global done_set
    processed_in_session = set()
    while True:
        done_set.update(load_done())
        if os.path.exists(config.LINK_FILE):
            with open(config.LINK_FILE, "r", encoding="utf-8-sig") as f:
                urls = [l.strip() for l in f if l.strip()]
            for url in urls:
                if url not in done_set and url not in processed_in_session:
                    title = extract_video_title(url)
                    if title:
                        with lock:
                            with open(config.TITLE_FILE, "a", encoding="utf-8") as tf:
                                tf.write(f"{title} | {url}\n")
                        safe_title = re.sub(r'[\\/:*?"<>|.]', "_", title).strip()
                        final_path = os.path.join(config.DOWNLOAD_DIR, f"{safe_title}.mp4")
                        if os.path.exists(final_path):
                            print(f"⏩ [이미 존재] 스킵: {title}")
                            with lock:
                                with open(config.DONE_FILE, "a", encoding="utf-8") as f:
                                    f.write(url + "\n")
                            done_set.add(url)
                            continue
                        print(f"📝 [타이틀 확보] {title}")
                        extract_queue.put((url, title))
                        processed_in_session.add(url)
        time.sleep(10)

def extractor_worker():
    extractor = VideoExtractor()
    while True:
        url, title = extract_queue.get()
        if url in done_set:
            extract_queue.task_done()
            continue
        print(f"📡 [추출 시작] {title[:20]}...")
        mp4_url, final_title = extractor.extract_mp4(url, title)
        if mp4_url:
            download_queue.put((mp4_url, final_title, url))
        else:
            print(f"❌ [에러] 주소 추출 실패: {title}")
        extract_queue.task_done()

def downloader_worker():
    global active_downloads
    retry_count = {}
    while True:
        mp4_url, title, original_url = download_queue.get()
        with lock: active_downloads += 1
        print(f"📥 [다운 시작] {title}.mp4 (현재 진행 중: {active_downloads}건)")
        if download_video(mp4_url, title, config.DOWNLOAD_DIR):
            print(f"✅ [다운 완료] {title}")
            with lock:
                with open(config.DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(original_url + "\n")
                done_set.add(original_url)
        else:
            current_retry = retry_count.get(original_url, 0)
            if current_retry < 2:
                retry_count[original_url] = current_retry + 1
                print(f"⚠️ [재시도] {title} (시도 {current_retry + 1}/2)...")
                download_queue.put((mp4_url, title, original_url))
            else:
                print(f"❌ [최종 실패] {title}")
                with lock:
                    with open(config.FAILED_FILE, "a", encoding="utf-8") as f:
                        f.write(original_url + "\n")
        with lock: active_downloads -= 1
        download_queue.task_done()

# --- 메인 실행 로직 ---
def main():
    config.init_directories()
    global done_set
    done_set = load_done()

    # [핵심 수정] 로그인 모드 (Headless False) 처리
    if not config.HEADLESS_MODE:
        print("\n" + "="*60)
        print("🔑 [로그인/인증 모드 활성화]")
        print("설명: 브라우저가 직접 나타납니다. 카카오TV 로그인을 완료해주세요.")
        print("주의: 이 모드에서는 자동 다운로드가 진행되지 않습니다.")
        print("="*60 + "\n")

        extractor = VideoExtractor()
        # 로그인 페이지로 직접 이동
        login_page = extractor.context.new_page()
        print("[*] 카카오 로그인 페이지로 이동합니다...")
        login_page.goto("https://accounts.kakao.com/login/?continue=https%3A%2F%2Ftv.kakao.com%2F")
        
        print("\n[!] 로그인을 완료한 후, 터미널에서 Enter를 누르면 프로그램이 종료됩니다.")
        print("[!] 종료 후 settings.json에서 headless를 true로 바꾸고 다시 실행하세요.")
        input(">>> 로그인을 마쳤으면 Enter를 누르세요...")
        
        # 브라우저 컨텍스트 저장 및 종료 (이때 user_data에 세션이 남음)
        extractor.pw.stop()
        print("[*] 세션 정보가 저장되었습니다. 프로그램을 종료합니다.")
        return # 워커들을 시작하지 않고 메인 함수 종료

    # 다운로드 모드 (Headless True) 실행
    print("="*50)
    print(f"🚀 다운로드 시스템 가동 (추출:1 / 다운로드:{config.DOWNLOAD_WORKER_COUNT})")
    print("="*50)

    threading.Thread(target=title_worker, daemon=True).start()
    threading.Thread(target=extractor_worker, daemon=True).start()
    for _ in range(config.DOWNLOAD_WORKER_COUNT):
        threading.Thread(target=downloader_worker, daemon=True).start()

    was_busy = False
    try:
        while True:
            e_size = extract_queue.qsize()
            d_size = download_queue.qsize()
            if e_size == 0 and d_size == 0 and active_downloads == 0:
                if was_busy:
                    print("\n✨ [알림] 모든 작업이 완료되었습니다!")
                    was_busy = False
            else:
                print(f"📊 [현황] 추출대기: {e_size} | 다운대기: {d_size} | 진행중: {active_downloads}   ", end="\r")
                was_busy = True
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nBye!")
        os._exit(0)

if __name__ == "__main__":
    main()