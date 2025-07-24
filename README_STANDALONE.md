# Standalone Dictionary Application

This is a standalone version of the Anki Dictionary Addon that can run independently without Anki. It provides dictionary lookup functionality with a web-based interface.

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Demo Data** (optional):
   ```bash
   python create_demo_data.py
   ```

3. **Run the Application**:
   ```bash
   python standalone_dictionary.py
   ```

4. **Access the Web Interface**:
   Open your browser and go to `http://localhost:12000`

## 📁 Files Overview

### Core Files
- **`standalone_dictionary.py`** - Main web application with Flask server
- **`standalone_image_search.py`** - Standalone image search functionality
- **`create_demo_data.py`** - Creates sample dictionary data for testing
- **`requirements.txt`** - Python dependencies

### Generated Files
- **`dictionaries.sqlite`** - SQLite database containing dictionary entries
- **`templates/index.html`** - Web interface template (auto-generated)

## 🔧 Features

### ✅ Working Features
- **Dictionary Search**: Search through dictionary entries with term and definition matching
- **Web Interface**: Clean, responsive web interface for dictionary lookup
- **Multi-language Support**: Support for multiple dictionaries (English, Japanese, etc.)
- **Database Storage**: SQLite database for storing dictionary entries
- **RESTful API**: JSON API endpoints for programmatic access

### 🚧 Limited Features
- **Image Search**: Basic DuckDuckGo image search (may have limited results due to API changes)
- **Audio Pronunciation**: Not implemented in standalone version
- **Card Export**: Not available (Anki-specific feature)

### ❌ Removed Features
- **Anki Integration**: All Anki-specific functionality removed
- **Global Hotkeys**: System-wide hotkeys not implemented
- **Forvo Integration**: Audio pronunciation service not included
- **Theme Editor**: Advanced theming not available

## 🛠 Technical Details

### Architecture
- **Backend**: Flask web server with SQLite database
- **Frontend**: HTML/CSS/JavaScript with responsive design
- **Database**: SQLite with tables for dictionaries and entries
- **Search**: Full-text search across terms and definitions

### API Endpoints
- `GET /` - Main web interface
- `GET /search?term=<word>` - Search dictionary and images
- `GET /static/<file>` - Static file serving

### Database Schema
```sql
-- Dictionaries table
CREATE TABLE dictionaries (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dictionary entries table
CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    dictionary_id INTEGER,
    term TEXT NOT NULL,
    definition TEXT,
    pronunciation TEXT,
    frequency INTEGER,
    FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id)
);
```

## 📊 What Was Extracted from the Original Addon

### Successfully Extracted
1. **Dictionary Database Logic** (`dictdb.py` → `StandaloneDictDB`)
2. **Image Search Functionality** (`duckduckgoimages.py` → `StandaloneImageSearch`)
3. **Core Search Logic** (term matching and lookup)
4. **Basic UI Structure** (converted to web interface)

### Adapted for Standalone Use
1. **Removed Anki Dependencies**: All `aqt` and `anki` imports removed
2. **Web Interface**: Replaced Qt GUI with HTML/CSS/JavaScript
3. **Simplified Database**: Basic SQLite schema without Anki-specific features
4. **Standalone Server**: Flask web server instead of Anki addon architecture

### Not Included
1. **Card Creation**: Anki-specific card export functionality
2. **Advanced Theming**: Complex theme system with Qt widgets
3. **System Integration**: Global hotkeys and clipboard monitoring
4. **Audio Features**: Forvo integration and audio playback
5. **Advanced Dictionary Formats**: Complex dictionary file parsing

## 🔄 Comparison with Original Addon

| Feature | Original Addon | Standalone Version |
|---------|----------------|-------------------|
| Dictionary Search | ✅ Full featured | ✅ Basic search |
| Image Search | ✅ Google/DuckDuckGo | 🚧 DuckDuckGo only |
| Card Export | ✅ To Anki | ❌ Not available |
| Audio Pronunciation | ✅ Forvo integration | ❌ Not available |
| Global Hotkeys | ✅ System-wide | ❌ Not available |
| Themes | ✅ Advanced theming | 🚧 Basic CSS |
| Multi-language | ✅ Full support | ✅ Basic support |
| Database | ✅ Complex schema | ✅ Simplified schema |
| User Interface | ✅ Qt desktop app | ✅ Web interface |

## 🚀 Extending the Standalone Version

### Adding New Dictionaries
1. Insert into `dictionaries` table:
   ```sql
   INSERT INTO dictionaries (name, language) VALUES ('My Dictionary', 'en');
   ```

2. Add entries:
   ```sql
   INSERT INTO entries (dictionary_id, term, definition, pronunciation) 
   VALUES (1, 'example', 'A representative sample', 'ɪɡˈzæmpəl');
   ```

### Customizing the Interface
- Edit the HTML template in `standalone_dictionary.py`
- Modify CSS styles in the `<style>` section
- Add JavaScript functionality as needed

### Adding New Features
- Extend the `StandaloneDictionary` class
- Add new Flask routes for additional functionality
- Implement new search algorithms or data sources

## 🐛 Known Issues

1. **Image Search**: Limited results due to DuckDuckGo API changes
2. **Unicode Handling**: Some encoding issues with non-ASCII characters in URLs
3. **Performance**: Not optimized for large dictionaries
4. **Security**: Development server not suitable for production use

## 📝 License

This standalone version maintains the same license as the original Anki Dictionary Addon (GNU AGPLv3).

## 🤝 Contributing

Feel free to contribute improvements:
1. Fix image search functionality
2. Add audio pronunciation support
3. Improve Unicode handling
4. Add more dictionary formats
5. Enhance the web interface

---

**Note**: This standalone version demonstrates that the core dictionary functionality can indeed be extracted from the Anki addon and run independently. While some features are simplified or missing, the essential dictionary lookup capability is preserved and accessible through a modern web interface.