import subprocess
import os
import re

def download_video(url, title, download_dir):
    # 특수문자 제거 및 윈도우 경로 호환성 처리
    safe_title = re.sub(r'[\\/:*?\"<>|]', "_", title).strip().replace(".", "_")
    final_path = os.path.join(download_dir, f"{safe_title}.mp4").replace("\\", "/")
    part_path = final_path + ".part"
    
    # 영상 존재시 스킵
    if os.path.exists(final_path):
        return True

    cmd = [
        "ffmpeg", "-y", "-user_agent", "Mozilla/5.0",
        "-headers", "Referer: https://tv.kakao.com/\r\nOrigin: https://tv.kakao.com/",
        "-i", url, "-c", "copy", "-f", "mp4", part_path
    ]

    # 에러로그 수집
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    _, stderr = process.communicate()

    if process.returncode == 0:
        if os.path.exists(final_path): 
            os.remove(final_path)
        os.rename(part_path, final_path)
        return True
    else:
        print(f"[Downloader-FFmpeg error] {stderr[-300:]}")
        if os.path.exists(part_path):
            os.remove(part_path)
        return False