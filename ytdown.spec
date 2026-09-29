# PyInstaller 빌드 설정:  pyinstaller ytdown.spec
# 결과물: Windows dist/ytdown.exe, macOS dist/ytdown.app
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("app/static", "app/static")]
datas += collect_data_files("imageio_ffmpeg")  # ffmpeg 바이너리 포함
datas += collect_data_files("webview")

hiddenimports = collect_submodules("uvicorn") + ["truststore"]

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ytdown", console=False, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="ytdown", upx=False)
    app = BUNDLE(coll, name="ytdown.app", bundle_identifier="com.codersongpro.ytdown")
else:
    # 콘솔 창 없이 프로그램 창만 뜨는 단일 실행파일
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="ytdown", console=False, upx=False)
