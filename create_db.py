import duckdb

def create_construction_db():
    # Connect to the database (this will create it if it doesn't exist)
    conn = duckdb.connect('construction_db.db')
    
    try:
        # Create tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY,
                project_name VARCHAR,
                client_name VARCHAR,
                start_date DATE,
                end_date DATE,
                status VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY,
                project_id INTEGER,
                task_name VARCHAR,
                description TEXT,
                status VARCHAR,
                due_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        print("Database created successfully!")

    except Exception as e:
        print(f"Error creating database: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    create_construction_db() 