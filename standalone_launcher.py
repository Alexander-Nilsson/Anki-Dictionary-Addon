#!/usr/bin/env python3
"""
Simplified Anki Dictionary Addon Launcher

A streamlined version that runs the dictionary addon without Anki,
with minimal dependencies and better error handling.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DependencyChecker:
    """Check and validate required dependencies."""
    
    REQUIRED_MODULES = {
        'PyQt6': 'PyQt6 GUI framework',
        'anki': 'Anki core library',
        'aqt': 'Anki Qt interface'
    }
    
    @classmethod
    def check_dependencies(cls) -> tuple[bool, list[str]]:
        """Check if all required dependencies are available."""
        missing = []
        
        for module, description in cls.REQUIRED_MODULES.items():
            try:
                __import__(module)
                logger.debug(f"✓ {module} - {description}")
            except ImportError:
                missing.append(f"{module} - {description}")
                logger.warning(f"✗ {module} - {description}")
        
        return len(missing) == 0, missing
    
    @classmethod
    def get_install_command(cls, missing_modules: list[str]) -> str:
        """Generate pip install command for missing modules."""
        modules = [mod.split(' - ')[0] for mod in missing_modules]
        if 'PyQt6' in modules:
            modules.extend(['PyQt6-WebEngine'])
        return f"pip install {' '.join(modules)}"


class ConfigManager:
    """Manage addon configuration with defaults."""
    
    DEFAULT_CONFIG = {
        "maxWidth": 800,
        "jReadingEdit": True,
        "enableHotkeys": True,
        "dictionaryPath": "dictionaries",
        "theme": "default"
    }
    
    def __init__(self, addon_path: Path):
        self.addon_path = addon_path
        self.config_file = addon_path / "config.json"
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("Configuration loaded from config.json")
                return {**self.DEFAULT_CONFIG, **config}  # Merge with defaults
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading config: {e}. Using defaults.")
        
        logger.info("Using default configuration")
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("Configuration saved")
            return True
        except IOError as e:
            logger.error(f"Error saving config: {e}")
            return False


class MinimalAnkiEnvironment:
    """Minimal Anki environment for running the dictionary addon."""
    
    def __init__(self, addon_path: Path):
        self.addon_path = addon_path
        self.config_manager = ConfigManager(addon_path)
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup required directories."""
        temp_dir = self.addon_path / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        # Add addon path to Python path
        if str(self.addon_path) not in sys.path:
            sys.path.insert(0, str(self.addon_path))
        
        vendor_path = self.addon_path / 'vendor'
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.append(str(vendor_path))
    
    def create_mock_main_window(self):
        """Create minimal mock of Anki's main window."""
        config = self.config_manager.load_config()
        
        class MockAddonManager:
            def __init__(self, addon_path: Path):
                self.addon_path = addon_path
            
            def getConfig(self, addon_name: str) -> Dict[str, Any]:
                return config
        
        class MockMainWindow:
            def __init__(self, addon_path: Path, config: Dict[str, Any]):
                self.addon_path = addon_path
                self.addonManager = MockAddonManager(addon_path)
                self.AnkiDictConfig = config
                
                # Initialize addon-specific attributes
                self.DictExportingDefinitions = False
                self.dictSettings = False
                self.miDictDB = None  # Will be set later
                self.misoEditorLoadedAfterDictionary = False
                self.DictBulkMediaExportWasCancelled = False
                
                # Add refresh function
                self.refreshAnkiDictConfig = self._refresh_config
            
            def _refresh_config(self, new_config=None):
                if new_config:
                    self.AnkiDictConfig = new_config
                else:
                    # Reload from file
                    config_manager = ConfigManager(self.addon_path)
                    self.AnkiDictConfig = config_manager.load_config()
        
        return MockMainWindow(self.addon_path, config)
    
    def initialize_database(self, mock_mw):
        """Initialize the dictionary database."""
        try:
            import dictdb
            mock_mw.miDictDB = dictdb.DictDB()
            logger.info("Dictionary database initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def setup_environment(self):
        """Setup the complete minimal Anki environment."""
        # Import required modules
        try:
            import aqt
        except ImportError as e:
            logger.error(f"Failed to import aqt: {e}")
            return None
        
        # Create mock main window
        mock_mw = self.create_mock_main_window()
        
        # Initialize database
        if not self.initialize_database(mock_mw):
            return None
        
        # Set global mw variable
        aqt.mw = mock_mw
        
        logger.info("Minimal Anki environment setup complete")
        return mock_mw


class DictionaryLauncher:
    """Launch the dictionary interface."""
    
    def __init__(self, addon_path: Path):
        self.addon_path = addon_path
        self.environment = MinimalAnkiEnvironment(addon_path)
    
    def create_qt_application(self):
        """Create Qt application."""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QIcon
            
            app = QApplication(sys.argv)
            app.setApplicationName("Anki Dictionary Addon")
            
            # Set icon if available
            icon_path = self.addon_path / "icons" / "miso.png"
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
            
            return app
        except ImportError as e:
            logger.error(f"Failed to create Qt application: {e}")
            return None
    
    def create_dictionary_interface(self, mock_mw):
        """Create and configure the dictionary interface."""
        try:
            from midict import DictInterface
            
            welcome_msg = """
            <h2>Anki Dictionary Addon</h2>
            <p><strong>Standalone Mode</strong></p>
            <p>Running without full Anki application</p>
            <p>All dictionary features are available!</p>
            """
            
            dict_interface = DictInterface(
                dictdb=mock_mw.miDictDB,
                mw=mock_mw,
                path=str(self.addon_path),
                welcome=welcome_msg,
                parent=None,
                terms=False
            )
            
            return dict_interface
        except Exception as e:
            logger.error(f"Failed to create dictionary interface: {e}")
            return None
    
    def launch(self) -> int:
        """Launch the dictionary addon."""
        logger.info("Starting Anki Dictionary Addon (Standalone)")
        
        # Check dependencies
        deps_ok, missing = DependencyChecker.check_dependencies()
        if not deps_ok:
            logger.error("Missing dependencies:")
            for dep in missing:
                logger.error(f"  - {dep}")
            logger.info(f"Install with: {DependencyChecker.get_install_command(missing)}")
            return 1
        
        # Create Qt application
        app = self.create_qt_application()
        if not app:
            return 1
        
        # Setup minimal Anki environment
        mock_mw = self.environment.setup_environment()
        if not mock_mw:
            logger.error("Failed to setup Anki environment")
            return 1
        
        # Create dictionary interface
        dict_interface = self.create_dictionary_interface(mock_mw)
        if not dict_interface:
            return 1
        
        # Show interface
        dict_interface.show()
        dict_interface.raise_()
        dict_interface.activateWindow()
        
        logger.info("Dictionary addon launched successfully!")
        
        # Run Qt event loop
        return app.exec()


def main():
    """Main entry point."""
    try:
        addon_path = Path(__file__).parent
        launcher = DictionaryLauncher(addon_path)
        return launcher.launch()
    except KeyboardInterrupt:
        logger.info("Dictionary addon closed by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())