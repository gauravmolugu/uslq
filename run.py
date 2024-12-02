import os
import sqlite3
import pandas as pd
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key = os.getenv("GOOGLE_API_KEY"))

def get_table_schema(db_path):
    """Get schema information for all tables in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_info = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        schema_info[table_name] = [f"{col[1]} ({col[2]})" for col in columns]
    
    conn.close()
    return schema_info

def identify_relevant_tables(question):
    """Step 1: Identify relevant tables from the question"""
    prompt = """
    Given the following question, identify which database tables might be needed to answer it.
    Only return the table names in a comma-separated list, nothing else.
    Available tables: STUDENT
    
    Question: {question}
    """
    
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt.format(question=question))
    return [table.strip() for table in response.text.split(',')]

def generate_sql_query(question, schema_info):
    """Step 2: Generate SQL query using the schema information"""
    schema_prompt = "Database Schema:\n"
    for table, columns in schema_info.items():
        schema_prompt += f"Table: {table}\n"
        schema_prompt += f"Columns: {', '.join(columns)}\n"
    
    prompt = f"""
    You are an expert in converting English questions to SQL queries.
    {schema_prompt}
    
    Generate a SQL query for the following question. 
    Return ONLY the SQL query without any additional text, explanations, or SQL formatting markers (like ```sql).
    Do not include any markdown formatting.
    
    Question: {question}
    """
    
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    
    # Clean the response
    clean_query = response.text.strip()
    # Remove SQL markdown if present
    clean_query = clean_query.replace('```sql', '').replace('```', '')
    # Remove any additional whitespace and newlines
    clean_query = ' '.join(clean_query.split())
    
    return clean_query

def execute_sql_query(sql, db_path):
    """Execute the SQL query and return results"""
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception as e:
        conn.close()
        return str(e)

# Streamlit UI
st.set_page_config(page_title="Natural Language to SQL")
st.header("Natural Language to SQL Query Generator")

db_path = "student.db"
question = st.text_input("Enter your question:", key="input")

if st.button("Execute"):
    if question:
        # Step 1: Identify relevant tables
        relevant_tables = identify_relevant_tables(question)
        st.write("Relevant tables identified:", relevant_tables)
        
        # Get schema information for relevant tables
        schema_info = {table: get_table_schema(db_path).get(table, []) 
                      for table in relevant_tables}
        st.write("Schema information:", schema_info)
        
        # Step 2: Generate SQL query
        sql_query = generate_sql_query(question, schema_info)
        st.write("Generated SQL Query:", sql_query)
        
        # Execute query and show results
        results = execute_sql_query(sql_query, db_path)
        if isinstance(results, pd.DataFrame):
            st.write("Query Results:")
            st.dataframe(results)
        else:
            st.error(f"Error executing query: {results}")

# Database initialization (run once)
def init_database():
    connection = sqlite3.connect("student.db")
    cursor = connection.cursor()
    
    # Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS STUDENT(
        NAME VARCHAR(25), 
        CLASS VARCHAR(25), 
        SECTION VARCHAR(25), 
        MARKS INT
    )
    """)
    
    # Insert sample data
    sample_data = [
        ('Krish', 'Data Science', 'A', 90),
        ('Manohar', 'Machine Learning', 'A', 90),
        ('Abhinav', 'Python', 'A', 90),
        ('Aneesh', 'SQL', 'A', 90),
        ('Rahul', 'FCS', 'A', 90)
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO STUDENT VALUES (?,?,?,?)', sample_data)
    connection.commit()
    connection.close()

if __name__ == "__main__":
    init_database()