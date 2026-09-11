import streamlit as st


NEIGHBOURHOODS = [
    {
        "name": "Bandra West",
        "vibe": "Old bungalows, indie cafés and the city's most photographed street corners.",
        "best_time": "Evening",
        "getting_there": "Bandra station (Western Line)",
        "known_for": ["Cafés", "Street art", "Nightlife"],
    },
    {
        "name": "Colaba",
        "vibe": "Colonial-era streets, art galleries and the Gateway of India crowd.",
        "best_time": "Morning to early evening",
        "getting_there": "Churchgate or CST station, then a 15-20 min walk",
        "known_for": ["Heritage architecture", "Art galleries", "Street shopping"],
    },
    {
        "name": "Marine Drive",
        "vibe": "The city's sweeping sea-facing promenade, best watched at sunset.",
        "best_time": "Evening, around sunset",
        "getting_there": "Churchgate station, 5 min walk",
        "known_for": ["Sea views", "Evening walks", "Queen's Necklace lights"],
    },
    {
        "name": "Churchgate",
        "vibe": "Business-district energy by day, heritage buildings all around.",
        "best_time": "Weekday mornings",
        "getting_there": "Churchgate station (Western Line terminus)",
        "known_for": ["Colonial architecture", "Irani cafés", "Local eateries"],
    },
    {
        "name": "Fort",
        "vibe": "Cobbled lanes, colonial facades and the city's oldest institutions.",
        "best_time": "Morning",
        "getting_there": "CST or Churchgate station, short walk",
        "known_for": ["Heritage buildings", "Bookshops", "Old cafés"],
    },
    {
        "name": "Juhu",
        "vibe": "A wide beach, film-industry landmarks and lively sunset crowds.",
        "best_time": "Evening",
        "getting_there": "Vile Parle or Santacruz station, then an auto",
        "known_for": ["Beach walks", "Street food", "Bollywood spotting"],
    },
    {
        "name": "Worli",
        "vibe": "Sea Link views, old fishing-village roots and new-Mumbai skyline.",
        "best_time": "Evening",
        "getting_there": "Prabhadevi station, then an auto to Worli Naka",
        "known_for": ["Sea Link views", "Koliwada fishing village", "Rooftop spots"],
    },
    {
        "name": "Malabar Hill",
        "vibe": "Leafy, upscale and quiet, with some of the best views in the city.",
        "best_time": "Morning or evening",
        "getting_there": "Charni Road station, then an auto/taxi uphill",
        "known_for": ["Hanging Gardens", "City views", "Quiet walks"],
    },
    {
        "name": "Andheri West",
        "vibe": "Busy and commercial, with good food if you know where to look.",
        "best_time": "Evening",
        "getting_there": "Andheri station (Western Line)",
        "known_for": ["Nightlife", "Restaurants", "Shopping"],
    },
    {
        "name": "Powai",
        "vibe": "A lake, a business-park skyline and a more laid-back pace.",
        "best_time": "Evening",
        "getting_there": "Kanjurmarg or Vikhroli station, then an auto",
        "known_for": ["Lakeside walks", "Cafés", "IIT Bombay campus"],
    },
]


def render_page():
    st.markdown(
        "<div class='eyebrow'>NEIGHBOURHOOD BY NEIGHBOURHOOD</div>"
        "<h1 class='display-title'>Know the <em>area</em>, not just the address.</h1>"
        "<p class='lede'>Ten neighbourhoods worth knowing before you pick where to spend your day.</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='section-heading'><h2>Pick a neighbourhood</h2><p>VIBE, TIMING &amp; HOW TO GET THERE</p></div>",
        unsafe_allow_html=True,
    )

    for row_start in range(0, len(NEIGHBOURHOODS), 2):
        row = NEIGHBOURHOODS[row_start:row_start + 2]
        for column, area in zip(st.columns(2), row):
            with column:
                tags_html = "".join(f"<span class='chip'>{tag}</span>" for tag in area["known_for"])
                st.markdown(
                    f"""
                    <article class='guide-card neighbourhood-card'>
                        <h3>{area['name']}</h3>
                        <p>{area['vibe']}</p>
                        <div class='neighbourhood-meta'>
                            <span><b>Best time</b> · {area['best_time']}</span>
                            <span><b>Getting there</b> · {area['getting_there']}</span>
                        </div>
                        <div class='neighbourhood-tags'>{tags_html}</div>
                    </article>
                    """,
                    unsafe_allow_html=True,
                )