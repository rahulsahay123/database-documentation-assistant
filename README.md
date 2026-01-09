# Database Documentation Assistant

AI-powered database documentation tool using Streamlit and Claude AI.

## Features

- 🤖 **Agentic AI Chat**: Ask questions about your database in natural language
- 📚 **Table Glossary**: AI-generated business descriptions for tables and columns
- 🔗 **ER Diagrams**: Visual representation of table relationships
- ⚙️ **Stored Procedure Analysis**: Automated documentation of SQL procedures
- 📊 **Data Profiling**: Exploratory data analysis with statistics and visualizations

## Tech Stack

- **Frontend**: Streamlit
- **Database**: SQL Server (via pyodbc)
- **AI**: Claude (Anthropic API)
- **Visualization**: Mermaid, Plotly

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
   cp config.template.py config.py
```
   Edit `config.py` with your SQL Server details and Anthropic API key.

4. **Run the application**
```bash
   streamlit run app.py
```

## Project Structure
```
├── app.py                  # Main Streamlit application
├── config.py              # Database & API configuration (not in Git)
├── config.template.py     # Template for configuration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## License

MIT
