# Quick Start: Running the Tree + MAS Analysis API

## Prerequisites

1. **Python 3.8+** installed
2. **API Keys** (set as environment variables):
   - `OPENAI_API_KEY` - Required for LLM operations
   - `GROQ_API_KEY` - Optional (if using Groq)
   - `SERPAPI_KEY` - Optional (for search)
   - `TAVILY_API_KEY` - Optional (for internet research)
   - `POLYGON_API_KEY` - Optional (for financial data)
   - `FRED_API_KEY` - Optional (for macroeconomic data)

## Step-by-Step Setup

### 1. Navigate to the OpenAI Directory

```bash
cd DAG-main/OpenAI
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you encounter any missing dependencies, you may also need to install from:
- `../MAS-main/requirements.txt` (if MAS dependencies are separate)

### 3. Set Environment Variables

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

**On Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**On Linux/Mac:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Or create a `.env` file** in the `OpenAI` directory:
```
OPENAI_API_KEY=your-api-key-here
GROQ_API_KEY=your-groq-key-here
TAVILY_API_KEY=your-tavily-key-here
```

### 4. Start the API Server

**Option A: Using Python directly**
```bash
python api.py
```

**Option B: Using uvicorn (recommended for production)**
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

### 5. Verify the Server is Running

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 6. Test the API

**Option A: Using the Interactive Docs**
Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test the API directly from these pages.

**Option B: Using curl**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
    "preferences": {
      "preset": "balanced"
    }
  }'
```

**Option C: Using Python**
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "user_id": "test_user",
        "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
        "preferences": {
            "preset": "balanced",
            "save": False
        }
    }
)

print(json.dumps(response.json(), indent=2))
```

**Option D: Using JavaScript/Node.js**
```javascript
const fetch = require('node-fetch');

fetch('http://localhost:8000/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    user_id: 'test_user',
    query: 'Should I invest in RELIANCE for October 2024 to December 2024?',
    preferences: {
      preset: 'balanced',
      save: false
    }
  })
})
.then(res => res.json())
.then(data => console.log(JSON.stringify(data, null, 2)))
.catch(error => console.error('Error:', error));
```

## Common Issues & Solutions

### Issue: ModuleNotFoundError
**Solution:** Make sure you're in the `OpenAI` directory and all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Port already in use
**Solution:** Use a different port:
```bash
uvicorn api:app --host 0.0.0.0 --port 8001
```

### Issue: API key not found
**Solution:** Verify your environment variables are set:
```bash
# Check if variable is set
echo $OPENAI_API_KEY  # Linux/Mac
echo %OPENAI_API_KEY%  # Windows CMD
$env:OPENAI_API_KEY   # Windows PowerShell
```

### Issue: Import errors from MAS-main
**Solution:** Ensure the MAS-main directory structure is correct:
```
DAG-main/
  ├── OpenAI/
  │   └── api.py
  └── MAS-main/
      └── (MAS files)
```

## Production Deployment

For production, use a production ASGI server:

```bash
# Install gunicorn with uvicorn workers
pip install gunicorn

# Run with multiple workers
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Or use Docker (create a `Dockerfile`):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## API Endpoint Details

### POST /analyze

**URL:** `http://localhost:8000/analyze`

**Request:**
```json
{
  "user_id": "string (required)",
  "query": "string (required)",
  "preferences": {
    "max_levels": 4,           // optional: tree depth
    "max_children": 2,          // optional: children per node
    "preset": "balanced",       // optional: "fast", "balanced", "thorough"
    "save": true                // optional: save preferences for user
  }
}
```

**Response:**
```json
{
  "answer": "Final analysis text...",
  "execution_report": {
    "tree_structure": {...},
    "all_nodes": {...},
    "stats": {...},
    "final_decision": {
      "position": "long|short|neutral",
      "confidence_level": 0.75,
      "detailed_analysis": "..."
    }
  },
  "metadata": {
    "max_levels": 4,
    "max_children": 2,
    "used_saved_preferences": false,
    "source": "MAS + Tree"
  }
}
```

## Performance Notes

- **Fast preset**: ~1-2 minutes (3 levels, 1 child)
- **Balanced preset**: ~3-4 minutes (4 levels, 2 children)
- **Thorough preset**: ~5-7 minutes (5 levels, 3 children)

The analysis time depends on:
- Number of tree levels and children
- MAS data fetching time
- Internet research queries
- LLM response times

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.
