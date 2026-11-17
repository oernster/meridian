"""Single source of truth for the resources every delivery script bundles.

`meridian/main.py` reads two licence texts at startup and injects them as the
`uiLicenceText` and `modelLicenceText` context properties. `_read_text`
degrades to "Licence text unavailable." rather than raising, so a delivery
script that omits a licence produces a build that starts cleanly and renders
that line in both licence dialogs instead of a licence.

The list lived in three hand-maintained copies (`buildexe.py`, `builddmg.py`
and `build_flatpak.sh`) and the macOS one had drifted to a single entry, so
every DMG shipped with both dialogs empty. The two Python scripts now read
this module; `tests/structural/test_delivery_resources.py` holds the shell
script and `meridian/main.py` to the same list, so no copy can drift again
without a test failing.

The header artwork joined it for the same reason from the other direction.
`create_icons.py` derives the marks and `HeaderBar.qml` sources them, so the
names had two homes and neither could see the other. They live here now, where
a structural test can hold the generator, the QML and the wheel's package-data
to one list without importing Pillow to do it.

The rules for what every bundle leaves out live here too, for the same reason:
four delivery routes have to agree on them. `bundle_prune.py` applies them.

This module deliberately states what is bundled or left out, never how. Each
script keeps its own argument spelling, which genuinely differs between
PyInstaller invocations and a Flatpak manifest.
"""

from __future__ import annotations

# Every licence text shipped with the application. LICENSE is the map that
# says which licence covers which directory; LICENSE-GPL-3.0.txt is present
# because the LGPL text incorporates it by reference.
LICENCE_FILES: tuple[str, ...] = (
    "LICENSE",
    "LICENSE-LGPL-3.0.txt",
    "LICENSE-APACHE-2.0.txt",
    "LICENSE-GPL-3.0.txt",
)

# Where the header masters live and where their renders are written, both
# relative to the repository root. The render directory sits inside the QML
# tree because all three delivery scripts already bundle `meridian/ui/qml`
# whole; the wheel reaches it through the package-data glob in pyproject.toml.
ART_MASTER_DIR = "assets"
ART_RENDER_DIR = "meridian/ui/qml/art"

# The height the header draws its marks at, plus the factor the render is
# multiplied by so they stay crisp under display scaling. The buttons carry no
# words, so the mark is the whole control and is sized to be read as one.
# TrayButton.qml's iconSize default must match; a structural test says so.
ART_DRAW_PX = 54
ART_SUPERSAMPLE = 4

# Every mark the header asks for, named as both master and render. A name here
# with no master fails the generator; a name in HeaderBar.qml that is not here
# fails the structural test.
ART_NAMES: tuple[str, ...] = (
    "import",
    "export",
    "search",
    "manage",
    "ui-licence",
    "model-licence",
    "help",
    "specification",
    "dark-mode",
    "light-mode",
)

# The donate mark. Its master sits at the repository root rather than in
# `assets/` because that is where it was delivered; everything downstream of
# the crop is identical to the header's, so it rides the same render step.
DONATE_NAME = "donate"
DONATE_MASTER = "donate.png"

# Where the donate render is written: the application's tray only. The site's
# docs/donate.png is never derived from it: it is the small mark every project
# site shares byte for byte, which the structural suite pins.
DONATE_OUTPUTS: tuple[str, ...] = ("meridian/ui/qml/art/donate.png",)
SITE_DONATE = "docs/donate.png"

# The footer mark as a fraction of the header's, which is ClearBudget's rule
# taken whole: the band at the foot is subordinate to the one at the top, so
# two matching bands would weigh the window down at both ends. Expressed
# against ART_DRAW_PX rather than as a second pixel number, so retuning the
# header carries the footer with it and the two cannot drift.
FOOTER_NUMERATOR = 2
FOOTER_DENOMINATOR = 3
DONATE_DRAW_PX = ART_DRAW_PX * FOOTER_NUMERATOR // FOOTER_DENOMINATOR

# ── What every bundle leaves out ─────────────────────────────────────────────
#
# PySide6 ships every Qt module and PyInstaller's Qt hooks collect far more than
# the application loads; on 2026-11-17 the Windows bundle measured 610 MB over
# 3,138 files. Each rule below was settled by measurement, not by name:
# the real PE import graph of the built bundle (pefile) plus the list of modules
# a launched build actually loaded, across Meridian.exe and its WebEngine helper
# processes. `bundle_prune.py` applies the rules; these tables only say what.
#
# Two findings shape the lists. QtPrintSupport stays: the WebEngine binding
# imports it at the Python level, which no DLL graph shows. Qt6Pdf goes: it was
# loaded only through the `qpdf` image-format plugin, which Qt loads at startup
# merely to list the formats it can read.

# Python packages nothing in the application runs. click, rich and pygments
# arrive only through httpx's command-line tool (`httpx._main`), whose import
# httpx wraps in `except ImportError`; pygments then drags in Pillow. setuptools
# arrives through its own runtime hook; sqlalchemy reads the stdlib
# importlib.metadata on every supported Python.
EXCLUDED_MODULES: tuple[str, ...] = (
    "tkinter",
    "unittest",
    "click",
    "rich",
    "pygments",
    "PIL",
    "setuptools",
)

# Qt modules the application never loads, matched as a prefix of the module
# name however the platform spells the file: Qt6<name>.dll, libQt6<name>.so.6,
# Qt<name>.framework or the Qt<name> binding. Positioning, PrintSupport, Svg,
# OpenGL and SerialPort are absent on purpose: something kept links them.
DROPPED_QT_MODULE_PREFIXES: tuple[str, ...] = (
    "3D",
    "Bluetooth",
    "Charts",
    "DataVisualization",
    "Designer",
    "Graphs",
    "Help",
    "HttpServer",
    "LabsAnimation",
    "LabsPlatform",
    "LabsQmlModels",
    "LabsSharedImage",
    "LabsStyleKit",
    "LabsSynchronizer",
    "LabsWavefrontMesh",
    "Location",
    "MultimediaWidgets",
    "Nfc",
    "OpenGLWidgets",
    "Pdf",
    "PositioningQuick",
    "QmlCore",
    "QmlLocalStorage",
    "QmlNetwork",
    "QmlXmlListModel",
    "Quick3D",
    "QuickControls2FluentWinUI3",
    "QuickControls2IOS",
    "QuickControls2Imagine",
    "QuickControls2MacOS",
    "QuickControls2Material",
    "QuickControls2Universal",
    "QuickControls2Windows",
    "QuickEffects",
    "QuickParticles",
    "QuickTest",
    "QuickTimeline",
    "QuickVectorImage",
    "RemoteObjects",
    "Scxml",
    "Sensors",
    "SerialBus",
    "SpatialAudio",
    "Sql",
    "StateMachine",
    "Test",
    "TextToSpeech",
    "UiTools",
    "VirtualKeyboard",
    "WebEngineWidgets",
    "WebSockets",
    "WebView",
)

# QML module trees, as paths under Qt's `qml` directory, that no QML file the
# application ships imports, directly or through a qmldir it reaches. The style
# is Fusion (set unconditionally in `meridian/main.py`), so the other styles go;
# `QtQuick.Controls` names them only as `optional import ... auto`.
DROPPED_QML_MODULES: tuple[str, ...] = (
    "Qt/labs/StyleKit",
    "Qt/labs/animation",
    "Qt/labs/platform",
    "Qt/labs/qmlmodels",
    "Qt/labs/sharedimage",
    "Qt/labs/synchronizer",
    "Qt/labs/wavefrontmesh",
    "Qt3D",
    "Qt5Compat",
    "QtCharts",
    "QtCore",
    "QtDataVisualization",
    "QtGraphs",
    "QtLocation",
    "QtNetwork",
    "QtPositioning",
    "QtQml/StateMachine",
    "QtQml/XmlListModel",
    "QtQuick/Controls/FluentWinUI3",
    "QtQuick/Controls/Imagine",
    "QtQuick/Controls/Material",
    "QtQuick/Controls/Universal",
    "QtQuick/Controls/Windows",
    "QtQuick/Controls/iOS",
    "QtQuick/Controls/macOS",
    "QtQuick/Effects",
    "QtQuick/LocalStorage",
    "QtQuick/NativeStyle",
    "QtQuick/Particles",
    "QtQuick/Pdf",
    "QtQuick/Scene2D",
    "QtQuick/Scene3D",
    "QtQuick/Timeline",
    "QtQuick/VectorImage",
    "QtQuick/VirtualKeyboard",
    "QtQuick/tooling",
    "QtQuick3D",
    "QtRemoteObjects",
    "QtScxml",
    "QtSensors",
    "QtSpatialAudio",
    "QtStateMachine",
    "QtTest",
    "QtTextToSpeech",
    "QtWebSockets",
    "QtWebView",
)

# Qt plugin folders serving only modules dropped above or the QML debugger.
# platforminputcontexts stays as a folder: on Linux it holds the compose and
# IBus input plugins that dead keys and input methods need.
DROPPED_PLUGIN_DIRS: tuple[str, ...] = (
    "assetimporters",
    "canbus",
    "designer",
    "geometryloaders",
    "geoservices",
    "qmllint",
    "qmltooling",
    "renderers",
    "renderplugins",
    "sceneparsers",
    "scxmldatamodel",
    "sensors",
    "sqldrivers",
    "texttospeech",
    "webview",
)

# Individual plugins named by a fragment of their file name: the on-screen
# keyboard, the PDF image reader that loads Qt6Pdf and the Direct2D platform,
# which nothing selects while the Windows platform plugin is present.
DROPPED_PLUGIN_MARKERS: tuple[str, ...] = ("virtualkeyboard", "qpdf", "qdirect2d")

# Whole files dropped by name. opengl32sw.dll is the software OpenGL fallback;
# Meridian and every WebEngine helper ran on Direct3D and none loaded OpenGL.
DROPPED_FILES: tuple[str, ...] = ("opengl32sw.dll",)

# WebEngine data. The debug variants serve only debug builds of Qt and the
# devtools pack serves only the inspector, which Meridian never opens. Nothing
# installs a QTranslator, so Qt's .qm catalogues are never read. Of Chromium's
# locale packs only en-US stays: it is the fallback for every other locale.
DROPPED_RESOURCE_SUFFIXES: tuple[str, ...] = (".debug.pak", ".debug.bin", ".qm")
DROPPED_RESOURCE_PREFIXES: tuple[str, ...] = ("qtwebengine_devtools_resources",)
WEBENGINE_LOCALE_DIR = "qtwebengine_locales"
KEPT_WEBENGINE_LOCALES: tuple[str, ...] = ("en-US.pak",)

# The setup program is a Qt Widgets window: launched to its first screen it
# loaded Qt6Core, Qt6Gui and Qt6Widgets plus the Windows platform and style
# plugins, nothing more. Qml and Quick reached it only through the on-screen
# keyboard plugin, so the rest of the application's stack is left out too.
# pywin and win32ui (the MFC layer) arrive through win32com.client.makepy,
# which imports them only inside functions the installer never calls; its
# shortcuts go through pythoncom, win32com.shell and win32com.propsys alone.
INSTALLER_EXCLUDED_MODULES: tuple[str, ...] = ("pywin", "win32ui")
INSTALLER_DROPPED_QT_MODULE_PREFIXES: tuple[str, ...] = (
    "Multimedia",
    "OpenGL",
    "Positioning",
    "Qml",
    "Quick",
    "SerialPort",
    "WebChannel",
    "WebEngine",
)

# Parts of the PySide6 wheel that serve development rather than running, which
# only the Flatpak meets because it installs the wheel whole: headers, binding
# generator inputs, type metadata, the pyside6-* tool shims and the Qt tools.
WHEEL_DEV_DIRS: tuple[str, ...] = (
    "glue",
    "include",
    "metatypes",
    "scripts",
    "typesystems",
)
WHEEL_TOOLS: tuple[str, ...] = (
    "assistant",
    "balsam",
    "balsamui",
    "designer",
    "linguist",
    "lrelease",
    "lupdate",
    "qmlcachegen",
    "qmlformat",
    "qmlimportscanner",
    "qmllint",
    "qmlls",
    "qmltyperegistrar",
    "qsb",
    "rcc",
    "svgtoqml",
    "uic",
)
