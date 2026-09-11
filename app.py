from pathlib import Path
import base64

import streamlit as st

import ui
from views import admin, assistant, city_guide, home, map_view


st.set_page_config(
    page_title="BODA personally mapped",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_asset(name: str) -> str:
    return (Path(__file__).parent / "assets" / name).read_text(encoding="utf-8")


@st.cache_data
def build_hero_photo_css() -> str:
    """Read every image in assets/hero, embed it as base64, and emit one
    CSS class per photo (.hero-photo-1, .hero-photo-2, ...). Embedding the
    bytes directly means the browser never makes a network request for
    these images, so hotlink protection on the original source can't
    break anything. Cached so Streamlit doesn't re-read + re-encode all
    17 files on every rerun/interaction in production."""
    hero_dir = Path(__file__).parent / "assets" / "hero"
    if not hero_dir.is_dir():
        return ""

    ext_to_mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
    rules = []
    for index, path in enumerate(sorted(hero_dir.iterdir()), start=1):
        mime = ext_to_mime.get(path.suffix.lower())
        if mime is None:
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        rules.append(
            f".hero-photo-{index} {{ background-image: url(data:image/{mime};base64,{encoded}); }}"
        )
    return "\n".join(rules)


st.markdown(
    f"<style>{load_asset('styles.css')}\n{build_hero_photo_css()}</style>",
    unsafe_allow_html=True,
)

# This was defined in ui.py but never actually called anywhere — which meant
# interactions.js (hero photo crossfade, reveal animations, etc.) never ran
# on any page. Calling it here means it runs on every page load.
ui.city_signal()

# ----------------------------------------------------------------------
# CATCH CUSTOM HTML QUERY PARAMS & MAINTAIN ROUTING STATE
# ----------------------------------------------------------------------
query_params = st.query_params
if "boda_query" in query_params or query_params.get("page") == "assistant":
    st.session_state["current_page"] = "Ask BODA"

# Standard session state initializations
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("selected_mood", "Photography")
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("current_page", "Discover Mumbai")

PAGES = {
    "Discover Mumbai": ("✦", home.render_page),
    "City Guide": ("◌", city_guide.render_page),
    "Explore Map": ("⌖", map_view.render_page),
    "Ask BODA": ("✦", assistant.render_page),
    "Admin": ("◫", admin.render_page),
}

# Callback for top navigation radio buttons
def on_radio_change():
    st.session_state["current_page"] = st.session_state["nav_radio"]

# Callback for the "Ask BODA" button
def go_to_assistant():
    st.session_state["current_page"] = "Ask BODA"

active_page = st.session_state.get("current_page", "Discover Mumbai")

# ONLY RENDER STANDARD HEADER ON MAIN WEBSITE PAGES
if active_page != "Ask BODA":
    with st.container(key="site_header"):
        brand_column, navigation_column, action_column = st.columns([1.45, 3.7, 1], vertical_alignment="center")

        with brand_column:
            st.markdown("<div class='brand-mark'>BODA<span>.</span><small>MUMBAI, PERSONALLY MAPPED</small></div>", unsafe_allow_html=True)

        with navigation_column:
            radio_options = ["Discover Mumbai", "City Guide", "Explore Map"]
            default_idx = radio_options.index(active_page) if active_page in radio_options else 0

            st.radio(
                "Navigation Menu", 
                radio_options, 
                index=default_idx,
                horizontal=True, 
                label_visibility="collapsed", 
                key="nav_radio",
                on_change=on_radio_change
            )

        with action_column:
            st.button(
                "Ask BODA  →", 
                type="primary", 
                use_container_width=True, 
                key="header_ai",
                on_click=go_to_assistant
            )

        st.markdown("<div class='top-nav-rule'></div>", unsafe_allow_html=True)

# Render active page view
if active_page in PAGES:
    PAGES[active_page][1]()