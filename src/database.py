import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "reddit_miner.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    """Initializes the database with the new schema, including sub-categories."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS run_opportunities")
    cursor.execute("DROP TABLE IF EXISTS opportunities")
    cursor.execute("DROP TABLE IF EXISTS runs")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            subreddit TEXT,
            keywords TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            opportunity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            post_created_utc DATETIME,
            category TEXT,
            sub_category TEXT, -- New field
            pain_points TEXT,
            business_opportunities TEXT,
            automation_ideas TEXT,
            confidence_score INTEGER,
            summary TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_opportunities (
            run_id INTEGER,
            opportunity_id INTEGER,
            FOREIGN KEY (run_id) REFERENCES runs(run_id),
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
            PRIMARY KEY (run_id, opportunity_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database '{DB_FILE}' initialized with sub-category and date tracking.")

def create_run(subreddit: str, keywords: str) -> int:
    """Creates a new run entry and returns the run_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO runs (subreddit, keywords) VALUES (?, ?)", (subreddit, keywords))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def insert_opportunity(run_id: int, opportunity: dict) -> bool:
    """
    Inserts an opportunity and links it to a run.
    Returns True if a new link was created for this run, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO opportunities (url, title, post_created_utc, category, sub_category, pain_points,
                                     business_opportunities, automation_ideas, confidence_score, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                post_created_utc=excluded.post_created_utc,
                category=excluded.category,
                sub_category=excluded.sub_category,
                pain_points=excluded.pain_points,
                business_opportunities=excluded.business_opportunities,
                automation_ideas=excluded.automation_ideas,
                confidence_score=excluded.confidence_score,
                summary=excluded.summary
        """, (
            opportunity.get('url'),
            opportunity.get('title'),
            opportunity.get('post_created_utc'),
            opportunity.get('category'),
            opportunity.get('sub_category'), # New field
            opportunity.get('pain_points'),
            opportunity.get('business_opportunities'),
            opportunity.get('automation_ideas'),
            opportunity.get('confidence_score'),
            opportunity.get('summary')
        ))
        
        cursor.execute("SELECT opportunity_id FROM opportunities WHERE url = ?", (opportunity.get('url'),))
        result = cursor.fetchone()
        if result is None: return False
        opportunity_id = result['opportunity_id']

        cursor.execute("INSERT OR IGNORE INTO run_opportunities (run_id, opportunity_id) VALUES (?, ?)", (run_id, opportunity_id))
        
        is_new_link = cursor.rowcount > 0
        conn.commit()
        return is_new_link
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def list_runs(runs_after: str = None, runs_before: str = None):
    # This function remains the same as before
    conn = get_db_connection()
    try:
        query = "SELECT run_id, timestamp, subreddit, keywords FROM runs"
        conditions = []
        params = []

        if runs_after:
            conditions.append("timestamp >= ?")
            params.append(runs_after)
        
        if runs_before:
            conditions.append("timestamp <= ?")
            params.append(runs_before)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC"

        df = pd.read_sql_query(query, conn, params=params)
        print("\n--- Previous Runs ---")
        if df.empty:
            print("No runs found for the specified criteria.")
        else:
            print(df.to_string(index=False))
        print("---------------------\n")
    finally:
        conn.close()

# This is the new, more powerful analysis function
def generate_report(filters: dict):
    """
    Generates and prints a report based on a set of filters.
    
    Args:
        filters (dict): A dictionary containing filters like:
            'report_type': 'category', 'subcategory', or 'subreddit_bias'
            'run_ids': list of ints
            'runs_after'/'runs_before': 'YYYY-MM-DD' strings
            'posts_after'/'posts_before': 'YYYY-MM-DD' strings
            'category_filter': string for filtering by main category
    """
    conn = get_db_connection()
    try:
        report_type = filters.get('report_type')
        
        # Base query joining all tables
        query = """
            FROM opportunities o
            JOIN run_opportunities ro ON o.opportunity_id = ro.opportunity_id
            JOIN runs r ON ro.run_id = r.run_id
        """
        
        conditions = []
        params = []
        
        # Build WHERE clause from filters
        if filters.get('run_ids'):
            ids = filters['run_ids']
            conditions.append("r.run_id IN ({seq})".format(seq=','.join(['?']*len(ids))))
            params.extend(ids)
        if filters.get('runs_after'):
            conditions.append("r.timestamp >= ?")
            params.append(filters['runs_after'])
        if filters.get('runs_before'):
            conditions.append("r.timestamp <= ?")
            params.append(filters['runs_before'])
        if filters.get('posts_after'):
            conditions.append("o.post_created_utc >= ?")
            params.append(filters['posts_after'])
        if filters.get('posts_before'):
            conditions.append("o.post_created_utc <= ?")
            params.append(filters['posts_before'])
        if filters.get('category_filter'):
            conditions.append("o.category = ?")
            params.append(filters['category_filter'])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # --- Select and Group based on Report Type ---
        if report_type == 'category':
            select_clause = "SELECT o.category, COUNT(DISTINCT o.opportunity_id) as count"
            group_by_clause = "GROUP BY o.category"
            title = "Category Summary"
        elif report_type == 'subcategory':
            select_clause = "SELECT o.category, o.sub_category, COUNT(DISTINCT o.opportunity_id) as count"
            group_by_clause = "GROUP BY o.category, o.sub_category"
            title = f"Sub-Category Summary for '{filters.get('category_filter', 'All')}'"
        elif report_type == 'subreddit_bias':
            select_clause = "SELECT r.subreddit, o.category, COUNT(DISTINCT o.opportunity_id) as count"
            group_by_clause = "GROUP BY r.subreddit, o.category"
            title = "Subreddit-Category Bias"
        else:
            print("Invalid report type specified.")
            return

        full_query = f"{select_clause} {query} {group_by_clause} ORDER BY count DESC"
        
        df = pd.read_sql_query(full_query, conn, params=params)
        
        print(f"\n--- Report: {title} ---")
        if df.empty:
            print("No data found for the specified criteria.")
        else:
            # Calculate and add percentage column
            total = df['count'].sum()
            df['percentage'] = (df['count'] / total * 100).round(2).astype(str) + '%' # Corrected percentage calculation
            print(df.to_string(index=False))
        print("--------------------------------\n")

    finally:
        conn.close()
