# 📺 Kakao VOD Downloader

카카오 TV의 동영상 링크를 분석하여 고화질 MP4 파일로 추출하고 다운로드하는 자동화 도구입니다.

---

## ✨ 주요 기능

- **자동 타이틀 추출**  
  영상 페이지에서 실제 제목과 업로드 날짜를 파악하여 파일명으로 지정합니다.

- **고화질 우선 추출**  
  1080p, 720p 등 사용 가능한 최고 화질을 자동으로 선택합니다.

- **멀티 워커 시스템**
  - **Title Worker**: 링크를 감시하고 제목을 정제합니다  
  - **Extractor Worker**: Playwright 기반으로 스트리밍 주소를 추출합니다  
  - **Downloader Worker**: FFmpeg 기반으로 안정적인 다운로드를 수행합니다  

- **중복 방지**  
  `done.txt`를 통해 이미 완료된 작업은 자동으로 건너뜁니다.

---

## 🚀 시작하기

### 1. 필수 준비물

이 프로그램은 영상 합성을 위해 FFmpeg가 필요합니다.

- FFmpeg: 공식 사이트에서 설치 후 환경 변수(Path)에 등록합니다  
- 참고: https://wikidocs.net/305234

---

### 2. 가상환경 및 라이브러리 설치

```bash
# 가상환경 생성 및 활성화
python -m venv .venv

# 가상환경 활성화 (Windows)
.\.venv\Scripts\activate

# 필요한 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

```

---

### 3. 실행 방법

1. 터미널에서 아래 명령어를 실행하세요.
```bash
(.venv) python -m src.main
```

2. 이후 data/links.txt 파일에 다운로드할 카카오 TV 주소를 한 줄에 하나씩 입력하면 실시간으로 작업 큐에 등록됩니다.

🛑 프로그램 종료: 키보드 인터럽트(Ctrl + C)를 사용하여 종료합니다.

---

### 📂 프로젝트 구조
```bash
.
├── src/                # 소스 코드 폴더
│   ├── main.py         # 메인 실행 파일
│   ├── config.py       # 설정 및 경로 관리
│   ├── extractor.py    # 영상 주소 추출 (Playwright)
│   ├── downloader.py   # FFmpeg 기반 다운로드 모듈
│   └── parser.py       # 페이지 타이틀 파서
├── data/               # 데이터 관리 폴더 (Git 제외)
│   ├── links.txt       # 다운로드할 URL 목록
│   ├── failed.txt      # 실패한 URL 기록
│   └── done.txt        # 완료된 URL 기록
├── videos/             # 다운로드 완료된 영상 저장 폴더
├── .gitignore          # Git 추적 제외 설정 파일
└── requirements.txt    # 파이썬 의존성 패키지 목록
```
---

### ⚙️ 주요 설정 (src/config.py)
설정 항목	설명	기본값
DOWNLOAD_DIR	영상이 저장될 경로를 지정합니다	./videos/
DOWNLOAD_WORKER_COUNT	동시에 다운로드할 파일 개수를 설정합니다	8
HEADLESS_MODE	브라우저 창 표시 여부를 설정합니다 (True: 숨김 / False: 표시)	True