import streamlit as st
import database

def render_page():
    st.markdown("##  Administrative Master Operations Control Console")
    
    tab1, tab2 = st.tabs(["Manage Hidden Records Database", "Live User Search Streams"])
    
    with tab1:
        st.markdown("### Insert New Verified Local Identity Spot")
        with st.form("add_place_form", clear_on_submit=True):
            p_name = st.text_input("Place Name")
            p_area = st.selectbox("Target Sector Area", ["South Mumbai", "Bandra", "Andheri", "Goregaon", "Borivali", "Navi Mumbai","Malabar Hill"])
            p_cat = st.selectbox("Primary Category Classification Mapping", ["Nature", "Food", "Photography", "Adventure", "Romantic", "Family"])
            p_budget = st.selectbox("Financial Class Tier", ["Low", "Medium", "High"])
            p_time = st.text_input("Best Temporal Visit Window (e.g., 5 AM - 8 AM)")
            p_desc = st.text_area("Internal Description Paragraph")
            p_img = st.text_input("External Image Address URL Source")
            
            submitted = st.form_submit_button("Commit Asset Record to Database")
            if submitted:
                q = "INSERT INTO places (place_name, area, category, budget, best_time, description, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                database.execute_query(q, (p_name, p_area, p_cat, p_budget, p_time, p_desc, p_img))
                st.success(f"Successfully recorded data entity: {p_name}")

    with tab2:
        st.markdown("### Aggregated Telemetry Log Queries")
        logs = database.execute_query("SELECT * FROM search_history ORDER BY created_at DESC LIMIT 50", fetch=True)
        if logs:
            st.table(logs)
        else:
            st.info("No queries tracked across runtime context matrices yet.")