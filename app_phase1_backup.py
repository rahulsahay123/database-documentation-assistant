# app.py - Main Streamlit Application
# Database Documentation Assistant - Phase 1: Basic Setup

import streamlit as st  # Web framework
import pyodbc  # SQL Server connection
import pandas as pd  # Data handling
from config import CONNECTION_STRING, DB_CONFIG  # Import connection details

# --- PAGE CONFIGURATION ---
# This sets up the Streamlit page appearance
st.set_page_config(
    page_title="Database Documentation Assistant",
    page_icon="📊",
    layout="wide"  # Use full width of browser
)

# --- MAIN TITLE ---
st.title("📊 Database Documentation Assistant")
st.markdown("**Connected to:** " + DB_CONFIG['database'])
st.divider()  # Horizontal line


# --- FUNCTION: Connect to SQL Server ---
# This function creates a connection to your SQL Server database
@st.cache_resource  # Cache the connection (don't reconnect every time)
def get_database_connection():
    """
    Creates and returns a database connection.
    Uses Windows Authentication as specified in your connection string.
    """
    try:
        # Create connection using pyodbc
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except Exception as e:
        # If connection fails, show error message
        st.error(f"❌ Connection Failed: {str(e)}")
        return None


# --- FUNCTION: Get List of Tables ---
# This queries INFORMATION_SCHEMA to get all tables in the database
def get_tables_list(conn):
    """
    Retrieves all table names from the database.
    Uses INFORMATION_SCHEMA.TABLES (standard SQL metadata view).
    """
    query = """
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    try:
        # Execute query and return results as a pandas DataFrame
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching tables: {str(e)}")
        return None


# --- FUNCTION: Get Column Details for a Table ---
# This gets detailed information about columns in a specific table
def get_table_columns(conn, schema, table_name):
    """
    Retrieves column details for a specific table.
    Shows: column name, data type, if it's nullable, etc.
    """
    query = """
    SELECT 
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE,
        COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """
    
    try:
        # Execute with parameters (? are placeholders)
        df = pd.read_sql(query, conn, params=(schema, table_name))
        return df
    except Exception as e:
        st.error(f"Error fetching columns: {str(e)}")
        return None


# --- MAIN APPLICATION ---
# This is where the app starts running

# Step 1: Try to connect to database
conn = get_database_connection()

if conn:
    # Connection successful!
    st.success("✅ Connected to SQL Server successfully!")
    
    # Step 2: Get list of all tables
    st.subheader("📋 Database Tables")
    
    tables_df = get_tables_list(conn)
    
    if tables_df is not None and not tables_df.empty:
        # Show how many tables were found
        st.info(f"Found **{len(tables_df)}** tables in the database")
        
        # Display the tables in a nice table format
        st.dataframe(
            tables_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Step 3: Let user select a table to see details
        st.subheader("🔍 Table Details")
        
        # Create a dropdown to select a table
        selected_table = st.selectbox(
            "Select a table to view its columns:",
            options=tables_df['TABLE_NAME'].tolist(),
            index=0  # Default to first table
        )
        
        if selected_table:
            # Get the schema for the selected table
            selected_schema = tables_df[
                tables_df['TABLE_NAME'] == selected_table
            ]['TABLE_SCHEMA'].iloc[0]
            
            # Show which table we're viewing
            st.markdown(f"**Viewing:** `{selected_schema}.{selected_table}`")
            
            # Get and display column information
            columns_df = get_table_columns(conn, selected_schema, selected_table)
            
            if columns_df is not None:
                st.dataframe(
                    columns_df,
                    use_container_width=True,
                    hide_index=True
                )
    
    else:
        st.warning("No tables found in the database.")

else:
    # Connection failed
    st.error("Could not connect to the database. Please check your configuration.")
    
    # Show helpful troubleshooting info
    st.info("""
    **Troubleshooting Tips:**
    1. Make sure SQL Server is running
    2. Check that the server name is correct in config.py
    3. Verify you have ODBC Driver 17 installed
    4. Ensure Windows Authentication is working
    """)


# --- SIDEBAR: Configuration Info ---
# Display current configuration in the sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    st.text(f"Server: {DB_CONFIG['server']}")
    st.text(f"Database: {DB_CONFIG['database']}")
    st.text(f"Driver: {DB_CONFIG['driver']}")
    
    st.divider()
    
    st.markdown("### 📝 Next Steps")
    st.markdown("""
    - [x] Basic connection
    - [ ] Add Claude AI integration
    - [ ] Generate table glossary
    - [ ] Create ER diagrams
    """)
