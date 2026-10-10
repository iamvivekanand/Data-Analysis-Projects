import streamlit as st
import importlib
import query_engine
importlib.reload(query_engine)
import pandas as pd
import plotly.express as px
import os
import query_engine

st.set_page_config(
    page_title="Conversational BI Engine",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💡 Conversational Business Intelligence Engine")
st.markdown("Natural Language se dynamic SQL queries execute karein aur automated visual analytics dekhein.")

# Sidebar Configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Google AI Studio ki API key enter karein")

uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset", type=["csv"])
default_data_path = os.path.join("data", "ecommerce_business_data.csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"Custom CSV Loaded: {len(df):,} rows")
elif os.path.exists(default_data_path):
    df = pd.read_csv(default_data_path)
    st.sidebar.info(f"Sample E-commerce Data Loaded: {len(df):,} rows")
else:
    st.error("Dataset nahi mila! Pehle data_generator.py chalayein ya CSV upload karein.")
    st.stop()

# Schema & DuckDB Setup
schema_dict = {col: str(dtype) for col, dtype in df.dtypes.items()}
con = query_engine.setup_duckdb(df)

with st.expander("👀 Dataset Preview & Schema Details", expanded=False):
    st.dataframe(df.head(5), use_container_width=True)
    st.json(schema_dict)

# Analytical Query Interface
st.subheader("Query Your Data")
sample_queries = [
    "Custom Question",
    "Top 5 categories by total revenue in a bar chart",
    "Monthly revenue trend over time",
    "Average profit and revenue by sales channel",
    "Region-wise total units sold"
]

selected_prompt = st.selectbox("Quick Analytical Questions:", sample_queries)

if selected_prompt == "Custom Question":
    user_prompt = st.text_input("Aapka sawal:", placeholder="e.g., Show profit breakdown across regions")
else:
    user_prompt = st.text_input("Aapka sawal:", value=selected_prompt)

run_btn = st.button("Analyze & Run Query", type="primary")

if run_btn:
    if not api_key:
        st.error("Kripya sidebar mein Gemini API Key enter karein.")
    elif not user_prompt:
        st.warning("Kripya koi analytical sawal enter karein.")
    else:
        with st.spinner("AI SQL query generate karke analyze kar raha hai..."):
            try:
                # 1. AI planning via query_engine
                plan = query_engine.generate_sql_and_viz_plan(user_prompt, schema_dict, api_key)
                sql_query = plan.get("sql")
                chart_type = plan.get("chart_type", "none")
                x_col = plan.get("x_col")
                y_col = plan.get("y_col")
                explanation = plan.get("explanation", "")

                st.markdown(f"**Business Focus:** {explanation}")

                # 2. DuckDB execution
                result_df = query_engine.execute_query(con, sql_query)

                col1, col2 = st.columns([1, 1.2])

                with col1:
                    st.markdown("**Structured Result:**")
                    st.dataframe(result_df, use_container_width=True)

                    with st.expander("Generated SQL Query"):
                        st.code(sql_query, language="sql")

                with col2:
                    st.markdown("**Visual Dashboard:**")
                    if chart_type != "none" and x_col in result_df.columns and y_col in result_df.columns:
                        if chart_type == "bar":
                            fig = px.bar(result_df, x=x_col, y=y_col, title=f"{y_col} by {x_col}", template="plotly_white")
                        elif chart_type == "line":
                            fig = px.line(result_df, x=x_col, y=y_col, title=f"{y_col} Trend", markers=True, template="plotly_white")
                        elif chart_type == "pie":
                            fig = px.pie(result_df, names=x_col, values=y_col, title=f"Share of {y_col} by {x_col}")
                        elif chart_type == "scatter":
                            fig = px.scatter(result_df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}", template="plotly_white")
                        else:
                            fig = None

                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Chart render ke liye standard parameters available nahi hain.")
                    else:
                        st.info("Is aggregation ke liye tabular view best suited hai.")

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")