📺 Kakao VOD Downloader
카카오 TV의 동영상 링크를 분석하여 고화질 MP4 파일로 추출하고 다운로드하는 자동화 도구입니다.

✨ 주요 기능
자동 타이틀 추출: 영상 페이지에서 실제 제목과 업로드 날짜를 파악하여 파일명으로 지정합니다.

고화질 우선 추출: 1080p, 720p 등 사용 가능한 최고 화질을 자동으로 선택합니다.

멀티 워커 시스템:

Title Worker: 링크 감시 및 제목 정제

Extractor Worker: Playwright 기반 스트리밍 주소 추출

Downloader Worker: FFmpeg 기반 안정적인 분할 다운로드

중복 방지: done.txt를 통해 이미 완료된 작업은 자동으로 건너뜁니다.

🚀 시작하기
1. 필수 준비물
이 프로그램은 영상 합성을 위한 FFmpeg가 필요합니다.

FFmpeg: 공식 사이트에서 설치 후 환경 변수(Path)에 등록되어 있어야 합니다.
참고 - https://wikidocs.net/305234

2. 가상환경 및 라이브러리 설치
Bash
# 가상환경 생성 및 활성화
python -m venv .venv

# 가상환경 활성화
.\.venv\Scripts\activate

# 필요한 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

3. 실행 방법
아래 명령어를 실행하세요.

Bash
(.venv) python -m src.main

이후 data/links.txt 파일에 다운로드할 카카오 TV 주소를 한 줄에 하나씩 입력하면 실시간으로 작업큐에 등록됩니다.

4. 프로그램 종료
키보드 인터럽트 (ctrl + C)

📂 프로젝트 구조
Plaintext
.
├── src/                # 소스 코드
│   ├── main.py         # 메인 실행 파일
│   ├── config.py       # 설정 및 경로 관리
│   ├── extractor.py    # 영상 주소 추출
│   ├── downloader.py   # FFmpeg 다운로드
│   └── parser.py       # 타이틀 파싱
├── data/               # 데이터 파일 (Git 제외)
│   ├── links.txt       # 다운로드 대상 URL
│   ├── failed.txt      # 실패한 URL
│   └── done.txt        # 완료된 목록
├── videos/             # 완료된 영상들 
├── .gitignore          # Git 제외 설정
└── requirements.txt    # 의존성 목록

⚙️ 설정 (config.py)
DOWNLOAD_DIR: 영상이 저장될 경로를 수정할 수 있습니다 (기본 ./videos/).

DOWNLOAD_WORKER_COUNT: 동시에 다운로드할 개수를 조절할 수 있습니다 (기본 8).

HEADLESS_MODE: 브라우저 창을 띄울지 여부를 결정합니다. (True: 끄기 / False: 성인인증에 필요시 이용)

⚠️ 주의사항
본 도구는 개인 소장 및 학습 목적으로만 사용해야 합니다.

저작권이 있는 콘텐츠의 무단 배포로 발생하는 책임은 사용자에게 있습니다.
