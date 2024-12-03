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
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema_info[table_name] = [f"{col[1]} ({col[2]})" for col in columns]
        
        return schema_info
    except Exception as e:
        st.error(f"Error getting schema: {str(e)}")
        return {}
    finally:
        conn.close()


def identify_relevant_tables(question):
    """Step 1: Identify relevant tables from the question"""
    try:
        # Get all available tables
        available_tables = list(get_table_schema("student.db").keys())
        
        prompt = f"""
        Given the following question, identify which database tables might be needed to answer it.
        Only return the table names in a comma-separated list, nothing else.
        Available tables: {', '.join(available_tables)}
        
        Question: {question}
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        tables = [table.strip() for table in response.text.split(',')]
        
        # Validate that returned tables actually exist
        valid_tables = [table for table in tables if table in available_tables]
        if not valid_tables:
            return available_tables  # Return all tables if no valid ones identified
        return valid_tables
    except Exception as e:
        st.error(f"Error identifying tables: {str(e)}")
        return []

def generate_sql_query(question, schema_info):
    """Step 2: Generate SQL query using the schema information"""
    try:
        schema_prompt = "Database Schema:\n"
        for table, columns in schema_info.items():
            schema_prompt += f"Table: {table}\n"
            schema_prompt += f"Columns: {', '.join(columns)}\n"
        
        prompt = f"""
        You are an expert in converting English questions to SQL queries.
        {schema_prompt}
        
        Rules:
        1. Return ONLY the SQL query without any additional text or formatting
        2. For CREATE TABLE queries, add IF NOT EXISTS
        3. For INSERT queries, use single quotes for string values
        4. For SELECT queries, ensure proper JOIN conditions if multiple tables
        5. Ensure proper WHERE clause formatting
        
        Question: {question}
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Clean the response
        clean_query = response.text.strip()
        clean_query = clean_query.replace('```sql', '').replace('```', '')
        clean_query = ' '.join(clean_query.split())
        
        # Validate basic SQL syntax
        if not any(clean_query.upper().startswith(keyword) for keyword in 
                  ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']):
            raise ValueError("Invalid SQL query generated")
            
        return clean_query
    except Exception as e:
        st.error(f"Error generating query: {str(e)}")
        return None

def execute_sql_query(sql, db_path):
    """Execute the SQL query and return results"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        sql_type = sql.strip().upper().split()[0]
        
        if sql_type == 'SELECT':
            df = pd.read_sql_query(sql, conn)
            # Reset index and format the dataframe
            # df = df.reset_index(drop=True)
            return {
                'success': True, 
                'data': df.style.set_properties(**{
                    'background-color': '#080808',
                    'border': '1px solid black',
                    'padding': '5px'
                }), 
                'message': 'Query executed successfully'
            }
        else:
            cursor.execute(sql)
            conn.commit()
            if sql_type == 'INSERT':
                return {'success': True, 'message': f'Successfully inserted {cursor.rowcount} row(s)'}
            elif sql_type == 'UPDATE':
                return {'success': True, 'message': f'Successfully updated {cursor.rowcount} row(s)'}
            elif sql_type == 'DELETE':
                return {'success': True, 'message': f'Successfully deleted {cursor.rowcount} row(s)'}
            elif sql_type in ['CREATE', 'ALTER', 'DROP']:
                return {'success': True, 'message': 'Schema modification completed successfully'}
            
    except sqlite3.OperationalError as e:
        return {'success': False, 'error': f"Database error: {str(e)}"}
    except Exception as e:
        return {'success': False, 'error': f"Unexpected error: {str(e)}"}
    finally:
        if conn:
            conn.close()

# Streamlit UI
st.set_page_config(page_title="Natural Language to SQL")
st.header("Natural Language to SQL Query Generator")

if not os.path.exists("student.db"):
    st.error("Database not found! Please run 'python init_db.py' first.")
    st.stop()

db_path = "student.db"
question = st.text_input("Enter your question:", key="input")

if st.button("Execute"):
    if not question:
        st.warning("Please enter a question")
    else:
        with st.spinner("Processing..."):
            # Step 1: Identify relevant tables
            relevant_tables = identify_relevant_tables(question)
            if relevant_tables:
                st.info("Relevant tables identified: " + ", ".join(relevant_tables))
                
                # Get schema information
                schema_info = {table: get_table_schema(db_path).get(table, []) 
                             for table in relevant_tables}
                
                # Step 2: Generate SQL query
                sql_query = generate_sql_query(question, schema_info)
                if sql_query:
                    st.code(sql_query, language="sql")
                    
                    # Execute query
                    result = execute_sql_query(sql_query, db_path)
                    
                    if result['success']:
                        if 'data' in result:
                            st.success(result['message'])
                            # Add container with fixed height and scrolling
                            with st.container():
                                st.dataframe(
                                    result['data'],
                                    height=400,  # Fixed height
                                    use_container_width=True
                                )
                        else:
                            st.success(result['message'])
                    else:
                        st.error(result['error'])
            else:
                st.error("No relevant tables identified")

if __name__ == "__main__":
    pass
    # init_database()