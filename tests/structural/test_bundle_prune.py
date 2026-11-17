"""Every bundle leaves out only what Meridian never loads.

`bundle_prune.py` drops files from all four delivery routes by the rules in
`build_resources.py`. A rule that catches something the application uses
produces a build that starts and then cannot load a QML module or a Qt
library, which nothing else in this suite would notice, because nothing here
asserts over a built bundle. These tests hold the rules to the application's
own imports, to the libraries a launched build was measured loading and to
each platform's file layout.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).parent.parent.parent


def _load_bundle_prune() -> ModuleType:
    """Load the root build module; it imports `build_resources` by name."""
    sys.path.insert(0, str(_ROOT))
    try:
        spec = importlib.util.spec_from_file_location(
            "bundle_prune", _ROOT / "bundle_prune.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(_ROOT))
    return module


_PRUNE = _load_bundle_prune()
_INSTALLER_PREFIXES: tuple[str, ...] = sys.modules[
    "build_resources"
].INSTALLER_DROPPED_QT_MODULE_PREFIXES

# Where the QML tree sits in each layout: the Windows wheel, then the Linux
# wheel and the macOS bundle, which both keep Qt's files under `Qt/`.
_QML_ROOTS = ("PySide6/qml", "PySide6/Qt/qml")


def _library_paths(module: str) -> tuple[str, ...]:
    """Every spelling of one Qt module's files, across the three platforms."""
    return (
        f"PySide6/Qt6{module}.dll",
        f"PySide6/Qt/lib/libQt6{module}.so.6",
        f"PySide6/Qt/lib/Qt{module}.framework/Versions/A/Qt{module}",
        f"PySide6/Qt{module}.pyd",
        f"PySide6/Qt{module}.abi3.so",
    )


# Qt modules a launched Windows build loaded on 2026-11-17, read from the
# module lists of Meridian.exe and its QtWebEngineProcess helpers. PrintSupport
# is here because the WebEngine binding imports it from Python, which no DLL
# import graph shows.
_MEASURED_LOADED = (
    "Core",
    "Gui",
    "LabsSettings",
    "Multimedia",
    "MultimediaQuick",
    "Network",
    "OpenGL",
    "Positioning",
    "PrintSupport",
    "Qml",
    "QmlMeta",
    "QmlModels",
    "QmlWorkerScript",
    "Quick",
    "QuickControls2",
    "QuickControls2Basic",
    "QuickControls2Fusion",
    "QuickControls2FusionStyleImpl",
    "QuickControls2Impl",
    "QuickDialogs2",
    "QuickDialogs2QuickImpl",
    "QuickDialogs2Utils",
    "QuickLayouts",
    "QuickTemplates2",
    "Svg",
    "WebChannel",
    "WebChannelQuick",
    "WebEngineCore",
    "WebEngineQuick",
    "Widgets",
)


def _qml_imports() -> set[str]:
    imports: set[str] = set()
    for path in (_ROOT / "meridian" / "ui" / "qml").rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        pattern = r"^\s*import\s+([A-Za-z][\w.]*)"
        imports.update(re.findall(pattern, text, re.MULTILINE))
    main = (_ROOT / "meridian" / "main.py").read_text(encoding="utf-8")
    styles = re.findall(r"setStyle\(\s*[\"'](\w+)[\"']", main)
    assert styles, "Found no QQuickStyle.setStyle call in meridian/main.py"
    imports.update(f"QtQuick.Controls.{style}" for style in styles)
    return imports


def _pyside_imports(package: str) -> set[str]:
    found: set[str] = set()
    for path in (_ROOT / package).rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found.update(re.findall(r"PySide6\.Qt(\w+)", text))
    return found


def test_every_qml_module_the_application_imports_survives() -> None:
    imports = _qml_imports()
    assert "QtWebEngine" in imports, "the QML scan found nothing it should"
    dropped = [
        f"{root}/{module.replace('.', '/')}/qmldir"
        for module in sorted(imports)
        for root in _QML_ROOTS
        if _PRUNE.is_dropped(f"{root}/{module.replace('.', '/')}/qmldir")
    ]
    assert not dropped, "Drop rules catch QML the application imports:\n" + (
        "\n".join(dropped)
    )


@pytest.mark.parametrize(
    ("package", "prefixes"),
    [("meridian", ()), ("installer", _INSTALLER_PREFIXES)],
)
def test_every_pyside_module_the_code_imports_survives(
    package: str, prefixes: tuple[str, ...]
) -> None:
    modules = _pyside_imports(package)
    assert "Core" in modules, f"the import scan found nothing in {package}/"
    dropped = [
        path
        for module in sorted(modules)
        for path in _library_paths(module)
        if _PRUNE.is_dropped(path, prefixes)
    ]
    assert not dropped, f"Drop rules catch modules {package}/ imports:\n" + (
        "\n".join(dropped)
    )


def test_every_library_measured_loading_survives() -> None:
    dropped = [
        path
        for module in _MEASURED_LOADED
        for path in _library_paths(module)
        if _PRUNE.is_dropped(path)
    ]
    assert not dropped, "Drop rules catch libraries a running build loads:\n" + (
        "\n".join(dropped)
    )


@pytest.mark.parametrize(
    "path",
    [
        "_internal/PySide6/Qt63DCore.dll",
        "PySide6/Qt/lib/libQt6Quick3D.so.6",
        "PySide6/Qt/lib/QtCharts.framework/Versions/A/QtCharts",
        "PySide6/Qt/lib/QtCharts.framework/Resources/Info.plist",
        "PySide6/QtMultimediaWidgets.pyd",
        "PySide6/qml/QtQuick/VirtualKeyboard/qmldir",
        "PySide6/Qt/qml/QtQuick/Controls/Material/Button.qml",
        "PySide6/plugins/qmltooling/qmldbg_debugger.dll",
        "PySide6/plugins/imageformats/qpdf.dll",
        "PySide6/Qt/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so",
        "PySide6/opengl32sw.dll",
        "PySide6/resources/qtwebengine_resources.debug.pak",
        "PySide6/resources/qtwebengine_devtools_resources.pak",
        "PySide6/translations/qt_de.qm",
        "PySide6/translations/qtwebengine_locales/en-GB.pak",
        "PySide6/Qt/libexec/rcc",
        "PySide6/designer.exe",
        "PySide6/metatypes/qt6core_metatypes.json",
    ],
)
def test_rules_drop_what_is_never_loaded(path: str) -> None:
    assert _PRUNE.is_dropped(path)


@pytest.mark.parametrize(
    "path",
    [
        "meridian/ui/qml/main.qml",
        "PIL/_imaging.pyd",
        "PySide6/QtWebEngineProcess.exe",
        "PySide6/Qt/libexec/QtWebEngineProcess",
        "PySide6/resources/qtwebengine_resources.pak",
        "PySide6/resources/icudtl.dat",
        "PySide6/translations/qtwebengine_locales/en-US.pak",
        "PySide6/plugins/platforms/qwindows.dll",
        (
            "PySide6/Qt/plugins/platforminputcontexts/"
            "libcomposeplatforminputcontextplugin.so"
        ),
        "PySide6/plugins/imageformats/qjpeg.dll",
        "PySide6/qml/QtQuick/Controls/Fusion/Button.qml",
        "PySide6/Qt/lib/QtWebEngineCore.framework/Versions/A/QtWebEngineCore",
    ],
)
def test_rules_keep_what_is_loaded(path: str) -> None:
    assert not _PRUNE.is_dropped(path)


def test_the_installer_drops_the_quick_stack_but_not_widgets() -> None:
    assert _PRUNE.is_dropped("PySide6/Qt6Quick.dll", _INSTALLER_PREFIXES)
    assert not _PRUNE.is_dropped("PySide6/Qt6Widgets.dll", _INSTALLER_PREFIXES)
    assert not _PRUNE.is_dropped("PySide6/Qt6Quick.dll")


def test_every_delivery_route_goes_through_the_prune() -> None:
    """No route may build its own way round the shared rules."""
    missing = [
        name
        for name in ("buildexe.py", "buildinstaller.py", "builddmg.py")
        if "run_pyinstaller(" not in (_ROOT / name).read_text(encoding="utf-8")
    ]
    flatpak = (_ROOT / "build_flatpak.sh").read_text(encoding="utf-8")
    if "python3 bundle_prune.py /app/lib/python3.12/site-packages" not in flatpak:
        missing.append("build_flatpak.sh")
    assert not missing, "Delivery scripts that bypass bundle_prune:\n" + (
        "\n".join(missing)
    )


def test_no_delivery_script_names_its_own_exclusions() -> None:
    """Exclusions live in build_resources.py, so the routes cannot drift."""
    offenders = [
        name
        for name in ("buildexe.py", "buildinstaller.py", "builddmg.py")
        if "--exclude-module" in (_ROOT / name).read_text(encoding="utf-8")
    ]
    assert not offenders, "Scripts naming exclusions directly:\n" + (
        "\n".join(offenders)
    )
