import io
import importlib.util
import json
import hashlib
import re
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="UPS Streamlit Prep",
    layout="wide",
)


NODE_TYPE_OPTIONS = ["Depot", "Access Point", "Customer"]
NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
IDENTIFIER_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
SAMPLE_FOLDER = Path(__file__).resolve().parent / "sample_project_gams"
ACCOUNT_FILE = Path(__file__).resolve().parent / "ups_dss_accounts.json"

PROJECT_NODES = [f"i{idx}" for idx in range(21)]
PROJECT_VEHICLES = ["k1", "k2", "k3"]
PROJECT_SCENARIOS = ["s1", "s2"]
PROJECT_ORDERS = [f"o{idx}" for idx in range(1, 23)]
PROJECT_AP_DEFAULTS = {
    "i1": (50, 2, 70),
    "i2": (10, 1, 50),
    "i3": (30, 3, 90),
    "i4": (70, 2, 60),
    "i5": (30, 2, 80),
    "i6": (30, 2, 80),
    "i7": (30, 2, 80),
    "i8": (30, 2, 80),
    "i9": (30, 2, 80),
    "i10": (25, 2, 80),
}
PROJECT_VEHICLE_DEFAULTS = {
    "k1": (300, 20),
    "k2": (400, 15),
    "k3": (700, 20),
}
DEFAULT_SETTINGS = {
    "w": 10,
    "M": 1000000,
    "optcr": 0,
    "optca": 0,
    "reslim": 6000,
    "iterlim": 2000000000,
    "MIP": "gurobi",
}


def openpyxl_available():
    return importlib.util.find_spec("openpyxl") is not None


st.markdown(
    """
<style>
    :root {
        --prep-ink: #1f2937;
        --prep-navy: #17324d;
        --prep-sand: #f7f0e3;
        --prep-gold: #d4a24a;
        --prep-muted: #6b7280;
        --prep-border: #d9cbb7;
        --prep-card: rgba(255, 252, 246, 0.94);
    }

    .stApp {
        background:
            radial-gradient(circle at top right, rgba(212, 162, 74, 0.16), transparent 26%),
            linear-gradient(180deg, #fbf8f1 0%, #efe6d6 100%);
        color: var(--prep-ink);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
    }

    .hero {
        background: linear-gradient(135deg, rgba(23, 50, 77, 0.97), rgba(49, 81, 112, 0.95));
        border-radius: 22px;
        padding: 1.45rem 1.55rem;
        border: 1px solid rgba(212, 162, 74, 0.34);
        box-shadow: 0 20px 48px rgba(23, 50, 77, 0.14);
        margin-bottom: 1rem;
    }

    .hero-title {
        font-size: 2rem;
        line-height: 1.05;
        font-weight: 700;
        color: #fdf9f1;
        margin-bottom: 0.35rem;
        font-family: Georgia, "Times New Roman", serif;
    }

    .hero-subtitle {
        color: #ecdfc8;
        line-height: 1.6;
        max-width: 900px;
        font-size: 1rem;
    }

    .metric-card {
        background: var(--prep-card);
        border: 1px solid var(--prep-border);
        border-radius: 16px;
        padding: 0.95rem 1rem;
        min-height: 96px;
        box-shadow: 0 10px 30px rgba(23, 50, 77, 0.05);
    }

    .metric-label {
        color: var(--prep-muted);
        text-transform: uppercase;
        font-size: 0.82rem;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        color: var(--prep-navy);
        font-size: 1.7rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 0.2rem;
    }

    .metric-help {
        color: #4b5563;
        font-size: 0.92rem;
    }

    .hero-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .login-shell {
        padding-top: 0.5rem;
    }

    .login-hero {
        min-height: 520px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background:
            radial-gradient(circle at top right, rgba(212, 162, 74, 0.26), transparent 28%),
            linear-gradient(145deg, rgba(30, 44, 61, 0.98), rgba(74, 54, 28, 0.96));
        border-radius: 28px;
        padding: 2rem 2rem 1.7rem 2rem;
        color: #fdf7ea;
        border: 1px solid rgba(212, 162, 74, 0.35);
        box-shadow: 0 24px 54px rgba(18, 24, 33, 0.22);
    }

    .login-card {
        background: rgba(255, 252, 246, 0.96);
        border-radius: 24px;
        padding: 1.5rem 1.35rem;
        border: 1px solid rgba(217, 203, 183, 0.95);
        box-shadow: 0 18px 40px rgba(23, 50, 77, 0.08);
        min-height: 520px;
    }

    .ups-badge {
        width: 98px;
        height: 116px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: Georgia, "Times New Roman", serif;
        font-weight: 700;
        font-size: 2rem;
        color: #fdf7ea;
        background: linear-gradient(180deg, #8a6330 0%, #5a401e 100%);
        border: 4px solid #d4a24a;
        box-shadow: inset 0 0 0 2px rgba(253, 247, 234, 0.22);
        clip-path: polygon(8% 0%, 92% 0%, 92% 63%, 50% 100%, 8% 63%);
        margin-bottom: 1.25rem;
    }

    .login-eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.82rem;
        color: #ecd8b2;
        margin-bottom: 0.8rem;
    }

    .login-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 2.45rem;
        line-height: 1.02;
        margin-bottom: 0.8rem;
    }

    .login-feature-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.8rem;
        margin-top: 1.4rem;
    }

    .login-feature {
        background: rgba(255, 250, 240, 0.08);
        border: 1px solid rgba(255, 222, 173, 0.14);
        border-radius: 18px;
        padding: 0.9rem 1rem;
    }

    .login-feature-title {
        color: #fdf7ea;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }

    .login-feature-copy {
        color: #e5d6b9;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .panel-title {
        font-size: 1.32rem;
        font-weight: 700;
        color: var(--prep-navy);
        margin-bottom: 0.25rem;
    }

    .panel-copy {
        color: #5b6572;
        margin-bottom: 1rem;
    }

    .note-card {
        background: rgba(255, 252, 246, 0.96);
        border: 1px solid rgba(217, 203, 183, 0.95);
        border-radius: 18px;
        padding: 1rem 1.05rem;
        min-height: 150px;
        box-shadow: 0 10px 24px rgba(23, 50, 77, 0.05);
    }

    .note-title {
        color: var(--prep-navy);
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    .note-copy {
        color: #5b6572;
        line-height: 1.6;
    }
</style>
""",
    unsafe_allow_html=True,
)


def unique_preserve(items):
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def to_num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def format_number(value):
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def parse_name_list(text, prefix):
    raw_items = [item.strip() for item in text.split(",") if item.strip()]
    if not raw_items:
        return [f"{prefix}1"]
    return unique_preserve(raw_items)


def init_state(name, value):
    if name not in st.session_state:
        st.session_state[name] = value


def username_key(username):
    return username.strip().lower()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_accounts():
    if not ACCOUNT_FILE.exists():
        return {}
    try:
        accounts = json.loads(ACCOUNT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return accounts if isinstance(accounts, dict) else {}


def save_accounts(accounts):
    ACCOUNT_FILE.write_text(json.dumps(accounts, indent=2), encoding="utf-8")


def init_auth_state():
    init_state("authenticated", False)
    init_state("auth_user", "")
    init_state("auth_notice", "")


def create_account_record(username, password):
    cleaned = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", cleaned):
        raise ValueError("Username must be 3-32 characters and use only letters, numbers, dot, underscore, or dash.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    accounts = load_accounts()
    key = username_key(cleaned)
    if key in accounts:
        raise ValueError("This username already exists.")

    accounts[key] = {
        "username": cleaned,
        "password_hash": hash_password(password),
    }
    save_accounts(accounts)
    return cleaned


def authenticate_user(username, password):
    accounts = load_accounts()
    key = username_key(username)
    record = accounts.get(key)
    if not record:
        return False, ""
    if record.get("password_hash") != hash_password(password):
        return False, ""
    return True, record.get("username", username.strip())


def render_login_screen():
    init_auth_state()
    accounts = load_accounts()

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown(
            """
            <div class="login-hero">
                <div>
                    <div class="ups-badge">UPS</div>
                    <div class="login-eyebrow">Decision Support Workspace</div>
                    <div class="login-title">UPS DSS LOGIN</div>
                    <div class="login-feature-grid">
                        <div class="login-feature">
                            <div class="login-feature-title">Editable Data</div>
                            <div class="login-feature-copy">Node, vehicle, demand and cost tables stay clean and easy to revise.</div>
                        </div>
                        <div class="login-feature">
                            <div class="login-feature-title">Source Imports</div>
                            <div class="login-feature-copy">Bring in Excel workbooks, CSV bundles or GAMS DAT/TXT files.</div>
                        </div>
                        <div class="login-feature">
                            <div class="login-feature-title">Gurobi Track</div>
                            <div class="login-feature-copy">The UI is kept ready for the upcoming Pyomo model and Gurobi solve stage.</div>
                        </div>
                        <div class="login-feature">
                            <div class="login-feature-title">Local Accounts</div>
                            <div class="login-feature-copy">Simple local sign-in stored in this workspace for demo and team use.</div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="login-card">
                <div class="panel-title">Access Panel</div>
                <div class="panel-copy">Use an existing account or create a new one for this local demo environment.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mode = st.radio(
            "Account Mode",
            ["Sign In", "Create Account"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if mode == "Sign In":
            if not accounts:
                st.info("No local account exists yet. Create your first account to unlock the interface.")
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="ups_team")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                ok, resolved_user = authenticate_user(username, password)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["auth_user"] = resolved_user
                    st.rerun()
                st.error("Username or password is incorrect.")
        else:
            with st.form("create_account_form", clear_on_submit=False):
                new_username = st.text_input("New Username", placeholder="ups_admin")
                new_password = st.text_input("New Password", type="password", placeholder="At least 6 characters")
                confirm_password = st.text_input("Confirm Password", type="password")
                created = st.form_submit_button("Create New Account", use_container_width=True)
            if created:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        created_user = create_account_record(new_username, new_password)
                        st.session_state["authenticated"] = True
                        st.session_state["auth_user"] = created_user
                        st.success("Account created successfully. Redirecting to the workspace.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

        st.markdown(
            """
            <div class="note-card" style="min-height: 0; margin-top: 1rem;">
                <div class="note-copy">Account data is stored locally in <code>ups_dss_accounts.json</code>.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def default_node_type(node, index):
    if node == "i0" or index == 0:
        return "Depot"
    if node in PROJECT_AP_DEFAULTS or index <= 10:
        return "Access Point"
    return "Customer"


def create_matrix(rows, cols, row_name="Node", fill_value=0):
    return pd.DataFrame(
        [[row] + [fill_value] * len(cols) for row in rows],
        columns=[row_name] + cols,
    )


def sync_matrix(existing_df, rows, cols, row_name="Node", fill_value=0):
    base = pd.DataFrame({row_name: rows})
    existing_df = existing_df.copy()
    if row_name not in existing_df.columns:
        existing_df = base.copy()

    for col in cols:
        if col in existing_df.columns:
            base = base.merge(existing_df[[row_name, col]], on=row_name, how="left")
        else:
            base[col] = fill_value

    for col in cols:
        base[col] = to_num(base[col])

    return base.fillna(fill_value)


def sync_cost_matrix(existing_df, nodes):
    base = pd.DataFrame({"From": nodes})
    existing_df = existing_df.copy()
    if "From" not in existing_df.columns:
        existing_df = base.copy()

    for node in nodes:
        if node in existing_df.columns:
            base = base.merge(existing_df[["From", node]], on="From", how="left")
        else:
            base[node] = 0

    for node in nodes:
        base[node] = to_num(base[node])

    return base.fillna(0)


def sync_node_table(existing_df, nodes):
    base = pd.DataFrame({"Node": nodes})
    existing_df = existing_df.copy()
    if "Node" in existing_df.columns:
        base = base.merge(existing_df, on="Node", how="left")

    default_types = {node: default_node_type(node, idx) for idx, node in enumerate(nodes)}
    base["Type"] = base.get("Type", pd.Series(dtype=str)).fillna(base["Node"].map(default_types))

    open_costs = {node: PROJECT_AP_DEFAULTS.get(node, (0, 0, 0))[0] for node in nodes}
    operating_costs = {node: PROJECT_AP_DEFAULTS.get(node, (0, 0, 0))[1] for node in nodes}
    capacities = {node: PROJECT_AP_DEFAULTS.get(node, (0, 0, 0))[2] for node in nodes}

    for col_name, default_map in [
        ("Opening Cost af(i)", open_costs),
        ("Operating Cost v(i)", operating_costs),
        ("Capacity apc(i)", capacities),
    ]:
        if col_name not in base.columns:
            base[col_name] = base["Node"].map(default_map)
        base[col_name] = pd.to_numeric(base[col_name], errors="coerce")
        base[col_name] = base[col_name].fillna(base["Node"].map(default_map))

    return base


def sync_vehicle_table(existing_df, vehicles):
    base = pd.DataFrame({"Vehicle": vehicles})
    existing_df = existing_df.copy()
    if "Vehicle" in existing_df.columns:
        base = base.merge(existing_df, on="Vehicle", how="left")

    capacity_defaults = {vehicle: PROJECT_VEHICLE_DEFAULTS.get(vehicle, (0, 0))[0] for vehicle in vehicles}
    fixed_defaults = {vehicle: PROJECT_VEHICLE_DEFAULTS.get(vehicle, (0, 0))[1] for vehicle in vehicles}

    for col_name, default_map in [
        ("Capacity q(k)", capacity_defaults),
        ("Fixed Cost tf(k)", fixed_defaults),
    ]:
        if col_name not in base.columns:
            base[col_name] = base["Vehicle"].map(default_map)
        base[col_name] = pd.to_numeric(base[col_name], errors="coerce")
        base[col_name] = base[col_name].fillna(base["Vehicle"].map(default_map))

    return base


def build_settings_df(existing_df=None):
    base = pd.DataFrame(
        {
            "Setting": list(DEFAULT_SETTINGS.keys()),
            "Value": list(DEFAULT_SETTINGS.values()),
        }
    )
    if existing_df is None or existing_df.empty or "Setting" not in existing_df.columns:
        return base

    merged = base.merge(existing_df, on="Setting", how="left", suffixes=("_default", ""))
    merged["Value"] = merged["Value"].fillna(merged["Value_default"])
    return merged[["Setting", "Value"]]


def settings_to_dict(settings_df):
    if settings_df.empty:
        return DEFAULT_SETTINGS.copy()
    return {
        row["Setting"]: row["Value"]
        for _, row in settings_df.iterrows()
    }


def decode_uploaded_file(uploaded_file):
    raw_bytes = uploaded_file.getvalue()
    for encoding in ["utf-8-sig", "utf-8", "cp1254", "latin-1"]:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def strip_comment_lines(text):
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("$"):
            continue
        lines.append(line)
    return "\n".join(lines)


def split_data_line(line):
    return [piece for piece in re.split(r"[\s,;]+", line.strip()) if piece]


def is_number_token(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def parse_set_text(text):
    cleaned = strip_comment_lines(text).replace("/", " ").replace(";", " ").replace(",", " ")
    return unique_preserve(re.findall(IDENTIFIER_PATTERN, cleaned))


def parse_sparse_records(text):
    cleaned = strip_comment_lines(text).replace("/", " ").replace(";", " ")
    dot_matches = re.findall(
        rf"({IDENTIFIER_PATTERN})\s*\.\s*({IDENTIFIER_PATTERN})\s+({NUMBER_PATTERN})",
        cleaned,
        flags=re.IGNORECASE,
    )
    if dot_matches:
        return [(row, col, float(value)) for row, col, value in dot_matches]

    records = []
    for line in cleaned.splitlines():
        parts = split_data_line(line)
        if len(parts) == 3 and is_number_token(parts[2]):
            records.append((parts[0], parts[1], float(parts[2])))
    return records


def records_to_matrix(records, row_name="Node", row_order=None, col_order=None):
    rows = row_order or unique_preserve([row for row, _, _ in records])
    cols = col_order or unique_preserve([col for _, col, _ in records])
    matrix_df = create_matrix(rows, cols, row_name=row_name)
    for row, col, value in records:
        if row in matrix_df[row_name].values and col in matrix_df.columns:
            matrix_df.loc[matrix_df[row_name] == row, col] = value
    return matrix_df


def parse_matrix_like_text(text, row_name):
    cleaned_lines = []
    for raw_line in strip_comment_lines(text).splitlines():
        line = raw_line.replace("/", " ").replace(";", " ").strip()
        if line:
            cleaned_lines.append(split_data_line(line))

    if len(cleaned_lines) < 2:
        return None

    header = cleaned_lines[0]
    if len(cleaned_lines[1]) != len(header) + 1:
        return None
    if not all(is_number_token(token) for token in cleaned_lines[1][1:]):
        return None

    rows = []
    for tokens in cleaned_lines[1:]:
        if len(tokens) != len(header) + 1:
            return None
        if not all(is_number_token(token) for token in tokens[1:]):
            return None
        rows.append([tokens[0]] + [float(token) for token in tokens[1:]])

    return pd.DataFrame(rows, columns=[row_name] + header)


def parse_parameter_text(text, row_name="Node"):
    matrix_df = parse_matrix_like_text(text, row_name)
    if matrix_df is not None:
        return matrix_df

    records = parse_sparse_records(text)
    if not records:
        return None
    return records_to_matrix(records, row_name=row_name)


def parse_cost_text(text):
    matrix_df = parse_matrix_like_text(text, "From")
    if matrix_df is not None:
        nodes = unique_preserve(matrix_df["From"].tolist() + matrix_df.columns[1:].tolist())
        return sync_cost_matrix(matrix_df, nodes)

    records = parse_sparse_records(text)
    if not records:
        return None

    nodes = unique_preserve([row for row, _, _ in records] + [col for _, col, _ in records])
    matrix_df = sync_cost_matrix(pd.DataFrame(), nodes)
    for row, col, value in records:
        matrix_df.loc[matrix_df["From"] == row, col] = value
    return matrix_df


def parse_named_value_block(text, parameter_name):
    match = re.search(
        rf"{re.escape(parameter_name)}\s*\([^)]*\)[^/;]*\/(.*?)\/",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return {}
    content = match.group(1).replace(",", "\n")
    pairs = re.findall(
        rf"({IDENTIFIER_PATTERN})\s*({NUMBER_PATTERN})",
        content,
        flags=re.IGNORECASE,
    )
    return {name: float(value) for name, value in pairs}


def parse_scalar_block(text, scalar_name):
    match = re.search(
        rf"\b{re.escape(scalar_name)}\b[^/;]*\/\s*({NUMBER_PATTERN})\s*\/",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return float(match.group(1))


def parse_options_block(text):
    options = {}
    match = re.search(r"Options(.*?);", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return options
    for key, value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^,\n;]+)", match.group(1)):
        options[key] = value.strip()
    return options


def find_uploaded_text(file_texts, expected_names):
    for expected in expected_names:
        normalized_expected = expected.lower().rsplit(".", maxsplit=1)[0]
        for file_name, content in file_texts.items():
            stem = file_name.lower().rsplit(".", maxsplit=1)[0]
            if file_name.lower() == expected.lower() or stem == normalized_expected:
                return file_name, content
    return None, None


def payload_from_gams_texts(file_texts):
    payload = {}

    set_files = {
        "nodes": ["UPS_I.dat", "UPS_I"],
        "vehicles": ["UPS_K.dat", "UPS_K"],
        "scenarios": ["UPS_S.dat", "UPS_S"],
        "orders": ["UPS_O.dat", "UPS_O"],
    }
    for key, names in set_files.items():
        _, content = find_uploaded_text(file_texts, names)
        if content:
            payload[key] = parse_set_text(content)

    matrix_files = {
        "d_df": ["UPS_d.dat", "UPS_d"],
        "dh_df": ["UPS_dh.dat", "UPS_dh"],
        "p_df": ["UPS_p.dat", "UPS_p"],
        "ph_df": ["UPS_ph.dat", "UPS_ph"],
    }
    for key, names in matrix_files.items():
        _, content = find_uploaded_text(file_texts, names)
        if content:
            payload[key] = parse_parameter_text(content, "Node")

    _, cost_content = find_uploaded_text(file_texts, ["UPS_cost.dat", "UPS_cost"])
    if cost_content:
        payload["cost_df"] = parse_cost_text(cost_content)

    text_blocks = [content for file_name, content in file_texts.items() if file_name.endswith((".gms", ".txt", ".inc"))]
    if text_blocks:
        joined_text = "\n\n".join(text_blocks)
        payload["q_map"] = parse_named_value_block(joined_text, "q")
        payload["tf_map"] = parse_named_value_block(joined_text, "tf")
        payload["af_map"] = parse_named_value_block(joined_text, "af")
        payload["v_map"] = parse_named_value_block(joined_text, "v")
        payload["apc_map"] = parse_named_value_block(joined_text, "apc")

        options = parse_options_block(joined_text)
        settings = DEFAULT_SETTINGS.copy()
        for key, default_value in settings.items():
            if key in options:
                settings[key] = options[key]
        scalar_w = parse_scalar_block(joined_text, "w")
        scalar_m = parse_scalar_block(joined_text, "M")
        if scalar_w is not None:
            settings["w"] = scalar_w
        if scalar_m is not None:
            settings["M"] = scalar_m
        payload["settings"] = settings

    return payload


def payload_from_excel(uploaded_file):
    if not openpyxl_available():
        raise RuntimeError(
            "Excel import requires the 'openpyxl' package. Install it or use the GAMS DAT/TXT import."
        )
    excel = pd.ExcelFile(uploaded_file)
    payload = {}
    available_sheets = {sheet.lower(): sheet for sheet in excel.sheet_names}

    if "nodes" in available_sheets:
        payload["nodes_df"] = pd.read_excel(excel, sheet_name=available_sheets["nodes"])
    if "vehicles" in available_sheets:
        payload["vehicles_df"] = pd.read_excel(excel, sheet_name=available_sheets["vehicles"])
    if "scenarios" in available_sheets:
        scenarios_df = pd.read_excel(excel, sheet_name=available_sheets["scenarios"])
        payload["scenarios"] = scenarios_df.iloc[:, 0].dropna().astype(str).tolist()
    if "orders" in available_sheets:
        orders_df = pd.read_excel(excel, sheet_name=available_sheets["orders"])
        payload["orders"] = orders_df.iloc[:, 0].dropna().astype(str).tolist()
    if "settings" in available_sheets:
        payload["settings_df"] = pd.read_excel(excel, sheet_name=available_sheets["settings"])

    for sheet_name in ["d", "dh", "p", "ph"]:
        if sheet_name in available_sheets:
            payload[f"{sheet_name}_df"] = pd.read_excel(excel, sheet_name=available_sheets[sheet_name])
    if "cost" in available_sheets:
        payload["cost_df"] = pd.read_excel(excel, sheet_name=available_sheets["cost"])

    return payload


def payload_from_csv_texts(file_texts):
    payload = {}
    csv_frames = {}
    csv_map = {
        "nodes_df": ["nodes.csv", "node_table.csv", "ups_nodes.csv"],
        "vehicles_df": ["vehicles.csv", "vehicle_table.csv", "ups_vehicles.csv"],
        "scenarios_df": ["scenarios.csv", "scenario_list.csv", "ups_scenarios.csv"],
        "orders_df": ["orders.csv", "order_list.csv", "ups_orders.csv"],
        "d_df": ["d.csv", "ups_d.csv"],
        "dh_df": ["dh.csv", "ups_dh.csv"],
        "p_df": ["p.csv", "ups_p.csv"],
        "ph_df": ["ph.csv", "ups_ph.csv"],
        "cost_df": ["cost.csv", "cost_matrix.csv", "ups_cost.csv"],
    }

    for key, names in csv_map.items():
        _, content = find_uploaded_text(file_texts, names)
        if content:
            csv_frames[key] = pd.read_csv(io.StringIO(content))

    if "nodes_df" in csv_frames:
        payload["nodes_df"] = csv_frames["nodes_df"]
        if "Node" in csv_frames["nodes_df"].columns:
            payload["nodes"] = csv_frames["nodes_df"]["Node"].dropna().astype(str).tolist()
    if "vehicles_df" in csv_frames:
        payload["vehicles_df"] = csv_frames["vehicles_df"]
        if "Vehicle" in csv_frames["vehicles_df"].columns:
            payload["vehicles"] = csv_frames["vehicles_df"]["Vehicle"].dropna().astype(str).tolist()
    if "scenarios_df" in csv_frames and not csv_frames["scenarios_df"].empty:
        payload["scenarios"] = csv_frames["scenarios_df"].iloc[:, 0].dropna().astype(str).tolist()
    if "orders_df" in csv_frames and not csv_frames["orders_df"].empty:
        payload["orders"] = csv_frames["orders_df"].iloc[:, 0].dropna().astype(str).tolist()

    for key in ["d_df", "dh_df", "p_df", "ph_df", "cost_df"]:
        if key in csv_frames:
            payload[key] = csv_frames[key]

    return payload


def init_prep_state():
    init_state("node_text", ",".join(PROJECT_NODES))
    init_state("vehicle_text", ",".join(PROJECT_VEHICLES))
    init_state("scenario_text", ",".join(PROJECT_SCENARIOS))
    init_state("order_text", ",".join(PROJECT_ORDERS))
    init_state("import_report", [])

    nodes = parse_name_list(st.session_state["node_text"], "i")
    vehicles = parse_name_list(st.session_state["vehicle_text"], "k")
    scenarios = parse_name_list(st.session_state["scenario_text"], "s")

    if "nodes_df" not in st.session_state:
        st.session_state["nodes_df"] = sync_node_table(pd.DataFrame(), nodes)
    if "vehicles_df" not in st.session_state:
        st.session_state["vehicles_df"] = sync_vehicle_table(pd.DataFrame(), vehicles)
    if "settings_df" not in st.session_state:
        st.session_state["settings_df"] = build_settings_df()
    for key in ["d_df", "dh_df", "p_df", "ph_df"]:
        if key not in st.session_state:
            st.session_state[key] = create_matrix(nodes, scenarios, row_name="Node")
    if "cost_df" not in st.session_state:
        st.session_state["cost_df"] = sync_cost_matrix(pd.DataFrame(), nodes)
    if "excel_upload_key" not in st.session_state:
        st.session_state["excel_upload_key"] = 0
    if "gams_upload_key" not in st.session_state:
        st.session_state["gams_upload_key"] = 0


def apply_structure(node_text, vehicle_text, scenario_text, order_text):
    nodes = parse_name_list(node_text, "i")
    vehicles = parse_name_list(vehicle_text, "k")
    scenarios = parse_name_list(scenario_text, "s")
    orders = parse_name_list(order_text, "o")

    st.session_state["node_text"] = ",".join(nodes)
    st.session_state["vehicle_text"] = ",".join(vehicles)
    st.session_state["scenario_text"] = ",".join(scenarios)
    st.session_state["order_text"] = ",".join(orders)

    st.session_state["nodes_df"] = sync_node_table(st.session_state["nodes_df"], nodes)
    st.session_state["vehicles_df"] = sync_vehicle_table(st.session_state["vehicles_df"], vehicles)
    st.session_state["d_df"] = sync_matrix(st.session_state["d_df"], nodes, scenarios)
    st.session_state["dh_df"] = sync_matrix(st.session_state["dh_df"], nodes, scenarios)
    st.session_state["p_df"] = sync_matrix(st.session_state["p_df"], nodes, scenarios)
    st.session_state["ph_df"] = sync_matrix(st.session_state["ph_df"], nodes, scenarios)
    st.session_state["cost_df"] = sync_cost_matrix(st.session_state["cost_df"], nodes)


def apply_payload(payload, source_label):
    nodes = payload.get("nodes")
    if nodes is None and "nodes_df" in payload and "Node" in payload["nodes_df"].columns:
        nodes = payload["nodes_df"]["Node"].dropna().astype(str).tolist()
    if nodes is None:
        nodes = parse_name_list(st.session_state["node_text"], "i")

    vehicles = payload.get("vehicles")
    if vehicles is None and "vehicles_df" in payload and "Vehicle" in payload["vehicles_df"].columns:
        vehicles = payload["vehicles_df"]["Vehicle"].dropna().astype(str).tolist()
    if vehicles is None:
        vehicles = parse_name_list(st.session_state["vehicle_text"], "k")

    scenarios = payload.get("scenarios")
    if scenarios is None:
        for key in ["d_df", "dh_df", "p_df", "ph_df"]:
            if key in payload:
                scenarios = payload[key].columns[1:].tolist()
                break
    if scenarios is None:
        scenarios = parse_name_list(st.session_state["scenario_text"], "s")

    orders = payload.get("orders") or parse_name_list(st.session_state["order_text"], "o")
    apply_structure(",".join(nodes), ",".join(vehicles), ",".join(scenarios), ",".join(orders))

    if "nodes_df" in payload:
        st.session_state["nodes_df"] = sync_node_table(payload["nodes_df"], nodes)

    if any(key in payload for key in ["af_map", "v_map", "apc_map"]):
        node_table = st.session_state["nodes_df"].copy()
        af_map = payload.get("af_map", {})
        v_map = payload.get("v_map", {})
        apc_map = payload.get("apc_map", {})
        for idx, row in node_table.iterrows():
            node = row["Node"]
            if node in af_map:
                node_table.at[idx, "Opening Cost af(i)"] = af_map[node]
            if node in v_map:
                node_table.at[idx, "Operating Cost v(i)"] = v_map[node]
            if node in apc_map:
                node_table.at[idx, "Capacity apc(i)"] = apc_map[node]
        st.session_state["nodes_df"] = node_table

    if "vehicles_df" in payload:
        st.session_state["vehicles_df"] = sync_vehicle_table(payload["vehicles_df"], vehicles)
    elif any(key in payload for key in ["q_map", "tf_map"]):
        vehicle_table = st.session_state["vehicles_df"].copy()
        q_map = payload.get("q_map", {})
        tf_map = payload.get("tf_map", {})
        for idx, row in vehicle_table.iterrows():
            vehicle = row["Vehicle"]
            if vehicle in q_map:
                vehicle_table.at[idx, "Capacity q(k)"] = q_map[vehicle]
            if vehicle in tf_map:
                vehicle_table.at[idx, "Fixed Cost tf(k)"] = tf_map[vehicle]
        st.session_state["vehicles_df"] = vehicle_table

    if "settings_df" in payload:
        st.session_state["settings_df"] = build_settings_df(payload["settings_df"])
    elif "settings" in payload:
        incoming_df = pd.DataFrame(
            {"Setting": list(payload["settings"].keys()), "Value": list(payload["settings"].values())}
        )
        st.session_state["settings_df"] = build_settings_df(incoming_df)

    for key in ["d_df", "dh_df", "p_df", "ph_df"]:
        if key in payload:
            st.session_state[key] = sync_matrix(payload[key], nodes, scenarios)

    if "cost_df" in payload:
        st.session_state["cost_df"] = sync_cost_matrix(payload["cost_df"], nodes)

    st.session_state["import_report"] = [f"{source_label} imported into the preparation app."]


def current_nodes():
    return parse_name_list(st.session_state["node_text"], "i")


def current_vehicles():
    return parse_name_list(st.session_state["vehicle_text"], "k")


def current_scenarios():
    return parse_name_list(st.session_state["scenario_text"], "s")


def current_orders():
    return parse_name_list(st.session_state["order_text"], "o")


def validate_state():
    errors = []
    warnings = []
    nodes_df = st.session_state["nodes_df"]
    nodes = current_nodes()
    scenarios = current_scenarios()

    depot_count = int((nodes_df["Type"] == "Depot").sum())
    ap_count = int((nodes_df["Type"] == "Access Point").sum())
    customer_count = int((nodes_df["Type"] == "Customer").sum())

    if depot_count != 1:
        errors.append("Node table should contain exactly one depot.")
    if ap_count == 0:
        errors.append("At least one access point is required.")
    if customer_count == 0:
        errors.append("At least one customer node is required.")

    for key in ["d_df", "dh_df", "p_df", "ph_df"]:
        matrix_df = st.session_state[key]
        if matrix_df.shape[0] != len(nodes):
            errors.append(f"{key} row count does not match node count.")
        missing_scenarios = [scenario for scenario in scenarios if scenario not in matrix_df.columns]
        if missing_scenarios:
            errors.append(f"{key} is missing scenario columns: {', '.join(missing_scenarios)}.")

    cost_df = st.session_state["cost_df"]
    missing_cost_cols = [node for node in nodes if node not in cost_df.columns]
    if missing_cost_cols:
        errors.append("Cost matrix is missing node columns.")
    if cost_df.shape[0] != len(nodes):
        errors.append("Cost matrix row count does not match node count.")

    ap_rows = nodes_df[nodes_df["Type"] == "Access Point"]
    if (to_num(ap_rows["Capacity apc(i)"]) <= 0).any():
        warnings.append("Some access points have zero or negative capacity.")

    customer_rows = nodes_df[nodes_df["Type"] == "Customer"]
    if (to_num(customer_rows["Opening Cost af(i)"]) > 0).any():
        warnings.append("Some customer rows still carry access-point opening costs.")

    if not errors and not warnings:
        warnings.append("No structural issue detected in the current preparation state.")

    return errors, warnings


def render_metric(label, value, help_text):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def state_payload():
    return {
        "node_text": st.session_state["node_text"],
        "vehicle_text": st.session_state["vehicle_text"],
        "scenario_text": st.session_state["scenario_text"],
        "order_text": st.session_state["order_text"],
        "nodes_df": st.session_state["nodes_df"].to_dict(orient="records"),
        "vehicles_df": st.session_state["vehicles_df"].to_dict(orient="records"),
        "settings_df": st.session_state["settings_df"].to_dict(orient="records"),
        "d_df": st.session_state["d_df"].to_dict(orient="records"),
        "dh_df": st.session_state["dh_df"].to_dict(orient="records"),
        "p_df": st.session_state["p_df"].to_dict(orient="records"),
        "ph_df": st.session_state["ph_df"].to_dict(orient="records"),
        "cost_df": st.session_state["cost_df"].to_dict(orient="records"),
    }


def build_excel_bytes():
    if not openpyxl_available():
        return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        st.session_state["nodes_df"].to_excel(writer, index=False, sheet_name="nodes")
        st.session_state["vehicles_df"].to_excel(writer, index=False, sheet_name="vehicles")
        pd.DataFrame({"Scenario": current_scenarios()}).to_excel(
            writer, index=False, sheet_name="scenarios"
        )
        pd.DataFrame({"Order": current_orders()}).to_excel(
            writer, index=False, sheet_name="orders"
        )
        st.session_state["d_df"].to_excel(writer, index=False, sheet_name="d")
        st.session_state["dh_df"].to_excel(writer, index=False, sheet_name="dh")
        st.session_state["p_df"].to_excel(writer, index=False, sheet_name="p")
        st.session_state["ph_df"].to_excel(writer, index=False, sheet_name="ph")
        st.session_state["cost_df"].to_excel(writer, index=False, sheet_name="cost")
    output.seek(0)
    return output.getvalue()


def format_set_file(items):
    return "\n".join(items) + "\n"


def format_sparse_matrix(df, row_name):
    lines = []
    for _, row in df.iterrows():
        row_key = row[row_name]
        for col in df.columns[1:]:
            lines.append(f"{row_key}.{col} {format_number(row[col])}")
    return "\n".join(lines) + "\n"


def generate_config_text():
    settings = settings_to_dict(st.session_state["settings_df"])
    q_pairs = ",".join(
        f"{row['Vehicle']} {format_number(row['Capacity q(k)'])}"
        for _, row in st.session_state["vehicles_df"].iterrows()
    )
    tf_pairs = ",".join(
        f"{row['Vehicle']} {format_number(row['Fixed Cost tf(k)'])}"
        for _, row in st.session_state["vehicles_df"].iterrows()
    )

    ap_rows = st.session_state["nodes_df"][st.session_state["nodes_df"]["Type"] == "Access Point"]
    af_pairs = ",".join(
        f"{row['Node']} {format_number(row['Opening Cost af(i)'])}"
        for _, row in ap_rows.iterrows()
    )
    v_pairs = ",".join(
        f"{row['Node']} {format_number(row['Operating Cost v(i)'])}"
        for _, row in ap_rows.iterrows()
    )
    apc_pairs = ",".join(
        f"{row['Node']} {format_number(row['Capacity apc(i)'])}"
        for _, row in ap_rows.iterrows()
    )

    lines = [
        "Options",
        "    solprint = off,",
        f"    optcr    = {settings.get('optcr', 0)},",
        f"    optca    = {settings.get('optca', 0)},",
        f"    reslim   = {settings.get('reslim', 0)},",
        f"    iterlim  = {settings.get('iterlim', 0)},",
        f"    MIP      = {settings.get('MIP', 'cplex')}",
        ";",
        "",
        f"Parameters q(k) /{q_pairs}/;",
        f"Parameters tf(k) /{tf_pairs}/;",
        f"Parameters af(i) /{af_pairs}/;",
        f"Parameters v(i) /{v_pairs}/;",
        f"Parameters apc(i) /{apc_pairs}/;",
        f"Scalar w /{settings.get('w', 10)}/;",
        f"Scalar M /{settings.get('M', 1000000)}/;",
        "",
        "* This file is a preparation export from the Streamlit interface.",
    ]
    return "\n".join(lines) + "\n"


def build_gams_zip_bytes():
    dat_files = {
        "UPS_I.dat": format_set_file(current_nodes()),
        "UPS_K.dat": format_set_file(current_vehicles()),
        "UPS_S.dat": format_set_file(current_scenarios()),
        "UPS_O.dat": format_set_file(current_orders()),
        "UPS_d.dat": format_sparse_matrix(st.session_state["d_df"], "Node"),
        "UPS_dh.dat": format_sparse_matrix(st.session_state["dh_df"], "Node"),
        "UPS_p.dat": format_sparse_matrix(st.session_state["p_df"], "Node"),
        "UPS_ph.dat": format_sparse_matrix(st.session_state["ph_df"], "Node"),
        "UPS_cost.dat": format_sparse_matrix(st.session_state["cost_df"], "From"),
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name, content in dat_files.items():
            archive.writestr(file_name, content)
    output.seek(0)
    return output.getvalue()


def build_csv_zip_bytes():
    csv_files = {
        "nodes.csv": st.session_state["nodes_df"].to_csv(index=False),
        "vehicles.csv": st.session_state["vehicles_df"].to_csv(index=False),
        "scenarios.csv": pd.DataFrame({"Scenario": current_scenarios()}).to_csv(index=False),
        "orders.csv": pd.DataFrame({"Order": current_orders()}).to_csv(index=False),
        "d.csv": st.session_state["d_df"].to_csv(index=False),
        "dh.csv": st.session_state["dh_df"].to_csv(index=False),
        "p.csv": st.session_state["p_df"].to_csv(index=False),
        "ph.csv": st.session_state["ph_df"].to_csv(index=False),
        "cost.csv": st.session_state["cost_df"].to_csv(index=False),
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name, content in csv_files.items():
            archive.writestr(file_name, content)
    output.seek(0)
    return output.getvalue()


def sample_available():
    required = [
        "UPS_I.dat",
        "UPS_K.dat",
        "UPS_S.dat",
        "UPS_O.dat",
        "UPS_d.dat",
        "UPS_dh.dat",
        "UPS_p.dat",
        "UPS_ph.dat",
        "UPS_cost.dat",
        "KOD.txt",
    ]
    return all((SAMPLE_FOLDER / name).exists() for name in required)


def payload_from_local_sample():
    file_texts = {}
    for path in SAMPLE_FOLDER.iterdir():
        if path.is_file():
            file_texts[path.name] = path.read_text(encoding="utf-8", errors="ignore")
    return payload_from_gams_texts(file_texts)


init_prep_state()
init_auth_state()

if not st.session_state["authenticated"]:
    render_login_screen()
    st.stop()


with st.sidebar:
    st.markdown(f"### {st.session_state['auth_user']}")
    st.caption("UPS DSS session is active.")
    if st.button("Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["auth_user"] = ""
        st.rerun()

    st.divider()
    st.markdown("## Structure")
    node_text_input = st.text_area("Nodes i", value=st.session_state["node_text"], height=100)
    vehicle_text_input = st.text_input("Vehicles k", value=st.session_state["vehicle_text"])
    scenario_text_input = st.text_input("Scenarios s", value=st.session_state["scenario_text"])
    order_text_input = st.text_area("Orders o", value=st.session_state["order_text"], height=90)

    left_btn, right_btn = st.columns(2)
    with left_btn:
        if st.button("Update Structure", use_container_width=True):
            apply_structure(
                node_text_input,
                vehicle_text_input,
                scenario_text_input,
                order_text_input,
            )
            st.rerun()
    with right_btn:
        if st.button("Reset Blank", use_container_width=True):
            st.session_state["nodes_df"] = sync_node_table(pd.DataFrame(), parse_name_list(node_text_input, "i"))
            st.session_state["vehicles_df"] = sync_vehicle_table(pd.DataFrame(), parse_name_list(vehicle_text_input, "k"))
            st.session_state["settings_df"] = build_settings_df()
            apply_structure(node_text_input, vehicle_text_input, scenario_text_input, order_text_input)
            st.rerun()

    if st.button("Load Project Defaults", use_container_width=True):
        st.session_state["nodes_df"] = sync_node_table(pd.DataFrame(), PROJECT_NODES)
        st.session_state["vehicles_df"] = sync_vehicle_table(pd.DataFrame(), PROJECT_VEHICLES)
        st.session_state["settings_df"] = build_settings_df()
        apply_structure(
            ",".join(PROJECT_NODES),
            ",".join(PROJECT_VEHICLES),
            ",".join(PROJECT_SCENARIOS),
            ",".join(PROJECT_ORDERS),
        )
        st.session_state["import_report"] = ["Project defaults loaded."]
        st.rerun()

    if sample_available() and st.button("Load Local Sample", use_container_width=True):
        apply_payload(payload_from_local_sample(), "Local sample bundle")
        st.rerun()


nodes = current_nodes()
vehicles = current_vehicles()
scenarios = current_scenarios()
orders = current_orders()
errors, warnings = validate_state()
nodes_df = st.session_state["nodes_df"]
ap_count = int((nodes_df["Type"] == "Access Point").sum())
customer_count = int((nodes_df["Type"] == "Customer").sum())
depot_count = int((nodes_df["Type"] == "Depot").sum())


st.markdown(
    """
    <div class="hero">
        <div class="hero-row">
            <div>
                <div class="hero-title">UPS Data Preparation</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    render_metric("Nodes", len(nodes), "Unified i set")
with metric_col2:
    render_metric("Access Points", ap_count, "Rows typed as Access Point")
with metric_col3:
    render_metric("Customers", customer_count, "Rows typed as Customer")
with metric_col4:
    render_metric("Scenarios", len(scenarios), "Scenario columns available")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Editable Data", "Demand Inputs", "Cost Matrix", "Import / Export"]
)


with tab1:
    overview_left, overview_right = st.columns([1.05, 0.95])
    with overview_left:
        st.markdown("### Current project mapping")
        st.markdown(
            """
            - `i`: unified node set
            - `k`: vehicle set
            - `s`: scenario set
            - `o`: visit-order set
            - `d`, `dh`, `p`, `ph`: scenario-based node inputs
            - `c(i,j)`: travel-cost matrix
            - `af(i)`, `v(i)`, `apc(i)`, `q(k)`, `tf(k)`:  parameters
            """
        )
    with overview_right:
        st.markdown("### Set summary")
        st.dataframe(
            pd.DataFrame(
                {
                    "Item": ["Depot", "Access Points", "Customers", "Vehicles", "Scenarios", "Orders"],
                    "Count": [depot_count, ap_count, customer_count, len(vehicles), len(scenarios), len(orders)],
                }
            ),
            hide_index=True,
            use_container_width=True,
        )


with tab2:
    st.markdown("### Editable Node Table")
    st.session_state["nodes_df"] = st.data_editor(
        st.session_state["nodes_df"],
        hide_index=True,
        use_container_width=True,
        disabled=["Node"],
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=NODE_TYPE_OPTIONS, required=True),
            "Opening Cost af(i)": st.column_config.NumberColumn("Opening Cost af(i)", min_value=0),
            "Operating Cost v(i)": st.column_config.NumberColumn("Operating Cost v(i)", min_value=0),
            "Capacity apc(i)": st.column_config.NumberColumn("Capacity apc(i)", min_value=0),
        },
        key="node_editor",
    )

    st.markdown("### Vehicle Table")
    st.session_state["vehicles_df"] = st.data_editor(
        st.session_state["vehicles_df"],
        hide_index=True,
        use_container_width=True,
        disabled=["Vehicle"],
        column_config={
            "Capacity q(k)": st.column_config.NumberColumn("Capacity q(k)", min_value=0),
            "Fixed Cost tf(k)": st.column_config.NumberColumn("Fixed Cost tf(k)", min_value=0),
        },
        key="vehicle_editor",
    )

    with st.expander("Data Check", expanded=False):
        for message in errors:
            st.error(message)
        for message in warnings:
            if message == "No structural issue detected in the current preparation state.":
                st.success(message)
            else:
                st.warning(message)


with tab3:
    st.markdown("### Scenario-Based Inputs")
    st.caption("These are preparation tables only. The optimization model is not solved here yet.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### d(i,s)")
        st.session_state["d_df"] = st.data_editor(
            st.session_state["d_df"],
            hide_index=True,
            use_container_width=True,
            disabled=["Node"],
            key="d_editor_prep",
        )
        st.markdown("#### p(i,s)")
        st.session_state["p_df"] = st.data_editor(
            st.session_state["p_df"],
            hide_index=True,
            use_container_width=True,
            disabled=["Node"],
            key="p_editor_prep",
        )
    with col2:
        st.markdown("#### dh(i,s)")
        st.session_state["dh_df"] = st.data_editor(
            st.session_state["dh_df"],
            hide_index=True,
            use_container_width=True,
            disabled=["Node"],
            key="dh_editor_prep",
        )
        st.markdown("#### ph(i,s)")
        st.session_state["ph_df"] = st.data_editor(
            st.session_state["ph_df"],
            hide_index=True,
            use_container_width=True,
            disabled=["Node"],
            key="ph_editor_prep",
        )

    totals_rows = []
    for scenario in scenarios:
        totals_rows.append(
            {
                "Scenario": scenario,
                "Total d": to_num(st.session_state["d_df"][scenario]).sum(),
                "Total dh": to_num(st.session_state["dh_df"][scenario]).sum(),
                "Total p": to_num(st.session_state["p_df"][scenario]).sum(),
                "Total ph": to_num(st.session_state["ph_df"][scenario]).sum(),
            }
        )
    totals_df = pd.DataFrame(totals_rows)
    st.markdown("### Scenario totals")
    st.dataframe(totals_df, hide_index=True, use_container_width=True)
    if not totals_df.empty:
        st.bar_chart(totals_df.set_index("Scenario"))


with tab4:
    st.markdown("### Cost Matrix c(i,j)")
    st.caption("Rows and columns follow the unified node set.")
    st.session_state["cost_df"] = st.data_editor(
        st.session_state["cost_df"],
        hide_index=True,
        use_container_width=True,
        disabled=["From"],
        key="cost_editor_prep",
    )


with tab5:
    st.markdown("### Import / Export")
    excel_support = openpyxl_available()

    import_left, import_right = st.columns([1, 1])
    with import_left:
        st.markdown("#### Import Excel")
        if not excel_support:
            st.warning("`openpyxl` not found. Excel import is disabled; use DAT/TXT import or install `openpyxl`.")
        excel_file = st.file_uploader(
            "Upload workbook",
            type=["xlsx"],
            key=f"excel_upload_{st.session_state['excel_upload_key']}",
        )
        if excel_file is not None and st.button(
            "Apply Excel Workbook",
            use_container_width=True,
            disabled=not excel_support,
        ):
            try:
                apply_payload(payload_from_excel(excel_file), "Excel workbook")
                st.session_state["excel_upload_key"] += 1
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

        st.markdown("#### Import CSV")
        csv_files = st.file_uploader(
            "Upload CSV files",
            type=["csv"],
            accept_multiple_files=True,
            key="csv_upload_bundle",
        )
        if csv_files:
            st.dataframe(
                pd.DataFrame(
                    {
                        "File": [file.name for file in csv_files],
                        "Size (bytes)": [file.size for file in csv_files],
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )
        if csv_files and st.button("Apply CSV Bundle", use_container_width=True):
            file_texts = {file.name: decode_uploaded_file(file) for file in csv_files}
            apply_payload(payload_from_csv_texts(file_texts), "CSV bundle")
            st.rerun()

        st.markdown("#### Import GAMS DAT/TXT")
        gams_files = st.file_uploader(
            "Upload DAT/GMS/TXT files",
            type=["dat", "gms", "txt", "inc"],
            accept_multiple_files=True,
            key=f"gams_upload_{st.session_state['gams_upload_key']}",
        )
        if gams_files:
            st.dataframe(
                pd.DataFrame(
                    {
                        "File": [file.name for file in gams_files],
                        "Size (bytes)": [file.size for file in gams_files],
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )
        if gams_files and st.button("Apply GAMS Bundle", use_container_width=True):
            file_texts = {file.name: decode_uploaded_file(file) for file in gams_files}
            apply_payload(payload_from_gams_texts(file_texts), "GAMS bundle")
            st.session_state["gams_upload_key"] += 1
            st.rerun()

    with import_right:
        st.markdown("#### Export")
        excel_bytes = build_excel_bytes()
        csv_zip_bytes = build_csv_zip_bytes()
        zip_bytes = build_gams_zip_bytes()
        if not excel_support:
            st.info("Excel export is disabled until `openpyxl` is installed. CSV and GAMS zip export still work.")
        st.download_button(
            "Download Excel Workbook",
            data=excel_bytes or b"",
            file_name="ups_prep_workbook.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=excel_bytes is None,
            use_container_width=True,
        )
        st.download_button(
            "Download CSV Bundle",
            data=csv_zip_bytes,
            file_name="ups_prep_csv_bundle.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.download_button(
            "Download GAMS DAT Zip",
            data=zip_bytes,
            file_name="ups_prep_gams_bundle.zip",
            mime="application/zip",
            use_container_width=True,
        )

    st.markdown("### Import report")
    if st.session_state["import_report"]:
        for message in st.session_state["import_report"]:
            st.info(message)
    else:
        st.caption("No external workbook or bundle has been applied yet.")
