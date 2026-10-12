import io
import os
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
import engine

# Environment variables load karein
load_dotenv()

st.set_page_config(
    page_title="Gaming Market Intelligence Engine",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Gaming Market Intelligence Engine")
st.caption("Enterprise-grade conversational analytics powered by DuckDB, Gemini, and Plotly.")

# Dataset Loading
@st.cache_data
def load_vgsales_data():
    file_path = os.path.join("data", "vgsales.csv")
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    return df

df = load_vgsales_data()

if df is None:
    st.error("Dataset 'data/vgsales.csv' nahi mila! Kripya CSV file ko data folder me place karein.")
    st.stop()

# DuckDB setup
schema_dict = {col: str(dtype) for col, dtype in df.dtypes.items()}
con = engine.setup_duckdb(df)

# Sidebar Configuration
st.sidebar.header("Enterprise Settings")
env_key = os.getenv("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "Gemini API Key", 
    value=env_key, 
    type="password", 
    help="Defaulted from .env file for production deployments"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Dataset Summary")
st.sidebar.write(f"**Total Records:** {len(df):,}")
st.sidebar.write(f"**Platforms:** {df['Platform'].nunique()}")
st.sidebar.write(f"**Publishers:** {df['Publisher'].nunique()}")

if st.sidebar.button("Clear Chat History"):
    st.session_state["messages"] = []
    st.rerun()

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
top_publisher = df.groupby("Publisher")["Global_Sales"].sum().idxmax()
top_platform = df.groupby("Platform")["Global_Sales"].sum().idxmax()

with kpi1:
    st.metric("Total Catalog Titles", f"{len(df):,}")
with kpi2:
    st.metric("Total Global Sales", f"{df['Global_Sales'].sum():,.2f} M units")
with kpi3:
    st.metric("Leading Publisher", str(top_publisher))
with kpi4:
    st.metric("Dominant Platform", str(top_platform))

st.markdown("---")

# Session State for Conversation History
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Quick Query Templates
with st.expander("Quick Analytical Prompt Ideas", expanded=False):
    st.markdown("""
    - `Top 10 publishers by global sales in a bar chart`
    - `Show the trend of global video game sales over the years`
    - `Which genre has the highest sales in North America vs Europe?`
    - `Compare regional sales breakdown (NA, EU, JP, Other) across Action, Sports, and Shooter genres`
    - `Top 5 bestselling games on Nintendo DS or PS2`
    """)

# Display Chat History
for msg in st.session_state["messages"]:
    with st.chat_message("user"):
        st.write(msg["question"])
    
    with st.chat_message("assistant"):
        st.markdown(f"**Executive Insight:** {msg['explanation']}")
        
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.dataframe(msg["data"], use_container_width=True)
            with st.expander("View Sanitized SQL (Audit Log)"):
                st.code(msg["sql"], language="sql")
        
        with c2:
            if msg.get("fig"):
                st.plotly_chart(msg["fig"], use_container_width=True)

# User Input
user_prompt = st.chat_input("Ask a market question (e.g., 'Compare PS4 vs Xbox One global sales by year')...")

if user_prompt:
    if not api_key:
        st.error("API Key missing! .env file me add karein ya sidebar me paste karein.")
    else:
        with st.chat_message("user"):
            st.write(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing market data and generating visual breakdown..."):
                try:
                    plan = engine.generate_analytical_plan(
                        user_query=user_prompt,
                        schema_dict=schema_dict,
                        chat_history=st.session_state["messages"],
                        api_key=api_key
                    )
                    
                    sql_query = plan.get("sql")
                    chart_type = plan.get("chart_type", "none")
                    x_col = plan.get("x_col")
                    y_col = plan.get("y_col")
                    explanation = plan.get("explanation", "")

                    # Execute query
                    result_df = engine.execute_query(con, sql_query)

                    st.markdown(f"**Executive Insight:** {explanation}")

                    fig = None
                    col_data, col_chart = st.columns([1, 1.2])

                    with col_data:
                        st.dataframe(result_df, use_container_width=True)
                        
                        # Client Export Buttons (CSV + Excel)
                        b1, b2 = st.columns(2)
                        with b1:
                            csv_data = result_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="📥 Export CSV",
                                data=csv_data,
                                file_name="gaming_market_analysis.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with b2:
                            excel_buffer = io.BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                                result_df.to_excel(writer, index=False, sheet_name="Market_Data")
                            st.download_button(
                                label="📊 Export Excel",
                                data=excel_buffer.getvalue(),
                                file_name="gaming_market_analysis.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

                        with st.expander("View Sanitized SQL (Audit Log)"):
                            st.code(sql_query, language="sql")

                    with col_chart:
                        if chart_type != "none" and x_col in result_df.columns and y_col in result_df.columns:
                            if chart_type == "bar":
                                fig = px.bar(result_df, x=x_col, y=y_col, title=f"{y_col} by {x_col}", template="plotly_white")
                            elif chart_type == "line":
                                fig = px.line(result_df, x=x_col, y=y_col, title=f"{y_col} Trend", markers=True, template="plotly_white")
                            elif chart_type == "pie":
                                fig = px.pie(result_df, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}")
                            elif chart_type == "scatter":
                                fig = px.scatter(result_df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}", template="plotly_white")
                            
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Tabular view is optimal for this summary.")

                    # Save to chat history
                    st.session_state["messages"].append({
                        "question": user_prompt,
                        "explanation": explanation,
                        "data": result_df,
                        "sql": sql_query,
                        "fig": fig
                    })

                except ValueError as ve:
                    st.error(f"Security Alert: {str(ve)}")
                except Exception as e:
                    st.error(f"Analysis Pipeline Error: {str(e)}")