# ytdown

유튜브 주소를 넣으면 **MP4(영상)** 또는 **MP3(음원)** 로 저장하는 로컬 웹앱입니다.
내 컴퓨터에서 실행하고 브라우저(`http://127.0.0.1:8000`)로 사용합니다.

> ⚠️ 본인이 만든 영상, CC 라이선스 영상, 이용 허락을 받은 자료만 받으세요.
> 유튜브 약관과 저작권법상 무단 다운로드·재배포는 금지되어 있습니다.

## 준비물 (실행 방법 B만 해당)
- Python 3.10 이상 ([python.org](https://www.python.org/downloads/))
  - Windows 설치 시 **"Add python.exe to PATH"** 체크
- ffmpeg는 자동으로 함께 설치되므로 따로 설치할 필요가 없습니다(실행파일에는 이미 포함).

## 실행 방법 A: 실행파일 (Python 설치 불필요, 추천)
1. GitHub 저장소 → **Actions** → 최신 **Build executables** 실행 → 아래 **Artifacts**에서 받기
   - Windows: `ytdown-windows` → 압축 풀고 `ytdown.exe` 더블클릭
   - macOS: `ytdown-macos` → 압축 풀기 → 터미널에서 `chmod +x ytdown` 후 실행
   - 정식 배포본은 **Releases** 페이지에 있습니다. (Actions → Build executables → Run workflow에 `v1.0.1` 같은 태그를 넣으면 새 릴리즈 생성)
2. 검은 창이 뜨고 브라우저가 자동으로 열립니다. **종료는 검은 창을 닫으면 됩니다.**

처음 실행 시 경고가 나올 수 있습니다(코드 서명이 없는 개인 프로그램이라 정상).
- Windows "PC 보호" 창 → **추가 정보** → **실행**
- macOS "확인되지 않은 개발자" → 파일 우클릭 → **열기**

> 유튜브가 바뀌어 안 될 때: 저장소가 매주 최신 yt-dlp로 자동 재빌드되므로 새 실행파일을 받으세요.
> Actions 탭에서 **Run workflow**를 눌러 즉시 새로 빌드할 수도 있습니다.

## 실행 방법 B: 스크립트 (Python 필요)
| 운영체제 | 방법 |
|---|---|
| Windows | 폴더의 `run.bat` 더블클릭 |
| macOS / Linux | 터미널에서 `./run.sh` |

처음 실행할 때 필요한 프로그램을 설치하느라 1~2분 걸립니다. 이후 브라우저가 자동으로 열립니다.

## 사용법
1. 유튜브 영상 주소 붙여넣기 → **정보 확인**
2. 형식 선택: **MP4 영상**(화질 최고/1080p/720p/480p) 또는 **MP3 음원**(320/192/128kbps)
3. **다운로드** → 진행률이 100%가 되면 브라우저 다운로드 폴더에 저장됩니다.

지원 주소: `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `music.youtube.com/watch?v=…`
(재생목록은 첫 영상 1개만, 3시간 초과 영상·라이브 방송·비공개/연령제한 영상은 불가)

## 문제 해결
- **"유튜브가 요청을 일시적으로 막았습니다" / 갑자기 안 될 때**: 유튜브 사양이 바뀐 경우가 대부분입니다.
  `run.bat`/`run.sh`를 다시 실행하면 yt-dlp가 최신 버전으로 자동 업데이트됩니다.
- 다른 기기에서 접속되지 않는 것은 정상입니다. 보안을 위해 이 컴퓨터(127.0.0.1)에서만 열리도록 되어 있습니다.

## 개발
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest httpx
python -m pytest
python -m uvicorn app.main:app --reload
```

구조
- `app/downloader.py` — URL 검증, yt-dlp 옵션 생성, 정보 조회·다운로드 (웹 서버와 분리되어 있어 추후 Docker 서버로 옮기기 쉬움)
- `app/main.py` — FastAPI API (`/api/info`, `/api/download`, `/api/progress/{id}`, `/api/file/{id}`)
- `app/static/index.html` — 화면
- `launcher.py` / `ytdown.spec` — 실행파일 진입점·빌드 설정 (`pyinstaller ytdown.spec` → `dist/`)
- `.github/workflows/build.yml` — Windows·macOS 실행파일 자동 빌드

> Vercel 같은 서버리스 환경은 유튜브의 데이터센터 IP 차단, ffmpeg 실행·응답 크기·실행 시간 제한 때문에 다운로드 서버로 적합하지 않아 로컬 실행 방식으로 만들었습니다.
