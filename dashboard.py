import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import tinytuya
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import os

# Detect if we're on Streamlit Cloud
IS_CLOUD = os.getenv("STREAMLIT_CLOUD", "0") == "1"

# --------------- Device Setup ---------------
DEVICE_ID = "bf1fb51a6032098478au4s"
LOCAL_KEY = "ZD@.!(|l[$V|3K=F"
LOCAL_IP = "192.168.68.107"
VERSION = 3.5

unit_cost_bdt = 6
csv_path = "energy_history.csv"

if not IS_CLOUD:
    device = tinytuya.OutletDevice(DEVICE_ID, LOCAL_IP, LOCAL_KEY)
    device.set_version(VERSION)

# Session state init
if 'history' not in st.session_state:
    if os.path.exists(csv_path):
        st.session_state.history = pd.read_csv(csv_path, parse_dates=['Time']).to_dict('records')
    else:
        st.session_state.history = []

if 'on_time' not in st.session_state:
    st.session_state.on_time = None

if 'duration_minutes' not in st.session_state:
    st.session_state.duration_minutes = 0

if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = datetime.now()

if 'accumulated_kwh' not in st.session_state:
    st.session_state.accumulated_kwh = 0.0

# Device status getter
def get_device_status():
    try:
        if IS_CLOUD:
            # Simulated values
            power_on = True
            power = 25.0
            voltage = 220.0
            current = 0.25
            current_ma = current * 1000
            incremental_kwh = 0.0001
            st.session_state.accumulated_kwh += incremental_kwh
            cost = st.session_state.accumulated_kwh * unit_cost_bdt
            duration = 5
            return power_on, power, voltage, current_ma, st.session_state.accumulated_kwh, cost, duration

        # Local - real device
        status = device.status()
        dps = status.get('dps', {})
        power_on = dps.get('1', False)
        power = dps.get('19', 0) / 10.0
        voltage = dps.get('20', 0) / 10.0
        current = dps.get('18', 0) / 1000.0

        current_time = datetime.now()
        delta_time_hours = (current_time - st.session_state.last_update_time).total_seconds() / 3600.0
        st.session_state.last_update_time = current_time

        incremental_kwh = (power / 1000.0) * delta_time_hours
        st.session_state.accumulated_kwh += incremental_kwh
        current_ma = current * 1000.0
        cost = st.session_state.accumulated_kwh * unit_cost_bdt

        if power_on:
            if not st.session_state.on_time:
                st.session_state.on_time = datetime.now()
            else:
                st.session_state.duration_minutes = int((datetime.now() - st.session_state.on_time).total_seconds() / 60)
        else:
            st.session_state.on_time = None
            st.session_state.duration_minutes = 0

        return power_on, power, voltage, current_ma, st.session_state.accumulated_kwh, cost, st.session_state.duration_minutes
    except Exception as e:
        st.warning(f"Device error: {e}")
        return False, 0, 0, 0, 0, 0, 0

# Update row to history
def update_history_row():
    now = datetime.now()
    status = get_device_status()
    record = {
        "Time": now,
        "Current (mA)": status[3],
        "Voltage (V)": status[2],
        "Power (W)": status[1],
        "Energy (kWh)": status[4],
        "Cost (BDT)": status[5],
        "Duration (min)": status[6]
    }
    if len(st.session_state.history) == 0 or (now - pd.to_datetime(st.session_state.history[-1]['Time'])).total_seconds() >= 60:
        st.session_state.history.append(record)
        df = pd.DataFrame(st.session_state.history)
        df.to_csv(csv_path, index=False)
    else:
        df = pd.DataFrame(st.session_state.history)
    return df, status

# Toggle device
def toggle_device(state: bool):
    try:
        device.turn_on() if state else device.turn_off()
        st.success(f"Device turned {'ON' if state else 'OFF'}")
    except Exception as e:
        st.error(f"Error toggling device: {e}")

# --- UI ---
st.set_page_config(page_title="Energy Monitor | Farzia", layout="wide")
st_autorefresh(interval=10000, limit=None, key="refresh")

left_col, right_col = st.columns([4, 1])
with right_col:
    if os.path.exists("farzia.jpeg"):
        st.image("farzia.jpeg", caption="👤 Farzia Hossain", width=80)
    else:
        st.warning("Image file 'farzia.jpeg' not found.")

with left_col:
    st.title("💡 Farzia - IoT Energy Monitoring Dashboard")

if not IS_CLOUD:
    colA, colB = st.columns([1, 4])
    with colA:
        st.button("🔌 Turn ON", on_click=toggle_device, args=(True,))
        st.button("💡 Turn OFF", on_click=toggle_device, args=(False,))

# Metrics
df, status = update_history_row()
power_on, power, voltage, current_ma, kwh, cost, duration = status

st.subheader("🔍 Real-Time Device Parameters")
row1 = st.columns(2)
row2 = st.columns(2)
metrics_1 = [
    ("🔋 Current", f"{current_ma:.2f} mA", "#e0f7fa"),
    ("⚡ Power", f"{power:.2f} W", "#ffe0b2"),
    ("🔢 Voltage", f"{voltage:.2f} V", "#f3e5f5"),
    ("📈 Energy", f"{kwh:.6f} kWh", "#e8f5e9")
]

for i in range(0, len(metrics_1), 2):
    for col, (label, val, color) in zip([row1, row2][i//2], metrics_1[i:i+2]):
        with col:
            st.markdown(f"""
            <div style='background-color:{color}; padding: 10px; border-radius: 10px; text-align: center; color: black;'>
                <div style='font-size: 14px; font-weight: bold'>{label}</div>
                <div style='font-size: 16px;'>{val}</div>
            </div>
            """, unsafe_allow_html=True)

row3 = st.columns(2)
metrics_2 = [
    ("💰 Cost Per Unit", "6.00 BDT/kWh", "#fff9c4"),
    ("💸 Current Cost", f"{cost:.4f} BDT", "#fce4ec"),
    ("⏱️ ON Duration", f"{duration} min", "#e1f5fe")
]

for col, (label, val, color) in zip(row3, metrics_2[:2]):
    with col:
        st.markdown(f"""
        <div style='background-color:{color}; padding: 10px; border-radius: 10px; text-align: center; color: black;'>
            <div style='font-size: 14px; font-weight: bold'>{label}</div>
            <div style='font-size: 16px;'>{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style='background-color:{metrics_2[2][2]}; padding: 10px; border-radius: 10px; text-align: center; color: black; width: 50%; margin: auto;'>
    <div style='font-size: 14px; font-weight: bold'>{metrics_2[2][0]}</div>
    <div style='font-size: 16px;'>{metrics_2[2][1]}</div>
</div>
""", unsafe_allow_html=True)

st.success(f"✅ Device is {'ON' if power_on else 'OFF'}")

# Live chart
st.subheader("📊 Live Graph of Power Parameters")
if not df.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['Time'], df['Current (mA)'], label="Current (mA)", color="teal")
    ax.plot(df['Time'], df['Voltage (V)'], label="Voltage (V)", color="orange")
    ax.plot(df['Time'], df['Power (W)'], label="Power (W)", color="blue")
    ax.plot(df['Time'], df['Energy (kWh)'], label="Energy (kWh)", color="green")
    ax.plot(df['Time'], df['Cost (BDT)'], label="Cost (BDT)", color="crimson")
    ax.set_xlabel("Time")
    ax.set_ylabel("Value")
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

# Export
if os.path.exists(csv_path):
    with open(csv_path, "rb") as f:
        st.download_button("📥 Download CSV", data=f, file_name="energy_history.csv", mime="text/csv")

# Visualize buttons
if st.button("📈 History Visualize"):
    st.subheader("📊 Parameter-wise 1-Minute Graphs")
    for metric, color in zip(["Current (mA)", "Voltage (V)", "Power (W)", "Energy (kWh)", "Cost (BDT)"],
                              ["teal", "orange", "blue", "green", "crimson"]):
        st.markdown(f"### {metric}")
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(df['Time'], df[metric], label=metric, color=color)
        ax.set_xlabel("Time")
        ax.set_ylabel(metric)
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)

if st.button("📊 Summary Bar Chart"):
    st.subheader("🔍 Summary Overview")
    latest = df.iloc[-1]
    categories = ["Current (mA)", "Voltage (V)", "Power (W)", "Energy (kWh)", "Cost (BDT)"]
    values = [latest[c] for c in categories]
    fig, ax = plt.subplots()
    ax.bar(categories, values, color=["teal", "orange", "blue", "green", "crimson"])
    plt.xticks(rotation=30)
    ax.set_ylabel("Latest Values")
    st.pyplot(fig)

st.caption("👩‍💻 Dashboard by Farzia | Cloud-ready with Mock Mode")


