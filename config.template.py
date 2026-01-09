# config.template.py - Template Configuration File
# Copy this to config.py and fill in your actual values

# SQL Server Connection Settings
DB_CONFIG = {
    'server': r'YOUR_SERVER\SQLEXPRESS',
    'database': 'YOUR_DATABASE',
    'driver': '{ODBC Driver 17 for SQL Server}'
}

# Connection String
CONNECTION_STRING = (
    f"DRIVER={DB_CONFIG['driver']};"
    f"SERVER={DB_CONFIG['server']};"
    f"DATABASE={DB_CONFIG['database']};"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

# Claude API Configuration
CLAUDE_API_KEY = ""