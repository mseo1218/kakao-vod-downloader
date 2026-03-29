import re
import requests
from datetime import datetime
import config

def extract_video_title(url):
    headers = {"User-Agent": config.USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # 1. 상세 제목 추출 (<strong class="tit_vod ">...</strong>)
            title_match = re.search(r'<strong class="tit_vod\s*">(.*?)</strong>', html, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'<[^>]+>', '', title) # 내부 태그 제거
            else:
                og_match = re.search(r'<meta property="og:title" content="(.*?)">', html)
                title = og_match.group(1) if og_match else "Unknown_Title"
            
            # 2. 날짜 및 시간 추출
            # content="2017(1) 06(2) 08(3) 22(4) 27(5) 30(6)"
            # 정규식 수정: 년(4), 월(2), 일(2), 시(2), 분(2), 초(2) 모두 캡처
            dt_match = re.search(r'property="article:published_time"\s+content="(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"', html)
            
            if not dt_match:
                # createTime 형태 대응: "createTime":"20170608222730"
                dt_match = re.search(r'"createTime":"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"', html)
            
            if dt_match:
                # 형식: YYYY.MM.DD_HHMMSS (예: 2017.06.08_222730)
                date_time_str = f"{dt_match.group(1)}.{dt_match.group(2)}.{dt_match.group(3)}_{dt_match.group(4)}{dt_match.group(5)}{dt_match.group(6)}"
            else:
                # 실패 시 현재 시간 사용
                date_time_str = datetime.now().strftime("%Y.%m.%d_%H%M%S")
            
            # 3. 파일명 안전 문자열 변환
            safe_title = re.sub(r'[\\/:*?"<>|.]', "_", title).strip()
            
            return f"{safe_title}_{date_time_str}"
            
    except Exception as e:
        print(f"❌ [parser] 제목 추출 에러: {e}")
        
    return None