import threading
import queue
import time
import os
import sys

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path: sys.path.append(SRC_DIR)
    
import config
from parser import extract_video_title
from extractor import VideoExtractor
from downloader import download_video

# --- 글로벌 변수 ---
extract_queue = None
download_queue = None
done_set = set()
active_downloads = 0
pending_links_count = 0
completed_count = 0
lock = threading.Lock()

# 재시도 횟수 관리용 (메모리 누수 방지를 위해 수동 관리 지양, 큐에 count 포함)
# 형식: (mp4_url, title, original_url, retry_count)

def load_done():
    if os.path.exists(config.DONE_FILE):
        with open(config.DONE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def title_worker():
    global done_set, pending_links_count
    processed_in_session = set()
    
    while True:
        done_set = load_done()
        if os.path.exists(config.LINK_FILE):
            try:
                with open(config.LINK_FILE, "r", encoding="utf-8-sig") as f:
                    all_urls = list(dict.fromkeys(line.strip() for line in f if line.strip()))

                new_urls = [u for u in all_urls if u not in done_set and u not in processed_in_session]
                
                if new_urls:
                    with lock:
                        pending_links_count += len(new_urls)

                for url in new_urls:
                    while extract_queue.full():
                        time.sleep(2)

                    title = extract_video_title(url)
                    if title:
                        with lock:
                            with open(config.TITLE_FILE, "a", encoding="utf-8") as tf:
                                tf.write(f"{title} | {url}\n")
                        
                        # retry_count 초기값 0 추가
                        extract_queue.put((url, title))
                        processed_in_session.add(url)
                        
                        with lock:
                            pending_links_count = max(0, pending_links_count - 1)
            except Exception as e:
                pass # 파일 읽기 에러 등 예외 처리
        time.sleep(10)

def extractor_worker():
    extractor = VideoExtractor()
    while True:
        url, title = extract_queue.get()
        while download_queue.full():
            time.sleep(3)

        if url in load_done():
            extract_queue.task_done()
            continue

        mp4_url, final_title = extractor.extract_mp4(url, title)
        if mp4_url:
            # (mp4_url, title, original_url, retry_count) 형태로 전달
            download_queue.put((mp4_url, final_title, url, 0))
        else:
            sys.stdout.write("\r" + " " * 120 + f"\r❌ [추출 실패] {title[:30]}\n")
            sys.stdout.flush()
        extract_queue.task_done()

def downloader_worker():
    global active_downloads, completed_count
    while True:
        # 큐에서 데이터를 가져옴
        mp4_url, title, original_url, retry_count = download_queue.get()
        with lock: active_downloads += 1
        
        sys.stdout.write("\r" + " " * 120 + f"\r📥 [다운 시작] {title[:40]}...\n")
        sys.stdout.flush()
        
        # [핵심 수정] download_video 내부에서 반드시 타임아웃 처리가 되어야 함
        if download_video(mp4_url, title, config.DOWNLOAD_DIR):
            sys.stdout.write("\r" + " " * 120 + f"\r✅ [다운 완료] {title[:40]}\n")
            sys.stdout.flush()
            with lock:
                with open(config.DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(original_url + "\n")
                done_set.add(original_url)
                completed_count += 1
        else:
            # [핵심 수정] 무한 재시도 방지 (최대 3회)
            if retry_count < 3:
                sys.stdout.write("\r" + " " * 120 + f"\r🔄 [재시도 {retry_count+1}/3] {title[:30]}\n")
                sys.stdout.flush()
                time.sleep(5) # 재시도 전 대기 시간
                download_queue.put((mp4_url, title, original_url, retry_count + 1))
            else:
                sys.stdout.write("\r" + " " * 120 + f"\r❌ [최종 실패] {title[:30]}\n")
                sys.stdout.flush()
                with lock:
                    if not os.path.exists(config.FAILED_FILE):
                        open(config.FAILED_FILE, 'w').close()
                    with open(config.FAILED_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{original_url}\n")
        
        with lock: active_downloads -= 1
        download_queue.task_done()

def main():
    global extract_queue, download_queue
    config.init_directories()
    
    limit_val = max(1, config.DOWNLOAD_WORKER_COUNT * 2)
    extract_queue = queue.Queue(maxsize=limit_val)
    download_queue = queue.Queue(maxsize=limit_val)

    if not config.HEADLESS_MODE:
        print("\n🔑 [로그인 세션 관리 모드]")
        # ... (기존 로그인 로직 동일)
        try:
            extractor = VideoExtractor() 
            page = extractor.context.new_page()
            login_url = "https://accounts.kakao.com/login/?continue=https%3A%2F%2Ftv.kakao.com%2F"
            page.goto(login_url)
            input("\n[WAIT] 로그인을 마치셨나요? Enter를 누르면 프로그램이 종료됩니다...")
        except Exception as e:
            print(f"❌ 오류: {e}")
        finally:
            if 'extractor' in locals():
                extractor.pw.stop()
        return

    print("="*50)
    print(f"🚀 가동 (추출:1 / 다운로드:{config.DOWNLOAD_WORKER_COUNT})")
    print("="*50)

    threading.Thread(target=title_worker, daemon=True).start()
    threading.Thread(target=extractor_worker, daemon=True).start()
    for _ in range(config.DOWNLOAD_WORKER_COUNT):
        threading.Thread(target=downloader_worker, daemon=True).start()

    was_busy = False
    last_status = ""
    try:
        while True:
            e_size = extract_queue.qsize()
            d_size = download_queue.qsize()
            with lock:
                is_empty = (e_size == 0 and d_size == 0 and active_downloads == 0 and pending_links_count == 0)
                if is_empty:
                    if was_busy:
                        sys.stdout.write("\r" + " " * 120 + "\r")
                        print(f"✨ [알림] 작업 완료! (세션 총 {completed_count}개)")
                        was_busy = False
                        last_status = ""
                else:
                    curr_status = f"📊 영상:{pending_links_count} | 추출대기:{e_size} | 다운대기:{d_size} | 다운중:{active_downloads} | 완료:{completed_count}"
                    if curr_status != last_status:
                        sys.stdout.write("\r" + " " * 120 + f"\r{curr_status}")
                        sys.stdout.flush()
                        last_status = curr_status
                    was_busy = True
            time.sleep(1)
    except KeyboardInterrupt:
        sys.stdout.write("\r" + " " * 120 + "\r")
        print(f"Bye!")
        os._exit(0)

if __name__ == "__main__":
    main()