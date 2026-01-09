# Database Documentation Assistant

   ![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
   ![Streamlit](https://img.shields.io/badge/streamlit-1.40.0-red.svg)
   ![Claude](https://img.shields.io/badge/AI-Claude%20Sonnet%204-orange.svg)
   [![Wiki](https://img.shields.io/badge/docs-wiki-green.svg)](https://github.com/rahulsahay123/database-documentation-assistant/wiki)
   [![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)
   ![Status](https://img.shields.io/badge/status-active-success.svg)

   AI-powered database documentation tool using Streamlit and Claude AI. Built in 3 phases to demonstrate progressive learning from basic database connections to agentic AI.

AI-powered database documentation tool using Streamlit and Claude AI. Built in 3 phases to demonstrate progressive learning from basic database connections to agentic AI capabilities.

## Features

- 🤖 **Agentic AI Chat**: Ask questions about your database in natural language - Claude autonomously uses tools to find answers
- 📚 **Table Glossary**: AI-generated business descriptions for tables and columns
- 🔗 **ER Diagrams**: Visual representation of table relationships using Mermaid
- ⚙️ **Stored Procedure Analysis**: Automated documentation and technical explanations of SQL procedures
- 📊 **Data Profiling**: Exploratory data analysis with statistics and visualizations

## Tech Stack

- **Frontend**: Streamlit
- **Database**: SQL Server (via pyodbc)
- **AI**: Claude Sonnet 4 (Anthropic API)
- **Visualization**: Mermaid diagrams, Plotly charts
- **Architecture**: Agentic AI with tool use/function calling

## Project Phases

This project was built incrementally across 3 learning phases:

- **Phase 1**: Basic Streamlit + SQL Server connection with metadata extraction
- **Phase 2**: Claude AI integration for documentation generation and analysis
- **Phase 3**: Agentic AI chat interface with autonomous tool orchestration

## Setup Instructions

1. **Clone the repository**
```bash
   git clone https://github.com/rahulsahay123/database-documentation-assistant.git
   cd database-documentation-assistant
```

2. **Install dependencies**
```bash
   pip install -r requirements.txt
```

3. **Configure database connection**
```bash
   copy config.template.py config.py
```
   Edit `config.py` with your:
   - SQL Server connection details
   - Anthropic API key (get from https://console.anthropic.com/)

4. **Run the application**
```bash
   streamlit run app.py
```

## Project Structure
```
├── app.py                    # Main Streamlit application (Phase 3 - Agentic)
├── app_phase1_backup.py      # Phase 1: Basic database connection
├── app_phase2_backup.py      # Phase 2: AI integration
├── app_phase3_backup.py      # Phase 3: Agentic chat interface
├── config.py                 # Database & API configuration (gitignored)
├── config.template.py        # Configuration template
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
└── README.md                # Project documentation
```

## How It Works

### Agentic AI Architecture

The Phase 3 implementation uses Claude's tool use capability to create an autonomous agent:

1. **User asks a question** in natural language
2. **Claude analyzes** the question and decides which tools to use
3. **Tools execute** database queries automatically
4. **Claude synthesizes** results into a helpful answer
5. **Multi-step reasoning** allows complex workflows

### Available Tools (Claude's Capabilities)

- `list_all_tables` - Get all database tables
- `get_table_details` - Retrieve column information
- `search_tables_by_keyword` - Find tables by name patterns
- `get_relationships` - Extract foreign key relationships
- `list_stored_procedures` - List all stored procedures
- `get_procedure_details` - Get SP code and metadata

## Features by Tab

### 1. AI Chat (Phase 3)
- Natural language interface to your database
- Claude autonomously orchestrates tools
- Examples: "What tables exist?", "Show me customer tables", "How are tables related?"

### 2. Overview
- Connection status
- Complete table listing

### 3. Table Glossary (AI)
- AI-generated business descriptions
- Column-level documentation
- Use cases and update frequency

### 4. ER Diagram
- Visual schema representation
- Mermaid diagram generation
- Export to mermaid.live for advanced features

### 5. Table Details
- Column metadata (types, nullability)
- Row counts
- Schema exploration

### 6. Stored Procedures (AI)
- Business purpose analysis
- Technical step-by-step explanations
- Input/output documentation

### 7. Data Profiling
- Statistical analysis per column
- Distribution histograms (numeric)
- Top values (categorical)
- Date range analysis

## Requirements

- Python 3.8+
- SQL Server with ODBC Driver 17
- Anthropic API key
- Windows Authentication for SQL Server (or modify connection string)

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Go to https://share.streamlit.io/
3. Deploy from your repository
4. Add secrets in Streamlit Cloud settings:
```toml
   [database]
   server = "your_server"
   database = "your_database"
   
   [api]
   CLAUDE_API_KEY = "your_api_key"
```

## Learning Path

This project demonstrates a beginner-friendly progression:

1. **Start simple**: Connect to database, display tables
2. **Add AI**: Generate documentation with Claude
3. **Go agentic**: Let Claude autonomously orchestrate tools

Perfect for learning Streamlit, SQL Server integration, and agentic AI patterns.

## License

MIT License - Free to use and modify

## Author

Built as a learning project to explore agentic AI capabilities with Claude and Streamlit.

## Acknowledgments

- Anthropic Claude for AI capabilities
- Streamlit for rapid UI development
- AdventureWorksDW2019 sample database for testing
