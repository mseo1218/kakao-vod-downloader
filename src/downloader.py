import subprocess
import os
import re
import config   # ✅ 추가


def download_with_aria2(url, title, download_dir):
    safe_title = re.sub(r'[\\/:*?\"<>|]', "_", title).strip().replace(".", "_")
    final_path = os.path.join(download_dir, f"{safe_title}.mp4")

    if os.path.exists(final_path):
        return True

    cmd = [
        config.ARIA2_EXE,   # ✅ 핵심 수정
        "-x", "12",
        "-s", "12",
        "-k", "1M",
        "--file-allocation=none",
        "--summary-interval=0",
        "--console-log-level=error",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "--header=Referer: https://tv.kakao.com/",
        "--header=Origin: https://tv.kakao.com",
        "--user-agent=Mozilla/5.0",
        "-d", download_dir,
        "-o", f"{safe_title}.mp4",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600
        )
        return result.returncode == 0

    except FileNotFoundError:
        # ✅ aria2 아예 없는 경우
        print("[WARN] aria2c 실행파일 없음 → ffmpeg fallback")
        return False

    except subprocess.TimeoutExpired:
        return False


def download_with_ffmpeg(url, title, download_dir):
    safe_title = re.sub(r'[\\/:*?\"<>|]', "_", title).strip().replace(".", "_")
    final_path = os.path.join(download_dir, f"{safe_title}.mp4").replace("\\", "/")
    part_path = final_path + ".part"

    cmd = [
        config.FFMPEG_EXE,   # ✅ 핵심 수정
        "-y",
        "-loglevel", "error",
        "-rw_timeout", "15000000",
        "-timeout", "15000000",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-user_agent", "Mozilla/5.0",
        "-headers", "Referer: https://tv.kakao.com/\r\nOrigin: https://tv.kakao.com/",
        "-i", url,
        "-c", "copy",
        "-f", "mp4",
        part_path
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        process.wait(timeout=600)

        if process.returncode == 0 and os.path.exists(part_path):
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(part_path, final_path)
            return True

    except FileNotFoundError:
        print("[ERROR] ffmpeg 실행파일 없음 (config/환경 확인 필요)")

    except subprocess.TimeoutExpired:
        process.kill()

    if os.path.exists(part_path):
        os.remove(part_path)

    return False


def download_video(url, title, download_dir):
    # 1차: aria2
    if download_with_aria2(url, title, download_dir):
        return True

    # 2차: ffmpeg fallback
    return download_with_ffmpeg(url, title, download_dir)