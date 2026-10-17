import html
import re
import sys
from pathlib import Path

# Fix relative import path for views directory
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import database
import gemini_service


def _query_box_html(query_text):
    return f"""
    <div style="
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 18px;
        margin: 15px 0 25px 0;
        color: #ffffff;
        font-size: 1rem;
        display: flex;
        align-items: center;
        gap: 12px;
    ">
        <span style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: rgba(163, 230, 53, 0.15);
            color: #a3e635;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            flex-shrink: 0;
        ">YOU</span>
        <div><strong>  </strong> {html.escape(query_text)}</div>
    </div>
    """


def _loading_box_html():
    return """
    <style>
    @keyframes bodaDotPulse { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }
    .boda-loading-dot { display: inline-block; width: 8px; height: 8px; margin-right: 6px; border-radius: 50%; background: #a3e635; animation: bodaDotPulse 1.2s infinite ease-in-out; }
    .boda-loading-dot:nth-child(2) { animation-delay: 0.2s; }
    .boda-loading-dot:nth-child(3) { animation-delay: 0.4s; }
    </style>
    <div style="
        display: flex;
        align-items: center;
        gap: 14px;
        background: linear-gradient(135deg, rgba(163, 230, 53, 0.08), rgba(255, 255, 255, 0.03));
        border: 1px solid rgba(163, 230, 53, 0.25);
        border-left: 3px solid #a3e635;
        border-radius: 14px;
        padding: 18px 24px;
        margin: 0 0 25px 0;
    ">
        <span style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #a3e635;
            color: #0f0f14;
            font-weight: 800;
            font-size: 1rem;
            flex-shrink: 0;
        ">B</span>
        <div style="color: #ffffff; font-size: 1.05rem;">
            Finding places and planning your route
            <span style="margin-left: 8px;"><span class="boda-loading-dot"></span><span class="boda-loading-dot"></span><span class="boda-loading-dot"></span></span>
        </div>
    </div>
    """


def _search_places_for_query(user_chat_input):
    # Clean search input and tokenize keywords
    clean_input = re.sub(r'[^a-zA-Z\s]', ' ', user_chat_input)
    raw_words = [w.strip().lower() for w in clean_input.split() if len(w.strip()) > 2]

    stop_words = {"have", "hrs", "hours", "in", "the", "for", "with", "and", "near", "find"}
    keywords = [w for w in raw_words if w not in stop_words]

    db_context_places = []
    if keywords:
        conditions = []
        params = []
        for word in keywords:
            conditions.append("(LOWER(TRIM(area)) LIKE %s OR LOWER(TRIM(place_name)) LIKE %s OR LOWER(TRIM(category)) LIKE %s)")
            pattern = f"%{word}%"
            params.extend([pattern, pattern, pattern])

        where_clause = " OR ".join(conditions)
        sql_query = f"SELECT * FROM places WHERE {where_clause} ORDER BY RAND() LIMIT 15"
        db_context_places = database.execute_query(sql_query, tuple(params), fetch=True) or []

    # Fallback broad search
    if not db_context_places:
        db_context_places = database.execute_query(
            "SELECT * FROM places WHERE LOWER(area) LIKE %s ORDER BY RAND() LIMIT 5",
            (f"%{user_chat_input.strip().lower()}%",),
            fetch=True
        ) or []

    return db_context_places


def _plan_trip_in_background():
    """Plans the trip WITHOUT blocking the page switch.

    pending_stage 1 : the page was just opened. Draw the question + a loading
                      card and return, so the page switch is instant.
    pending_stage 2 : the fragment timer fired. Do the slow work (database +
                      Gemini), save the result, then rerun the whole app.

    IMPORTANT: stage 2 must not call any st.* function before the work is
    finished. If it did, a queued timer rerun could interrupt it and the
    trip would be planned twice.
    """
    query = st.session_state.get("pending_query")
    stage = st.session_state.get("pending_stage", 0)
    if not query or not stage:
        return

    if stage == 1:
        st.markdown(_query_box_html(query), unsafe_allow_html=True)
        st.markdown(_loading_box_html(), unsafe_allow_html=True)
        st.session_state["pending_stage"] = 2
        return

    # ---- stage 2: the slow work ----
    st.session_state["pending_stage"] = 3  # nothing can start it a second time
    weather_state = st.session_state.get("weather_state", "Sunny")
    current_uid = st.session_state.get("user_id", 1) or 1

    ai_response = None
    db_context_places = []
    error_message = None

    # Log query to analytics
    try:
        database.execute_query(
            "INSERT INTO search_history (user_id, search_query) VALUES (%s, %s)",
            (current_uid, query)
        )
    except Exception:
        pass

    try:
        db_context_places = _search_places_for_query(query)
        ai_response = gemini_service.generate_ai_itinerary(
            query,
            db_context_places,
            current_weather=weather_state
        )
    except Exception as e:
        error_text = str(e)
        if "RESOURCE_EXHAUSTED" in error_text or "429" in error_text:
            error_message = "⚠️ Your Gemini API free trial limit is over for today. Please try again tomorrow."
        else:
            error_message = "Something went wrong while planning your trip. Please try again."
        ai_response = None

    st.session_state["active_query"] = query
    if ai_response is not None:
        st.session_state["active_response"] = ai_response
        st.session_state["active_db_places"] = db_context_places
    else:
        # Don't leave a stale/broken result behind.
        st.session_state.pop("active_response", None)
        st.session_state.pop("active_db_places", None)
    if error_message:
        st.session_state["ai_error"] = error_message

    st.session_state.pop("pending_query", None)
    st.session_state["pending_stage"] = 0
    st.rerun()  # inside a fragment this reruns the whole app, so the result shows


def render_page():
    # --- GLOBAL FONT: Poppins applied across the whole app (questions, answers, everything) ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp, .stMarkdown, p, div, span, input, textarea, button {
        font-family: 'Poppins', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- STANDALONE ASSISTANT HEADER ALIGNED TO ORIGINAL WEBSITE BRAND POSITION ---
    with st.container(key="assistant_header"):
        nav_col1, nav_col2 = st.columns([4, 1], vertical_alignment="center")

        with nav_col1:
            st.markdown("<div class='brand-mark' style='margin:0;'>BODA<span>.</span><small>AI TRAVEL ASSISTANT</small></div>", unsafe_allow_html=True)

        with nav_col2:
            if st.button("← Back to Website", key="back_to_site", use_container_width=True):
                st.session_state["current_page"] = "Discover Mumbai"
                if "active_response" in st.session_state:
                    del st.session_state["active_response"]
                st.session_state.pop("pending_query", None)
                st.session_state["pending_stage"] = 0
                st.session_state.pop("ai_error", None)
                st.rerun()

    st.markdown("<hr style='border:0; border-top:1px solid rgba(255,255,255,0.08); margin:15px 0 25px 0;' />", unsafe_allow_html=True)

    st.markdown("## BODA Travel Assistant")
    st.markdown("#### Plan your perfect Mumbai trip in seconds." \
    "\nTell me where you are, how much time you have, and what you want to explore.")
    
    weather_state = st.selectbox(
        "🌤️ Current Weather", 
        ["Sunny", "Rainy / Heavy Monsoons", "Overcast Dusk"],
        key="weather_state"
    )

    # Check query params for submissions from our custom HTML bar
    query_params = st.query_params
    submitted_query = query_params.get("boda_query", None)

    # The place popup ("Ask BODA for a plan") queues its question here.
    queued_query = st.session_state.pop("queued_boda_query", None)

    new_query = submitted_query or queued_query
    if new_query:
        if submitted_query:
            # Clear query param to prevent infinite refresh loops
            st.query_params.clear()

        # Only remember the question here. The slow part (database + Gemini)
        # runs in the background step below, so this page opens instantly.
        st.session_state["pending_query"] = new_query
        st.session_state["pending_stage"] = 1
        st.session_state.pop("active_response", None)
        st.session_state.pop("active_query", None)
        st.session_state.pop("active_db_places", None)
        st.session_state.pop("ai_error", None)

    if st.session_state.get("pending_stage", 0):
        if hasattr(st, "fragment"):
            st.fragment(run_every=0.15)(_plan_trip_in_background)()
        else:
            # Very old Streamlit without fragments: plan inline (slower).
            st.session_state["pending_stage"] = 2
            _plan_trip_in_background()

    if st.session_state.get("ai_error"):
        st.error(st.session_state["ai_error"])

    # RENDER STORED RESULT ON PAGE
    if "active_response" in st.session_state and st.session_state.active_response:
        query_text = st.session_state.active_query
        ai_response = st.session_state.active_response
        db_context_places = st.session_state.active_db_places

        st.markdown(_query_box_html(query_text), unsafe_allow_html=True)

        # Off-topic query (math, trivia, code, etc.) — show the fixed decline
        # message only, skip cards/itinerary/food/budget entirely.
        if not ai_response.get("is_travel_related", True):
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: flex-start;
                gap: 14px;
                background: linear-gradient(135deg, rgba(163, 230, 53, 0.08), rgba(255, 255, 255, 0.03));
                border: 1px solid rgba(163, 230, 53, 0.25);
                border-left: 3px solid #a3e635;
                border-radius: 14px;
                padding: 22px 24px;
                margin: 0 0 25px 0;
            ">
                <span style="
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    background: #a3e635;
                    color: #0f0f14;
                    font-weight: 800;
                    font-size: 1rem;
                    letter-spacing: 0.5px;
                    flex-shrink: 0;
                ">B</span>
                <div>
                    <div style="
                        color: #a3e635;
                        font-size: 0.75rem;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-bottom: 6px;
                    ">BODA</div>
                    <div style="
                        color: #ffffff;
                        font-size: 1.15rem;
                        line-height: 1.6;
                        font-weight: 400;
                        font-family: 'Poppins', sans-serif;
                    ">{html.escape(ai_response.get("decline_message", "I can only help you plan your Mumbai trip"))}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            recommended_ids = ai_response.get("recommended_place_ids", [])
            cards_to_show = [p for p in db_context_places if p.get("id") in recommended_ids]

            if not cards_to_show and db_context_places:
                cards_to_show = db_context_places[:3]

            if cards_to_show:
                st.markdown("### Featured Recommendations")
                cols = st.columns(len(cards_to_show))
                for col, place in zip(cols, cards_to_show):
                    with col:
                        img = html.escape(str(place.get("image_url") or "https://images.unsplash.com/photo-1567157577867-05ccb1388e66?auto=format&fit=crop&w=900&q=80"), quote=True)
                        cat = html.escape(str(place.get("category", "LOCAL FIND"))).upper()
                        title = html.escape(str(place.get("place_name", "Untitled")))
                        area = html.escape(str(place.get("area", "Mumbai")))
                        time_info = html.escape(str(place.get("best_time", "Anytime")))
                        desc = html.escape(str(place.get("description", "")))

                        st.markdown(f"""
                        <article class='glass-card'>
                            <img src='{img}' alt='{title}'>
                            <div class='place-copy'>
                                <span class='place-tag'>{cat}</span>
                                <div class='place-title'><strong>{title}</strong></div>
                                <div class='place-meta'>⌖ {area} · {time_info}</div>
                                <p>{desc}</p>
                            </div>
                        </article>
                        """, unsafe_allow_html=True)

            st.markdown("### Your Mumbai Travel Plan")
            itinerary = ai_response.get("itinerary", [])
            for item in itinerary:
                st.markdown(f"""
                <div class="timeline-item">
                    <span class="timeline-time">{item.get('time', '10:00 AM')}</span> — <strong>{item.get('action', 'Explore')}</strong>
                    <p style="margin:5px 0 0 0; color:#b0b0cc; font-size:0.95rem;">{item.get('description', '')}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("###  Local Food Guide")
            for food in ai_response.get("food_suggestions", []):
                st.markdown(f"*  {food}")

            st.markdown("###  Trip Cost Estimate")
            budget_data = ai_response.get("budget_breakdown", {})

            if isinstance(budget_data, dict) and budget_data:
                b_cols = st.columns(len(budget_data))
                for col, (k, v) in zip(b_cols, budget_data.items()):
                    with col:
                        st.markdown(f"""
                        <div style="
                            background: rgba(255, 255, 255, 0.04);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 10px;
                            padding: 12px;
                            text-align: center;
                            margin-bottom: 10px;
                        ">
                            <span style="font-size: 0.75rem; color: #8888aa; text-transform: uppercase; letter-spacing: 0.5px;">{k}</span>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #a3e635; margin-top: 4px;">{v}</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info(str(budget_data))

    # --- NON-REDIRECTING FLOATING SEARCH BAR ---
    st.markdown("""
    <div style="
        position: fixed;
        bottom: 25px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 620px;
        z-index: 99999;
    ">
        <form id="bodaHtmlForm" action="" method="GET" style="margin: 0;">
            <input type="hidden" name="page" value="assistant" />
            <div style="
                display: flex;
                align-items: center;
                background: rgba(18, 18, 24, 0.85);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 35px;
                padding: 6px 22px 6px 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
            ">
                <input 
                    type="text" 
                    name="boda_query" 
                    placeholder="Ask BODA: 'I have ₹1000, 5 hours in Bandra...'" 
                    required
                    style="
                        flex: 1;
                        background: transparent;
                        border: none;
                        outline: none;
                        color: #ffffff;
                        font-size: 0.95rem;
                        padding: 10px 12px;
                        font-family: inherit;
                    "
                />
                <button type="submit" style="
                    background: #a3e635;
                    border: none;
                    border-radius: 50%;
                    width: 38px;
                    height: 38px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    margin-left: 8px;
                    margin-right: 0;
                    transition: transform 0.2s ease;
                ">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </form>
    </div>
    """, unsafe_allow_html=True)