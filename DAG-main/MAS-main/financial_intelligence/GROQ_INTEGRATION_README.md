# Groq Fallback Integration

This document describes the integration of the Groq-based fallback system with the financial intelligence system.

## Overview

The financial intelligence system now supports three fallback configurations:

1. **Groq Fallback** (Default) - Uses the new Groq-based WebGPT system
2. **OpenAI Fallback** - Uses the original OpenAI-based WebGPT system  
3. **Hybrid Fallback** - Tries Groq first, falls back to OpenAI if needed

## Configuration

### Environment Variables

```bash
# Fallback system selection
FALLBACK_SYSTEM=groq              # Options: groq, openai, hybrid

# Enable/disable specific fallbacks
ENABLE_GROQ_FALLBACK=true
ENABLE_OPENAI_FALLBACK=true

# API keys (required)
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional, for openai/hybrid modes
```

### Configuration Options

| Variable | Default | Description |
|----------|----------|-------------|
| `FALLBACK_SYSTEM` | `groq` | Fallback system to use |
| `ENABLE_GROQ_FALLBACK` | `true` | Enable Groq fallback |
| `ENABLE_OPENAI_FALLBACK` | `true` | Enable OpenAI fallback |
| `GROQ_API_KEY` | Required | Groq API key |
| `TAVILY_API_KEY` | Required | Tavily search API key |
| `OPENAI_API_KEY` | Optional | OpenAI API key |

## Architecture

### Groq Fallback System

- **Location**: `groq_fallback.py`
- **Dependencies**: `groq-backend` modules
- **Features**:
  - Web search via Tavily
  - Query routing and intent detection
  - Financial data synthesis
  - Source citation

### Integration Points

1. **Configuration** (`config.py`)
   - Added fallback system selection
   - API key validation
   - Helper functions

2. **Orchestrator** (`orchestrator.py`)
   - Dynamic fallback handler initialization
   - System-aware logging and error messages

3. **Compatibility**
   - Maintains existing interface
   - Backward compatible with OpenAI fallback

## Usage Examples

### Using Groq Fallback (Default)

```python
from orchestrator import ParallelOrchestrator

orchestrator = ParallelOrchestrator()  # Automatically uses Groq
result = await orchestrator.execute(planner_output)
```

### Using OpenAI Fallback

```bash
export FALLBACK_SYSTEM=openai
```

### Using Hybrid Fallback

```bash
export FALLBACK_SYSTEM=hybrid
```

## Testing

Run the integration test:

```bash
cd financial_intelligence
python test_groq_integration.py
```

## Features

### Groq Fallback Benefits

- **Cost Effective**: Uses Groq's affordable models
- **Fast Performance**: Optimized search and synthesis
- **Financial Focus**: Specialized for financial queries
- **Real-time Data**: Live web search via Tavily

### Hybrid Fallback Benefits

- **Reliability**: Falls back to OpenAI if Groq fails
- **Best of Both**: Cost-effective primary with robust backup
- **Transparent**: Clear indication of which system was used

## Error Handling

The system provides detailed error information:

- Configuration validation errors
- API key missing warnings
- Fallback system availability checks
- Graceful degradation between systems

## Migration

To migrate from OpenAI to Groq fallback:

1. Set environment variables:
   ```bash
   export FALLBACK_SYSTEM=groq
   export GROQ_API_KEY=your_key
   export TAVILY_API_KEY=your_key
   ```

2. No code changes required - fully backward compatible

## Troubleshooting

### Common Issues

1. **"groq-backend modules not available"**
   - Ensure `groq-backend` directory exists
   - Check Python path includes groq-backend

2. **"GROQ_API_KEY not set"**
   - Set the environment variable
   - Check .env file configuration

3. **"TAVILY_API_KEY not set"**
   - Required for web search functionality
   - Get key from https://tavily.com/

### Debug Mode

Enable debug logging:

```bash
export DEBUG_MODE=true
```

## Files Modified

- `config.py` - Added Groq fallback configuration
- `orchestrator.py` - Updated fallback handler initialization
- `groq_fallback.py` - New Groq fallback adapter
- `test_groq_integration.py` - Integration test script

## Dependencies

New dependencies added:

- `groq-backend` modules (agents, llm, search)
- `tavily-python` (via groq-backend)
- `openai` (for hybrid compatibility)

## Performance

Typical performance metrics:

- **Groq Fallback**: 8-15 seconds per query
- **OpenAI Fallback**: 10-20 seconds per query
- **Hybrid**: 8-20 seconds (depending on fallback used)

## Support

For issues with the Groq fallback integration:

1. Check configuration validation output
2. Run integration test script
3. Verify API keys are set correctly
4. Check groq-backend module availability
