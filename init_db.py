import sqlite3
import os

def init_database():
    # Remove existing database if it exists
    if os.path.exists("student.db"):
        os.remove("student.db")
        
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
    
    cursor.executemany('INSERT INTO STUDENT VALUES (?,?,?,?)', sample_data)
    connection.commit()
    connection.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()