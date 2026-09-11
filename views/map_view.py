import html
import streamlit as st

import database

REGIONS = [
    "Aarey","Airoli","Ambernath","Andheri East","Andheri West","Arnala","virar","Badlapur","Bandra / Worli",
    "Bandra West","Bhandup","Bhendi Bazaar","Bhuleshwar","Bordi","Borivali","Borivali East","Byculla","CBD Belapur",
    "Charni Road","Churchgate","Colaba","Dahanu","Dharavi","Fort","Gamdevi","Gharapuri","Girgaon","Gorai",
    "Goregaon","Goregaon East","Jawhar","Juhu","Junnar","Kala Ghoda","Kalyan","Kalyan / Badlapur","Karjat",
    "Kelva","Kharghar","Madh","Madh Island","Mahalaxmi","Mahim","Malabar Hill","Malad West","Manori","Marine Drive",
    "Masjid Bunder","Matheran","Mazgaon","Mumbra","Murbad","Murbad / Ahmednagar","Nariman Point","Navi Mumbai",
    "Nerul","Palghar","Panvel","Powai","Powai / SGNP","Prabhadevi","Pune / MMR Excursion","Raigad","Sewri",
    "Shahapur","Thane","Thane / Navi Mumbai","Thane / Pune Border","Thane Creek","Vajreshwari","Vasai","Vashi",
    "Versova","Walkeshwar","Worli"]


def render_page():
    st.markdown("<div class='eyebrow'>CHOOSE A PIN</div>"
    "<h1 class='display-title'>EXPLORE BY LOCATION"
    "<em>\nDiscover places near you.</em></h1>"
    "<p class='lede'>Choose an area in Mumbai or search for a location " \
    "\nto discover interesting places nearby.</p>", unsafe_allow_html=True)

    region = st.selectbox("Search or select an area", REGIONS)
    places = database.find_places(area=region)
    st.markdown(f"<div class='section-heading'><h2>{html.escape(region)}</h2><p>{len(places)} PLACES ON THE MAP</p></div>", unsafe_allow_html=True)
    if not places: st.info("Nothing is pinned here yet. Try a nearby neighbourhood."); return
    for row in range(0, len(places), 3):
        for column, place in zip(st.columns(3), places[row:row+3]):
            with column:
                image = html.escape(place.get("image_url") or "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?auto=format&fit=crop&w=900&q=80", quote=True)
                st.markdown(f"""<article class='map-place-card'>
                    <img src='{image}' alt=''>
                    <div class='map-place-copy'>
                        <span class='place-tag'>{html.escape(place.get('category','LOCAL FIND')).upper()}</span>
                        <h3>{html.escape(place.get('place_name','Untitled place'))}</h3>
                        <div class='place-meta'>⌖ {html.escape(place.get('best_time','Any time'))}</div>
                        <p>{html.escape(place.get('description',''))}</p>
                    </div>
                </article>""", unsafe_allow_html=True)
