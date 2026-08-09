import QtQuick

// The application palette: Catppuccin Mocha for dark, Latte for light.
//
// Extracted from main.qml. Every component in the front end takes a `theme`
// property and reads colour roles off it, so this is the one place the two
// palettes are written down and the one place the choice between them is made.
//
// `isDark` is a plain property rather than a binding to the stored setting.
// The caller binds it on startup and assigns it on toggle, which is what makes
// the toggle stick: the first assignment breaks the startup binding; the
// caller writes the new value back to storage itself.
QtObject {
    id: theme

    property bool isDark: true

    // Catppuccin Mocha (dark)
    readonly property color _dCrust:    "#11111b"
    readonly property color _dMantle:   "#181825"
    readonly property color _dBase:     "#1e1e2e"
    readonly property color _dSurface0: "#313244"
    readonly property color _dSurface1: "#45475a"
    readonly property color _dOverlay:  "#6c7086"
    readonly property color _dSubtext:  "#a6adc8"
    readonly property color _dText:     "#cdd6f4"
    readonly property color _dBlue:     "#89b4fa"
    readonly property color _dRed:      "#f38ba8"
    readonly property color _dGreen:    "#a6e3a1"

    // Catppuccin Latte (light)
    readonly property color _lCrust:    "#dce0e8"
    readonly property color _lMantle:   "#e6e9ef"
    readonly property color _lBase:     "#eff1f5"
    readonly property color _lSurface0: "#ccd0da"
    readonly property color _lSurface1: "#bcc0cc"
    readonly property color _lOverlay:  "#9ca0b0"
    readonly property color _lSubtext:  "#6c6f85"
    readonly property color _lText:     "#4c4f69"
    readonly property color _lBlue:     "#1e66f5"
    readonly property color _lRed:      "#d20f39"
    readonly property color _lGreen:    "#40a02b"

    property color crust:    isDark ? _dCrust    : _lCrust
    property color mantle:   isDark ? _dMantle   : _lMantle
    property color base:     isDark ? _dBase     : _lBase
    property color surface0: isDark ? _dSurface0 : _lSurface0
    property color surface1: isDark ? _dSurface1 : _lSurface1
    property color overlay:  isDark ? _dOverlay  : _lOverlay
    property color subtext:  isDark ? _dSubtext  : _lSubtext
    property color text:     isDark ? _dText     : _lText
    property color blue:     isDark ? _dBlue     : _lBlue
    property color red:      isDark ? _dRed      : _lRed
    property color green:    isDark ? _dGreen    : _lGreen
    property color amber:    isDark ? "#fab387"  : "#e67e22"
}
