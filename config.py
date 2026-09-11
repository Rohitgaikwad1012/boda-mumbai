import streamlit as st

MYSQL_HOST = st.secrets["MYSQL_HOST"]
MYSQL_PORT = int(st.secrets["MYSQL_PORT"])
MYSQL_USER = st.secrets["MYSQL_USER"]
MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
MYSQL_DATABASE = st.secrets["MYSQL_DATABASE"]

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]