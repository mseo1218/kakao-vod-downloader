import threading
import queue
import time
import os
import sys
import shutil


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

import config
from parser import extract_video_title
from extractor import VideoExtractor
from downloader import download_video

extract_queue = None
download_queue = None
done_set = set()
active_downloads = 0
pending_links_count = 0
completed_count = 0
failed_count = 0
lock = threading.Lock()


def load_done():
    if os.path.exists(config.DONE_FILE):
        with open(config.DONE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def title_worker():
    global done_set, pending_links_count
    processed_in_session = set()

    while True:
        with lock:
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
                    title = extract_video_title(url)
                    if not title:
                        continue

                    with lock:
                        with open(config.TITLE_FILE, "a", encoding="utf-8") as f:
                            f.write(f"{title}|{url}\n")

                    # ✅ blocking put (큐 자리 날 때까지 기다림)
                    extract_queue.put((url, title))

                    processed_in_session.add(url)

                    # ✅ 성공했을 때만 감소
                    with lock:
                        pending_links_count = max(0, pending_links_count - 1)

            except Exception:
                pass

        time.sleep(10)


def extractor_worker():
    global failed_count
    extractor = VideoExtractor()

    while True:
        try:
            url, title = extract_queue.get(timeout=10)
        except:
            continue

        if url in done_set:
            extract_queue.task_done()
            continue

        mp4_url, final_title = extractor.extract_mp4(url, title)

        if mp4_url:
            try:
                download_queue.put((mp4_url, final_title, url, 0))
            except:
                pass
        else:
            log(f"❌ [추출 실패] {title[:40]}")
            with lock:
                failed_count += 1
                with open(config.FAILED_FILE, "a", encoding="utf-8") as f:
                    f.write(url + "\n")
        extract_queue.task_done()


def downloader_worker():
    global active_downloads, completed_count, failed_count

    while True:
        try:
            mp4_url, title, original_url, retry_count = download_queue.get(timeout=10)
        except:
            continue

        with lock:
            active_downloads += 1

        log(f"📥 [다운 시작] {title[:40]}")

        success = download_video(mp4_url, title, config.DOWNLOAD_DIR)

        if success:
            log(f"✅ [완료] {title[:40]}")
            with lock:
                with open(config.DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(original_url + "\n")
                done_set.add(original_url)
                completed_count += 1
        else:
            if retry_count < 3:
                log(f"🔄 [재시도 {retry_count+1}/3] {title[:30]}")
                time.sleep(3)
                try:
                    download_queue.put((mp4_url, title, original_url, retry_count + 1))
                except:
                    pass
            else:
                log(f"❌ [최종 실패] {title[:30]}")
                with lock:
                    failed_count += 1
                    with open(config.FAILED_FILE, "a", encoding="utf-8") as f:
                        f.write(original_url + "\n")

        with lock:
            active_downloads -= 1

        download_queue.task_done()

def log(msg):
    # 터미널 너비 가져오기 (fallback 120)
    try:
        width = shutil.get_terminal_size().columns
    except:
        width = 120

    # 상태줄 지우기
    print("\r" + " " * width, end="")

    # 로그 출력
    print(f"\r{msg}")

def main():
    global extract_queue, download_queue

    config.init_directories()

    limit_val = max(10, config.DOWNLOAD_WORKER_COUNT * 2)
    extract_queue = queue.Queue(maxsize=limit_val)
    download_queue = queue.Queue(maxsize=limit_val)

    if not config.HEADLESS_MODE:
            print("\n🔑 [로그인 세션 관리 모드]")
            print("1. 브라우저가 열리면 로그인을 진행하세요.")
            print("2. 로그인 완료 후, 이 창에서 Enter를 누르면 세션이 저장되고 종료됩니다.")
            
            try:
                # VideoExtractor 인스턴스 생성 (내부에서 브라우저/컨텍스트 시작)
                extractor = VideoExtractor() 
                page = extractor.context.new_page()
                
                # 카카오 로그인 페이지로 이동
                login_url = "https://accounts.kakao.com/login/?continue=https%3A%2F%2Ftv.kakao.com%2F"
                page.goto(login_url)
                
                # 사용자가 Enter를 누를 때까지 프로세스를 점유하여 브라우저 유지
                input("\n[WAIT] 로그인을 마치셨나요? Enter를 누르면 프로그램이 종료됩니다...")
                
            except Exception as e:
                print(f"❌ 브라우저 실행 중 오류 발생: {e}")
            finally:
                if 'extractor' in locals():
                    extractor.pw.stop()
            return

    print("=" * 50)
    print(f"🚀 실행 (extract=1 / download={config.DOWNLOAD_WORKER_COUNT})")
    print("=" * 50)

    threading.Thread(target=title_worker, daemon=True).start()
    threading.Thread(target=extractor_worker, daemon=True).start()

    for _ in range(config.DOWNLOAD_WORKER_COUNT):
        threading.Thread(target=downloader_worker, daemon=True).start()

    last_len = 0  # ✅ 추가

    try:
        while True:
            with lock:
                status = (
                    f"📊 대기:{pending_links_count} | "
                    f"추출:{extract_queue.qsize()} | "
                    f"다운대기:{download_queue.qsize()} | "
                    f"다운중:{active_downloads} | "
                    f"완료:{completed_count} | "
                    f"실패:{failed_count}"
                )
            # ✅ 길이 보정 (잔여 문자 제거)
            pad = " " * max(0, last_len - len(status))

            # ✅ 한 줄 갱신 출력
            print(f"\r{status}{pad}", end="", flush=True)

            last_len = len(status)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n종료")
        os._exit(0)

if __name__ == "__main__":
    main()