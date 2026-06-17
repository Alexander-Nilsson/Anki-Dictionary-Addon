# Anki Dictionary Add-on User Manual

## Table of Contents

- [Intro](#intro)
- [Installation](#installation)
  - [Anki Version](#anki-version)
  - [Add-on Installation](#add-on-installation)
  - [Dictionaries](#dictionaries)
  - [Frequency Lists](#frequency-lists)
  - [Deconjugation Support](#deconjugation-support)
  - [Customising the Definition Header](#customising-the-definition-header)
  - [Updating](#updating)
  - [Uninstalling](#uninstalling)
- [Basic Functionality](#basic-functionality)
  - [Opening the Dictionary](#opening-the-dictionary)
  - [Searching](#searching)
  - [Main Dictionary Window](#main-dictionary-window)
  - [Sending Definitions to Cards](#sending-definitions-to-cards)
  - [DuckDuckGo Images](#duckduckgo-images)
  - [Forvo Audio](#forvo-audio)
- [LLM (AI) Definitions](#llm-ai-definitions)
- [Card Exporter](#card-exporter)
  - [Export Templates](#export-templates)
  - [Opening the Exporter](#opening-the-exporter)
  - [Adding Definitions Manually](#adding-definitions-manually)
  - [Adding Images Manually](#adding-images-manually)
  - [Adding Audio Manually](#adding-audio-manually)
  - [Adding Definitions Automatically](#adding-definitions-automatically)
  - [Adding Images Automatically](#adding-images-automatically)
  - [Adding Audio Automatically](#adding-audio-automatically)
  - [Adding Cards](#adding-cards)
  - [Adding Cards Automatically](#adding-cards-automatically)
  - [Text Styling in the Exporter](#text-styling-in-the-exporter)
- [Mass Exporting Definitions](#mass-exporting-definitions)
- [Settings](#settings)
  - [Restoring Defaults](#restoring-defaults)
  - [Dictionary Groups](#dictionary-groups)
  - [Export Templates](#export-templates-1)
  - [Options](#options)
  - [Dictionaries Tab](#dictionaries-tab)
  - [LLM Settings](#llm-settings)
  - [Forvo Settings](#forvo-settings)
  - [Frequency Settings](#frequency-settings)
- [Themes](#themes)

---

## Intro

The Anki Dictionary Add-on dramatically simplifies and expedites the use of Anki for language learning. Features include:

- Multi-dictionary lookup with seven search modes
- Frequency-based word ranking (stars, rank, HSK, JLPT, CEFR)
- AI-generated definitions via LLM (OpenAI, Ollama)
- DuckDuckGo image search
- Forvo audio recordings
- One-click card export and mass batch export
- Fully customisable themes

---

## Installation

### Anki Version

This add-on requires **Anki 25.09 or later**.

You can check your Anki version:

- **Windows**: **Help → About…** from Anki's top menu bar
- **Mac**: **Anki → About Anki…** from Anki's top menu bar

### Add-on Installation

1. Download the `.ankiaddon` file from the [releases page](https://github.com/anki-dictionary-addon/releases)
2. Open Anki, go to **Tools → Add-ons**
3. Click **Install from file…**
4. Select the downloaded `.ankiaddon` file
5. Restart Anki

An **Anki Dictionary** menu will appear in Anki's top menu bar.

### Dictionaries

The add-on includes two built-in dictionaries: **DuckDuckGo Images** and **Forvo Audio**. You install additional dictionaries (Yomichan or Migaku format) for your target language.

#### Supported Formats

Two dictionary formats are supported:

1. **Yomichan Format** — ZIP files containing JSON files, used by the Yomichan browser extension
2. **Migaku Format** — a single JSON file per dictionary

Migaku format example:

```
[{"term": "example", "altterm": "", "pronunciation": "ɪɡˈzæmpəl", "definition": "a thing serving as a model", "pos": "", "examples": "", "audio": ""}]
```

Fields:

- `term` — the word being defined
- `altterm` — alternative form of the word
- `pronunciation` — pronunciation guide
- `definition` — the definition text
- `pos` — part of speech (reserved for future use)
- `examples` — example sentences (reserved for future use)
- `audio` — audio file path (reserved for future use)

#### Installing Dictionaries

##### Using the Wizard

1. Open **Anki Dictionary → Dictionary Settings → Dictionaries**
2. Click **Install Languages in Wizard**
3. Select a server (default: the add-on's dictionary server)
4. Click **Next**, choose a target language and translation language
5. Check the dictionaries you want, optionally enable frequency and conjugation data
6. Click **Next**, review your selection, then **Confirm**

##### From a ZIP File

1. In the Dictionaries tab, select a language on the left
2. Click **Install Dictionary From File**
3. Select a dictionary ZIP and optionally rename it
4. Click **OK**

##### By Adding a Language

1. In the Dictionaries tab, click **Add a Language**
2. Enter a name and click **OK**
3. Select the new language and use the wizard or file installer to add dictionaries

#### Removing Dictionaries

1. In the Dictionaries tab, select the dictionary on the left
2. Click **Remove Dictionary**

To remove an entire language (and all its dictionaries), select the language and click **Remove Language**.

### Frequency Lists

Frequency lists rank words by how common they are, displayed as star ratings (★★★★★–★) alongside search results.

#### Format

Simple list (for languages without readings):

```
["you", "I", "to", "the", "a", "and", "that", "it"]
```

List with readings (for Japanese, Chinese):

```
[["去る","サル"], ["バナナ","バナナ"], ["する","スル"]]
```

> The reading must be in katakana.

#### Installation

Frequency lists can be installed:

- **Automatically** via the wizard (when available for your language)
- **From file** — select a language, click **Install Frequency Data From File**
- **From server** — select a language, click **Install Frequency Data in Wizard**

> Install the frequency list **before** installing dictionaries for that language, or uninstall and reinstall dictionaries afterward.

### Deconjugation Support

Deconjugation mode allows you to search conjugated words and automatically find their dictionary form.

#### Conjugation Table Format

A `conjugations.json` file mapping inflected endings to dictionary form endings:

```
[{"inflected":"いなさい","dict":["う"]}, {"inflected":"いました","dict":["う"]}]
```

#### Installation

1. In the Dictionaries tab, select a language
2. Click **Install Conjugation Data in Wizard**
3. Select the language and click **Download**

### Customising the Definition Header

You can control which information appears in a definition's header and in what order.

1. Open **Dictionaries** tab in settings
2. Select a dictionary on the left
3. Click **Edit Definition Header**
4. Choose from the available orders (term, altterm, pronunciation)

### Updating

1. Go to **Tools → Add-ons**
2. Click **Check for Updates**
3. If an update is found, confirm and restart Anki

### Uninstalling

Because the add-on uses an SQLite database that cannot be deleted while in use:

1. **Disable** the add-on in **Tools → Add-ons**
2. **Restart Anki**
3. **Delete** the add-on from **Tools → Add-ons**

---

## Basic Functionality

### Opening the Dictionary

- Click **Anki Dictionary → Open Dictionary** in the top menu
- Or press **Ctrl+W** (Windows/Linux) or **⌘+W** (Mac)

![Dictionary welcome screen](images/welcome-screen.png)

The dictionary opens to the welcome screen showing available hotkeys.

**Hotkeys:**

| Action | Windows/Linux | Mac |
|---|---|---|
| Open/hide dictionary | Ctrl+W | ⌘+W |
| Search selected text | Ctrl+S | ⌘+S |
| Search in collection | Ctrl+Shift+B | ⌘+Shift+B |

### Searching

Type a word into the search bar and press **Enter** or click the search button.

![Search bar](images/search-bar.png)

You can also highlight any text in Anki and:
- Press **Ctrl+S** / **⌘+S** to search instantly
- Right-click and select **Search in Dictionary**

#### Dictionary Groups

Dictionary groups let you search a specific subset of your installed dictionaries.

Select a group from the dropdown in the toolbar:

![Dictionary group dropdown](images/dictionary-group-dropdown.png)

Default groups:

- **All** — searches every installed dictionary
- **Images** — DuckDuckGo image search
- **Forvo** — Forvo audio search
- **LLM** — AI-generated definitions
- **Language groups** — one per installed language

Custom groups can be created in settings. See [Dictionary Groups](#dictionary-groups-1).

#### Search Modes

| Mode | Description |
|---|---|
| Forward | Entries beginning with your query |
| Backward | Entries ending with your query |
| Exact | Entries matching your query exactly |
| Anywhere | Query appears anywhere in the entry |
| Definition | Query appears in the definition text |
| Example | Query appears in an example sentence |
| Pronunciation | Entries whose pronunciation matches the query (Forward-style) |

Select the mode from the dropdown next to the search bar.

![Search mode dropdown](images/search-mode-dropdown.png)

#### Tabs

Tabs let you keep results from multiple searches open. Two modes:

- **Multi-Tab** — a new tab opens for each search
- **Single-Tab** — each new search overwrites the current tab

Toggle between modes with the tab button in the toolbar. Right-click a tab to close it.

#### Deconjugation Mode

When toggled on, conjugated words are automatically deconjugated to their dictionary form before searching.

Toggle deconjugation mode with the cube icon in the toolbar.

![Deconjugation toggle](images/deconjugation-toggle.png)

Requires a conjugation table installed for the language. See [Deconjugation Support](#deconjugation-support).

#### Brackets

The add-on automatically strips bracket pairs `() [] （） 《》` and their contents from search queries, so you can copy-paste text containing furigana readings without manual cleanup.

#### Searching Your Anki Collection

Highlight a word, right-click, and select **Search Collection** to find all cards containing that word in the Card Browser.

### Main Dictionary Window

Results are grouped by dictionary. Dictionary order is determined by the selected [dictionary group](#dictionary-groups). Within a dictionary, results are sorted by frequency (highest first) when a frequency list is installed, otherwise by relevance then alphabetically.

#### Dictionary Headers

Each dictionary section has a header showing:

- **Left**: Dictionary name
- **Right**: Duplicate header toggle, output mode, field selector, previous/next dictionary buttons

![Dictionary header](images/dictionary-header.png)

#### Definition Headers

Each result entry has a header showing:

- **Left**: Term, alternative term(s), pronunciation, frequency score
- **Right**: Send to Exporter, Copy, Send to Field, next/previous entry buttons

![Definition header](images/definition-header.png)

- The **Copy** button copies the entire definition to clipboard (or only the highlighted portion)
- Header order can be customised per dictionary. See [Customising the Definition Header](#customising-the-definition-header)

#### Frequency Score

Words are ranked by star count:

| Stars | Rank range |
|---|---|
| ★★★★★ | 1st – 1,500 |
| ★★★★ | 1,500 – 5,000 |
| ★★★ | 5,000 – 15,000 |
| ★★ | 15,000 – 30,000 |
| ★ | 30,000 – 60,000 |
| _(no stars)_ | 60,000+ |

Frequency data can also display numerical rank, HSK levels, JLPT levels, and CEFR levels depending on what you have installed. Configure these in [Frequency Settings](#frequency-settings).

#### Sidebar

The sidebar lists every result from the current search. Click an entry to jump to it. Right-click a dictionary name to minimise it and hide its entries.

Toggle the sidebar with the icon next to the search button.

#### Zooming

Use the **+** and **−** buttons to increase or decrease font size in the definitions and sidebar.

#### Search History

Click the clock icon to view your search history. Double-click a term to re-search it. Click **Clear History** to erase it.

#### Themes

The add-on supports full custom theming — not just dark mode, but any colour scheme you want. See [Themes](#themes) for details.

### Sending Definitions to Cards

One of the most powerful features: send definitions directly to fields on your Anki cards.

1. Use the **Field Selector** dropdown in a dictionary header to choose which fields the add-on should target

![Field selector](images/field-selector.png)

2. Click the **Send to Field** button in a definition header

This works from the Add Cards window, Edit window, Card Browser, and Reviewer.

#### Export Target

If multiple cards are open, the add-on sends the definition to the card in the most recently used window.

Enable **Show Export Target Identifier** in settings to see which card is targeted.

#### Sending a Portion of a Definition

- If nothing is highlighted, the entire definition is sent
- If a portion is highlighted, only that portion (plus the header) is sent

#### Output Modes

| Mode | Behaviour |
|---|---|
| **Add** | Appends to existing field content |
| **Overwrite** | Replaces existing field content |
| **If Empty** | Only sends if the field is empty |

Select the mode from the dictionary header dropdown.

#### Duplicate Headers

Some dictionary entries include the term within the definition text, which can cause duplicate headers. Check the **Duplicate Header** checkbox in the dictionary header to strip the auto-generated header and avoid duplication.

### DuckDuckGo Images

The add-on can search DuckDuckGo for images related to your query, just like any other dictionary.

1. Select the **Images** dictionary group
2. Click an image to select it, click again to deselect
3. Click **Send to Field** to add the image to your card

![DuckDuckGo image results](images/image-results.png)

Configure the image search region and maximum image dimensions in [Settings](#options).

### Forvo Audio

Search Forvo for audio pronunciations and send them to your cards.

1. Select the **Forvo** dictionary group
2. Check the box next to a recording to select it
3. Click **Send to Field** to add it to your card

Configure the Forvo language in [Forvo Settings](#forvo-settings).

---

## LLM (AI) Definitions

The add-on can generate definitions using large language models (LLMs) via OpenAI-compatible APIs or Ollama.

### Setup

1. Open **Anki Dictionary → Dictionary Settings → LLM** tab
2. Enable LLM, then configure:
   - **Provider** — select OpenAI or Ollama
   - **Base URL** — API endpoint (e.g. `https://api.openai.com/v1` or `http://localhost:11434`)
   - **API Key** — your API key (not needed for local Ollama)
   - **Model** — e.g. `gpt-4o-mini`, `llama3`
   - **Prompt** — customise the instruction sent to the model
   - **Temperature** — creativity level (0.0–2.0)
   - **Timeout** — maximum wait time

### Usage

1. Search a word with a dictionary group containing dictionaries
2. Switch to the **LLM** dictionary group or wait for the LLM result to load
3. The LLM definition appears alongside regular dictionary results

The LLM receives the word, its part of speech, and optionally its frequency and HSK level as context.

![LLM result](images/llm-result.png)

### Troubleshooting

- **Connection errors** — verify the base URL and API key
- **Timeouts** — increase the timeout setting or use a faster model
- **Empty responses** — the model may have refused; try different phrasing in the prompt

---

## Card Exporter

The Card Exporter is a dedicated window for building cards with multiple definitions, images, and audio before adding them to your collection.

### Export Templates

An Export Template maps card content types (sentence, term, definition, image, audio) to fields on a specific note type.

| Field | Purpose |
|---|---|
| **Notetype** | The note type to use |
| **Sentence Field** | Where the sentence goes |
| **Word Field** | Where the looked-up term goes |
| **Secondary Field** | Secondary subtitle line |
| **User Notes** | Free-form notes |
| **Image Field** | Screenshots, images |
| **Audio Field** | Audio recordings |
| **Tags** | Tags added to the card |

You must create at least one template before using the exporter. See [Export Templates](#export-templates-1) in Settings.

### Opening the Exporter

- Click the **Send to Exporter** (Anki icon) button in any definition header
- Or use the hotkey **Ctrl+C+Alt** (Windows/Linux) / **⌘+C+Ctrl** (Mac)

When opened via hotkey, any selected text is sent to the sentence field. If nothing is selected, clipboard contents are used.

![Card exporter window](images/card-exporter.png)

### Adding Definitions Manually

Click the **Send to Exporter** button in a definition header. The definition appears in the exporter's definition list.

- If no text is highlighted, the entire entry is sent
- If text is highlighted, only that portion plus the header is sent

Remove a definition by clicking the **X** button.

### Adding Images Manually

1. Copy an image to your clipboard
2. In the exporter, press **Ctrl+Shift+V** / **⌘+Shift+V** to paste

> Only one image can be added per card. Adding a second replaces the first.

### Adding Audio Manually

1. Copy an MP3 file to your clipboard
2. In the exporter, press **Ctrl+Shift+V** / **⌘+Shift+V** to paste

> Only one audio file can be added manually per card. Adding a second replaces the first.

### Adding Definitions Automatically

1. In the exporter, check **Automatically Add Definitions**
2. Click **Automatic Definition Settings**
3. Select up to three dictionaries and a maximum number of definitions per dictionary
4. Click **Save Settings**

Definitions are populated when you create the card.

### Adding Images Automatically

1. In the exporter, check **Automatically Add Definitions**
2. Click **Automatic Definition Settings**
3. Select **DuckDuckGo Images** from one of the dropdowns
4. Set the maximum number of images
5. Click **Save Settings**

### Adding Audio Automatically

1. In the exporter, check **Automatically Add Definitions**
2. Click **Automatic Definition Settings**
3. Select **Forvo** from one of the dropdowns
4. Set the maximum number of audio files
5. Click **Save Settings**

### Adding Cards

Once all content is ready, click the **Add** button or press **Ctrl+Enter** / **⌘+Enter** to create the card.

### Adding Cards Automatically

Check **Add Extension Cards Automatically** to bypass the Add button — the card is created as soon as all content is populated.

### Text Styling in the Exporter

Style text in the Sentence, Secondary, and User Notes fields:

| Shortcut | Effect |
|---|---|
| Ctrl+B / ⌘+B | Bold |
| Ctrl+I / ⌘+I | Italic |
| Ctrl+U / ⌘+U | Underline |

---

## Mass Exporting Definitions

Add definitions to multiple cards at once from the Card Browser.

1. Select cards in the Card Browser
2. Go to **Edit → Export Definitions**
3. Configure:
   - **Input Field** — the field containing the word to look up (must be a single, unconjugated term)
   - **Output Field** — where definitions will be written
   - **Dictionaries** — up to 3 dictionaries to source definitions from
   - **Output Mode** — Add, Overwrite, or If Empty
   - **Max Per Dict** — maximum definitions per dictionary
4. Click **Execute**

![Mass export dialog](images/mass-export.png)

---

## Settings

Open settings: **Anki Dictionary → Dictionary Settings** or the gear icon in the dictionary window.

![Settings window](images/settings-window.png)

### Restoring Defaults

Click **Restore Defaults** in the bottom-left corner of the settings window to reset all settings. The main dictionary window must be closed and reopened for changes to take effect.

### Dictionary Groups

Groups control which dictionaries are searched and in what order.

#### Adding a Group

1. Click **Add Dictionary Group**
2. Enter a unique name
3. Check the dictionaries to include (numbers indicate search order)
4. Optionally select a font for the group
5. Click **Save**

#### Editing a Group

1. Click **Edit** next to the group
2. Make your changes
3. Click **Save**

> You cannot rename a group after creation. Remove and re-create it.

#### Removing a Group

Click the **X** button next to the group and confirm.

### Export Templates

Templates are blueprints for the Card Exporter.

#### Adding a Template

1. Click **Add Export Template**
2. Select a note type and map each field (Sentence, Word, User Notes, Image, Audio, Tags)
3. Click **Save**

#### Editing a Template

1. Click **Edit** next to the template
2. Make changes and click **Save**

#### Removing a Template

Click the **X** button next to the template and confirm.

### Options

| Setting | Description |
|---|---|
| **Max Total Search Results** | Maximum results returned per search |
| **Max Dictionary Search Results** | Maximum results per dictionary |
| **Highlight Searched Term** | Highlight the matched term in definitions |
| **Show Export Target Identifier** | Show which window will receive the definition |
| **Enable Tooltips** | Show tooltips on buttons |
| **Always on Top** | Keep the dictionary window on top |
| **Image Search Region** | DuckDuckGo region for image results |
| **Maximum Image Width** | Max width for images sent to fields |
| **Maximum Image Height** | Max height for images sent to fields |
| **Surround Term Brackets** | Characters placed around terms (front and back) |
| **Font Size (Definitions)** | Base font size for definition text |
| **Font Size (Sidebar)** | Base font size for sidebar entries |

### Dictionaries Tab

Manage installed dictionaries and languages:

- **Install Languages in Wizard** — guided dictionary installation
- **Install Dictionary From File** — install from a ZIP
- **Add a Language** — create a new language group
- **Remove Language / Remove Dictionary** — uninstall
- **Install Frequency Data** — from file or server
- **Install Conjugation Data** — from file or server
- **Edit Definition Header** — customise per-dictionary header order

![Dictionaries tab](images/dictionaries-tab.png)

### LLM Settings

| Setting | Description |
|---|---|
| **Enabled** | Toggle LLM feature on/off |
| **Base URL** | API endpoint (OpenAI or Ollama) |
| **API Key** | Authentication key |
| **Model** | Model name (e.g. `gpt-4o-mini`, `llama3`) |
| **Prompt** | Custom instruction sent to the model |
| **Temperature** | Response creativity (0.0–2.0) |
| **Timeout** | Seconds before giving up |
| **Keep Alive** | Ollama model keep-alive duration |
| **Stream** | Stream response as it's generated |

### Forvo Settings

| Setting | Description |
|---|---|
| **Enabled** | Toggle Forvo feature on/off |
| **Language** | Which language to search for recordings |

### Frequency Settings

| Setting | Description |
|---|---|
| **Show Stars** | Display star rating |
| **Star Character** | Custom star symbol |
| **Star Thresholds** | Configure rank ranges for each star level |
| **Show Rank** | Display numerical rank |
| **Show HSK** | Display HSK level (for Chinese) |
| **HSK Mode** | HSK 2.0, 3.0, or both |

---

## Themes

The add-on supports full custom theming — not just dark/light mode but any colour scheme.

The active theme is stored in `user_files/themes/active.json`. You can create and edit themes visually using the **Theme Editor**.

To open the theme editor: click the theme icon in the dictionary window toolbar.

### Creating a Theme

1. Open the Theme Editor
2. Start from a preset or customise each UI element's colour
3. Save the theme

### Applying a Theme

Saved themes appear in the theme dropdown in the dictionary window. Select one to apply it immediately.

### Theme Components

Themes control colours for:

- Background and text colours for all UI panels
- Dictionary and definition headers
- Search bar and sidebar
- Buttons and icons
- Links and highlighted text

![Theme editor](images/theme-editor.png)
