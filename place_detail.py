import html
import streamlit as st
import database


def fetch_place_by_id(place_id):
    rows = database.execute_query(
        "SELECT * FROM places WHERE id = %s",
        (place_id,),
        fetch=True,
    )
    return rows[0] if rows else None


def render_place_modal(place):
    with st.container(key="place_modal"):
        with st.container(key="place_modal_close"):
            if st.button("✕", key="close_place_modal"):
                st.session_state.pop("selected_place_id", None)
                st.rerun()

        image = html.escape(
            place.get("image_url") or "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?auto=format&fit=crop&w=1400&q=85",
            quote=True,
        )
        category = html.escape(str(place.get("category", "LOCAL FIND"))).upper()
        title = html.escape(str(place.get("place_name", "Untitled place")))
        area = html.escape(str(place.get("area", "Mumbai")))
        best_time = html.escape(str(place.get("best_time") or "Anytime"))
        entry_fee = html.escape(str(place.get("entry_fee") or "Free"))
        best_for_raw = place.get("best_for") or place.get("category") or "Local find"
        best_for_tags = [t.strip() for t in str(best_for_raw).split(",") if t.strip()]
        description = html.escape(str(place.get("description", "")))
        map_url = place.get("map_url")

        st.markdown(f"<img class='detail-photo' src='{image}' alt='{title}'>", unsafe_allow_html=True)

        st.markdown(
            f"<span class='place-tag'>{category}</span>"
            f"<h1 class='detail-title'>{title}</h1>"
            f"<div class='place-meta'>⌖ {area}</div>",
            unsafe_allow_html=True,
        )

        best_for_html = "".join(f"<span class='chip'>{html.escape(t)}</span>" for t in best_for_tags)
        st.markdown(
            f"""
            <div class='detail-chips'>
                <div class='detail-chip'><span class='detail-chip-label'>⏱ Best time</span><b>{best_time}</b></div>
                <div class='detail-chip'><span class='detail-chip-label'>₹ Entry Fee</span><b>{entry_fee}</b></div>
                <div class='detail-chip'><span class='detail-chip-label'>◎ Best For</span><div class='detail-chip-tags'>{best_for_html}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div class='detail-about'><h3>About</h3><p>{description}</p></div>",
            unsafe_allow_html=True,
        )

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if map_url:
                st.link_button("📍 View Location", map_url, use_container_width=True)
            else:
                st.button(" Location not available", disabled=True, use_container_width=True)
        with action_col2:
            if st.button(" Ask BODA for a plan", key="ask_boda_about_place", type="primary", use_container_width=True):
                st.query_params["boda_query"] = f"Tell me about {place.get('place_name', '')} in {place.get('area', '')} and suggest a plan around it"
                st.query_params["page"] = "assistant"
                st.session_state.pop("selected_place_id", None)
                st.rerun()


def render_selected_place_modal():
    """Call this once near the end of a page's render_page(). If a card
    was tapped (selected_place_id is set in session state), this renders
    the popup on top of everything else on the page."""
    selected_place_id = st.session_state.get("selected_place_id")
    if not selected_place_id:
        return
    place = fetch_place_by_id(selected_place_id)
    if place:
        render_place_modal(place)
    else:
        # The id didn't resolve to a real row - clear it silently.
        st.session_state.pop("selected_place_id", None)