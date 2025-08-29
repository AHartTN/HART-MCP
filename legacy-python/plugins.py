"""
Plugin system for MCP agent extensions.
"""

import asyncio
import importlib
import logging
import os
import traceback
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

__all__ = ["register_plugin", "call_plugin", "list_plugins", "load_plugins"]

PLUGINS_FOLDER = "plugins_folder"
_plugin_registry = {}


def register_plugin(name, func):
    _plugin_registry[name] = func


async def load_plugins():
    """Load all plugins from plugins_folder."""
    _plugin_registry.clear()
    plugin_dir = os.path.join(os.path.dirname(__file__), PLUGINS_FOLDER)
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{PLUGINS_FOLDER}.{filename[:-3]}"
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "register"):
                    reg_func = mod.register
                    if asyncio.iscoroutinefunction(reg_func):
                        await reg_func(_plugin_registry)
                    else:
                        reg_func(_plugin_registry)
            except ImportError as err:
                logger.error(
                    f"ImportError loading plugin {filename}: {err}\n{traceback.format_exc()}"
                )
            except Exception as err:
                logger.error(
                    f"Error loading plugin {filename}: {err}\n{traceback.format_exc()}"
                )


async def call_plugin(*args, **kwargs):
    """Call a registered plugin by name."""
    if not args:
        return {"error": "No plugin name provided."}
    plugin_name = args[0]
    plugin_args = args[1:]
    if plugin_name in _plugin_registry:
        try:
            plugin_func = _plugin_registry[plugin_name]
            if asyncio.iscoroutinefunction(plugin_func):
                return await plugin_func(*plugin_args, **kwargs)
            else:
                return plugin_func(*plugin_args, **kwargs)
        except Exception as e:
            logger.error(
                f"Plugin '{plugin_name}' execution error: {e}\n{traceback.format_exc()}"
            )
            return {"error": f"Plugin '{plugin_name}' execution error: {e}"}
    else:
        return {"error": f"Plugin '{plugin_name}' not found."}


def list_plugins():
    """Return a list of registered plugin names."""
    return list(_plugin_registry.keys())


async def _register_all_plugins():
    """Registers all core and example plugins."""
    try:
        import plugins_folder.agent_core as agent_core

        if hasattr(agent_core, "create_agent"):
            register_plugin("create_agent", agent_core.create_agent)
    except Exception as e:
        logger.error(
            f"Error loading agent_core plugin on import: {e}\n{traceback.format_exc()}"
        )

    register_plugin("echo", echo_plugin)
    register_plugin("search", search_plugin)
    register_plugin("timestamp", timestamp_plugin)
    register_plugin("transform", transform_plugin)


def echo_plugin(payload):
    return {"echo": payload}


def search_plugin(payload):
    query = payload.get("query", "")
    return {"search_results": [f"Result for {query}"]}


def timestamp_plugin(data):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": data,
    }


def transform_plugin(payload):
    text = payload.get("text", "")
    return {"transformed": text.upper()}


if __name__ == "__main__":
    asyncio.run(_register_all_plugins())
    logger.info("Plugins registered: %s", list_plugins())
