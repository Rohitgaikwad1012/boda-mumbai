from pathlib import Path

import streamlit.components.v1 as components


def city_signal():
    script = (Path(__file__).parent / "assets" / "interactions.js").read_text(encoding="utf-8")
    components.html(
        f"""<style>
        *{{box-sizing:border-box}}body{{background:transparent;margin:0;font-family:Arial,sans-serif}}
        .city-signal{{align-items:center;background:#191a19;border:1px solid rgba(247,243,237,.12);border-radius:12px;color:#aaa49d;cursor:pointer;display:flex;font-size:11px;justify-content:space-between;letter-spacing:1.8px;padding:13px 16px;text-transform:uppercase;transition:.25s}}
        .city-signal:hover,.city-signal--awake{{border-color:rgba(216,251,85,.65);color:#f7f3ed}}.pulse{{background:#d8fb55;border-radius:50%;box-shadow:0 0 0 0 rgba(216,251,85,.5);height:8px;width:8px}}.city-signal--awake .pulse{{animation:pulse 1.4s infinite}}@keyframes pulse{{70%{{box-shadow:0 0 0 8px rgba(216,251,85,0)}}100%{{box-shadow:0 0 0 0 rgba(216,251,85,0)}}}}
        </style><div class='city-signal' data-boda-reveal><span>Mumbai signal · tap to wake</span><span class='pulse'></span></div><script>{script}</script>""",
        height=49,
    )
