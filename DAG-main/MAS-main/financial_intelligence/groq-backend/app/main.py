from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.schemas import ChatRequest, ChatResponse
from app.agents import route_query
from app.llm import openai_stream_chat
from app.search import web_search, format_search_context
import json

app = FastAPI(
    title="WebGPT Backend",
    description="AI assistant with real-time web search using Tavily and OpenAI",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main chat endpoint - routes query and returns response
    """
    result = route_query(req.message)
    return ChatResponse(**result)

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint for real-time responses
    """
    async def generate():
        # First, determine if we need search
        from app.agents import needs_web_search
        
        if needs_web_search(req.message):
            # Perform search
            search_results = web_search(req.message)
            context = format_search_context(search_results)
            
            # Send sources first
            yield f"data: {json.dumps({'type': 'sources', 'sources': search_results.get('results', [])})}\n\n"
            
            # Stream the response
            messages = [
                {
                    "role": "system",
                    "content": "You are WebGPT. Synthesize the search results into a comprehensive answer."
                },
                {
                    "role": "user",
                    "content": f"Query: {req.message}\n\n{context}\n\nAnswer:"
                }
            ]
        else:
            # Regular chat
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                },
                {"role": "user", "content": req.message}
            ]
        
        # Stream response
        for chunk in openai_stream_chat(messages):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/search")
def search(query: str, max_results: int = 5):
    """
    Direct search endpoint for testing
    """
    return web_search(query, max_results)

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "WebGPT",
        "features": ["web_search", "chat", "streaming"]
    }

@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "message": "WebGPT API",
        "endpoints": {
            "POST /chat": "Main chat endpoint",
            "POST /chat/stream": "Streaming chat endpoint",
            "GET /search": "Direct web search",
            "GET /health": "Health check"
        }
    }