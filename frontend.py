import streamlit as st
import requests
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="AI Product Analyzer", layout="wide")

FASTAPI_BASE_URL = "http://127.0.0.1:8000"
FASTAPI_ANALYZE_URL = f"{FASTAPI_BASE_URL}/analyze"
FASTAPI_HISTORY_URL = f"{FASTAPI_BASE_URL}/history"
FASTAPI_REGISTER_URL = f"{FASTAPI_BASE_URL}/register"
FASTAPI_TOKEN_URL = f"{FASTAPI_BASE_URL}/token"

if "token" not in st.session_state:
    st.session_state["token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if st.session_state["token"] is None:
    st.title("AI Product Analyzer ")
    st.write("Access protected machine-learning diagnostic reports by registering or signing into your session profile.")
    
    auth_tab1, auth_tab2 = st.tabs(["Login", "SignUp"])
    
    with auth_tab1:
        with st.form("login_form"):
            login_username = st.text_input("Username")
            login_password = st.text_input("Password ", type="password")
            submit_login = st.form_submit_button("Secure Login")
            
            if submit_login:
                if login_username and login_password:
                    try:
                        payload = {"username": login_username, "password": login_password}
                        response = requests.post(FASTAPI_TOKEN_URL, data=payload)
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state["token"] = data["access_token"]
                            st.session_state["username"] = login_username
                            st.success(f"Session established for profile: {login_username}")
                            st.rerun()
                        else:
                            st.error("Access Denied: Invalid combination sequence parameters.")
                    except requests.exceptions.ConnectionError:
                        st.error("Fatal: Core network interface backend connection dropped.")
                else:
                    st.warning("All entry spaces are mandatory requirements.")
                    
    with auth_tab2:
        with st.form("register_form"):
            reg_username = st.text_input("Create Username")
            reg_password = st.text_input("Create Password", type="password")
            submit_reg = st.form_submit_button("Done")
            
            if submit_reg:
                if reg_username and reg_password:
                    try:
                        payload = {"username": reg_username, "password": reg_password}
                        response = requests.post(FASTAPI_REGISTER_URL, json=payload)
                        if response.status_code == 201:
                            data = response.json()
                            st.session_state["token"] = data["access_token"]
                            st.session_state["username"] = reg_username
                            st.success("Profile created successfully!")
                            st.rerun()
                        else:
                            try:
                                detail_err = response.json().get('detail', 'Registration failed.')
                            except Exception:
                                detail_err = f"Server Error ({response.status_code}): {response.text}"
                            st.error(detail_err)
                    except requests.exceptions.ConnectionError:
                        st.error("Fatal: Core network interface backend connection dropped.")
                else:
                    st.warning("All signature profiles require active string values.")
    st.stop()

auth_headers = {"Authorization": f"Bearer {st.session_state['token']}"}

with st.sidebar:
    st.markdown(f"### User : **{st.session_state['username']}**")
    st.divider()
    if st.button("Logout", type="primary"):
        st.session_state["token"] = None
        st.session_state["username"] = None
        st.rerun()

tab1, tab2, tab3 = st.tabs(["Analyze my product", "Visual Analytics", "History"])

with tab1:
    st.title("AI-Powered Product Analyzer")
    st.write("Pass an imaging blueprint containing ingredient lists to review dynamic safety analysis.")
    st.divider()

    uploaded_file = st.file_uploader("Upload product packaging file...", type=["jpg", "jpeg", "png", "heic", "heif"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Target Processing Matrix", width='stretch')
        
        if st.button("Execute Pipeline Audit", type="primary"):
            with st.spinner("Decoding pixels,Processing...."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(FASTAPI_ANALYZE_URL, files=files, headers=auth_headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Evaluation completed.")
                        st.divider()
                        
                        col_score, col_sum = st.columns([1, 2])
                        with col_score:
                            st.subheader("Numerical Metric Evaluation")
                            score = result.get('health_score', 0)
                            color_flag = result.get('color', 'yellow').lower()
                            
                            if color_flag == "green":
                                st.success(f"### Rating Index: {score} / 10\n\n**Clean Profile Evaluation.**")
                            elif color_flag == "yellow":
                                st.warning(f"### Rating Index: {score} / 10\n\n**Moderate evaluation profile metrics.**")
                            else:
                                st.error(f"### Rating Index: {score} / 10\n\n**High Risk: Ultra-processed additives found.**")
                                
                        with col_sum:
                            st.subheader("Product Executive Summary")
                            st.info(result.get('summary', 'Evaluation overview string structural payload empty.'))
                            
                        st.divider()
                        col_ing, col_flg, col_alt = st.columns(3)
                        
                        with col_ing:
                            st.subheader(" Parsed Elements")
                            for item in result.get('detected_ingredients', []):
                                st.write(f"- {item}")
                                
                        with col_flg:
                            st.subheader(" Risk Warning Arrays")
                            flags_arr = result.get('red_flags', [])
                            if flags_arr:
                                for flag in flags_arr:
                                    st.write(f"🛑 {flag}")
                            else:
                                st.write(" Safe matrix: No dangerous compounds recognized.")
                                
                        with col_alt:
                            st.subheader(" Healthier Substitutions")
                            alts_arr = result.get('healthy_alternatives', [])
                            if alts_arr:
                                for alt in alts_arr:
                                    st.write(f"{alt}")
                            else:
                                st.write("No modifications or substitute switches required.")
                    else:
                        st.error(f"Error matrix returned tracking reference: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not reach backend API pipeline.")

with tab2:
    st.title("Nutritional Diagnostic Analytics Dashboard")
    st.write("Dynamic visual profile evaluation mapped from personal encrypted scanning history log databases.")
    st.divider()

    try:
        hist_res = requests.get(FASTAPI_HISTORY_URL, headers=auth_headers)
        if hist_res.status_code == 200:
            hist_dataset = hist_res.json()
            
            if not hist_dataset:
                st.info("Analytics engine needs data entries before compiling curves. Execute a scan task first!")
            else:
                df = pd.DataFrame(hist_dataset)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.metric(label="Total Scans Processed", value=len(df))
                with m_col2:
                    st.metric(label="Mean Historical Health Index", value=f"{df['health_score'].mean():.2f} / 10")
                with m_col3:
                    unsafe_count = len(df[df['color'].str.lower() == 'red'])
                    st.metric(label="Critical Risk Alerts Encountered", value=unsafe_count, delta="Attention Advised" if unsafe_count > 0 else "Nominal", delta_color="inverse")
                
                st.divider()
                graph_col1, graph_col2 = st.columns(2)
                
                with graph_col1:
                    st.subheader("Dietary Composition Health Profile Distribution")
                    color_pie = px.pie(df, names='color', color='color',
                                       color_discrete_map={'green':'#2ca02c', 'yellow':'#bcbd22', 'red':'#d62728'},
                                       hole=0.4)
                    st.plotly_chart(color_pie, use_container_width=True)
                    
                with graph_col2:
                    st.subheader("Chronological Scan Index Progress Curve")
                    df_sorted = df.sort_values(by='timestamp')
                    timeline_chart = px.line(df_sorted, x='timestamp', y='health_score', 
                                             markers=True, labels={'health_score': 'Score Index Metric', 'timestamp': 'Date Mapping Timeline'})
                    st.plotly_chart(timeline_chart, use_container_width=True)
        else:
            st.error("Data pipeline authorization clearance missing.")
    except Exception as analytics_err:
        st.error(f"Plotly charting interface failed visualization mapping: {analytics_err}")
with tab3:
    st.title(" Archived Audit Log Ledger")
    st.write("Review past evaluations saved on your account profile.")
    st.divider()

    try:
        history_response = requests.get(FASTAPI_HISTORY_URL, headers=auth_headers)
        if history_response.status_code == 200:
            history_data = history_response.json()
            
            if not history_data:
                st.info("No history found :)")
            else:
                for record in history_data:
                    clean_time = record.get("timestamp", "").replace("T", " ")[:19]
                    
                    with st.container(border=True):
                        h_col1, h_col2 = st.columns([1, 4])
                        with h_col1:
                            h_score = record.get("health_score", 0)
                            h_color = record.get("color", "yellow").lower()
                            if h_color == "green":
                                st.metric(label="Status: Safe", value=f"{h_score}/10")
                            elif h_color == "yellow":
                                st.metric(label="Status: Warn", value=f"{h_score}/10", delta_color="off")
                            else:
                                st.metric(label="Status: Risk", value=f"{h_score}/10", delta_color="inverse")
                                
                        with h_col2:
                            st.markdown(f"### 📦 File Profile: {record.get('filename')}")
                            st.caption(f"🕒 Engine Registry Timestamp: {clean_time} | Database Entry ID Reference: #{record.get('id')}")
                            st.write(f"**Structural Synthesis:** {record.get('summary')}")
                            
                            with st.expander("Expand Deep Metric Element Analysis Breakdown"):
                                exp_col1, exp_col2 = st.columns(2)
                                with exp_col1:
                                    st.markdown("**Recognized Chemical Additive Lists:**")
                                    for flags_item in record.get("red_flags", []):
                                        st.markdown(f" {flags_item}")
                                with exp_col2:
                                    st.markdown("**Suggested Nutritional Swaps:**")
                                    for alts_item in record.get("healthy_alternatives", []):
                                        st.markdown(f" {alts_item}")
        else:
            st.error("Failed server request initialization payload authentication tracking parameters.")
    except Exception as e:
        st.error(f"Cannot map data streams to history interface: {e}")