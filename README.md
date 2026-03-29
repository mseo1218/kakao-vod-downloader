# 📺 Kakao VOD Downloader

카카오 TV의 동영상 링크를 분석하여 고화질 MP4 파일로 추출하고 다운로드하는 자동화 도구입니다.

---

## ✨ 주요 기능

- **자동 타이틀 추출**  
  영상 페이지에서 실제 제목과 업로드 날짜를 파악하여 파일명으로 지정합니다.

- **고화질 우선 추출**  
  1080p, 720p 등 사용 가능한 최고 화질을 자동으로 선택합니다.

- **멀티 워커 시스템**
  - **Downloader Worker**: FFmpeg 기반으로 다운로드를 수행합니다. (기본값: 동시 16개)

- **중복 방지**  
  `done.txt`를 통해 이미 완료된 작업은 자동으로 건너뜁니다.

---

## 🚀 설치 및 실행 방법 (Installation & Usage)

이 프로그램은 두 가지 방식으로 실행할 수 있습니다.

### 1. 일반 사용자
파이썬 설치 없이 바로 사용하려는 분들을 위한 방법입니다.

```bash
1.  [Releases](https://github.com/mseo1218/kakao-vod-downloader/releases) 페이지에서 최신 버전의 `KakaoDownloader.zip`을 다운로드합니다.
2. `KakaoDownloader.exe`를 실행합니다.
3. 처음 실행하면 폴더에 **`settings.json`** 파일이 자동 생성됩니다.
4. data/links.txt 메모장을 열고 다운받기를 원하는 링크를 한줄씩 붙여넣고 저장하세요.
5. 실시간으로 메모장에 추가되는 링크의 영상 다운로드가 진행됩니다.
6. 프로그램 종료는 Control + C 를 눌러주세요.
```

🛑 **설정 변경**: PC환경에 따라 동시 다운로드 개수를 변경하고 싶으면 `settings.json`을 메모장으로 수정 후 프로그램을 재시작하세요.
   - `extractor_workers`: 주소 추출기 개수 (기본 1, 변경 비추천)
   - `download_workers`: 동시 다운로드 개수 (기본 16, 문제발생시 줄이기)
   - `headless`: 브라우저 창 숨김 여부 (기본 True)

🛑 성인인증 필요시
  - 프로그램 종료 후 headless 모드를 False로 변경
  - 프로그램 실행 후 필요한 영상 다운로드 진행시 브라우저 창이 열리면 로그인 완료
  - 이후 프로그램 종료후 다시 headless 모드를 True로 변경하면, 로그인 세션 저장되어 headless 모드로 성인인증필요한 영상 다운로드 진행가능

---

#### 📂 배포판 구조 (dist)
사용자에게 공유할 때는 아래 파일들이 포함되어 있어야 합니다.

```bash
.
├── KakaoDownloader.exe    # 메인 실행 파일
├── settings.json          # 사용자 설정 파일 (실행 시 자동 생성)
├── bin/                   # 필수 바이너리 (Chromium, FFmpeg)
│   ├── playwright/        # 브라우저 엔진
│   └── ffmpeg.exe         # 영상 합성 엔진
├── data/                  # 작업 기록 (links.txt 등)
└── videos/                # 영상 저장 폴더
└── src/                   # 로그인 세션 찌꺼기

```

--- 

### 2. 개발자 및 스크립트 사용자

#### 1. 필수 준비물

이 프로그램은 영상 합성을 위해 FFmpeg가 필요합니다.

- FFmpeg: 공식 사이트에서 설치 후 환경 변수(Path)에 등록합니다  
- 참고: https://zerobit.tistory.com/42

---

#### 2. 가상환경 및 라이브러리 설치

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

#### 3. 실행 방법

1. 터미널에서 아래 명령어를 실행하세요.
```bash
(.venv) python -m src.main
```

2. 이후 data/links.txt 파일에 다운로드할 카카오 TV 주소를 한 줄에 하나씩 입력하면 실시간으로 작업 큐에 등록됩니다.

🛑 프로그램 종료: 키보드 인터럽트(Ctrl + C)를 사용하여 종료합니다.

---

#### 📂 프로젝트 구조
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

#### ⚙️ 주요 설정 ('settings.json' or 'src/config.py')

| 설정 항목 | 설명 | 기본값 |
| :--- | :--- | :--- |
| `DOWNLOAD_DIR` | 영상이 저장될 경로를 지정합니다. | `./videos/` |
| `DOWNLOAD_WORKER_COUNT` | 동시에 다운로드할 파일 개수를 설정합니다. | `8` |
| `HEADLESS_MODE` | 브라우저 창 표시 여부 (True: 숨김 / False: 표시) | `True` |

🛑 성인인증 필요시 잠깐 HEADLESS모드 꺼서 로그인만 했다가 스크립트 재실행하면 가능