# ytdown

유튜브 주소를 넣으면 **MP4(영상)** 또는 **MP3(음원)** 로 저장하는 데스크톱 프로그램입니다.
브라우저 없이 ytdown 창 안에서 주소 입력부터 저장까지 모두 처리합니다.

## 설치·실행 (추천: 실행파일)
1. 저장소의 **Releases**에서 최신 버전 받기
   - Windows: `ytdown.exe` 더블클릭
   - macOS: `ytdown-macos.zip` 압축 풀기 → `ytdown.app` 우클릭 → **열기**
2. ytdown 창이 열립니다. 창을 닫으면 종료됩니다.

처음 실행 시 경고가 나올 수 있습니다(코드 서명이 없는 개인 프로그램이라 정상).
- Windows "PC 보호" 창 → **추가 정보** → **실행**
- macOS "확인되지 않은 개발자" → 우클릭 → **열기**

Windows 10/11에 기본 포함된 WebView2로 창을 띄웁니다. 창이 안 뜨면
[WebView2 런타임](https://developer.microsoft.com/microsoft-edge/webview2/)을 설치하세요.

## 사용법
1. 유튜브 영상 주소 붙여넣기 → **정보 확인**
2. 형식 선택: **MP4 영상**(화질 최고/1080p/720p/480p) 또는 **MP3 음원**(320/192/128kbps)
3. **다운로드** → 완료되면 저장 위치에 바로 저장됩니다. **저장된 파일 보기**로 폴더를 열 수 있습니다.

- 저장 위치: 기본은 `다운로드` 폴더이며, 위쪽 **변경** 버튼으로 바꿀 수 있습니다(설정은 기억됨).
- 지원 주소: `youtube.com/watch?v=…`, `youtu.be/…`, `youtube.com/shorts/…`, `music.youtube.com/watch?v=…`
- 재생목록은 첫 영상 1개만, 3시간 초과 영상·라이브 방송·비공개/연령제한 영상은 불가

## 문제 해결
- **갑자기 다운로드가 안 될 때**: 유튜브 사양이 바뀐 경우가 대부분입니다. Releases에서 새 버전을 받으세요.
  (Actions → Build executables → **Run workflow**에 `v1.1.1` 같은 태그를 넣으면 최신 yt-dlp로 새 릴리즈 생성)
- **인증서(SSL) 오류**: 학교·회사망 보안 장비나 백신의 HTTPS 검사 때문입니다. v1.1.0부터 Windows/macOS에
  등록된 인증서를 사용하도록 고쳐 대부분 해결됩니다. 그래도 나오면 다른 네트워크(핫스팟 등)에서 시도하세요.
- 오류 기록: `사용자 폴더/.ytdown/ytdown.log`

## 스크립트로 실행 (Python 3.10+ 필요)
| 운영체제 | 방법 |
|---|---|
| Windows | `run.bat` 더블클릭 |
| macOS / Linux | `./run.sh` |

## 개발
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest httpx
python -m pytest
python launcher.py            # 프로그램 창으로 실행
python launcher.py --browser  # 브라우저로 실행(디버깅용)
```

구조
- `app/downloader.py` — URL 검증, yt-dlp 옵션 생성, 정보 조회·다운로드
- `app/main.py` — 내부 API (`/api/info`, `/api/download`, `/api/progress/{id}`, `/api/settings`, `/api/open`)
- `app/static/index.html` — 화면
- `launcher.py` — 내부 서버 시작 + pywebview 프로그램 창
- `ytdown.spec` — PyInstaller 빌드 설정 (`pyinstaller ytdown.spec` → `dist/`)
- `.github/workflows/build.yml` — Windows·macOS 실행파일 자동 빌드·릴리즈
