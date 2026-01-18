# Financial Analysis Tree System

A comprehensive multi-agent financial analysis system with interactive node editing capabilities.

## Features

- **Multi-Agent System (MAS)**: Extracts financial data from multiple sources
- **Tree-Based Analysis**: Hierarchical decision tree for investment analysis
- **Interactive Node Editing**: Edit and regenerate analysis nodes via web interface
- **Fast Inference**: Optimized for 2-minute analysis with Fast preset
- **REST API**: Full API support for programmatic access
- **Web Frontend**: Modern, professional web interface

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
cd DAG-main
```

### 2. Install Dependencies

```bash
# Install OpenAI dependencies
cd OpenAI
pip install -r requirements.txt

# Install MAS dependencies
cd ../MAS-main/financial_intelligence
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required:
- `OPENAI_API_KEY` - Required for LLM operations

Optional:
- `TAVILY_API_KEY` - For internet research
- `GROQ_API_KEY` - For MAS fallback
- `FRED_API_KEY` - For macroeconomic data
- `POLYGON_API_KEY` - For financial data

### 4. Run the API Server

```bash
cd OpenAI
python api.py
```

The API will be available at `http://localhost:8000`

### 5. Open the Frontend

Open `OpenAI/frontend.html` in your browser, or serve it:

```bash
cd OpenAI
python -m http.server 8080
# Then open http://localhost:8080/frontend.html
```

## Project Structure

```
DAG-main/
├── OpenAI/              # Tree orchestrator and API
│   ├── api.py          # FastAPI server
│   ├── frontend.html   # Web interface
│   ├── tree_orchestrator_main.py
│   └── requirements.txt
├── MAS-main/           # Multi-agent system
│   ├── financial_intelligence/
│   └── agents/
└── README.md           # Main documentation
```

## API Endpoints

- `POST /analyze` - Start analysis
- `GET /sessions/{session_id}/nodes` - Get all nodes
- `GET /sessions/{session_id}/nodes/{node_id}` - Get node details
- `POST /sessions/{session_id}/nodes/{node_id}/edit` - Edit node
- `GET /sessions/{session_id}/report` - Get full report

See `OpenAI/README.md` for detailed API documentation.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
