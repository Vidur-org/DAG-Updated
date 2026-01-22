# API Documentation for Frontend Integration

## Base URL
```
http://localhost:8000
```

## CORS Configuration
The API is configured to accept requests from any origin, making it accessible to any frontend application. CORS is enabled with the following settings:
- Allow Origins: All origins (*)
- Allow Credentials: True
- Allow Methods: All HTTP methods
- Allow Headers: All headers

## Available Endpoints

### 1. Root Endpoint
**GET /**  
Returns API information and available endpoints.

**Response:**
```json
{
  "message": "Tree + MAS Analysis API",
  "version": "1.0.0",
  "endpoints": {
    "POST /analyze": "Analyze investment query",
    "GET /sessions/{session_id}/nodes": "Get all nodes for a session",
    "GET /sessions/{session_id}/nodes/{node_id}": "Get a specific node",
    "POST /sessions/{session_id}/nodes/{node_id}/edit": "Edit a node and regenerate subtree",
    "GET /sessions/{session_id}/report": "Get full execution report"
  }
}
```

### 2. Start Analysis
**POST /analyze**  
Initiates a new financial analysis and returns a session ID for subsequent operations.

**Request Body:**
```json
{
  "user_id": "string",
  "query": "Should I invest in RELIANCE for October 2024 to December 2024?",
  "preferences": {
    "max_levels": 2,
    "max_children": 1,
    "preset": "fast",
    "save": false
  }
}
```

**Request Parameters:**
- `user_id` (required): User identifier for preference management
- `query` (required): Investment analysis query or question
- `preferences` (optional): Analysis configuration
  - `max_levels`: Maximum tree depth (overrides preset)
  - `max_children`: Maximum children per node (overrides preset)
  - `preset`: Preset name - "fast", "balanced", or "thorough"
    - `fast`: max_levels=2, max_children=1 (~2 minutes)
    - `balanced`: max_levels=3, max_children=2 (~5 minutes)
    - `thorough`: max_levels=4, max_children=2 (~10 minutes)
  - `save`: Whether to save preferences for the user (default: false)

**Response:**
```json
{
  "session_id": "uuid-string",
  "answer": "Final aggregated analysis text",
  "execution_report": {
    "tree_structure": {...},
    "all_nodes": {...},
    "stats": {
      "llm_calls": 42,
      "bm25_hits": 15,
      "internet_searches": 8,
      "num_nodes": 25
    },
    "final_decision": {
      "position": "long",
      "confidence_level": 0.75,
      "detailed_analysis": "..."
    },
    "execution_log": [...]
  },
  "metadata": {
    "max_levels": 2,
    "max_children": 1,
    "used_saved_preferences": false,
    "source": "MAS + Tree"
  }
}
```

### 3. Get All Nodes
**GET /sessions/{session_id}/nodes**  
Retrieves all nodes in the decision tree for a given session.

**Path Parameters:**
- `session_id` (required): Session ID returned from /analyze endpoint

**Response:**
```json
{
  "session_id": "uuid-string",
  "nodes": [
    {
      "id": "0",
      "level": 0,
      "question": "Should I invest in RELIANCE...",
      "is_leaf": false,
      "has_answer": true,
      "answer_preview": "Based on analysis...",
      "children": ["1", "2", "3"],
      "parent_id": null
    },
    ...
  ],
  "total_nodes": 25
}
```

### 4. Get Node Details
**GET /sessions/{session_id}/nodes/{node_id}**  
Retrieves detailed information about a specific node.

**Path Parameters:**
- `session_id` (required): Session ID
- `node_id` (required): Node ID (e.g., "0", "1", "2")

**Response:**
```json
{
  "id": "0",
  "level": 0,
  "question": "Full question text",
  "answer": "Complete answer text",
  "is_leaf": false,
  "children": ["1", "2", "3"],
  "parent_id": null,
  "context": "Context preview...",
  "internet_research": {
    "citations": [...],
    "urls": [...],
    "summary": "..."
  },
  "mas_data_used": {...}
}
```

### 5. Edit Node
**POST /sessions/{session_id}/nodes/{node_id}/edit**  
Edits a node's question and regenerates its subtree.

**Path Parameters:**
- `session_id` (required): Session ID
- `node_id` (required): Node ID to edit

**Request Body:**
```json
{
  "new_question": "Updated question text"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Node 5 edited and subtree regenerated",
  "edit_count": 1,
  "updated_node": {
    "id": "5",
    "question": "Updated question text",
    "answer": "Regenerated answer",
    "children": ["6", "7"]
  },
  "execution_report": {
    "tree_structure": {...},
    "all_nodes": {...},
    "stats": {...},
    "final_decision": {...}
  }
}
```

**Note:** This operation may take 1-3 minutes as it regenerates the subtree and updates parent nodes.

### 6. List All Sessions
**GET /sessions**  
Retrieves a list of all stored sessions from persistent storage.

**Query Parameters:**
- `user_id` (optional): Filter sessions by user ID
- `limit` (optional): Maximum number of sessions to return (default: 50)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid-string",
      "created_at": "2026-01-18T18:00:00",
      "query": "Should I invest in RELIANCE...",
      "user_id": "user123",
      "stock": "RELIANCE",
      "num_nodes": 25,
      "final_position": "long",
      "file_path": "sessions/uuid-string.json"
    },
    ...
  ],
  "total": 10,
  "total_stored": 10
}
```

### 7. Get Full Report
**GET /sessions/{session_id}/report**  
Retrieves the complete execution report for a session. Works with both active (in-memory) and stored (on-disk) sessions.

**Path Parameters:**
- `session_id` (required): Session ID

**Response:**
```json
{
  "session_id": "uuid-string",
  "execution_report": {
    "tree_structure": {...},
    "all_nodes": {...},
    "stats": {
      "llm_calls": 42,
      "bm25_hits": 15,
      "internet_searches": 8,
      "num_nodes": 25,
      "edit_count": 0
    },
    "final_decision": {
      "position": "long",
      "confidence_level": 0.75,
      "detailed_analysis": "..."
    },
    "execution_log": [...]
  }
}
```

## Error Responses

All endpoints may return the following error responses:

**404 Not Found:**
```json
{
  "detail": "Session not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Analysis failed: error message"
}
```

## Example Frontend Integration

### JavaScript/TypeScript Example

```javascript
const API_BASE = 'http://localhost:8000';

// Start analysis
async function startAnalysis(query, preset = 'fast') {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: 'user123',
      query: query,
      preferences: {
        preset: preset,
        save: false
      }
    })
  });
  
  if (!response.ok) {
    throw new Error('Analysis failed');
  }
  
  return await response.json();
}

// Get all nodes
async function getNodes(sessionId) {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/nodes`);
  return await response.json();
}

// Get node details
async function getNodeDetails(sessionId, nodeId) {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/nodes/${nodeId}`);
  return await response.json();
}

// Edit node
async function editNode(sessionId, nodeId, newQuestion) {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/nodes/${nodeId}/edit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      new_question: newQuestion
    })
  });
  
  return await response.json();
}

// Get full report
async function getReport(sessionId) {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/report`);
  return await response.json();
}

// List all previous sessions
async function listSessions(userId = null, limit = 50) {
  const url = userId 
    ? `${API_BASE}/sessions?user_id=${userId}&limit=${limit}`
    : `${API_BASE}/sessions?limit=${limit}`;
  const response = await fetch(url);
  return await response.json();
}
```

### Python Example

```python
import requests

API_BASE = "http://localhost:8000"

# Start analysis
def start_analysis(query, preset="fast"):
    response = requests.post(
        f"{API_BASE}/analyze",
        json={
            "user_id": "user123",
            "query": query,
            "preferences": {
                "preset": preset,
                "save": False
            }
        }
    )
    response.raise_for_status()
    return response.json()

# Get all nodes
def get_nodes(session_id):
    response = requests.get(f"{API_BASE}/sessions/{session_id}/nodes")
    response.raise_for_status()
    return response.json()

# Edit node
def edit_node(session_id, node_id, new_question):
    response = requests.post(
        f"{API_BASE}/sessions/{session_id}/nodes/{node_id}/edit",
        json={"new_question": new_question}
    )
    response.raise_for_status()
    return response.json()
```

## Interactive API Documentation

When the API server is running, you can access interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive testing interfaces where you can try all endpoints directly from your browser.

## Session Management

- Each analysis creates a unique session ID
- Sessions are automatically saved to persistent storage (disk)
- Sessions persist across server restarts
- Use the session ID for all subsequent operations
- Previous sessions can be retrieved using GET /sessions endpoint
- Reports are stored in the `sessions/` directory as JSON files

## Rate Limiting

Currently, there are no rate limits implemented. For production use, consider implementing rate limiting based on your requirements.

## Production Considerations

For production deployment:

1. **CORS Configuration**: Update `allow_origins` in `api.py` to specify your frontend domain instead of "*"
2. **Authentication**: Add authentication middleware if needed
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Session Storage**: Consider using Redis or database for session persistence
5. **Error Handling**: Implement comprehensive error logging
6. **HTTPS**: Use HTTPS in production
7. **API Versioning**: Consider versioning your API endpoints

## Support

For issues or questions, refer to the main README.md or open an issue on the GitHub repository.
