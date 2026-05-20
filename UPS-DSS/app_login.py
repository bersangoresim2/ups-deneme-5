import streamlit as st
from pathlib import Path
import base64
import json
from optimizationpanel_app import render_optimization_panel
from deliverypanel_app import render_delivery_panel
from manager_dashboard import render_manager_dashboard
from improve_solution_app import render_improve_solution
from src.dashboard_daily import render_daily_operating_dashboard
from applications_view import render_applications_page

st.set_page_config(page_title="UPS DSS", layout="wide")
st.markdown("""
<style>
[data-testid="stStatusWidget"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)
USERS_FILE = Path("users.json")


# -----------------------------
# Users
# -----------------------------
def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "manager1": {
            "password": "1234",
            "role": "decision_maker",
            "full_name": "Manager One",
            "phone_number": ""
        },
        "manager2": {
            "password": "5678",
            "role": "decision_maker",
            "full_name": "Manager Two",
            "phone_number": ""
        },
        "driver1": {
            "password": "abcd",
            "role": "delivery_staff",
            "full_name": "Driver One",
            "phone_number": ""
        },
        "driver2": {
            "password": "efgh",
            "role": "delivery_staff",
            "full_name": "Driver Two",
            "phone_number": ""
        },
    }


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


# -----------------------------
# Session state
# -----------------------------
if "view" not in st.session_state:
    st.session_state.view = "intro"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "role" not in st.session_state:
    st.session_state.role = ""

if "users" not in st.session_state:
    st.session_state.users = load_users()

if "language" not in st.session_state:
    st.session_state.language = "EN"

query_view = st.query_params.get("view")
allowed_views = {
    "intro",
    "about",
    "faq",
    "requests",
    "login",
    "manager_login",
    "delivery_login",
    "signup",
    "home",
}

if query_view in allowed_views and not st.session_state.logged_in:
    st.session_state.view = query_view


# -----------------------------
# Helpers
# -----------------------------
def go(view_name):
    st.session_state.view = view_name
    st.query_params["view"] = view_name

@st.cache_data
def get_base64_file(file_path):
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode()
def get_base64_image(image_path):
        return get_base64_file(str(image_path))


def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.view = "intro"
    st.query_params["view"] = "intro"
    


def login_user(username, password, expected_role):
    username = username.strip()
    users = st.session_state.users

    if username not in users:
        st.error("User not found.")
        return

    if users[username]["password"] != password:
        st.error("Invalid password.")
        return

    if users[username]["role"] != expected_role:
        st.error("This account does not belong to the selected login panel.")
        return

    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.role = users[username]["role"]
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    st.rerun()


def signup_user(username, password, role, full_name="", phone_number=""):
    users = st.session_state.users
    username = username.strip()

    if len(password) < 4:
        st.error("Password must be at least 4 characters long.")
        return

    if username in users:
        st.error("This username already exists.")
        return

    users[username] = {
        "password": password,
        "role": role,
        "full_name": full_name,
        "phone_number": phone_number
    }

    save_users(users)
    st.session_state.users = users
    st.success("Account created successfully. You can now log in.")
    st.session_state.view = "login"
    st.query_params["view"] = "login"
    st.rerun()


# -----------------------------
# Shared styling
# -----------------------------
def apply_shared_styles():
    background_css = ""

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: #FAF7F2;
        }}

        {background_css}

        .block-container {{
            position: relative;
            z-index: 1;
            padding-top: 1.5rem;
        }}

        .main-title {{
            text-align: center;
            color: #5A3418;
            font-size: 32px;
            font-weight: 850;
            margin-top: 8px;
            margin-bottom: 6px;
        }}

        .main-subtitle {{
            text-align: left;
            color: #7A5A45;
            font-size: 18px;
            margin-bottom: 28px;
        }}

        .page-title {{
            text-align: center;
            font-size: 32px;
            font-weight: 700;
            margin-top: 10px;
            margin-bottom: 8px;
            color: #5A3418;
        }}

        .page-subtitle {{
            text-align: center;
            font-size: 16px;
            color: #6B6B6B;
            margin-bottom: 30px;
        }}

        .card-title {{
            font-size: 22px;
            font-weight: 700;
            color: #5A3418;
            margin-bottom: 8px;
        }}

        .card-text {{
            color: #666666;
            font-size: 15px;
            margin-bottom: 18px;
        }}

        .demo-box {{
            background-color: #F2F2F2;
            border: 1px solid #E2E2E2;
            border-radius: 12px;
            padding: 14px 16px;
            margin-top: 24px;
        }}

        .choice-heading {{
            text-align: left;
            color: #5A3418;
            font-size: 22px;
            font-weight: 700;
            margin-top: 6px;
            margin-bottom: 10px;
        }}

        .auth-right-wrap {{
            max-width: 760px;
            margin-left: auto;
            margin-right: 40px;
            margin-top: 20px;
        }}

        .auth-panel {{
            background: #F2F2F2;
            border: 1px solid #E2E2E2;
            border-radius: 16px;
            padding: 28px 28px 24px 28px;
            box-shadow: none;
        }}

        .auth-heading {{
            text-align: left;
            color: #5A3418;
            font-size: 22px;
            font-weight: 1000;
            margin-top: 6px;
            margin-bottom: 10px;
        }}

        .auth-spacer {{
            height: 20px;
        }}

        .stButton > button {{
            background-color: transparent;
            color: #5A3418;
            border: 1.8px solid #5A3418;
            border-radius: 12px;
            height: 42px;
            font-size: 25px;
            font-weight: 1000;
            box-shadow: none;
        }}

        .stButton > button:hover {{
            background-color: #F7F1EC;
            color: #5A3418;
            border: 1.5px solid #5A3418;
        }}

        .stButton > button:focus {{
            outline: none;
            box-shadow: none;
            color: #5A3418;
            border: 1.5px solid #5A3418;
        }}

        div[data-testid="stTextInput"] input {{
            background-color: #ffffff;
            border: 1px solid #D8D8D8;
            border-radius: 10px;
        }}

        div[data-testid="stSelectbox"] > div {{
            background-color: #ffffff;
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# Intro menu
# -----------------------------
def render_intro_menu():
    logo_path = Path("assets/ups_logo.png")

    if logo_path.exists():
        logo_base64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="intro-nav-logo-img">'
    else:
        logo_html = "UPS DSS"

    st.html(f"""
<style>
.intro-nav {{
    position: fixed;
    top: 22px;
    left: 38px;
    right: 38px;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    pointer-events: auto;
}}

.intro-nav-left {{
    color: white;
    font-size: 30px;
    font-weight: 800;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
}}

.intro-nav-logo-img {{
    height: 100px;
    width: auto;
    display: block;
}}

.intro-nav-center {{
    display: flex;
    align-items: center;
    gap: 50px;
    margin-left: -80px;
}}

.intro-nav-center a {{
    color: white;
    text-decoration: none;
    font-size: 25px;
    font-weight: 600;
    padding-bottom: 6px;
    border-bottom: 2px solid transparent;
    transition: 0.2s ease;
}}

.intro-nav-center a:hover {{
    border-bottom: 2px solid white;
}}

.intro-nav-right {{
    color: white;
    font-size: 18px;
    font-weight: 600;
}}
</style>

<div class="intro-nav">
<div class="intro-nav-left">{logo_html}</div>
<div class="intro-nav-center">
<a href="?view=about" target="_self">About Us</a>
<a href="?view=faq" target="_self">FAQ</a>
<a href="?view=requests" target="_self">Requests</a>
<a href="?view=login" target="_self">User Login</a>
</div>
<div class="intro-nav-right">EN</div>
</div>
""")


# -----------------------------
# Intro page
# -----------------------------
def intro_page():
    video_path = Path("assets/intro_video.mp4")
    why_ups_path = Path("assets/why_ups.png")

    if not video_path.exists():
        st.error("Video file not found: assets/intro_video.mp4")
        return

    video_base64 = base64.b64encode(video_path.read_bytes()).decode()

    st.markdown(
        f"""
<style>
.main .block-container {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}}

header[data-testid="stHeader"] {{
    background: transparent !important;
}}

.stApp {{
    background: transparent !important;
}}

#MainMenu {{
    visibility: hidden;
}}

footer {{
    visibility: hidden;
}}

.video-background {{
    position: fixed;
    top: 10px;
    left: 0;
    width: 100vw;
    height: 100vh;
    object-fit: cover;
    z-index: -2;
    transform: scale(1.08);
}}

.video-overlay {{
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.62);
    z-index: -1;
}}

.intro-overlay-content {{
    position: relative;
    z-index: 5;
    min-height: 100vh;
    margin-top: -100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    pointer-events: none;
    padding-top: 120px;
    padding-bottom: 60px;
}}

.intro-inner {{
    pointer-events: auto;
    max-width: 1200px;
    padding: 0 24px;
}}

.intro-title {{
    color: white;
    font-size: 64px;
    font-weight: 800;
    line-height: 1.05;
    margin-bottom: 18px;
    text-shadow: 0 2px 16px rgba(0,0,0,0.45);
}}

.intro-subtitle {{
    color: white;
    font-size: 22px;
    line-height: 1.4;
    margin-bottom: 28px;
    text-shadow: 0 2px 12px rgba(0,0,0,0.35);
}}

.intro-extra-image {{
    margin-top: 550px;
    display: flex;
    justify-content: center;
}}

.intro-extra-image img {{
    width: min(700px, 70vw);
    height: auto;
    border-radius: 18px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.18);
}}
</style>

<video class="video-background" autoplay muted loop playsinline>
    <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
</video>
<div class="video-overlay"></div>

<div class="intro-overlay-content">
    <div class="intro-inner">
        <div class="intro-title">UPS Decision Support System</div>
        <div class="intro-subtitle">
            Smarter planning and delivery operations through a unified platform
        </div>
        {"<div class='intro-extra-image'><img src='data:image/png;base64," + base64.b64encode(why_ups_path.read_bytes()).decode() + "'></div>" if why_ups_path.exists() else "<div style='color:white; font-size:20px;'>why_ups.png not found in assets folder</div>"}
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    render_intro_menu()
# -----------------------------
# Login choice page
# -----------------------------
def login_page():
    apply_shared_styles()

    bg_path = Path("assets/login_bg.png")

    if bg_path.exists():
        bg_base64 = get_base64_image(bg_path)

        st.markdown(f"""
        <style>
        .stApp {{
            background:
                linear-gradient(rgba(250,247,242,0.75), rgba(250,247,242,0.75)),
                url("data:image/png;base64,{bg_base64}") center/cover no-repeat fixed !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        .main .block-container {{
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }}

        [data-testid="stHorizontalBlock"] {{
            gap: 0 !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 1], gap="small")

    with left_col:
        st.empty()

    with right_col:
        st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="main-title" style="text-align:center; margin-top:50px;">
                UPS Decision Support System
            </div>
            <div class="main-subtitle" style="text-align:center; margin-bottom:20px;">
                Access for planning and delivery operations
            </div>
            """,
            unsafe_allow_html=True
        )

        inner_left, inner_mid, inner_right = st.columns([0.08, 0.84, 0.08])

        with inner_mid:
            st.markdown(
                '<div class="auth-heading" style="margin-top:0px; margin-bottom:14px;">Please choose your user type</div>',
                unsafe_allow_html=True
            )

            st.button(
                "Manager Login",
                use_container_width=True,
                key="auth_manager_login_btn",
                on_click=lambda: go("manager_login")
            )

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

            st.button(
                "Delivery Staff Login",
                use_container_width=True,
                key="auth_delivery_login_btn",
                on_click=lambda: go("delivery_login")
            )

            st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

            back_left, back_mid, back_right = st.columns([0.2, 0.6, 0.2])
            with back_mid:
                st.button(
                    "Back",
                    use_container_width=True,
                    key="auth_back_btn",
                    on_click=lambda: go("intro")
                )
# -----------------------------
# Manager login page
# -----------------------------
def manager_login_page():
    apply_shared_styles()

    bg_path = Path("assets/login_devam.png")

    if bg_path.exists():
        bg_base64 = get_base64_image(bg_path)

        st.markdown(f"""
        <style>
        .stApp {{
            background:
                linear-gradient(rgba(250,247,242,0.70), rgba(250,247,242,0.70)),
                url("data:image/png;base64,{bg_base64}") center/cover no-repeat fixed !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        .main .block-container {{
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Manager Login</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Please sign in with your manager account.</div>',
        unsafe_allow_html=True
    )

    left_space, center_col, right_space = st.columns([0.9, 1.2, 0.9])

    with center_col:
        with st.container(border=True):
            username = st.text_input("Username", key="manager_username")
            password = st.text_input("Password", type="password", key="manager_password")

            if st.button("Login", width="stretch", key="manager_login_button"):
                login_user(username, password, "decision_maker")

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.button(
                "Back",
                width="stretch",
                key="manager_login_back_btn",
                on_click=lambda: go("login")
            )

# -----------------------------
# Delivery login page
# -----------------------------
def delivery_login_page():
    apply_shared_styles()

    bg_path = Path("assets/login_devam.png")

    if bg_path.exists():
        bg_base64 = get_base64_image(bg_path)

        st.markdown(f"""
        <style>
        .stApp {{
            background:
                linear-gradient(rgba(250,247,242,0.70), rgba(250,247,242,0.70)),
                url("data:image/png;base64,{bg_base64}") center/cover no-repeat fixed !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        .main .block-container {{
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Delivery Staff Login</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Please sign in with your delivery staff account.</div>',
        unsafe_allow_html=True
    )

    left_space, center_col, right_space = st.columns([0.9, 1.2, 0.9])

    with center_col:
        with st.container(border=True):
            username = st.text_input("Username", key="delivery_username")
            password = st.text_input("Password", type="password", key="delivery_password")

            if st.button("Login", width="stretch", key="delivery_login_button"):
                login_user(username, password, "delivery_staff")

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.button(
                "Back",
                width="stretch",
                key="delivery_login_back_btn",
                on_click=lambda: go("login")
            )
# -----------------------------
# Signup page
# -----------------------------
def signup_page():
    apply_shared_styles()

    
    st.markdown('<div class="page-title">Register</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Fill in the form below to create your account.</div>',
        unsafe_allow_html=True
    )

    left_space, center_col, right_space = st.columns([0.6, 1.3, 0.6])

    with center_col:
        with st.container(border=True):
            st.markdown('<div class="card-title">New Account Registration</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="card-text">Please enter your details below.</div>',
                unsafe_allow_html=True
            )

            full_name = st.text_input("Full Name *", key="signup_full_name")
            new_username = st.text_input("Username *", key="signup_username")
            phone_number = st.text_input("Phone Number", key="signup_phone")
            new_password = st.text_input("Password *", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password *", type="password", key="signup_confirm_password")

            role_options = {
                "Manager": "decision_maker",
                "Delivery Staff": "delivery_staff"
            }

            selected_role_label = st.selectbox(
                "Role *",
                list(role_options.keys()),
                index=None,
                placeholder="Select a role",
                key="signup_role"
            )

            new_role = None
            if selected_role_label is not None:
                new_role = role_options[selected_role_label]

            if st.button("Register", width="stretch", key="signup_create_button"):
                if not full_name.strip():
                    st.error("Full name cannot be empty.")
                elif not new_username.strip():
                    st.error("Username cannot be empty.")
                elif not new_password.strip():
                    st.error("Password cannot be empty.")
                elif not confirm_password.strip():
                    st.error("Please confirm your password.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif new_role is None:
                    st.error("Please select a role.")
                else:
                    signup_user(
                        username=new_username,
                        password=new_password,
                        role=new_role,
                        full_name=full_name,
                        phone_number=phone_number
                    )

            st.button("Back", width="stretch", key="signup_back_button", on_click=lambda: go("login"))


# -----------------------------
# About page
# -----------------------------
def about_page():
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 20px !important;
        padding-bottom: 40px !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }

    .stApp {
        background: #f7f4ef !important;
    }

    .about-title {
        text-align: center;
        font-size: 54px;
        font-weight: 800;
        color: #5A2200;
        margin-top: 10px;
        margin-bottom: 16px;
    }

    .about-subtitle {
        text-align: center;
        font-size: 20px;
        line-height: 1.7;
        color: #3d2a20;
        margin-bottom: 35px;
    }

    div.stButton > button {
        background-color: transparent !important;
        color: #5A3418 !important;
        border: 1.5px solid #8b5a2b !important;
        border-radius: 14px !important;
        height: 48px !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        min-width: 220px;
    }
    </style>
    """, unsafe_allow_html=True)

    images = [
        "assets/aboutus1.png",
        "assets/aboutus2.jpg",
        "assets/aboutus3.png",
        "assets/aboutus4.jpg",
        "assets/aboutus5.jpg",
        "assets/aboutus6.jpg",
    ]

    left_margin, center, right_margin = st.columns([0.12, 0.76, 0.12])

    with center:
        st.markdown('<div class="about-title">ABOUT US</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="about-subtitle">
            UPS is one of the world's leading logistics and package delivery companies.
            It provides transportation, supply chain solutions, and international shipping services.
        </div>
        """, unsafe_allow_html=True)

        for img in images:
            if Path(img).exists():
                st.image(img, width="stretch")
                st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)
            else:
                st.warning(f"Missing image: {img}")

        back_left, back_mid, back_right = st.columns([1.2, 1, 1.2])
        with back_mid:
            st.button("Back", width="stretch", key="about_back", on_click=lambda: go("intro"))

# -----------------------------
# FAQ page
# -----------------------------
import streamlit as st

def faq_page():
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 1100px;
        padding-top: 40px;
        padding-bottom: 60px;
    }

    .stApp {
        background-color: #f7f4ef;
    }

    .faq-title {
        text-align: center;
        font-size: 46px;
        font-weight: 800;
        color: #5A2200;
        margin-bottom: 35px;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        font-size: 17px;
        font-weight: 700;
        color: #5A2200;
        background: transparent;
        border: none;
        padding: 12px 18px;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #d97a00 !important;
        border-bottom: 3px solid #d97a00 !important;
    }

    /* Expander Box */
    div[data-testid="stExpander"] {
        border: 1px solid #e3d8c9 !important;
        border-radius: 0 !important;
        background: #ffffff !important;
        margin-bottom: 12px !important;
        box-shadow: none !important;
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        font-size: 18px !important;
        font-weight: 650 !important;
        color: #3a2a1f !important;
        padding: 16px 18px !important;
    }

    div[data-testid="stExpander"] summary:hover {
        background-color: #fcf8f3;
    }

    div[data-testid="stExpander"] .streamlit-expanderContent {
        padding: 0 18px 16px 18px !important;
    }

    div[data-testid="stExpander"] p {
        font-size: 16px !important;
        line-height: 1.7 !important;
        color: #5a5148 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="faq-title">Frequently Asked Questions</div>',
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs([
        "Customer Frequently Asked Questions",
        "Access Point Applications Questions"
    ])

    with tab1:
        with st.expander("How can I track my shipment?"):
            st.write("You can track your shipment by entering your tracking number in the shipment tracking section.")

        with st.expander("What should I do if my package is delayed?"):
            st.write("Please check the latest shipment status first. If the delay continues, you can contact customer support.")

        with st.expander("Can I change my delivery address after shipment?"):
            st.write("Address changes may be possible depending on the shipment stage and delivery status.")

        with st.expander("What happens if I am not at the delivery address?"):
            st.write("If you are unavailable, the shipment may be redirected, re-attempted, or held at a designated point depending on the delivery policy.")

        with st.expander("How can I contact customer support?"):
            st.write("You can contact customer support through the communication channels provided on the platform.")

    with tab2:
        with st.expander("How can I apply to become an access point?"):
            st.write("You can submit your application through the access point application section by providing the required business information.")

        with st.expander("What are the requirements for becoming an access point?"):
            st.write("Requirements may include location suitability, accessibility, business operation conditions, and capacity criteria.")

        with st.expander("How is the evaluation process carried out after application?"):
            st.write("Applications are reviewed based on predefined operational and location-based criteria.")

        with st.expander("Can I update my application information after submission?"):
            st.write("Depending on the system design, you may be allowed to update certain application details before final approval.")

        with st.expander("How will I know whether my application is approved?"):
            st.write("You will be informed through the system or contact information provided during the application process.")


# -----------------------------
# Applications page
# -----------------------------
def applications_page():
    apply_shared_styles()

    left, center, right = st.columns([0.2, 0.6, 0.2])
    with center:
        render_applications_page()

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        st.button(
            "Back",
            use_container_width=True,
            key="requests_back",
            on_click=lambda: go("intro")
        )


# -----------------------------
# Home page
# -----------------------------
def home_page():
    apply_shared_styles()
    
    if st.session_state.role == "decision_maker":
        render_manager_dashboard()
    elif st.session_state.role == "delivery_staff":
        render_delivery_panel()


# -----------------------------
# Router
# -----------------------------
if st.session_state.logged_in and st.session_state.view != "home":
    st.session_state.view = "home"

if (not st.session_state.logged_in) and st.session_state.view == "home":
    st.session_state.view = "intro"

if st.session_state.view == "intro":
    intro_page()
elif st.session_state.view == "about":
    about_page()
elif st.session_state.view == "faq":
    faq_page()
elif st.session_state.view == "requests":
    applications_page()
elif st.session_state.view == "login":
    login_page()
elif st.session_state.view == "manager_login":
    manager_login_page()
elif st.session_state.view == "delivery_login":
    delivery_login_page()
elif st.session_state.view == "signup":
    signup_page()
elif st.session_state.view == "home":
    home_page()