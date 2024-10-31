import duckdb

def initialize_databases():
    """Initialize all DuckDB databases with proper schemas"""
    
    # Document Store Schema
    doc_db = duckdb.connect("document_store.db")
    doc_db.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            type VARCHAR NOT NULL,
            content TEXT NOT NULL,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            content TEXT NOT NULL,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Technical Store Schema
    tech_db = duckdb.connect("technical_store.db")
    tech_db.execute("""
        CREATE TABLE IF NOT EXISTS validations (
            id INTEGER PRIMARY KEY,
            project_type VARCHAR NOT NULL,
            specifications JSON,
            results TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS standards (
            id INTEGER PRIMARY KEY,
            category VARCHAR NOT NULL,
            content TEXT NOT NULL,
            source VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Compliance Store Schema
    comp_db = duckdb.connect("compliance_store.db")
    comp_db.execute("""
        CREATE TABLE IF NOT EXISTS compliance_checks (
            id INTEGER PRIMARY KEY,
            project_location VARCHAR NOT NULL,
            check_type VARCHAR NOT NULL,
            results TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS permits (
            id INTEGER PRIMARY KEY,
            type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            details JSON,
            expiry_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Cost Store Schema
    cost_db = duckdb.connect("cost_store.db")
    cost_db.execute("""
        CREATE TABLE IF NOT EXISTS cost_estimates (
            id INTEGER PRIMARY KEY,
            location VARCHAR NOT NULL,
            estimate_type VARCHAR NOT NULL,
            specifications JSON,
            results TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS market_rates (
            id INTEGER PRIMARY KEY,
            category VARCHAR NOT NULL,
            location VARCHAR NOT NULL,
            rate DECIMAL(10,2),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Resource Store Schema
    res_db = duckdb.connect("resource_store.db")
    res_db.execute("""
        CREATE TABLE IF NOT EXISTS resource_allocations (
            id INTEGER PRIMARY KEY,
            request_details JSON,
            priority VARCHAR NOT NULL,
            allocation_plan TEXT NOT NULL,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS resource_monitoring (
            id INTEGER PRIMARY KEY,
            project_id VARCHAR NOT NULL,
            monitoring_type VARCHAR NOT NULL,
            results TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS resource_utilization (
            id INTEGER PRIMARY KEY,
            project_id VARCHAR NOT NULL,
            resource_type VARCHAR NOT NULL,
            utilization_rate DECIMAL(5,2),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """) 