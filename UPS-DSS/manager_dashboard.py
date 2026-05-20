import streamlit as st
from optimizationpanel_app import render_optimization_panel
from improve_solution_app import render_improve_solution
from daily_routing_app import render_daily_routing
from src.dashboard_daily import render_daily_operating_dashboard
from src.dashboard_strategic import render_strategic_dashboard
import pandas as pd
from pathlib import Path


def render_home():
    st.markdown("""
        <h1 style="
            color:#5A3418;
            font-weight:800;
            letter-spacing:0.5px;
            margin-bottom:10px;
        ">
            Welcome to UPS Decision Support System
        </h1>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Active AP", "7")
    col2.metric("Vehicles", "3")
    col3.metric("Last Cost", "1250")
    col4.metric("Dmax", "18.4")

    st.markdown("---")



def render_applications():
    st.title("Requests")

    applications_file = Path("applications.xlsx")

    if applications_file.exists():
        df = pd.read_excel(applications_file)

        st.subheader("Application List")

        st.dataframe(
            df,
            width="stretch",
            hide_index=True
        )

        with open(applications_file, "rb") as file:
            st.download_button(
                label="Download Applications as Excel",
                data=file,
                file_name="applications.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No applications found yet.")


def render_manager_dashboard():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        background-color: #f6f1eb;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #2b2b2b !important;
        padding: 12px 8px !important;
        margin-bottom: 18px !important;
        box-shadow: none !important;
        height: auto !important;
        width: 100% !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #eee5dc !important;
        color: #5A3418 !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] .stButton > button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if "manager_page" not in st.session_state:
        st.session_state.manager_page = "Daily Operating Dashboard"

    with st.sidebar:
        if st.button("Daily Operating Dashboard", key="menu_daily_dashboard"):
            st.session_state.manager_page = "Daily Operating Dashboard"
        
        if st.button("Strategic Dashboard", key="menu_strategic_dashboard"):
           st.session_state.manager_page = "Strategic Dashboard"

        if st.button("Optimization Panel", key="menu_optimization"):
            st.session_state.manager_page = "Optimization Panel"

        if st.button("Re-optimization Panel", key="menu_improve_solution"):
            st.session_state.manager_page = "Re-optimization Panel"

        if st.button("Daily Routing", key="menu_daily_routing"):
            st.session_state.manager_page = "Daily Routing"

        if st.button("Requests", key="menu_requests"):
            st.session_state.manager_page = "Requests"

        st.markdown("---")

        if st.button("Logout", key="menu_logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.view = "intro"
            st.rerun()

    page = st.session_state.manager_page

    if page == "Daily Operating Dashboard":
        render_daily_operating_dashboard()
    elif page == "Strategic Dashboard":
        render_strategic_dashboard()
    elif page == "Optimization Panel":
        render_optimization_panel()
    elif page == "Re-optimization Panel":
        render_improve_solution()
    elif page == "Daily Routing":
        render_daily_routing()
    elif page == "Requests":
        render_applications()