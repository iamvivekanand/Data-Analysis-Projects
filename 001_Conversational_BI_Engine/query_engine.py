import json
import re
import duckdb
import pandas as pd
import google.generativeai as genai

def setup_duckdb(df: pd.DataFrame):
    """Pandas DataFrame ko DuckDB in-memory table me register karta hai."""
    con = duckdb.connect(database=":memory:")
    con.register("df_table", df)
    return con

def generate_sql_and_viz_plan(user_query: str, schema_dict: dict, api_key: str) -> dict:
    """User ke question aur schema se valid DuckDB SQL aur chart metadata banata hai."""
    genai.configure(api_key=api_key)
    
    # Active supported model
    try:
        model = genai.GenerativeModel("gemini-3.8-flash")
    except Exception:
        model = genai.GenerativeModel("gemini-flash-latest")

    system_instruction = f"""
    You are an expert Data Analyst and DuckDB SQL Engineer.
    The user wants to analyze an in-memory SQL table named 'df_table'.
    Table schema:
    {json.dumps(schema_dict)}

    Return ONLY a strict JSON object with these keys:
    1. "sql": A valid DuckDB SQL query querying 'df_table'.
    2. "chart_type": One of ["bar", "line", "pie", "scatter", "none"].
    3. "x_col": Column name for X-axis (if applicable, else null).
    4. "y_col": Column name for Y-axis (if applicable, else null).
    5. "explanation": 1-2 line summary of what this analysis reveals.

    Do NOT include markdown fences, comments, or backticks in the response.
    """

    response = model.generate_content(f"{system_instruction}\n\nUser Question: {user_query}")
    clean_text = response.text.strip()
    clean_text = re.sub(r"^```json", "", clean_text, flags=re.IGNORECASE).strip()
    clean_text = re.sub(r"^```", "", clean_text).strip()
    clean_text = re.sub(r"```$", "", clean_text).strip()

    return json.loads(clean_text)

def execute_query(con, sql_query: str) -> pd.DataFrame:
    """DuckDB SQL query run karke result DataFrame return karta hai."""
    return con.execute(sql_query).df()