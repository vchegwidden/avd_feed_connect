"""On-disk persistence for the GUI.

Holds the saved workspace list (so reopening shows the grid instantly, like the
Windows App), per-resource icon PNGs, and the display/connection preferences,
plus the option lists for the settings dialog. Everything lives next to the
token cache under the app data dir.

These helpers are deliberately free of any session state: ``save_ws_cache`` is
handed the UPN to store, and ``load_ws_cache`` returns the cached UPN for the
caller to adopt — so this module never reaches into the client.
"""

import json
import os
import re
import urllib.request

from .. import config, http

WS_CACHE = os.path.join(os.path.dirname(config.CACHE), "workspaces.json")
ICON_DIR = os.path.join(os.path.dirname(config.CACHE), "icons")
SETTINGS_FILE = os.path.join(os.path.dirname(config.CACHE), "settings.json")

# Option lists for the per-resource settings dialog (label shown, value stored).
SCALE_LABELS = ["Automatic (match display)", "100%", "125%", "150%",
                "175%", "200%", "250%", "300%"]
SCALE_VALUES = ["auto", "100", "125", "150", "175", "200", "250", "300"]
MULTIMON_LABELS = ["Automatic (match monitors)", "Single monitor", "All monitors"]
MULTIMON_VALUES = ["auto", "off", "on"]
# Server-certificate handling. Anything but "ignore" pins the host cert on first
# connect (FreeRDP /cert:tofu); "ignore" turns the check off (/cert:ignore) — the
# escape hatch for host pools whose session-host certs rotate. "auto" inherits the
# default, which is itself verify, so the secure mode is the out-of-the-box one.
CERT_LABELS = ["Automatic (verify)", "Verify", "Don't verify (if you can't connect)"]
CERT_VALUES = ["auto", "verify", "ignore"]
# sdl-freerdp's own Right Shift + key shortcuts (D disconnects the session, Enter
# toggles fullscreen). "auto" leaves FreeRDP's config untouched; "off" passes every
# key through to the remote desktop.
HOTKEY_LABELS = ["Automatic (FreeRDP default)", "Enabled (Right Shift + key)",
                 "Disabled (send all keys to the PC)"]
HOTKEY_VALUES = ["auto", "on", "off"]


def icon_path(res_id):
    return os.path.join(ICON_DIR, re.sub(r"[^A-Za-z0-9_.-]", "_", res_id) + ".png")


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f)
    except OSError:
        pass


def save_ws_cache(resources, upn):
    try:
        os.makedirs(os.path.dirname(WS_CACHE), exist_ok=True)
        with open(WS_CACHE, "w") as f:
            json.dump({"upn": upn, "resources": resources}, f)
    except OSError:
        pass


def load_ws_cache():
    """Return ``(resources, cached_upn)``. ``cached_upn`` is ``""`` when absent;
    the caller decides whether to adopt it (only when no UPN is set yet)."""
    try:
        with open(WS_CACHE) as f:
            d = json.load(f)
        return d.get("resources") or [], d.get("upn") or ""
    except (OSError, ValueError):
        return [], ""


def bearer_bytes(url, token):
    """Binary GET with the approved UA headers (for icons; http.get decodes text)."""
    http.check_trusted(url)
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "*/*")
    req.add_header("User-Agent", config.MS_USER_AGENT)
    req.add_header("X-MS-User-Agent", config.MS_USER_AGENT)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()
