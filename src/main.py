import threading
import queue
import time
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
    
import config
import parser
from parser import extract_video_title
from extractor import VideoExtractor
from downloader import download_video

# --- 큐 설정 ---
extract_queue = queue.Queue()  # 타이틀 -> 영상링크용
download_queue = queue.Queue() # 영상링크 -> 실제파일용


done_set = set()
active_downloads = 0  # 현재 실제 다운로드 중인 작업 수
lock = threading.Lock()

def load_done():
    """done.txt를 읽어 최신 완료 목록을 반환"""
    loaded_set = set()
    if os.path.exists(config.DONE_FILE):
        with open(config.DONE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    loaded_set.add(line.strip())
    return loaded_set

# --- [Worker 1] 링크 감시 및 타이틀 정제 ---
def title_worker():
    global done_set
    processed_in_session = set()
    
    while True:
        # 1. 매 루프마다 done_set 최신화
        done_set.update(load_done())
        
        if os.path.exists(config.LINK_FILE):
            with open(config.LINK_FILE, "r", encoding="utf-8-sig") as f:
                urls = [l.strip() for l in f if l.strip()]
            
            for url in urls:
                if url not in done_set and url not in processed_in_session:
                    title = extract_video_title(url)
                    if title:
                        # 2. titles.txt에 로그 기록
                        with lock:
                            with open(config.TITLE_FILE, "a", encoding="utf-8") as tf:
                                tf.write(f"{title} | {url}\n")

                        # 3. 큐에 넣기 전 실제 파일 존재 여부 최종 확인
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
                    else:
                        print(f"❌ [에러] 타이틀 획득 실패: {url}")
        time.sleep(10)

# --- [Worker 2] 영상 주소 추출 ---
def extractor_worker():
    extractor = VideoExtractor()
    while True:
        url, title = extract_queue.get()
        
        # 브라우저 실행 전 스킵 (안전장치)
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

# --- [Worker 3] 실제 다운로드 ---
def downloader_worker():
    global active_downloads # 카운터 참조
    while True:
        mp4_url, title, original_url = download_queue.get()
        
        # 다운로드 시작: 카운터 증가
        with lock:
            active_downloads += 1
            
        print(f"📥 [다운 시작] {title}.mp4 (현재 진행 중: {active_downloads}건)")
        
        try:
            if download_video(mp4_url, title, config.DOWNLOAD_DIR):
                print(f"✅ [다운 완료] {title}")
                with lock:
                    with open(config.DONE_FILE, "a", encoding="utf-8") as f:
                        f.write(original_url + "\n")
                    done_set.add(original_url)
            else:
                print(f"❌ [에러] 다운로드 실패: {title}")
                with lock:
                    with open(config.FAILED_FILE, "a", encoding="utf-8") as f:
                        f.write(original_url + "\n")
        finally:
            # 다운로드 종료(성공/실패 무관): 카운터 감소 및 task_done
            with lock:
                active_downloads -= 1
            download_queue.task_done()

# --- 메인 실행 ---
def main():
    # 환경 초기화 (폴더/파일 자동 생성)
    config.init_directories()
    global done_set
    done_set = load_done()
    
    print("="*50)
    print(f"🚀 링크 추출 워커 & 다운로드 워커 시작(추출:1 / 다운로드:{config.DOWNLOAD_WORKER_COUNT})")
    print("="*50)
    print("/data/links.txt에 다운받고 싶은 영상 링크를 한줄씩 추가하세요")
    print("종료: Ctrl + C")
    
    threading.Thread(target=title_worker, daemon=True).start()
    threading.Thread(target=extractor_worker, daemon=True).start()
    
    for i in range(config.DOWNLOAD_WORKER_COUNT):
        threading.Thread(target=downloader_worker, daemon=True).start()

    # --- 상태 모니터링 루프 ---
    was_busy = False
    try:
        while True:
            e_size = extract_queue.qsize()
            d_size = download_queue.qsize()
            
            # 모든 큐가 비어있고, 실제 진행 중인 다운로드도 없을 때
            if e_size == 0 and d_size == 0 and active_downloads == 0:
                if was_busy:
                    print("\n✨ [알림] 모든 작업(추출/다운로드)이 완전히 종료되었습니다!")
                    print("☕ [대기 중] 새 링크를 기다리는 중... (10초 주기 감시)")
                    was_busy = False
            else:
                # 진행 상황을 한 줄에 표시 (선택 사항)
                if e_size > 0 or d_size > 0 or active_downloads > 0:
                    print(f"📊 [현황] 추출대기: {e_size} | 다운대기: {d_size} | 진행중: {active_downloads}   ", end="\r")
                    was_busy = True
                
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n종료합니다.")

if __name__ == "__main__":
    config.init_directories()
    main()