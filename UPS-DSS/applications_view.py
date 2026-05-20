import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime


APPLICATIONS_FILE = Path("applications.xlsx")


def save_application(data):
    new_row = pd.DataFrame([data])

    if APPLICATIONS_FILE.exists():
        old_data = pd.read_excel(APPLICATIONS_FILE)
        updated_data = pd.concat([old_data, new_row], ignore_index=True)
    else:
        updated_data = new_row

    with pd.ExcelWriter(APPLICATIONS_FILE, engine="xlsxwriter") as writer:
        updated_data.to_excel(
            writer,
            index=False,
            sheet_name="Applications",
            startrow=1,
            header=False
        )

        workbook = writer.book
        worksheet = writer.sheets["Applications"]

        max_row, max_col = updated_data.shape

        columns = [{"header": col} for col in updated_data.columns]

        worksheet.add_table(
            0,
            0,
            max_row,
            max_col - 1,
            {
                "columns": columns,
                "style": "Table Style Medium 9"
            }
        )

        worksheet.set_column(0, max_col - 1, 22)
        worksheet.set_column(7, 8, 35)


def render_applications_page():
    st.markdown('<div class="page-title">Access Point Request Form</div>', unsafe_allow_html=True)

    st.markdown("### Personal Information")

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name")
    with col2:
        last_name = st.text_input("Last Name")

    col3, col4 = st.columns(2)
    with col3:
        email = st.text_input("Email Address")
    with col4:
        phone = st.text_input("Mobile Phone")

    st.markdown("### Access Point Location Address")

    col5, col6 = st.columns(2)
    with col5:
        province = st.text_input("Province")
    with col6:
        district = st.text_input("District")

    st.markdown("### Full Address for Installation")
    address = st.text_area("Enter full address")

    st.markdown("### Upload Area Photo")
    photo = st.file_uploader("Upload Photo", type=["jpg", "png", "jpeg"])

    st.markdown("### Location Details")
    site_name = st.text_input("Residential Complex / Site / Apartment Name")

    if st.button("Submit Application"):
        if not first_name or not last_name or not email or not phone or not province or not district or not address:
            st.error("Please fill in all required fields.")
        else:
            data = {
                "Submission Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "First Name": first_name,
                "Last Name": last_name,
                "Email Address": email,
                "Mobile Phone": phone,
                "Province": province,
                "District": district,
                "Full Address": address,
                "Residential Complex / Site / Apartment Name": site_name,
                "Photo Uploaded": "Yes" if photo else "No"
            }

            save_application(data)
            st.success("Application submitted successfully!")