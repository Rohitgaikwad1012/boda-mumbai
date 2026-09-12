import html
import streamlit as st
import database
import place_detail

# Clean list of mood strings without icons
MOODS = ["Nature", "Photography", "Adventure", "Romantic", "Family"]


def _render_place_card(place):
    """Render one card plus an invisible full-cover button on top of it
    (see the CSS rule for div[data-testid='column']:has(article.glass-card)
    in styles.css) so tapping anywhere on the card opens the detail view."""
    image = html.escape(
        place.get("image_url") or "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?auto=format&fit=crop&w=900&q=80",
        quote=True,
    )
    st.markdown(
        f"<article class='glass-card'>"
        f"<img src='{image}' alt='' style='height:190px;object-fit:cover;width:100%'>"
        f"<div class='place-copy'>"
        f"<span class='place-tag'>{html.escape(place.get('category', 'LOCAL FIND')).upper()}</span>"
        f"<h3 class='place-title'>{html.escape(place.get('place_name', 'Untitled place'))}</h3>"
        f"<div class='place-meta'>{html.escape(place.get('area', 'Mumbai'))} · {html.escape(place.get('best_time', 'Any time'))}</div>"
        f"<p>{html.escape(place.get('description', ''))}</p>"
        f"</div>"
        f"</article>",
        unsafe_allow_html=True,
    )
    if st.button(
        place.get("place_name", "View place"),
        key=f"place_card_{place['id']}",
    ):
        st.session_state.selected_place_id = place["id"]
        st.rerun()


def render_page():
    # Initialize default selected_mood to prevent KeyError
    if "selected_mood" not in st.session_state:
        st.session_state.selected_mood = "Nature"

    st.markdown("""<section class='hero'><div class='eyebrow'>MUMBAI / DISCOVER DIFFERENT</div><h1 class='display-title'>
    Explore Mumbai,\n<em>your way.</em></h1><p class='lede'>
    Discover places to visit, local food, hidden spots, and experiences — all in one personalized city guide.</p>
    <div class='metric'><b>∞</b><span>Plan your day. Discover more.</span></div></section>""", unsafe_allow_html=True)
    
    st.markdown("<div class='section-heading'><h2>Choose a feeling</h2><p>YOUR MOOD SHAPES THE MAP</p></div>", unsafe_allow_html=True)
    
    # Top spacing to push the buttons down slightly from heading
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    
    # 5 equal columns matching len(MOODS)
    columns = st.columns(len(MOODS))
    for column, mood in zip(columns, MOODS):
        with column:
            active = (st.session_state.selected_mood == mood)
            # Set type to 'primary' for the selected mood to give it the lime highlight
            btn_type = "primary" if active else "secondary"
            
            if st.button(mood, key=f"mood_{mood}", type=btn_type, use_container_width=True):
                st.session_state.selected_mood = mood
                st.rerun()

    # Bottom spacing to separate buttons from the expander box below
    st.markdown("<div style='margin-bottom: 22px;'></div>", unsafe_allow_html=True)

    with st.expander("Fine tune your day", expanded=False):
        with st.form("preferences"):
            a, b, c = st.columns(3)
            name = a.text_input("Your name", value="Explorer")
            area = a.selectbox("Starting from", ["South Mumbai", "Bandra", "Andheri", "Goregaon", "Borivali", "Navi Mumbai"])
            budget = b.selectbox("Budget", ["Low", "Medium", "High"])
            duration = b.selectbox("Time available", ["2 hours", "4 hours", "A full day"])
            group = c.selectbox("Going with", ["Solo", "Friends", "Couple", "Family"])
            saved = st.form_submit_button("Save my preferences", use_container_width=True)

        if saved:
            user_id = database.create_preference(name, area, budget, st.session_state.selected_mood, group, duration)
            if user_id: 
                st.session_state.user_id = user_id
            st.toast("Your city profile is ready.")

    st.markdown(f"<div class='section-heading'><h2>For your {st.session_state.selected_mood.lower()} side</h2><p>LOCAL FINDS, NOT TOURIST TICKS</p></div>", unsafe_allow_html=True)
    
    places = database.find_places(st.session_state.selected_mood)
    if not places:
        st.info("No matching places are in the collection yet. Try another feeling or add one through Admin.")
        return

    for row in range(0, len(places), 3):
        for column, place in zip(st.columns(3), places[row:row+3]):
            with column:
                _render_place_card(place)
        st.markdown("<div class='card-row-gap'></div>", unsafe_allow_html=True)

    # A card was tapped -> render the popup on top of everything above,
    # instead of replacing the page.
    place_detail.render_selected_place_modal()