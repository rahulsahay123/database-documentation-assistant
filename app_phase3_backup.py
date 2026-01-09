# app.py - Main Streamlit Application
# Database Documentation Assistant - Phase 3: Agentic AI Chat Interface
# Built on Phase 2 - NEW: Intelligent chat with autonomous tool use

import streamlit as st
import pyodbc
import pandas as pd
import anthropic
import json
from config import CONNECTION_STRING, DB_CONFIG

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Database Documentation Assistant",
    page_icon="📊",
    layout="wide"
)

# ==============================================================================
# DATABASE FUNCTIONS (FROM PHASE 2 - UNCHANGED)
# ==============================================================================

@st.cache_resource
def get_database_connection():
    """Creates and returns a database connection."""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except Exception as e:
        st.error(f"❌ Connection Failed: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def get_tables_list(_conn):
    """Retrieves all table names from the database."""
    query = """
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    AND TABLE_NAME NOT IN ('sysdiagrams','AdventureWorksDWBuildVersion')
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    try:
        df = pd.read_sql(query, _conn)
        return df
    except Exception as e:
        st.error(f"Error fetching tables: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def get_table_columns(_conn, schema, table_name):
    """Retrieves column details for a specific table."""
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
        df = pd.read_sql(query, _conn, params=(schema, table_name))
        return df
    except Exception as e:
        st.error(f"Error fetching columns: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def get_tables_with_columns():
    """Gets all tables with their columns in one query."""
    conn = get_database_connection()
    if not conn:
        return []
    
    query = """
    SELECT 
        t.TABLE_SCHEMA,
        t.TABLE_NAME,
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.IS_NULLABLE,
        c.CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.TABLES t
    INNER JOIN INFORMATION_SCHEMA.COLUMNS c 
        ON t.TABLE_NAME = c.TABLE_NAME 
        AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
    WHERE t.TABLE_TYPE = 'BASE TABLE'
    AND t.TABLE_NAME NOT IN ('sysdiagrams','AdventureWorksDWBuildVersion')
    ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    tables = {}
    for row in cursor.fetchall():
        table_key = f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}"
        if table_key not in tables:
            tables[table_key] = {
                'schema': row.TABLE_SCHEMA,
                'name': row.TABLE_NAME,
                'columns': []
            }
        
        tables[table_key]['columns'].append({
            'name': row.COLUMN_NAME,
            'type': row.DATA_TYPE,
            'nullable': row.IS_NULLABLE,
            'max_length': row.CHARACTER_MAXIMUM_LENGTH
        })
    
    return list(tables.values())


@st.cache_data(ttl=3600)
def get_foreign_keys():
    """Extracts foreign key relationships."""
    conn = get_database_connection()
    if not conn:
        return []
    
    query = """
    SELECT 
        fk.name AS FK_NAME,
        tp.name AS PARENT_TABLE,
        cp.name AS PARENT_COLUMN,
        tr.name AS REFERENCED_TABLE,
        cr.name AS REFERENCED_COLUMN
    FROM sys.foreign_keys fk
    INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
    INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
    INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id 
        AND fkc.parent_column_id = cp.column_id
    INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
    INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id 
        AND fkc.referenced_column_id = cr.column_id
    ORDER BY tp.name, fk.name
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    fks = []
    for row in cursor.fetchall():
        fks.append({
            'parent_table': row.PARENT_TABLE,
            'parent_column': row.PARENT_COLUMN,
            'referenced_table': row.REFERENCED_TABLE,
            'referenced_column': row.REFERENCED_COLUMN
        })
    
    return fks


@st.cache_data(ttl=3600)
def get_stored_procedures():
    """Gets all stored procedures with their SQL code."""
    conn = get_database_connection()
    if not conn:
        return []
    
    query = """
    SELECT 
        p.name AS PROCEDURE_NAME,
        SCHEMA_NAME(p.schema_id) AS SCHEMA_NAME,
        m.definition AS DEFINITION,
        p.create_date,
        p.modify_date
    FROM sys.procedures p
    INNER JOIN sys.sql_modules m ON p.object_id = m.object_id
    WHERE P.NAME LIKE 'usp_%'
    ORDER BY p.name
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    procedures = []
    for row in cursor.fetchall():
        procedures.append({
            'name': row.PROCEDURE_NAME,
            'schema': row.SCHEMA_NAME,
            'definition': row.DEFINITION,
            'created': str(row.create_date),
            'modified': str(row.modify_date)
        })
    
    return procedures


# ==============================================================================
# AI FUNCTIONS (FROM PHASE 2 - UNCHANGED)
# ==============================================================================

def initialize_claude():
    """Initializes Claude AI client."""
    if 'anthropic_api_key' not in st.session_state:
        st.session_state.anthropic_api_key = None
    
    if st.session_state.anthropic_api_key:
        return anthropic.Anthropic(api_key=st.session_state.anthropic_api_key)
    return None


def generate_table_glossary(tables, claude_client):
    """Uses Claude AI to generate business descriptions for tables AND columns."""
    if not claude_client:
        return {}
    
    table_info = []
    for table in tables[:10]:
        columns_list = [f"{col['name']} ({col['type']})" for col in table['columns']]
        table_info.append(f"Table: {table['name']}\nColumns: {', '.join(columns_list)}")
    
    prompt = f"""You are a database analyst. Analyze these database tables and create a comprehensive business glossary.

Tables:
{chr(10).join(table_info)}

For each table, provide:
1. Purpose: What business data does this table store? (2-3 sentences)
2. Key use cases: How is this data typically used?
3. Update frequency: Based on the table name, estimate how often data is added/updated
4. Column descriptions: For EACH column, provide a brief business-friendly description (1 sentence)

Return your response as JSON in this format:
{{
    "TableName": {{
        "purpose": "description here",
        "use_cases": ["use case 1", "use case 2"],
        "update_frequency": "daily/weekly/monthly/etc",
        "columns": {{
            "ColumnName1": "what this column represents",
            "ColumnName2": "what this column represents"
        }}
    }}
}}
"""
    
    try:
        with st.spinner("🤖 Claude is analyzing tables and columns..."):
            message = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            glossary = json.loads(response_text.strip())
            return glossary
    
    except Exception as e:
        st.error(f"Error generating glossary: {str(e)}")
        return {}


def generate_mermaid_erd(tables, foreign_keys):
    """Generates Mermaid diagram code for ER diagram."""
    mermaid_lines = ["erDiagram"]
    
    added_tables = set()
    for table in tables:
        table_name = table['name'].replace(' ', '_').replace('-', '_')
        added_tables.add(table_name)
        
        mermaid_lines.append(f"    {table_name} {{")
        
        for col in table['columns'][:5]:
            col_name = col['name'].replace(' ', '_').replace('-', '_')
            col_type = col['type']
            mermaid_lines.append(f"        {col_type} {col_name}")
        
        mermaid_lines.append("    }")
    
    for fk in foreign_keys:
        parent = fk['parent_table'].replace(' ', '_').replace('-', '_')
        referenced = fk['referenced_table'].replace(' ', '_').replace('-', '_')
        
        if parent in added_tables and referenced in added_tables:
            mermaid_lines.append(f"    {referenced} ||--o{{ {parent} : references")
    
    return "\n".join(mermaid_lines)


def analyze_stored_procedure(sp_name, sp_definition, claude_client):
    """Uses Claude AI to analyze a stored procedure."""
    if not claude_client:
        return {}
    
    sp_definition_short = sp_definition[:2000]
    
    prompt = f"""Analyze this SQL Server stored procedure and provide:

1. Purpose: What does this procedure do? (2 sentences)
2. Inputs: What parameters does it accept?
3. Outputs: What does it return or modify?
4. Key operations: What are the main SQL operations?

Stored Procedure Name: {sp_name}

Code:
{sp_definition_short}

Return as JSON:
{{
    "purpose": "...",
    "inputs": ["param1", "param2"],
    "outputs": "...",
    "operations": ["operation1", "operation2"]
}}
"""
    
    try:
        with st.spinner("🤖 Claude is analyzing the procedure..."):
            message = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            analysis = json.loads(response_text.strip())
            return analysis
    
    except Exception as e:
        st.error(f"Error analyzing procedure: {str(e)}")
        return {}


def explain_procedure_technically(sp_name, sp_definition, claude_client):
    """Provides point-by-point technical explanation of stored procedure."""
    if not claude_client:
        return {}
    
    prompt = f"""You are a SQL expert. Analyze this stored procedure and explain it TECHNICALLY, point by point, from top to bottom.

Stored Procedure: {sp_name}

SQL Code:
{sp_definition}

Provide a CLEAR, TECHNICAL explanation as a numbered list. For each logical section of code:
- What SQL operation is happening
- What tables/columns are involved
- What the WHERE/JOIN conditions do
- What data transformations occur
- Expected result at that step

Go through the ENTIRE procedure sequentially. Be concise but technical.

Return as JSON:
{{
    "explanation_steps": [
        {{
            "step_number": 1,
            "code_section": "brief code snippet or description",
            "technical_explanation": "what this code does technically"
        }},
        {{
            "step_number": 2,
            "code_section": "...",
            "technical_explanation": "..."
        }}
    ]
}}

Cover the entire procedure from start to finish.
"""
    
    try:
        with st.spinner("📋 Generating technical explanation..."):
            message = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=6000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            explanation = json.loads(response_text.strip())
            return explanation
    
    except Exception as e:
        st.error(f"Error generating explanation: {str(e)}")
        return {}


def profile_column_data(conn, schema, table_name, column_name, data_type):
    """Performs exploratory data analysis on a specific column."""
    try:
        full_table = f"{schema}.{table_name}"
        
        base_query = f"""
        SELECT 
            COUNT(*) as total_count,
            COUNT([{column_name}]) as non_null_count,
            COUNT(*) - COUNT([{column_name}]) as null_count
        FROM {full_table}
        """
        
        cursor = conn.cursor()
        cursor.execute(base_query)
        row = cursor.fetchone()
        
        profile = {
            'total_count': row.total_count,
            'non_null_count': row.non_null_count,
            'null_count': row.null_count,
            'null_percentage': round((row.null_count / row.total_count * 100) if row.total_count > 0 else 0, 2)
        }
        
        if data_type in ['int', 'bigint', 'smallint', 'tinyint', 'decimal', 'numeric', 'float', 'real', 'money']:
            stats_query = f"""
            SELECT 
                MIN([{column_name}]) as min_val,
                MAX([{column_name}]) as max_val,
                AVG(CAST([{column_name}] AS FLOAT)) as avg_val,
                STDEV(CAST([{column_name}] AS FLOAT)) as std_dev
            FROM {full_table}
            WHERE [{column_name}] IS NOT NULL
            """
            cursor.execute(stats_query)
            row = cursor.fetchone()
            
            profile.update({
                'min': row.min_val,
                'max': row.max_val,
                'mean': round(row.avg_val, 2) if row.avg_val else None,
                'std_dev': round(row.std_dev, 2) if row.std_dev else None
            })
            
            dist_query = f"""
            SELECT TOP 1000 [{column_name}] as value
            FROM {full_table}
            WHERE [{column_name}] IS NOT NULL
            ORDER BY NEWID()
            """
            df = pd.read_sql(dist_query, conn)
            profile['distribution_data'] = df['value'].tolist() if not df.empty else []
            
        elif data_type in ['varchar', 'nvarchar', 'char', 'nchar', 'text', 'ntext']:
            distinct_query = f"""
            SELECT 
                COUNT(DISTINCT [{column_name}]) as distinct_count
            FROM {full_table}
            WHERE [{column_name}] IS NOT NULL
            """
            cursor.execute(distinct_query)
            row = cursor.fetchone()
            profile['distinct_count'] = row.distinct_count
            
            top_values_query = f"""
            SELECT TOP 10 
                [{column_name}] as value,
                COUNT(*) as frequency
            FROM {full_table}
            WHERE [{column_name}] IS NOT NULL
            GROUP BY [{column_name}]
            ORDER BY COUNT(*) DESC
            """
            df = pd.read_sql(top_values_query, conn)
            profile['top_values'] = df.to_dict('records') if not df.empty else []
            
        elif data_type in ['date', 'datetime', 'datetime2', 'smalldatetime']:
            date_query = f"""
            SELECT 
                MIN([{column_name}]) as min_date,
                MAX([{column_name}]) as max_date
            FROM {full_table}
            WHERE [{column_name}] IS NOT NULL
            """
            cursor.execute(date_query)
            row = cursor.fetchone()
            
            profile.update({
                'min_date': str(row.min_date) if row.min_date else None,
                'max_date': str(row.max_date) if row.max_date else None
            })
        
        return profile
    
    except Exception as e:
        st.error(f"Error profiling column: {str(e)}")
        return None


# ==============================================================================
# NEW PHASE 3: AGENTIC CHAT - TOOL DEFINITIONS
# ==============================================================================

# These are the "tools" that Claude can autonomously choose to use
# Each tool has a name, description, and input schema (parameters)

TOOLS = [
    {
        "name": "list_all_tables",
        "description": "Returns a list of all tables in the database with their schemas. Use this when the user asks about what tables exist, wants an overview of the database structure, or asks about specific table names.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_table_details",
        "description": "Gets detailed information about a specific table including all its columns, data types, and nullability. Use this when the user asks about a specific table's structure, columns, or schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table (e.g., 'DimCustomer', 'FactInternetSales')"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "search_tables_by_keyword",
        "description": "Searches for tables whose names contain a specific keyword. Use this when the user asks about tables related to a concept (e.g., 'customer tables', 'sales tables', 'product tables').",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The keyword to search for in table names (e.g., 'Customer', 'Sales', 'Product')"
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "get_relationships",
        "description": "Gets foreign key relationships for the database or a specific table. Use this when the user asks about how tables are related, what references what, or table relationships.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Optional: specific table to get relationships for. If not provided, returns all relationships."
                }
            },
            "required": []
        }
    },
    {
        "name": "list_stored_procedures",
        "description": "Returns a list of all stored procedures in the database. Use this when the user asks about stored procedures, what procedures exist, or wants an overview of database logic.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_procedure_details",
        "description": "Gets the SQL code and metadata for a specific stored procedure. Use this when the user asks about what a specific procedure does or wants to see its code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_name": {
                    "type": "string",
                    "description": "The name of the stored procedure (e.g., 'usp_GetCustomerOrders')"
                }
            },
            "required": ["procedure_name"]
        }
    }
]


# ==============================================================================
# NEW PHASE 3: TOOL EXECUTION FUNCTIONS
# ==============================================================================

def execute_tool(tool_name, tool_input):
    """
    Executes a tool based on its name and returns the result.
    This is called by the agentic loop when Claude decides to use a tool.
    """
    
    try:
        # Tool 1: List all tables
        if tool_name == "list_all_tables":
            conn = get_database_connection()
            if not conn:
                return {"error": "Database connection failed"}
            
            tables_df = get_tables_list(conn)
            if tables_df is None or tables_df.empty:
                return {"tables": [], "count": 0}
            
            # Convert to a simple list
            tables_list = []
            for _, row in tables_df.iterrows():
                tables_list.append({
                    "schema": row['TABLE_SCHEMA'],
                    "name": row['TABLE_NAME']
                })
            
            return {
                "tables": tables_list,
                "count": len(tables_list)
            }
        
        # Tool 2: Get table details
        elif tool_name == "get_table_details":
            table_name = tool_input.get("table_name")
            
            conn = get_database_connection()
            if not conn:
                return {"error": "Database connection failed"}
            
            # Find the table's schema
            tables_df = get_tables_list(conn)
            table_row = tables_df[tables_df['TABLE_NAME'].str.lower() == table_name.lower()]
            
            if table_row.empty:
                return {"error": f"Table '{table_name}' not found"}
            
            schema = table_row.iloc[0]['TABLE_SCHEMA']
            
            # Get column details
            columns_df = get_table_columns(conn, schema, table_name)
            
            if columns_df is None or columns_df.empty:
                return {"error": f"No columns found for table '{table_name}'"}
            
            columns_list = []
            for _, row in columns_df.iterrows():
                col_info = {
                    "name": row['COLUMN_NAME'],
                    "data_type": row['DATA_TYPE'],
                    "nullable": row['IS_NULLABLE']
                }
                if pd.notna(row['CHARACTER_MAXIMUM_LENGTH']):
                    col_info["max_length"] = int(row['CHARACTER_MAXIMUM_LENGTH'])
                columns_list.append(col_info)
            
            return {
                "schema": schema,
                "table_name": table_name,
                "columns": columns_list,
                "column_count": len(columns_list)
            }
        
        # Tool 3: Search tables by keyword
        elif tool_name == "search_tables_by_keyword":
            keyword = tool_input.get("keyword", "").lower()
            
            conn = get_database_connection()
            if not conn:
                return {"error": "Database connection failed"}
            
            tables_df = get_tables_list(conn)
            
            # Filter tables containing the keyword
            matching_tables = tables_df[
                tables_df['TABLE_NAME'].str.lower().str.contains(keyword)
            ]
            
            results = []
            for _, row in matching_tables.iterrows():
                results.append({
                    "schema": row['TABLE_SCHEMA'],
                    "name": row['TABLE_NAME']
                })
            
            return {
                "keyword": keyword,
                "matching_tables": results,
                "count": len(results)
            }
        
        # Tool 4: Get relationships
        elif tool_name == "get_relationships":
            table_name = tool_input.get("table_name", "").lower()
            
            fks = get_foreign_keys()
            
            if table_name:
                # Filter for specific table
                filtered_fks = [
                    fk for fk in fks 
                    if fk['parent_table'].lower() == table_name or 
                       fk['referenced_table'].lower() == table_name
                ]
                return {
                    "table": table_name,
                    "relationships": filtered_fks,
                    "count": len(filtered_fks)
                }
            else:
                # Return all relationships
                return {
                    "relationships": fks,
                    "count": len(fks)
                }
        
        # Tool 5: List stored procedures
        elif tool_name == "list_stored_procedures":
            procedures = get_stored_procedures()
            
            proc_list = []
            for proc in procedures:
                proc_list.append({
                    "schema": proc['schema'],
                    "name": proc['name'],
                    "created": proc['created'],
                    "modified": proc['modified']
                })
            
            return {
                "procedures": proc_list,
                "count": len(proc_list)
            }
        
        # Tool 6: Get procedure details
        elif tool_name == "get_procedure_details":
            proc_name = tool_input.get("procedure_name")
            
            procedures = get_stored_procedures()
            
            # Find the procedure
            proc = next(
                (p for p in procedures if p['name'].lower() == proc_name.lower()),
                None
            )
            
            if not proc:
                return {"error": f"Procedure '{proc_name}' not found"}
            
            return {
                "name": proc['name'],
                "schema": proc['schema'],
                "definition": proc['definition'][:1000],  # Limit to first 1000 chars
                "created": proc['created'],
                "modified": proc['modified']
            }
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}


# ==============================================================================
# NEW PHASE 3: AGENTIC CHAT LOOP
# ==============================================================================

def process_agentic_chat(user_message, claude_client):
    """
    Main agentic loop. Claude decides which tools to use and orchestrates them.
    
    How it works:
    1. Send user message + available tools to Claude
    2. Claude responds with either:
       - tool_use (wants to call a tool)
       - text (final answer)
    3. If tool_use, execute the tool and send results back to Claude
    4. Repeat until Claude gives a final text response
    """
    
    if not claude_client:
        return "⚠️ Please enter your API key in the sidebar first!"
    
    # Initialize conversation history for this request
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    # System prompt that tells Claude about the database
    system_prompt = f"""You are a helpful database documentation assistant for the {DB_CONFIG['database']} database.

You have access to tools that let you query database metadata. Use these tools to answer the user's questions accurately.

When answering:
- Be concise and helpful
- Use tools when you need information
- Explain technical concepts in simple terms
- If you find multiple relevant items, summarize them clearly

The database is: {DB_CONFIG['database']} on server {DB_CONFIG['server']}
"""
    
    # Maximum iterations to prevent infinite loops
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            # Call Claude with current messages and available tools
            response = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )
            
            # Check what Claude wants to do
            if response.stop_reason == "tool_use":
                # Claude wants to use a tool!
                # Extract all tool uses from the response
                tool_uses = [block for block in response.content if block.type == "tool_use"]
                
                # Also get any text Claude included
                text_blocks = [block.text for block in response.content if hasattr(block, "text")]
                
                # Add Claude's response to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute each tool and collect results
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    
                    # Show user what tool is being used (in UI)
                    st.caption(f"🔧 Using tool: {tool_name}")
                    
                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    
                    # Add result to tool_results
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result)
                    })
                
                # Send tool results back to Claude
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue loop - Claude will process results
                
            elif response.stop_reason == "end_turn":
                # Claude is done! Extract the final text response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                
                return final_text
            
            else:
                # Unexpected stop reason
                return f"Unexpected response from Claude: {response.stop_reason}"
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    return "⚠️ Maximum iterations reached. Please try a simpler question."


# ==============================================================================
# MAIN APPLICATION UI
# ==============================================================================

def main():
    # Title
    st.title("📊 Database Documentation Assistant")
    st.markdown("**Phase 3: Agentic AI Chat** | Connected to: " + DB_CONFIG['database'])
    st.divider()
    
    # ===========================================================================
    # SIDEBAR - Configuration & API Key
    # ===========================================================================
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key Input
        st.subheader("🔑 Claude API Key")
        api_key_input = st.text_input(
            "Enter your Anthropic API key",
            type="password",
            value=st.session_state.get('anthropic_api_key', '') or '',
            help="Get your key from https://console.anthropic.com/"
        )
        
        if api_key_input:
            st.session_state.anthropic_api_key = api_key_input
            st.success("✅ API Key saved!")
        else:
            st.warning("⚠️ Enter API key to use AI features")
        
        st.divider()
        
        # Database info
        st.text(f"Server: {DB_CONFIG['server']}")
        st.text(f"Database: {DB_CONFIG['database']}")
        st.text(f"Driver: {DB_CONFIG['driver']}")
        
        # Test connection button
        if st.button("🔌 Test Database Connection"):
            conn = get_database_connection()
            if conn:
                st.success("✅ Connected!")
            else:
                st.error("❌ Connection failed")
        
        st.divider()
        
        st.markdown("### 📋 Progress")
        st.markdown("""
        - [x] Phase 1: Basic Setup
        - [x] Phase 2: AI Integration
        - [x] Phase 3: Agentic Chat ✨
        """)
        
        st.divider()
        
        # NEW: Available Tools Info
        st.markdown("### 🛠️ Available Tools")
        st.caption("Claude can use these autonomously:")
        st.markdown("""
        - List all tables
        - Get table details
        - Search tables
        - Get relationships
        - List procedures
        - Get procedure details
        """)
    
    # ===========================================================================
    # MAIN CONTENT - TABS
    # ===========================================================================
    
    # Initialize Claude client
    claude_client = initialize_claude()
    
    # Create tabs - NEW: Added Chat tab as first tab
    tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💬 AI Chat",  # NEW!
        "🏠 Overview",
        "📚 Table Glossary (AI)",
        "🔗 ER Diagram",
        "📋 Table Details",
        "⚙️ Stored Procedures (AI)",
        "📊 Data Profiling"
    ])
    
    # ============================================================================
    # TAB 0: AGENTIC AI CHAT (NEW!)
    # ============================================================================
    with tab0:
        st.header("💬 AI Database Assistant")
        st.markdown("Ask questions about your database in natural language. Claude will autonomously use tools to find answers.")
        
        # Show example questions
        with st.expander("💡 Example Questions"):
            st.markdown("""
            - "What tables are in this database?"
            - "Tell me about the DimCustomer table"
            - "What tables are related to sales?"
            - "Show me all tables with 'Product' in the name"
            - "What stored procedures exist?"
            - "How is DimCustomer related to other tables?"
            - "What columns does FactInternetSales have?"
            """)
        
        st.divider()
        
        # Initialize chat history in session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Chat input
        user_question = st.chat_input("Ask me anything about the database...")
        
        # Process new question
        if user_question:
            if not claude_client:
                st.error("⚠️ Please enter your API key in the sidebar first!")
            else:
                # Add user message to history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_question
                })
                
                # Get AI response (with tool use)
                with st.spinner("🤖 Claude is thinking and using tools..."):
                    ai_response = process_agentic_chat(user_question, claude_client)
                
                # Add AI response to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": ai_response
                })
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
        
        # Clear chat button
        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()
    
    # ============================================================================
    # TAB 1: OVERVIEW (from Phase 2)
    # ============================================================================
    with tab1:
        st.header("Database Overview")
        
        conn = get_database_connection()
        
        if conn:
            st.success("✅ Connected to SQL Server successfully!")
            
            tables_df = get_tables_list(conn)
            
            if tables_df is not None and not tables_df.empty:
                st.info(f"Found **{len(tables_df)}** tables in the database")
                
                st.dataframe(
                    tables_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No tables found in the database.")
        else:
            st.error("Could not connect to the database.")
            st.info("""
            **Troubleshooting:**
            1. Make sure SQL Server is running
            2. Check config.py settings
            3. Verify ODBC Driver 17 is installed
            """)
    
    # ============================================================================
    # TAB 2: TABLE GLOSSARY (from Phase 2)
    # ============================================================================
    with tab2:
        st.header("📚 Table Glossary - AI Generated")
        st.markdown("Claude AI creates business-friendly descriptions of tables AND columns")
        
        if st.button("🤖 Generate Glossary with Claude AI", key="gen_glossary"):
            if not claude_client:
                st.error("⚠️ Please enter your API key in the sidebar first!")
            else:
                tables = get_tables_with_columns()
                if tables:
                    glossary = generate_table_glossary(tables, claude_client)
                    
                    if glossary:
                        st.session_state.glossary = glossary
                        st.success(f"✅ Generated glossary for {len(glossary)} tables!")
        
        if 'glossary' in st.session_state:
            st.divider()
            for table_name, details in st.session_state.glossary.items():
                with st.expander(f"📄 {table_name}", expanded=False):
                    st.markdown(f"**Purpose:**")
                    st.write(details.get('purpose', 'N/A'))
                    
                    st.markdown(f"**Key Use Cases:**")
                    for uc in details.get('use_cases', []):
                        st.write(f"• {uc}")
                    
                    st.markdown(f"**Update Frequency:** {details.get('update_frequency', 'Unknown')}")
                    
                    if 'columns' in details and details['columns']:
                        st.markdown("---")
                        st.markdown("**📊 Column Descriptions:**")
                        
                        col_data = []
                        for col_name, col_desc in details['columns'].items():
                            col_data.append({'Column': col_name, 'Description': col_desc})
                        
                        if col_data:
                            col_df = pd.DataFrame(col_data)
                            st.dataframe(col_df, use_container_width=True, hide_index=True)
    
    # ============================================================================
    # TAB 3: ER DIAGRAM (from Phase 2)
    # ============================================================================
    with tab3:
        st.header("🔗 Entity Relationship Diagram")
        st.markdown("Visual representation of table relationships")
        
        if st.button("📊 Generate ER Diagram", key="gen_erd"):
            with st.spinner("Creating diagram..."):
                tables = get_tables_with_columns()
                fks = get_foreign_keys()
                
                mermaid_code = generate_mermaid_erd(tables, fks)
                st.session_state.erd_code = mermaid_code
                st.success("✅ Diagram generated!")
        
        if 'erd_code' in st.session_state:
            st.divider()
            
            try:
                from streamlit_mermaid import st_mermaid
                
                st.subheader("📊 ER Diagram Preview")
                st_mermaid(st.session_state.erd_code)
                
                st.divider()
                
                st.markdown("### 🔍 Need Zoom/Pan Controls?")
                
                import urllib.parse
                mermaid_json = {
                    "code": st.session_state.erd_code,
                    "mermaid": {"theme": "default"}
                }
                encoded = urllib.parse.quote(str(mermaid_json))
                mermaid_url = f"https://mermaid.live/edit#base64:{encoded}"
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.link_button("🚀 Open in Mermaid.live (Full Zoom)", mermaid_url, use_container_width=True)
                with col2:
                    st.caption("Opens in new tab with pan, zoom, export, and editing features")
                
                st.divider()
                
                with st.expander("📄 View/Copy Mermaid Code"):
                    st.code(st.session_state.erd_code, language="mermaid")
                    st.info("💡 Copy this code to use in documentation or other tools")
                    
            except ImportError:
                st.warning("⚠️ streamlit-mermaid not installed. Showing code only.")
                st.code(st.session_state.erd_code, language="mermaid")
                st.info("""
                **To visualize:**
                1. Copy the code above
                2. Go to https://mermaid.live
                3. Paste and view your diagram with full zoom/pan controls
                """)
            except Exception as e:
                st.error(f"Error rendering diagram: {str(e)}")
                st.info("Showing code instead:")
                st.code(st.session_state.erd_code, language="mermaid")
    
    # Tabs 4-6 remain the same as Phase 2
    # (Table Details, Stored Procedures, Data Profiling)
    # Including them for completeness...
    
    with tab4:
        st.header("📋 Detailed Table Documentation")
        
        conn = get_database_connection()
        if conn:
            tables_df = get_tables_list(conn)
            
            if tables_df is not None and not tables_df.empty:
                table_names = [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" 
                              for _, row in tables_df.iterrows()]
                
                selected_table = st.selectbox(
                    "Select a table to view details:",
                    options=table_names
                )
                
                if selected_table:
                    schema, table_name = selected_table.split('.')
                    
                    st.subheader(f"📊 {selected_table}")
                    
                    columns_df = get_table_columns(conn, schema, table_name)
                    
                    if columns_df is not None:
                        st.dataframe(
                            columns_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        if st.button("📈 Get Row Count", key="row_count"):
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                            count = cursor.fetchone()[0]
                            st.metric("Total Rows", f"{count:,}")
    
    with tab5:
        st.header("⚙️ Stored Procedure Documentation")
        st.markdown("AI-powered analysis of stored procedures")
        
        procedures = get_stored_procedures()
        
        if procedures:
            st.info(f"Found **{len(procedures)}** stored procedures")
            
            sp_names = [f"{sp['schema']}.{sp['name']}" for sp in procedures]
            selected_sp = st.selectbox("Select a stored procedure:", sp_names)
            
            selected_sp_data = next(
                (sp for sp in procedures if f"{sp['schema']}.{sp['name']}" == selected_sp),
                None
            )
            
            if selected_sp_data:
                st.subheader(f"⚙️ {selected_sp}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"Created: {selected_sp_data['created']}")
                with col2:
                    st.caption(f"Modified: {selected_sp_data['modified']}")
                
                with st.expander("📄 View SQL Code"):
                    st.code(selected_sp_data['definition'], language="sql")
                
                if st.button("🤖 Analyze with Claude AI", key="analyze_sp"):
                    if not claude_client:
                        st.error("⚠️ Please enter your API key in the sidebar first!")
                    else:
                        analysis = analyze_stored_procedure(
                            selected_sp_data['name'],
                            selected_sp_data['definition'],
                            claude_client
                        )
                        
                        if analysis:
                            st.session_state.sp_analysis = analysis
                            st.session_state.sp_analysis_name = selected_sp
                
                if 'sp_analysis' in st.session_state and st.session_state.get('sp_analysis_name') == selected_sp:
                    st.divider()
                    st.markdown("### 📖 Business Analysis")
                    
                    analysis = st.session_state.sp_analysis
                    
                    st.markdown(f"**Purpose:**")
                    st.write(analysis.get('purpose', 'N/A'))
                    
                    st.markdown(f"**Input Parameters:**")
                    for inp in analysis.get('inputs', []):
                        st.write(f"• {inp}")
                    
                    st.markdown(f"**Outputs:**")
                    st.write(analysis.get('outputs', 'N/A'))
                    
                    st.markdown(f"**Key Operations:**")
                    for op in analysis.get('operations', []):
                        st.write(f"• {op}")
                
                st.divider()
                
                if st.button("📋 Technical Explanation (Step-by-Step)", key="tech_explain_sp"):
                    if not claude_client:
                        st.error("⚠️ Please enter your API key in the sidebar first!")
                    else:
                        explanation = explain_procedure_technically(
                            selected_sp_data['name'],
                            selected_sp_data['definition'],
                            claude_client
                        )
                        
                        if explanation:
                            st.session_state.sp_explanation = explanation
                            st.session_state.sp_explanation_name = selected_sp
                
                if 'sp_explanation' in st.session_state and st.session_state.get('sp_explanation_name') == selected_sp:
                    st.divider()
                    st.markdown("### 📋 Technical Explanation (Top to Bottom)")
                    
                    explanation = st.session_state.sp_explanation
                    
                    if explanation.get('explanation_steps'):
                        for step in explanation['explanation_steps']:
                            step_num = step.get('step_number', '?')
                            code_section = step.get('code_section', 'Code section')
                            tech_explain = step.get('technical_explanation', 'No explanation')
                            
                            st.markdown(f"**Step {step_num}:** `{code_section}`")
                            st.write(f"→ {tech_explain}")
                            st.markdown("")
                    else:
                        st.info("No explanation steps found")
        else:
            st.info("No stored procedures found in this database")
    
    with tab6:
        st.header("📊 Data Profiling & Exploratory Analysis")
        st.markdown("Analyze column statistics and distributions")
        
        conn = get_database_connection()
        if conn:
            tables_df = get_tables_list(conn)
            
            if tables_df is not None and not tables_df.empty:
                table_names = [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" 
                              for _, row in tables_df.iterrows()]
                
                selected_table = st.selectbox(
                    "Select a table to profile:",
                    options=table_names,
                    key="profile_table_select"
                )
                
                if selected_table:
                    schema, table_name = selected_table.split('.')
                    
                    columns_df = get_table_columns(conn, schema, table_name)
                    
                    if columns_df is not None and not columns_df.empty:
                        selected_column = st.selectbox(
                            "Select a column to analyze:",
                            options=columns_df['COLUMN_NAME'].tolist(),
                            key="profile_column_select"
                        )
                        
                        if selected_column:
                            col_info = columns_df[columns_df['COLUMN_NAME'] == selected_column].iloc[0]
                            data_type = col_info['DATA_TYPE']
                            
                            st.subheader(f"📈 Profile: {selected_column}")
                            st.caption(f"Type: {data_type} | Nullable: {col_info['IS_NULLABLE']}")
                            
                            if st.button("🔍 Analyze Column", key="analyze_column_btn"):
                                with st.spinner(f"Analyzing {selected_column}..."):
                                    profile = profile_column_data(
                                        conn, schema, table_name, selected_column, data_type
                                    )
                                    
                                    if profile:
                                        st.session_state.column_profile = profile
                                        st.session_state.profile_column_name = selected_column
                                        st.session_state.profile_data_type = data_type
                            
                            if 'column_profile' in st.session_state and \
                               st.session_state.get('profile_column_name') == selected_column:
                                
                                profile = st.session_state.column_profile
                                
                                st.markdown("### 📊 Basic Statistics")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Total Rows", f"{profile['total_count']:,}")
                                with col2:
                                    st.metric("Non-Null", f"{profile['non_null_count']:,}")
                                with col3:
                                    st.metric("Null Count", f"{profile['null_count']:,}")
                                with col4:
                                    st.metric("Null %", f"{profile['null_percentage']}%")
                                
                                st.divider()
                                
                                if data_type in ['int', 'bigint', 'smallint', 'tinyint', 'decimal', 
                                               'numeric', 'float', 'real', 'money']:
                                    st.markdown("### 🔢 Numeric Analysis")
                                    
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Min", f"{profile.get('min', 'N/A'):,}" if profile.get('min') is not None else "N/A")
                                    with col2:
                                        st.metric("Max", f"{profile.get('max', 'N/A'):,}" if profile.get('max') is not None else "N/A")
                                    with col3:
                                        st.metric("Mean", f"{profile.get('mean', 'N/A')}" if profile.get('mean') else "N/A")
                                    with col4:
                                        st.metric("Std Dev", f"{profile.get('std_dev', 'N/A')}" if profile.get('std_dev') else "N/A")
                                    
                                    if profile.get('distribution_data'):
                                        st.markdown("### 📊 Distribution")
                                        try:
                                            import plotly.express as px
                                            
                                            fig = px.histogram(
                                                x=profile['distribution_data'],
                                                nbins=30,
                                                labels={'x': selected_column, 'y': 'Frequency'},
                                                title=f"Distribution of {selected_column}"
                                            )
                                            fig.update_layout(showlegend=False)
                                            st.plotly_chart(fig, use_container_width=True)
                                        except ImportError:
                                            st.info("Install plotly for visualizations: pip install plotly")
                                
                                elif data_type in ['varchar', 'nvarchar', 'char', 'nchar', 'text', 'ntext']:
                                    st.markdown("### 🔤 Text Analysis")
                                    
                                    st.metric("Distinct Values", f"{profile.get('distinct_count', 'N/A'):,}")
                                    
                                    if profile.get('top_values'):
                                        st.markdown("### 📊 Top 10 Most Common Values")
                                        
                                        try:
                                            import plotly.express as px
                                            
                                            top_df = pd.DataFrame(profile['top_values'])
                                            
                                            fig = px.bar(
                                                top_df,
                                                x='frequency',
                                                y='value',
                                                orientation='h',
                                                labels={'value': selected_column, 'frequency': 'Count'},
                                                title=f"Top Values in {selected_column}"
                                            )
                                            st.plotly_chart(fig, use_container_width=True)
                                            
                                            st.dataframe(top_df, use_container_width=True, hide_index=True)
                                            
                                        except ImportError:
                                            top_df = pd.DataFrame(profile['top_values'])
                                            st.dataframe(top_df, use_container_width=True, hide_index=True)
                                
                                elif data_type in ['date', 'datetime', 'datetime2', 'smalldatetime']:
                                    st.markdown("### 📅 Date Analysis")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Earliest Date", profile.get('min_date', 'N/A'))
                                    with col2:
                                        st.metric("Latest Date", profile.get('max_date', 'N/A'))
                                    
                                    if profile.get('min_date') and profile.get('max_date'):
                                        from datetime import datetime
                                        try:
                                            min_dt = datetime.fromisoformat(profile['min_date'].replace('Z', '+00:00'))
                                            max_dt = datetime.fromisoformat(profile['max_date'].replace('Z', '+00:00'))
                                            date_range = (max_dt - min_dt).days
                                            st.metric("Date Range (days)", f"{date_range:,}")
                                        except:
                                            pass
            else:
                st.warning("No tables found")
        else:
            st.error("Database connection required")


# ==============================================================================
# RUN THE APP
# ==============================================================================
if __name__ == "__main__":
    main()
