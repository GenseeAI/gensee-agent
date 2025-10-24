# Gensee Agent Template

A powerful, modular AI agent framework for building intelligent web search and document analysis applications. This template provides a complete foundation for creating AI agents with tool integration, search capabilities, and document processing features.

## Features

### 🔍 **Deep Search Agent**
- Intelligent web search with multiple query breakdown
- Structured response format with references and explanations
- Integration with Gensee search platform
- Support for PDF and web content extraction

### 🛠️ **Modular Architecture**
- Plugin-based tool system
- MCP (Model Context Protocol) support
- Configurable LLM backends
- Extensible prompt management

### 🌐 **Multiple Interfaces**
- FastAPI REST endpoints
- Slack integration
- Web interface for testing
- Command-line interface

## Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API key (or compatible LLM service)
- Gensee platform API key (for search functionality)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd agent-template
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Set up environment variables:**
   ```bash
   cp src/deep_search/app/config.json.example src/deep_search/app/config.json
   # Edit config.json with your API keys and settings
   ```

### Running the Application

#### Deep Search API
```bash
cd src/deep_search/app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Slack Bot
```bash
cd src/slack_interface/app
python main.py
```

## API Endpoints

### Health Check
```bash
GET /healthz
```

### Deep Search
```bash
POST /agent/deep-search
Content-Type: application/json

{
  "query": "What is the capital of France?"
}
```

## Configuration

The agent system uses JSON configuration files for customization:

```json
{
  "controller": {
    "name": "deep_search_agent",
    "allow_user_interaction": false,
    "streaming": false
  },
  "llm_manager": {
    "model_name": "gpt-4",
    "api_key": "your-openai-api-key"
  },
  "tools": {
    "gensee.search": {
      "gensee_api_key": "your-gensee-api-key"
    }
  }
}
```

## Available Tools

### Built-in Tools
- **`gensee.search`**: Web search using Gensee platform
- **`gensee.letter_counter`**: Text analysis utilities
- **`system.user_interaction`**: User interaction handling
- ...

### MCP Tools
The framework supports Model Context Protocol (MCP) for external tool integration:
- File system operations
- Database queries
- External API integrations
- Custom business logic

## Architecture

```
src/
├── gensee_agent/           # Core agent framework
│   ├── controller/         # Main controller logic
│   ├── models/            # LLM integrations (OpenAI, etc.)
│   ├── tools/             # Tool implementations
│   ├── prompts/           # Prompt templates
│   └── configs/           # Configuration management
├── deep_search/           # Deep search application
└── slack_interface/       # Slack bot implementation
```

### Key Components

- **Controller**: Orchestrates the entire agent workflow
- **LLM Manager**: Handles language model interactions
- **Tool Manager**: Manages tool registration and execution
- **Prompt Manager**: Template-based prompt generation
- **Task Manager**: Coordinates task execution and streaming

## Development

### Adding New Tools

1. Create a new tool class inheriting from `BaseTool`:
```python
from gensee_agent.tools.base import BaseTool, public_api, register_tool

class MyCustomTool(BaseTool):
    @public_api
    async def my_function(self, param: str) -> str:
        """Tool function description."""
        return f"Processed: {param}"

register_tool("my_custom_tool", MyCustomTool)
```

2. Register the tool in your configuration:
```json
{
  "tools": {
    "my_custom_tool": {}
  }
}
```

### Customizing Prompts

Create custom prompt templates using Jinja2:
```python
TEMPLATE = """
You are a specialized agent for {{domain}}.
Your task is: {{objective}}
Available tools: {{tools}}
"""
```


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request


## Support

For questions and support:
- Create an issue in the repository
- Contact the development team
- Check the documentation in the `docs/` directory
