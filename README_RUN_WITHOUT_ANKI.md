# Running Anki Dictionary Addon Without Anki

This guide shows you how to run the Anki Dictionary Addon directly with a Python script, **without having to launch the full Anki application**.

## 🎯 What This Does

- ✅ Runs the **original addon** with all its features
- ✅ Uses the **same Qt interface** as in Anki
- ✅ Keeps all **Anki dependencies** (themes, styling, etc.)
- ✅ **No need to start Anki** - just run a Python script
- ✅ All dictionary features work exactly as in Anki

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements_addon.txt

# Or install manually:
pip install anki PyQt6 PyQt6-WebEngine requests
```

### 2. Launch the Dictionary

```bash
# Simple launcher (recommended)
python launch_dictionary.py

# Or run directly
python run_addon_standalone.py
```

### 3. Use the Dictionary

The original Anki Dictionary Addon interface will open in a separate window, with all features available:

- 🔍 Dictionary search
- 🖼️ Image search  
- 🎵 Audio pronunciation
- 📝 Card export (limited without full Anki)
- 🎨 Theme customization
- ⌨️ Hotkeys and shortcuts
- 🌐 Multi-language support

## 📁 Files Added

### Core Files
- **`run_addon_standalone.py`** - Main script that initializes minimal Anki environment
- **`launch_dictionary.py`** - Simple launcher with dependency checking
- **`requirements_addon.txt`** - Python dependencies needed

### What These Scripts Do

1. **Minimal Anki Environment**: Creates just the Anki components needed by the addon
2. **Mock Main Window**: Provides the `mw` object that the addon expects
3. **Configuration Loading**: Loads addon settings from `config.json`
4. **Database Initialization**: Sets up the dictionary database
5. **UI Launch**: Starts the original Qt interface

## 🔧 How It Works

### The Problem
The original addon expects to run inside Anki and relies on:
- `aqt.mw` (Anki's main window object)
- Anki's addon manager
- Anki's configuration system
- Anki's database connections

### The Solution
The standalone scripts create minimal versions of these components:

```python
# Create minimal main window mock
class MinimalAnkiMainWindow:
    def __init__(self):
        self.addonManager = MinimalAddonManager()
        self.AnkiDictConfig = load_config()
        self.miDictDB = dictdb.DictDB()
        # ... other required attributes

# Set as global mw that addon expects
aqt.mw = MinimalAnkiMainWindow()

# Launch original addon interface
dict_interface = DictInterface(mw.miDictDB, mw, addon_path, welcome_msg)
dict_interface.show()
```

## 🆚 Comparison: Full Anki vs Standalone

| Feature | Full Anki | Standalone Script |
|---------|-----------|-------------------|
| **Dictionary Search** | ✅ | ✅ |
| **Image Search** | ✅ | ✅ |
| **Audio Pronunciation** | ✅ | ✅ |
| **Qt Interface** | ✅ | ✅ |
| **Themes & Styling** | ✅ | ✅ |
| **Hotkeys** | ✅ | ✅ |
| **Multi-language** | ✅ | ✅ |
| **Card Export** | ✅ | 🚧 Limited |
| **Anki Integration** | ✅ | ❌ |
| **Startup Time** | Slow | **Fast** |
| **Memory Usage** | High | **Low** |
| **Dependencies** | Full Anki | **Minimal** |

## 🛠 Troubleshooting

### Common Issues

1. **"No module named 'anki'"**
   ```bash
   pip install anki
   ```

2. **"No module named 'PyQt6'"**
   ```bash
   pip install PyQt6 PyQt6-WebEngine
   ```

3. **"Error loading dictionary database"**
   - Make sure you're running from the addon directory
   - Check that dictionary files are present

4. **Interface doesn't appear**
   - Try running with `python -u launch_dictionary.py` for better output
   - Check console for error messages

### Advanced Troubleshooting

If you encounter issues, you can:

1. **Check dependencies**:
   ```bash
   python -c "import anki, PyQt6; print('Dependencies OK')"
   ```

2. **Run with debug output**:
   ```bash
   python -u run_addon_standalone.py
   ```

3. **Check addon files**:
   ```bash
   ls -la midict.py dictdb.py  # Should exist
   ```

## 🎉 Benefits of This Approach

### ✅ Advantages
- **Faster startup** - No need to load full Anki
- **Lower memory usage** - Only dictionary components loaded
- **Same functionality** - Original addon features preserved
- **Easy to use** - Just run a Python script
- **Development friendly** - Great for testing addon changes

### 🚧 Limitations
- **Card export limited** - Can't directly add to Anki collection
- **Some integrations missing** - Features that require full Anki context
- **Manual setup** - Need to install dependencies separately

## 🔄 Updating

To update the addon:

1. **Pull latest changes** from the repository
2. **No additional setup needed** - scripts will use updated addon code
3. **Dependencies rarely change** - Usually no need to reinstall

## 💡 Use Cases

This approach is perfect for:

- 📚 **Quick dictionary lookups** without starting Anki
- 🧪 **Testing addon changes** during development  
- 💻 **Lightweight dictionary app** on systems with limited resources
- 🔧 **Debugging addon issues** in isolation
- 📖 **Language learning** when you don't need full Anki features

## 🤝 Contributing

If you improve these scripts:

1. Test with different operating systems
2. Add better error handling
3. Improve dependency detection
4. Add more configuration options

---

**Result**: You can now run the full Anki Dictionary Addon without launching Anki! 🎉