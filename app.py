import os
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from groq import Groq

st.set_page_config(page_title="SQLSense", layout="centered")
st.title("🧠 SQLSense")
st.caption("Upload any CSV or Excel file and ask questions about it in plain English.")

MAX_CHART_CATEGORIES = 10  # beyond this, we group the rest into "Others" to avoid clutter


def round_value(val):
    """Round numbers neatly for display. Keeps text/dates untouched."""
    if isinstance(val, float):
        return round(val, 2)
    return val


def suggest_questions(df):
    """Look at column types and propose a few relevant starter questions."""
    questions = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

    if numeric_cols:
        questions.append(f"What is the total {numeric_cols[0]}?")
    if text_cols and numeric_cols:
        questions.append(f"Show total {numeric_cols[0]} by {text_cols[0]}")
    if text_cols:
        questions.append(f"Which {text_cols[0]} appears the most?")
    if date_cols and numeric_cols:
        questions.append(f"How has {numeric_cols[0]} changed over time?")

    return questions[:4]


def build_prompt(question, schema_text, sample_rows, error_context=None):
    base = f"""
You are a SQL expert working with DuckDB. The table is named "data" and has these columns: {schema_text}.
Here are a few sample rows from the table to understand the data format:
{sample_rows}

Write ONE valid DuckDB SQL query that answers this question: "{question}"
Only return the SQL query. No explanation, no markdown formatting.
"""
    if error_context:
        base += f"\nThe previous attempt failed with this error: {error_context}\nFix the query and try again."
    return base


def ask_llm(client, prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    sql_query = response.choices[0].message.content.strip()
    return sql_query.replace("```sql", "").replace("```", "").strip()


def render_result(result, question):
    """Decide the best way to display a query result: metric, table, or chart."""
    # Round all numeric columns for clean display
    for col in result.select_dtypes(include="number").columns:
        result[col] = result[col].round(2)

    if result.shape == (1, 1):
        st.metric(label=question, value=result.iloc[0, 0])
        return

    if result.shape[0] > 1 and result.shape[1] == 2:
        label_col, value_col = result.columns[0], result.columns[1]
        chart_data = result.sort_values(by=value_col, ascending=False)

        # Avoid clutter: if too many categories, keep top N and group the rest as "Others"
        if chart_data.shape[0] > MAX_CHART_CATEGORIES:
            top = chart_data.head(MAX_CHART_CATEGORIES - 1)
            others_total = chart_data.iloc[MAX_CHART_CATEGORIES - 1:][value_col].sum()
            others_row = pd.DataFrame({label_col: ["Others"], value_col: [others_total]})
            chart_data = pd.concat([top, others_row], ignore_index=True)

        st.dataframe(result, use_container_width=True)

        # Horizontal bar chart reads better when labels are long or numerous
        fig = px.bar(
            chart_data,
            x=value_col,
            y=label_col,
            orientation="h",
            text=value_col,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        return

    st.dataframe(result, use_container_width=True)


# --- API key comes from an environment variable, set in Render's dashboard ---
# This keeps the key private and means visitors never have to enter anything.
api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("GROQ_API_KEY is not set. Add it as an environment variable to use this app.")
    st.stop()

# --- File upload ---
uploaded_file = st.file_uploader("Upload your data file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"File uploaded: {uploaded_file.name} ({df.shape[0]} rows, {df.shape[1]} columns)")
    st.dataframe(df.head(), use_container_width=True)

    # Clean column names: spaces, colons, and other special characters confuse SQL engines
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"[^0-9a-zA-Z_]+", "_", regex=True)
        .str.strip("_")
    )

    con = duckdb.connect(database=":memory:")
    con.register("data", df)

    schema_text = ", ".join([f"{col} ({str(dtype)})" for col, dtype in df.dtypes.items()])
    sample_rows = df.head(3).to_string(index=False)

    # --- Suggested questions ---
    st.write("**Try one of these, or ask your own:**")
    suggestions = suggest_questions(df)
    cols = st.columns(len(suggestions)) if suggestions else []
    clicked_question = None
    for col, q in zip(cols, suggestions):
        if col.button(q):
            clicked_question = q

    question = st.text_input("Ask a question about your data", value=clicked_question or "")

    if question:
        client = Groq(api_key=api_key)
        prompt = build_prompt(question, schema_text, sample_rows)

        with st.spinner("Thinking..."):
            sql_query = ask_llm(client, prompt)

        st.code(sql_query, language="sql")

        try:
            result = con.execute(sql_query).fetchdf()
            render_result(result, question)

        except Exception as first_error:
            # Retry once: send the error back to the LLM so it can self-correct
            with st.spinner("That didn't work, trying a fix..."):
                retry_prompt = build_prompt(question, schema_text, sample_rows, error_context=str(first_error))
                sql_query_retry = ask_llm(client, retry_prompt)

            st.code(sql_query_retry, language="sql")
            try:
                result = con.execute(sql_query_retry).fetchdf()
                render_result(result, question)
            except Exception as second_error:
                st.error(
                    "Couldn't answer that question, even after a retry. "
                    "Try rephrasing it more simply, or check that column names are spelled correctly.\n\n"
                    f"Technical details: {second_error}"
                )

else:
    st.info("Upload a CSV or Excel file to get started.")
