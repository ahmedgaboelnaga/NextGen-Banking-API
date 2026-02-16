import importlib
import os
import pathlib

from backend.app.core.logging import get_logger

logger = get_logger()


def discover_models() -> list[str]:
    """Discover all models.py files in the application and return their module paths."""
    models_modules = []
    root_path = pathlib.Path(__file__).parent.parent
    logger.debug(f"Scanning for model modules in root path: {root_path}")

    for root, _, files in os.walk(root_path):
        if any(excluded in root for excluded in ["venv", "__pycache__", "pytest_cache"]):
            continue

        if "models.py" in files:
            relative_path = pathlib.Path(root).relative_to(root_path)
            module_path = "backend.app." + ".".join(relative_path.parts + ("models",))
            models_modules.append(module_path)
            logger.debug(f"Discovered model file: {module_path}")
    
    return models_modules
    

def load_models() -> None:
    modules = discover_models()
    if not modules:
        logger.warning("No model modules found to load.")
    else:
        logger.info(f"Successfully loaded {len(modules)} model modules.")
    
    for module_path in modules:
        try:
            importlib.import_module(module_path)
            logger.debug(f"Imported model module: {module_path}")
        except ImportError as e:
            logger.error(f"Failed to import model module {module_path}: {e}")