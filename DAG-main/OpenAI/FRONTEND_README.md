# Frontend Node Editor - Quick Start Guide

## 🚀 Getting Started

### 1. Start the API Server
The API server should already be running on `http://localhost:8000`. If not, start it:
```bash
cd OpenAI
python api.py
```

### 2. Open the Frontend
Open `frontend.html` in your web browser. You can:
- Double-click the file to open it
- Or use a local web server:
  ```bash
  # Python 3
  python -m http.server 8080
  # Then open: http://localhost:8080/frontend.html
  ```

## 📋 Features

### ✅ Analysis
1. Enter your User ID (or use default: `user123`)
2. Enter your investment query (e.g., "Should I invest in RELIANCE for October 2024 to December 2024?")
3. Select a preset (Fast/Balanced/Thorough)
4. Click "🚀 Start Analysis"
5. Wait for the analysis to complete (this may take a few minutes)

### ✅ Tree Visualization
- After analysis completes, you'll see the decision tree
- Nodes are color-coded by level:
  - **Level 0** (Blue): Root question
  - **Level 1** (Green): Main analysis categories
  - **Level 2** (Yellow): Sub-questions
  - **Level 3+** (Orange/Red): Deeper analysis

### ✅ Node Editing
1. **Select a Node**: Click on any node in the tree
2. **View Details**: Node details appear in the sidebar
3. **Edit Question**: 
   - The current question is shown
   - Modify the "New Question" field
   - Click "💾 Save & Regenerate"
4. **Automatic Regeneration**:
   - The system will:
     - Delete all children of the edited node
     - Regenerate the subtree with new questions
     - Update all parent node answers
     - Regenerate the final investment decision

### ✅ Session Management
- Each analysis creates a unique session ID
- All node edits are tracked within the session
- Edit count is displayed in the stats panel

## 🎯 API Endpoints

The frontend uses these API endpoints:

- `POST /analyze` - Start new analysis
- `GET /sessions/{session_id}/nodes` - Get all nodes
- `GET /sessions/{session_id}/nodes/{node_id}` - Get node details
- `POST /sessions/{session_id}/nodes/{node_id}/edit` - Edit a node
- `GET /sessions/{session_id}/report` - Get full report

## 💡 Tips

1. **Start with Balanced Preset**: Good balance between speed and depth
2. **Edit Root Node**: Editing the root node (Node 0) will regenerate the entire tree
3. **Check Node Details**: Click nodes to see full answers and context
4. **Multiple Edits**: You can edit multiple nodes in sequence
5. **Session Persistence**: The session stays active until you start a new analysis

## 🔧 Troubleshooting

### Frontend can't connect to API
- Make sure the API server is running on port 8000
- Check browser console for CORS errors
- Verify `API_BASE` in `frontend.html` matches your API URL

### Analysis takes too long
- Use "Fast" preset for quicker results
- Reduce max_levels and max_children in preferences

### Node edit fails
- Check that the session ID is valid
- Ensure the node ID exists
- Check API server logs for errors

## 📊 Example Workflow

1. **Initial Analysis**:
   ```
   Query: "Should I invest in RELIANCE for October 2024 to December 2024?"
   Preset: Balanced
   → Wait for completion
   → View tree structure
   ```

2. **Edit a Node**:
   ```
   Click on Node 5 (e.g., "Technical Analysis")
   → Modify question to "Analyze RELIANCE's technical indicators and price patterns"
   → Click "Save & Regenerate"
   → Wait for subtree regeneration
   → View updated tree
   ```

3. **Review Results**:
   ```
   Check updated final decision
   View statistics (nodes, LLM calls, edits)
   Export report if needed
   ```

---

**Enjoy interactive node editing!** 🎉