"""
Configuration constants for credits block detection.
"""
# Band selection
BOTTOM_BAND_Y_MIN = 0.70
BOTTOM_BAND_Y_MAX = 1.00

TOP_LITE_BAND_Y_MIN = 0.00
TOP_LITE_BAND_Y_MAX = 0.25

# Overlay heuristics
OVERLAY_AREA_SMALL = 0.0020  # tune
OVERLAY_HEIGHT_TINY = 0.030  # tune
OVERLAY_ASPECT_WIDE = 3.5  # tune

# Cluster / credits heuristics
CREDITS_LINE_COUNT_MIN = 8  # tune
CREDITS_FONT_HEIGHT_MAX = 0.030  # tune (small text)
CREDITS_ANGLE_STD_MAX = 8.0  # degrees

# Grouping / over-under detection
OVER_UNDER_MAX_GAP_Y = 0.012  # tune
OVER_UNDER_MIN_X_OVERLAP = 0.65  # tune

# Lexical anchors (boost only)
CREDITS_ROLE_ANCHORS = [
    "directed by",
    "written by",
    "screenplay by",
    "story by",
    "produced by",
    "executive producer",
    "executive producers",
    "director of photography",
    "production designer",
    "music by",
    "edited by",
    "casting by",
    "based on",
    "a film by",
]
