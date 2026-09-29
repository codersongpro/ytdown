# PyInstaller 빌드 설정:  pyinstaller ytdown.spec
# 결과물: dist/ytdown(.exe) — 단일 실행파일
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("app/static", "app/static")]
datas += collect_data_files("imageio_ffmpeg")  # ffmpeg 바이너리 포함

hiddenimports = collect_submodules("uvicorn")

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="ytdown",
    console=True,  # 콘솔 창을 닫으면 종료되도록 유지
    upx=False,
)
