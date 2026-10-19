# -*- mode: python ; coding: utf-8 -*-
# Budowanie: pyinstaller ddcontrol.spec  ->  dist/DDControl/DDControl.exe

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[("ddcontrol/qml", "ddcontrol/qml"), ("ddcontrol/assets", "ddcontrol/assets")],
    hiddenimports=["hid", "serial", "serial.tools.list_ports"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore", "PySide6.QtMultimedia"],
)
# Hooki PySide6 dorzucają wszystkie moduły QML (WebEngine, 3D, ...). Aplikacja używa tylko
# QtQuick + Controls.Basic + Shapes + Dialogs, więc reszta wylatuje (~400 MB -> ~100 MB).
UNUSED = ("WebEngine", "WebView", "WebChannel", "Quick3D", "Qt63D", "Qt3D", "/Qt3D", "Pdf", "Graphs",
          "Charts", "DataVisualization", "Multimedia", "SpatialAudio", "Location", "Positioning",
          "Sensors", "VirtualKeyboard", "Scxml", "StateMachine", "RemoteObjects", "Bluetooth", "Nfc",
          "SerialBus", "SerialPort", "TextToSpeech", "Lottie", "Designer", "Help", "UiTools",
          "Imagine", "Material", "Universal", "FluentWinUI3", "Fusion", "opengl32sw", "translations",
          "QtTest", "Qt6Test", "Qt6Sql", "QtSql")


def _keep(entry):
    name = entry[0].replace("\\", "/")
    return not any(part in name for part in UNUSED)


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DDControl",
    console=False,
    icon="ddcontrol/assets/icon.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, name="DDControl")
