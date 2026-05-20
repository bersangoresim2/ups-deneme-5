import streamlit as st

import requests
import time
import streamlit.components.v1 as components
import pandas as pd
# ALTAR BAŞLANGIÇ
def render_delivery_panel():
    st.title("Delivery Panel")
    st.write("Today's assigned routes are shown below.")

    if st.button("🔄 Refresh Route", use_container_width=True):
        st.rerun()

    url = f"https://api.jsonbin.io/v3/b/6a00cd28adc21f119a7e6bb9/latest?_t={time.time()}"
    headers = {
        "X-Master-Key": "$2a$10$T72jRhqyg.phWLbuSxdMVe.PQpnDi8BN6pEU/Sa7KaJvevaHK5eyO" 
    }
# ALTAR BİTİŞ
    try:
        with st.spinner("Fetching latest routes from cloud storage."):
            response = requests.get(url, headers=headers)
            
        if response.status_code == 200:
            hazir_rota = response.json().get("record", {})
            
            # ALTAR BAŞLANGIÇ: "Routes ready" yeşil kutusu ve Customer Assignments tablosu bu aralıktan tamamen kaldırıldı.
            distance_info = hazir_rota.get("total_distance", "")
            st.markdown(f"<p style='color:#5A3418; font-size:18px;'><b>Distance:</b> {distance_info}</p>", unsafe_allow_html=True)
            
            if "map_html" in hazir_rota and hazir_rota["map_html"]:
                st.markdown("<p style='color:#5A3418; font-size:18px; margin-top:20px;'><b>Google Maps Route View:</b></p>", unsafe_allow_html=True)
                components.html(hazir_rota["map_html"], height=620)

            if "google_links" in hazir_rota and hazir_rota["google_links"]:
                st.markdown("<p style='color:#5A3418; font-size:18px; margin-top:20px;'><b>Google Maps Road Directions:</b></p>", unsafe_allow_html=True)
                for vehicle, link_data in hazir_rota["google_links"].items():
                    url_link = link_data["url"]
                    st.markdown(f"**Vehicle {vehicle}:** [📍 Open in Google Maps]({url_link})")
            # ALTAR BİTİŞ
                    
        else:
            st.warning("No fast routing result is available yet. Please ask the manager to run fast routing first.")
            
    except Exception as e:
        st.error("Could not connect to cloud storage. Please check your internet connection.")