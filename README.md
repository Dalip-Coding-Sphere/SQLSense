# SQLSense 🧠

**An AI-powered data analyst assistant that lets you upload any CSV or Excel file and query it in plain English — no SQL knowledge required.**

🔗 **Live demo:** [sqlsense.onrender.com](https://sqlsense-s7vg.onrender.com) *(first load may take ~30-50s on free hosting)*

---

## Overview

SQLSense bridges the gap between business users and their data. Instead of writing SQL queries, a user simply uploads a spreadsheet and asks a question like *"Which category had the highest sales?"* — the app translates that question into a real SQL query, runs it, and returns the answer as a number, table, or chart.

This was built to demonstrate how large language models can be combined with traditional data tools (SQL, pandas) to make data analysis accessible to non-technical users — a pattern increasingly used in real business intelligence tools.

## Features

- **Upload any dataset** — works with any CSV or Excel file, not limited to one fixed dataset
- **Natural language to SQL** — powered by Groq's Llama 3.3 70B model
- **Self-correcting queries** — if a generated query fails, the app automatically sends the error back to the LLM and retries
- **Smart visualization** — automatically chooses between a metric card, a data table, or a horizontal bar chart depending on the shape of the result
- **Chart clutter control** — datasets with many categories are automatically condensed (top categories + an "Others" group) so charts stay readable
- **Auto-suggested questions** — generates relevant starter questions based on the uploaded file's column types
- **Robust column handling** — automatically cleans messy column names (spaces, special characters) so the SQL engine never breaks on real-world, untidy data

## Tech stack

| Layer | Tool |
|---|---|
| Frontend / app framework | Streamlit |
| Data processing | Pandas |
| Query engine | DuckDB (in-memory SQL on uploaded files) |
| LLM | Groq API (Llama 3.3 70B) |
| Visualization | Plotly |
| Deployment | Render |

## How it works

1. User uploads a CSV/Excel file → loaded into a pandas DataFrame and registered as a table in an in-memory DuckDB database
2. User types a question in plain English
3. The app sends the column names, data types, and a few sample rows to the Groq LLM, asking it to write one valid SQL query that answers the question
4. The generated SQL is executed against the DuckDB table
5. If the query fails (e.g. due to a misunderstood column name), the error is sent back to the LLM for a single self-correction attempt
6. The result is rendered as a metric, table, or chart depending on its shape

## Running locally

```bash
git clone https://github.com/Dalip-Coding-Sphere/SQLSense.git
cd SQLSense
pip install -r requirements.txt

# set your Groq API key (free at console.groq.com)
export GROQ_API_KEY="your-key-here"   # Windows PowerShell: $env:GROQ_API_KEY="your-key-here"

streamlit run app.py
```

## Future improvements

- Support for connecting directly to live databases instead of static file uploads
- Query history per session
- Support for multi-table joins when more than one file is uploaded

---