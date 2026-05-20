import streamlit as st
import pandas as pd
import json
# ALTAR BAŞLANGIÇ: Bulut kasasına veri göndermek için gerekli kütüphaneler eklendi
import requests
import time
# ALTAR BİTİŞ
from pathlib import Path
from datetime import datetime
from html import escape
from urllib.parse import urlencode
import streamlit.components.v1 as components
from src.fast_routing_model import solve_fast_model

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_HISTORY_PATH = BASE_DIR / "dashboard_history.json"

def save_dashboard_history(record):
    if DASHBOARD_HISTORY_PATH.exists():
        with open(DASHBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append(record)

    with open(DASHBOARD_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

DATA_LABELS = {
    "S": "Demand Scenario Set",
    "K": "Vehicle Set",
    "I": "All Stops Set (Depot, Access Point, Customer)",
    "O": "Visit Order Set",
    "d": "Delivery Demand Parameter",
    "dh": "Hand-to-Hand Delivery Demand Parameter",
    "p": "Pickup Demand Parameter",
    "ph": "Hand-to-Hand Pickup Demand Parameter",
    "c": "Travel Cost Between Locations",
    "q": "Vehicle Capacity Parameter",
}
def format_sheet_name(sheet_name):
    return DATA_LABELS.get(sheet_name, sheet_name)

SERVICE_SHEETS = {
    "d": ("Delivery", "demand"),
    "dh": ("Hand-to-Hand Delivery", "handtohand_demand"),
    "p": ("Pickup", "pickup"),
    "ph": ("Hand-to-Hand Pickup", "handtohand_pickup"),
}

def empty_service_quantities():
    return {
        "Delivery": 0.0,
        "Hand-to-Hand Delivery": 0.0,
        "Pickup": 0.0,
        "Hand-to-Hand Pickup": 0.0,
        "Total Delivery": 0.0,
        "Total Pickup": 0.0,
    }

def format_quantity(value):
    if value is None or pd.isna(value):
        return "0"
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")

def get_value_column(df, preferred_column):
    if preferred_column in df.columns:
        return preferred_column

    excluded_columns = {"scenario", "customer"}
    value_columns = [
        column for column in df.columns
        if str(column).lower() not in excluded_columns
    ]
    if not value_columns:
        return None
    return value_columns[-1]

def build_service_lookup(data, nodes, scenario):
    lookup = {
        str(node): empty_service_quantities()
        for node in nodes
    }

    for sheet_name, (service_name, preferred_column) in SERVICE_SHEETS.items():
        if sheet_name not in data:
            continue

        service_df = data[sheet_name].copy()
        if "scenario" in service_df.columns:
            service_df = service_df[
                service_df["scenario"].astype(str) == str(scenario)
            ]

        if "customer" not in service_df.columns:
            continue

        value_column = get_value_column(service_df, preferred_column)
        if value_column is None:
            continue

        service_df[value_column] = pd.to_numeric(
            service_df[value_column],
            errors="coerce"
        ).fillna(0)

        for _, row in service_df.iterrows():
            node = str(row["customer"])
            if node not in lookup:
                continue
            lookup[node][service_name] += float(row[value_column])

    for quantities in lookup.values():
        quantities["Total Delivery"] = (
            quantities["Delivery"] + quantities["Hand-to-Hand Delivery"]
        )
        quantities["Total Pickup"] = (
            quantities["Pickup"] + quantities["Hand-to-Hand Pickup"]
        )

    return lookup

def order_vehicle_nodes(vehicle_routes):
    arcs = {
        str(row["From"]): str(row["To"])
        for _, row in vehicle_routes.iterrows()
    }

    route = ["i0"]
    current = "i0"
    visited_edges = set()

    while current in arcs:
        next_node = arcs[current]
        edge = (current, next_node)
        if edge in visited_edges:
            break

        visited_edges.add(edge)
        route.append(next_node)
        current = next_node

        if current == "i0":
            break

    if len(route) <= 1 and not vehicle_routes.empty:
        route = [
            str(vehicle_routes.iloc[0]["From"]),
            str(vehicle_routes.iloc[0]["To"]),
        ]

    return route

def build_vehicle_load_lookup(ordered_routes, service_lookup):
    load_lookup = {}

    for vehicle, nodes in ordered_routes.items():
        route_nodes = [
            str(node) for node in nodes
            if str(node) != "i0"
        ]

        remaining_delivery = sum(
            service_lookup.get(node, empty_service_quantities())["Total Delivery"]
            for node in route_nodes
        )
        collected_pickup = 0.0
        current_load = remaining_delivery

        for route_order, node in enumerate(route_nodes, start=1):
            quantities = service_lookup.get(node, empty_service_quantities())
            delivered_here = quantities["Total Delivery"]
            picked_up_here = quantities["Total Pickup"]
            load_before_stop = current_load

            remaining_delivery -= delivered_here
            collected_pickup += picked_up_here
            current_load = remaining_delivery + collected_pickup

            load_lookup[(str(vehicle), node)] = {
                "Route Order": route_order,
                "Load Before Stop": load_before_stop,
                "Delivered Here": delivered_here,
                "Picked Up Here": picked_up_here,
                "Remaining Delivery Load": remaining_delivery,
                "Collected Pickup Load": collected_pickup,
                "Load After Stop": current_load,
            }

    return load_lookup

def load_coordinate_data(coordinate_file):
    coordinate_file.seek(0)
    df = pd.read_excel(coordinate_file, engine="openpyxl")

    required_columns = {"NO", "REGION", "TYPE", "X", "Y"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(f"Missing coordinate columns: {sorted(missing_columns)}")

    coordinates = {}
    for _, row in df.iterrows():
        node = f"i{int(row['NO'])}"
        node_type = str(row["TYPE"]).strip().lower()
        if node_type == "hub":
            node_kind = "depot"
        elif "access" in node_type:
            node_kind = "ap"
        else:
            node_kind = "customer"

        coordinates[node] = {
            "lat": float(row["Y"]),
            "lng": float(row["X"]),
            "name": str(row["REGION"]),
            "kind": node_kind,
        }

    return coordinates

def build_google_maps_url(nodes, coordinates):
    points = [coordinates[node] for node in nodes if node in coordinates]
    if len(points) < 2:
        return None

    query = {
        "api": "1",
        "origin": f"{points[0]['lat']},{points[0]['lng']}",
        "destination": f"{points[-1]['lat']},{points[-1]['lng']}",
        "travelmode": "driving",
    }

    waypoints = [
        f"{point['lat']},{point['lng']}"
        for point in points[1:-1]
    ]
    if waypoints:
        query["waypoints"] = "|".join(waypoints)

    return "https://www.google.com/maps/dir/?" + urlencode(query)


def build_node_popup_html(vehicle, route_order, node, coordinate, service, load):
    location_type = {
        "depot": "Depot",
        "ap": "Access Point",
        "customer": "Customer",
    }.get(coordinate["kind"], coordinate["kind"])

    # BURASI EKLENDI BASLANGIC: Demand / Pickup bolumu sadece customer node'lari icin olusturulur.
    # AP node'unda delivery/pickup gostermemek icin conditional service_section yapisi eklendi.
    service_section = ""
    if coordinate["kind"] == "customer":
        service_rows = [
            ("Delivery", service["Delivery"]),
            ("Hand-to-Hand Delivery", service["Hand-to-Hand Delivery"]),
            ("Total Delivery", service["Total Delivery"]),
            ("Pickup", service["Pickup"]),
            ("Hand-to-Hand Pickup", service["Hand-to-Hand Pickup"]),
            ("Total Pickup", service["Total Pickup"]),
        ]
        service_html = "".join(
            f"<div>{escape(label)}</div><strong>{format_quantity(value)}</strong>"
            for label, value in service_rows
        )
        service_section = (
            "<div class='popup-section'>Demand / Pickup</div>"
            f"<div class='popup-grid'>{service_html}</div>"
        )
    # BURASI EKLENDI BITIS: Customer-only Demand / Pickup service_section blogu burada biter.
    # BURASI CIKARILDI: service_html'in her node icin kosulsuz uretilen eski hali kaldirildi.
    # Eski blok AP popup'inda da Delivery/Pickup gosteriyordu; artik yalniz customer icin calisir.

    if load:
        if coordinate["kind"] == "customer":
            load_rows = [
                ("Load Before", load["Load Before Stop"]),
                ("Delivered Here", load["Delivered Here"]),
                ("Picked Up Here", load["Picked Up Here"]),
                ("Remaining Delivery", load["Remaining Delivery Load"]),
                ("Collected Pickup", load["Collected Pickup Load"]),
                ("Load After", load["Load After Stop"]),
            ]
        else:
            load_rows = [
                ("Load Before", load["Load Before Stop"]),
                ("Load After", load["Load After Stop"]),
            ]
        load_html = "".join(
            f"<div>{escape(label)}</div><strong>{format_quantity(value)}</strong>"
            for label, value in load_rows
        )
    else:
        load_html = "<div>Vehicle Load</div><strong>Depot / route end</strong>"

    return (
        "<div class='node-popup'>"
        f"<div class='popup-title'>Vehicle {escape(str(vehicle))} - Stop {route_order}</div>"
        f"<div class='popup-subtitle'>{escape(str(node))} | {escape(location_type)} | {escape(str(coordinate['name']))}</div>"
        f"{service_section}"
        "<div class='popup-section'>Vehicle Load</div>"
        f"<div class='popup-grid'>{load_html}</div>"
        "</div>"
    )


def build_node_tooltip(vehicle, route_order, node, coordinate, service, load):
    load_text = ""
    if load:
        load_text = (
            " | Load "
            f"{format_quantity(load['Load Before Stop'])}"
            " -> "
            f"{format_quantity(load['Load After Stop'])}"
        )

    if coordinate["kind"] == "customer":
        service_text = (
            f"Delivery {format_quantity(service['Total Delivery'])} | "
            f"Pickup {format_quantity(service['Total Pickup'])}"
        )
    else:
        service_text = "Access Point Stop"

    return (
        f"Vehicle {escape(str(vehicle))}: Stop {route_order}<br>"
        f"{escape(str(node))} - {escape(str(coordinate['name']))}<br>"
        f"{service_text}"
        f"{load_text}"
    )


def build_route_map_html(ordered_routes, coordinates, service_lookup=None, load_lookup=None):
    service_lookup = service_lookup or {}
    load_lookup = load_lookup or {}
    colors = ["#e53935", "#1e88e5", "#43a047", "#8e24aa", "#fb8c00", "#00897b"]
    route_payload = []
    all_points = []

    for idx, (vehicle, nodes) in enumerate(ordered_routes.items()):
        points = []
        for route_order, node in enumerate(nodes):
            if node not in coordinates:
                continue

            coordinate = coordinates[node]
            node_key = str(node)
            service_quantities = service_lookup.get(node_key, empty_service_quantities())
            load_quantities = load_lookup.get((str(vehicle), node_key), {})
            point = {
                "node": node_key,
                "label": "Depot" if coordinate["kind"] == "depot" else node_key,
                "name": coordinate["name"],
                "kind": coordinate["kind"],
                "lat": coordinate["lat"],
                "lng": coordinate["lng"],
                "popup": build_node_popup_html(
                    vehicle,
                    route_order,
                    node_key,
                    coordinate,
                    service_quantities,
                    load_quantities,
                ),
                "tooltip": build_node_tooltip(
                    vehicle,
                    route_order,
                    node_key,
                    coordinate,
                    service_quantities,
                    load_quantities,
                ),
            }
            points.append(point)
            all_points.append([point["lat"], point["lng"]])

        if len(points) >= 2:
            route_payload.append({
                "vehicle": str(vehicle),
                "color": colors[idx % len(colors)],
                "points": points,
            })

    if not route_payload:
        return None

    center_lat = sum(point[0] for point in all_points) / len(all_points)
    center_lng = sum(point[1] for point in all_points) / len(all_points)

# ALTAR BAŞLANGIÇ: Yollardaki kalabalık yazıları (route-label) silmek ve tooltip dokunmatik ayarı için temizlenmiş HTML yapısı
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map {{
      height: 100%;
      margin: 0;
      background: #f7f2ec;
      font-family: Arial, sans-serif;
    }}
    .node-marker {{
      width: 38px;
      height: 38px;
      border: 3px solid #fff;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
      box-shadow: 0 3px 10px rgba(0,0,0,.35);
    }}
    .depot-marker {{
      background: #2f2118;
      border-radius: 50%;
      width: 42px;
      height: 42px;
      font-size: 13px;
    }}
    .ap-marker {{
      border-radius: 8px;
      transform: rotate(45deg);
      border-color: #2f2118;
    }}
    .ap-marker span {{
      transform: rotate(-45deg);
      display: inline-block;
      font-size: 12px;
    }}
    .customer-marker {{
      border-radius: 50%;
    }}
    .arrow-marker {{
      width: 0;
      height: 0;
      border-left: 11px solid transparent;
      border-right: 11px solid transparent;
      border-bottom: 24px solid currentColor;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,.45));
      transform-origin: center center;
    }}
    .legend {{
      position: absolute;
      right: 14px;
      top: 14px;
      z-index: 900;
      background: rgba(255,255,255,.95);
      border-radius: 10px;
      padding: 10px 12px;
      box-shadow: 0 4px 18px rgba(0,0,0,.18);
      font-size: 12px;
      color: #2f2118;
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }}
    .legend-line {{
      width: 20px;
      height: 5px;
      border-radius: 999px;
    }}
    .legend-ap {{
      width: 14px;
      height: 14px;
      background: linear-gradient(135deg, #e53935 0%, #43a047 100%);
      border: 2px solid #2f2118;
      transform: rotate(45deg);
    }}
    .node-popup {{
      min-width: 230px;
      color: #2f2118;
      font-size: 12px;
    }}
    .popup-title {{
      font-weight: 800;
      font-size: 14px;
      margin-bottom: 3px;
    }}
    .popup-subtitle {{
      color: #6d5a4d;
      margin-bottom: 8px;
    }}
    .popup-section {{
      font-weight: 800;
      margin: 9px 0 5px;
      padding-top: 7px;
      border-top: 1px solid #e4d8cd;
    }}
    .popup-grid {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 4px 12px;
      align-items: center;
    }}
    .popup-grid strong {{
      text-align: right;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="legend" id="legend">
    <strong>Route Colors</strong>
    <div class="legend-row"><span class="legend-ap"></span><span>AP: Access Point</span></div>
    <div class="legend-row"><span class="legend-line" style="background:#2f2118"></span><span>Depot</span></div>
  </div>
  <script>
    const routes = {json.dumps(route_payload)};
    const map = L.map('map', {{ zoomControl: true }}).setView([{center_lat}, {center_lng}], 10);

    L.tileLayer('https://{{s}}.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
      maxZoom: 20,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '© Google Maps'
    }}).addTo(map);

    const bounds = [];
    const legend = document.getElementById('legend');

    function bearing(a, b) {{
      const lat1 = a.lat * Math.PI / 180;
      const lat2 = b.lat * Math.PI / 180;
      const dLng = (b.lng - a.lng) * Math.PI / 180;
      const y = Math.sin(dLng) * Math.cos(lat2);
      const x = Math.cos(lat1) * Math.sin(lat2) -
        Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
      return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
    }}

    routes.forEach((route) => {{
      const latLngs = route.points.map((p) => [p.lat, p.lng]);
      latLngs.forEach((p) => bounds.push(p));

      L.polyline(latLngs, {{
        color: route.color,
        weight: 6,
        opacity: 0.85,
        lineJoin: 'round'
      }}).addTo(map);

      route.points.forEach((point, index) => {{
        const markerClass = point.kind === 'depot'
          ? 'depot-marker'
          : (point.kind === 'ap' ? 'ap-marker' : 'customer-marker');
        const markerLabel = point.kind === 'depot'
          ? 'D'
          : (point.kind === 'ap' ? 'AP' : String(index));
        const markerStyle = point.kind === 'depot'
          ? 'background:#2f2118'
          : `background:${{route.color}}`;

        const marker = L.marker([point.lat, point.lng], {{
          icon: L.divIcon({{
            html: `<div class="node-marker ${{markerClass}}" style="${{markerStyle}}"><span>${{markerLabel}}</span></div>`,
            className: '',
            iconSize: [46, 46],
            iconAnchor: [23, 23]
          }})
        }}).addTo(map);
        marker.bindTooltip(point.tooltip, {{direction: 'top'}});
        marker.bindPopup(point.tooltip, {{maxWidth: 320}});
      }});

      for (let i = 0; i < route.points.length - 1; i++) {{
        const a = route.points[i];
        const b = route.points[i + 1];
        const angle = bearing(a, b);
        const mid = [(a.lat + b.lat) / 2, (a.lng + b.lng) / 2];

        L.marker(mid, {{
          icon: L.divIcon({{
            html: `<div class="arrow-marker" style="color:${{route.color}}; transform:rotate(${{angle}}deg)"></div>`,
            className: '',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          }})
        }}).addTo(map);
      }}

      const row = document.createElement('div');
      row.className = 'legend-row';
      row.innerHTML = `<span class="legend-line" style="background:${{route.color}}"></span><span>${{route.vehicle}}</span>`;
      legend.appendChild(row);
    }});

    if (bounds.length) {{
      map.fitBounds(bounds, {{ padding: [40, 40], maxZoom: 13 }});
    }}
  </script>
</body>
</html>
"""
    # ALTAR BİTİŞ


def render_route_map(routes_df, coordinate_file, data, active_nodes, scenario, assignments_df):
    try:
        coordinates = load_coordinate_data(coordinate_file)
    except Exception as e:
        st.error(f"Coordinate file could not be read: {e}")
       # ALTAR BAŞLANGIÇ
        return None
       # ALTAR BİTİŞ

    ordered_routes = {}
    for vehicle in routes_df["Vehicle"].unique():
        vehicle_routes = routes_df[routes_df["Vehicle"] == vehicle]
        ordered_routes[str(vehicle)] = order_vehicle_nodes(vehicle_routes)

    direct_service_lookup = build_service_lookup(data, active_nodes, scenario)
    load_lookup = build_vehicle_load_lookup(ordered_routes, direct_service_lookup)

    map_html = build_route_map_html(
        ordered_routes,
        coordinates,
        direct_service_lookup,
        load_lookup,
    )
    if map_html is None:
        st.warning("No mappable route found. Check coordinate nodes and route nodes.")
        # ALTAR BAŞLANGIÇ
        return None
        # ALTAR BİTİŞ

    st.subheader("Google Maps Route View")
    components.html(map_html, height=620)

    st.subheader("Google Maps Road Directions")
    st.caption("Links open Google Maps directions on real roads. No API key is used.")
    for vehicle, nodes in ordered_routes.items():
        url = build_google_maps_url(nodes, coordinates)
        if url:
            st.markdown(f"**{vehicle}:** [{' -> '.join(nodes)}]({url})")
    # ALTAR BAŞLANGIÇ: Ana fonksiyona geri döndürülüyor ki buluta postalayabilelim
    return map_html, ordered_routes, coordinates
    # ALTAR BİTİŞ

def render_daily_routing():
    st.subheader("Daily Routing")
    st.write("Upload an Excel file and run daily routing based on selected active access points.")

    uploaded_file = st.file_uploader(
        "Upload Excel file",
        type=["xlsx"],
        key="daily_routing_excel"
    )
    # BURASI EKLENDI BASLANGIC: Harita icin opsiyonel koordinat Excel yukleme alani.
    coordinate_file = st.file_uploader(
        "Upload coordinate Excel file for Google Maps route view",
        type=["xlsx"],
        key="daily_routing_coordinate_excel"
    )
    # BURASI EKLENDI BITIS: Koordinat Excel yukleme alani burada biter.

    required_sheets = ["I", "K", "c", "q", "S", "d", "dh", "p", "ph"]

    def build_route_text(vehicle_routes):
        arcs = dict(zip(vehicle_routes["From"], vehicle_routes["To"]))

        route = ["i0"]
        current = "i0"
        visited = set()

        while current in arcs:
            if current in visited:
                break

            visited.add(current)
            next_node = arcs[current]
            route.append(next_node)
            current = next_node

            if current == "i0":
                break

        return " → ".join(route)

    if uploaded_file is None:
        st.info("Please upload an Excel file to run daily routing.")
        return

    try:
        uploaded_file.seek(0)
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

        missing_sheets = [
            sheet for sheet in required_sheets
            if sheet not in xls.sheet_names
        ]

        if missing_sheets:
            st.error(f"Missing Excel sheets: {missing_sheets}")
            return

        uploaded_file.seek(0)
        

        data = {
            "I": pd.read_excel(uploaded_file, sheet_name="I"),
            "K": pd.read_excel(uploaded_file, sheet_name="K"),
            "c": pd.read_excel(uploaded_file, sheet_name="c"),
            "q": pd.read_excel(uploaded_file, sheet_name="q"),
            "S": pd.read_excel(uploaded_file, sheet_name="S"),
            "d": pd.read_excel(uploaded_file, sheet_name="d"),
            "dh": pd.read_excel(uploaded_file, sheet_name="dh"),
            "p": pd.read_excel(uploaded_file, sheet_name="p"),
            "ph": pd.read_excel(uploaded_file, sheet_name="ph"),
        }

        st.success(f"Uploaded file: {uploaded_file.name}")

        st.markdown("### Data Preview")

        selected_sheet = st.selectbox(
            "Select data",
            list(data.keys()),
            format_func=format_sheet_name,
            key="daily_selected_sheet"
        )

        st.write(f"Showing: {format_sheet_name(selected_sheet)}")
        st.dataframe(data[selected_sheet], width="stretch")

        all_nodes = data["I"]["Customer"].astype(str).tolist()

        st.markdown("### Candidate Access Points")

        candidate_ap_count = st.number_input(
            "Number of candidate access points",
            min_value=1,
            max_value=max(len(all_nodes) - 1, 1),
            value=min(10, max(len(all_nodes) - 1, 1)),
            step=1,
            key="daily_candidate_ap_count"
        )

        candidate_aps = [
            node for node in all_nodes
            if node != "i0"
            and node.startswith("i")
            and node[1:].isdigit()
            and int(node[1:]) <= candidate_ap_count
        ]

        customers = [
            node for node in all_nodes
            if node != "i0" and node not in candidate_aps
        ]
        first_scenario = data["S"]["Scenario"].iloc[0]

        dh_df = data["dh"][
            data["dh"]["scenario"].astype(str) == str(first_scenario)
        ].copy()

        ph_df = data["ph"][
            data["ph"]["scenario"].astype(str) == str(first_scenario)
        ].copy()

        active_customers = []

        dh_value_col = dh_df.columns[-1]
        ph_value_col = ph_df.columns[-1]

        for customer in customers:

          dh_val = dh_df.loc[
            dh_df["customer"].astype(str) == str(customer),
            dh_value_col
          ].sum()

          ph_val = ph_df.loc[
            ph_df["customer"].astype(str) == str(customer),
            ph_value_col
          ].sum()

          if dh_val > 0 or ph_val > 0:
           active_customers.append(customer)

        customers = active_customers

        active_aps = st.multiselect(
            "Select active access points for today",
            options=candidate_aps,
            key="daily_active_aps"
        )

        st.markdown("### Vehicles")

        vehicle_options = data["K"]["Vehicle"].tolist()

        selected_vehicles = st.multiselect(
            "Select vehicles for today",
            options=vehicle_options,
            default=vehicle_options[:min(3, len(vehicle_options))],
            key="daily_selected_vehicles"
        )

        if st.button("Run Daily Routing", key="run_daily_routing"):
            if len(active_aps) == 0:
                st.error("Please select at least one active access point.")
                return

            if len(selected_vehicles) == 0:
                st.error("Please select at least one vehicle.")
                return

            active_nodes = ["i0"] + active_aps + customers

            routing_data = data.copy()

            routing_data["active_points"] = active_aps
            routing_data["customers"] = customers

            routing_data["I"] = routing_data["I"][
                routing_data["I"]["Customer"].astype(str).isin(active_nodes)
            ].copy()

            routing_data["c"] = routing_data["c"][
                routing_data["c"]["i"].astype(str).isin(active_nodes)
                & routing_data["c"]["j"].astype(str).isin(active_nodes)
            ].copy()

            routing_data["d"] = routing_data["d"][
                routing_data["d"]["customer"].astype(str).isin(customers)
            ].copy()

            routing_data["K"] = routing_data["K"][
                routing_data["K"]["Vehicle"].isin(selected_vehicles)
            ].copy()

            routing_data["q"] = routing_data["q"][
                routing_data["q"]["vehicle"].isin(selected_vehicles)
            ].copy()

    
            with st.spinner("Solving daily routing..."):
                model, result, routes, assignments = solve_fast_model(routing_data)

            routes_df = pd.DataFrame(routes)
            assignments_df = pd.DataFrame(assignments)

            st.subheader("Daily Routing Result")
            st.write("Solver status:", result.solver.status)
            st.write("Termination:", result.solver.termination_condition)

            try:
                total_distance = float(model.obj())
                st.metric("Total Distance", round(total_distance, 2))
            except Exception:
                pass

            if routes_df.empty:
                st.warning("No route found.")
            else:
                st.subheader("Route Table")
                st.dataframe(routes_df, width="stretch")
                st.subheader("Customer Assignment to Active Points")

                if assignments_df.empty:
                   st.warning("No customer assignment found.")
                else:
                   st.dataframe(assignments_df, width="stretch")
                   

                st.subheader("Vehicle Routes")

                for vehicle in routes_df["Vehicle"].unique():
                    vehicle_routes = routes_df[
                        routes_df["Vehicle"] == vehicle
                    ]

                    route_text = build_route_text(vehicle_routes)
                    st.markdown(f"**Vehicle {vehicle}:** {route_text}")

                # BURASI EKLENDI BASLANGIC: Cozumden sonra rota haritasini gosterme blogu.
                if coordinate_file is None:
                    st.info("Upload a coordinate Excel file to show the routes on Google Maps.")
                else:
                    # ALTAR BAŞLANGIÇ: Harita verilerini değişkene atıyoruz
                    map_results = render_route_map(
                        routes_df,
                        coordinate_file,
                        data,
                        active_nodes,
                        first_scenario,
                        assignments_df,
                    )
                    # BULUT ENTEGRASYONU - Harita, rotalar ve talep takibi verileri JSONBin'e aktarılıyor
                    if map_results is not None:
                        map_html, ordered_routes, coordinates = map_results
                        
                        with st.spinner("Uploading map and routes to cloud storage."):
                            google_links_data = {}
                            for vehicle, nodes in ordered_routes.items():
                                g_url = build_google_maps_url(nodes, coordinates)
                                if g_url:
                                    google_links_data[str(vehicle)] = {"url": g_url}

                            # Telefondaki uygulamanın çekeceği veri paketi hazırlanıyor
                            payload = {
                                "map_html": map_html,
                                "total_distance": round(total_distance, 2) if "total_distance" in locals() else 0.0,
                                "google_links": google_links_data,
                                "assignments": assignments_df.to_dict(orient="records") if not assignments_df.empty else []
                            }

                            headers = {
                                "Content-Type": "application/json",
                                "X-Master-Key": "$2a$10$T72jRhqyg.phWLbuSxdMVe.PQpnDi8BN6pEU/Sa7KaJvevaHK5eyO" 
                            }
                            url = "https://api.jsonbin.io/v3/b/6a00cd28adc21f119a7e6bb9"

                            try:
                                req = requests.put(url, json=payload, headers=headers)
                                if req.status_code == 200:
                                    st.success("")
                                else:
                                    st.error("Cloud upload failed!")
                            except Exception as e:
                                st.error(f"Could not connect to cloud storage: {e}")
                    # ALTAR BİTİŞ
                # BURASI EKLENDI BITIS: Cozumden sonra rota haritasini gosterme blogu burada biter.

                used_vehicle_count = routes_df["Vehicle"].nunique() if not routes_df.empty else 0
                
                service_lookup_for_dashboard = build_service_lookup(
                  routing_data,
                  customers,
                  first_scenario
                )

                ap_loads = {}

                for ap in active_aps:
                   assigned_customers = assignments_df[
                     assignments_df["Active Point"].astype(str) == str(ap)
                   ]["Customer"].astype(str).tolist()

                   delivery_load = sum(
                     service_lookup_for_dashboard.get(customer, empty_service_quantities())["Total Delivery"]
                     for customer in assigned_customers
                   )

                   pickup_load = sum(
                     service_lookup_for_dashboard.get(customer, empty_service_quantities())["Total Pickup"]
                     for customer in assigned_customers
                   )

                   ap_loads[ap] = {
                       "delivery_load": round(delivery_load, 2),
                       "pickup_load": round(pickup_load, 2),
                       "total_load": round(delivery_load + pickup_load, 2),
                       "customer_count": len(assigned_customers)
                   }

                farthest_customer_distance = (
                    float(assignments_df["Distance"].max())
                    if not assignments_df.empty and "Distance" in assignments_df.columns
                    else 0
                )

                total_delivery_demand = sum(
                  values["Total Delivery"]
                  for values in service_lookup_for_dashboard.values()
                )

                total_pickup_demand = sum(
                  values["Total Pickup"]
                  for values in service_lookup_for_dashboard.values()
                )

                total_ap_delivery_load= total_delivery_demand 

                total_route_count = routes_df["Vehicle"].nunique() if not routes_df.empty else 0
                
                dashboard_record = {
                    "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "run_type": "daily_routing",

                    "file_name": uploaded_file.name,

                    "daily_routing_cost": round(total_distance, 2) if "total_distance" in locals() else None,

                    "used_vehicle_count": int(used_vehicle_count),

                    "active_aps_today": active_aps,
                    "active_ap_count_today": len(active_aps),

                    "selected_vehicles": selected_vehicles,
                    "selected_vehicle_count": len(selected_vehicles),

                    "customer_count_today": len(customers),

                    "solver_status": str(result.solver.status),
                    "termination": str(result.solver.termination_condition),
                    "ap_loads": ap_loads,
                    "farthest_customer_distance": round(farthest_customer_distance, 2),
                    "total_delivery_demand": round(total_delivery_demand, 2),
                    "total_pickup_demand": round(total_pickup_demand, 2),
                    "total_ap_delivery_load": round(total_ap_delivery_load, 2),
                    "total_route_count": int(total_route_count),
                    
                }

                save_dashboard_history(dashboard_record)
                st.session_state["fast_routes"] = routes_df
                st.session_state["fast_routing_ready"] = True

    except Exception as e:
        st.error("Daily routing error.")
        st.exception(e)