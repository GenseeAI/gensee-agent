import importlib
from pathlib import Path

# Import all tools to register them
# Get the current directory
current_dir = Path(__file__).parent

# Automatically import all Python files in the tools directory
for file_path in current_dir.glob("*.py"):
    if file_path.name != "__init__.py":
        module_name = f"gensee_agent.tools.{file_path.stem}"
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass  # Skip files that can't be imported


# import gensee_agent.tools.letter_counter  # noqa: F401
# import gensee_agent.tools.gensee_search  # noqa: F401
# import gensee_agent.tools.slack_tool  # noqa: F401