import json
import re
import duckdb
import pandas as pd
import google.generativeai as genai

# Enterprise Security: Allowed only safe analytical read queries
FORBIDDEN_SQL_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bREPLACE\b"
]

def validate_sql_security(sql_query: str) -> bool:
    """Blocks any query attempting data mutation or structural changes."""
    cleaned = re.sub(r"--.*?\$|/\*.*?\*/", "", sql_query, flags=re.MULTILINE)
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            return False
    return True

def setup_duckdb(df: pd.DataFrame):
    """Registers Pandas DataFrame into DuckDB in-memory database."""
    con = duckdb.connect(database=":memory:")
    con.register("vgsales", df)
    return con

def generate_analytical_plan(user_query: str, schema_dict: dict, chat_history: list, api_key: str) -> dict:
    genai.configure(api_key=api_key)

    history_context = ""
    if chat_history:
        recent = chat_history[-3:]
        history_context = "\nRecent conversation turns for context:\n"
        for item in recent:
            history_context += f"- User: {item['question']}\n  SQL: {item.get('sql', 'N/A')}\n"

    system_instruction = f"""
    You are a Principal Data Engineer and Gaming Market Analyst.
    You analyze an in-memory SQL table named 'vgsales'.
    Table schema:
    {json.dumps(schema_dict)}

    Business Column Reference:
    - Rank (Integer): Overall ranking
    - Name (Text): Game title
    - Platform (Text): Console/Platform (e.g., PS4, X360, Wii, PC)
    - Year (Integer): Release year
    - Genre (Text): Game genre (e.g., Action, Sports, Shooter)
    - Publisher (Text): Publishing company (e.g., Nintendo, Electronic Arts)
    - NA_Sales, EU_Sales, JP_Sales, Other_Sales, Global_Sales (Float): Sales in Millions of units
    {history_context}

    Return ONLY a strict JSON object with these keys:
    1. "sql": A valid DuckDB SQL SELECT query on 'vgsales'.
    2. "chart_type": One of ["bar", "line", "pie", "scatter", "none"].
    3. "x_col": Column name for X-axis (if applicable, else null).
    4. "y_col": Column name for Y-axis (if applicable, else null).
    5. "explanation": 1-2 line executive summary of what this query reveals.

    STRICT RULES:
    - Never generate DDL or DML (NO DROP, DELETE, INSERT, UPDATE).
    - Only query from table 'vgsales'.
    - Use clean DuckDB syntax (e.g., ROUND, COALESCE where helpful).
    - Do NOT include markdown fences, triple backticks, or comments.
    """

    # Quota Fallback Hierarchy (ek model rate-limit ho toh agla use karein)
    candidate_models = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
    response = None
    last_error = None

    for m_name in candidate_models:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(f"{system_instruction}\n\nCurrent Question: {user_query}")
            if response:
                break
        except Exception as e:
            last_error = e
            continue

    if response is None:
        raise RuntimeError(f"Rate limit hit across all free-tier models. Please wait 30 seconds. Details: {last_error}")

    clean_text = response.text.strip()
    clean_text = re.sub(r"^```json", "", clean_text, flags=re.IGNORECASE).strip()
    clean_text = re.sub(r"^```", "", clean_text).strip()
    clean_text = re.sub(r"```$", "", clean_text).strip()

    plan = json.loads(clean_text)

    if not validate_sql_security(plan.get("sql", "")):
        raise ValueError("Security Violation: Non-read operation detected in generated SQL.")

    return plan

def execute_query(con, sql_query: str) -> pd.DataFrame:
    """Executes safe SQL query and returns result DataFrame."""
    return con.execute(sql_query).df()