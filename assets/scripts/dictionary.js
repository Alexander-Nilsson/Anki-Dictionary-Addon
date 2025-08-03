/**
 * Dictionary Interface JavaScript
 * Main JavaScript functionality for the Anki Dictionary Addon interface
 */

var fefs = 12, dbfs = 22;
var hresizeInt;
var mouseX;
var nightMode = false;
var expanded = false;
var sidebarOpened = false;
var tabs = [];

/**
 * Load image HTML content
 * @param {string} html - The HTML content to load
 * @param {string} idName - The ID name for the content
 */
/**
 * Load image HTML content
 * @param {string} html - The HTML content to load
 * @param {string} idName - The ID name for the content
 */
function loadImageHtml(html, idName) {
    try {
        var target = document.getElementById(idName);
        if (target) {
            target.innerHTML = html;
        } else {
            console.warn('Target element not found:', idName);
        }
    } catch (error) {
        console.error('Error in loadImageHtml:', error);
    }
}

/**
 * Get selected text from the document
 */
function getSelectionText() {
    var text = "";
    if (window.getSelection) {
        text = window.getSelection().toString();
    }
    if (text === "") return false;
    return text.replace(/\n✂➠\n▲\n▼\n/g, '\n');
}

/**
 * Get term definition text for copying/exporting
 */
function getTermDefText(el, clip = false) {
    var term = el.parentElement.parentElement;
    var def = term.nextElementSibling;
    var rep = '<br>';
    if (clip) rep = '\n';
    return cleanTermDef(term.innerHTML, rep) + rep + cleanTermDef(def.innerHTML, rep);
}

/**
 * Clean term definition text
 */
function cleanTermDef(text, rep) {
    // Handle all variants of <br> tags (case insensitive, with or without closing slash)
    text = text.replace(/<br\s*\/?>/gi, '---NL---');
    text = text.replace(/<[^>]+>/g, '').replace('✂', '').replace('➠', '').replace('▲', '').replace('▼', '');
    return text.replace(/---NL---/g, rep);
}

/**
 * Get definition word and clean definition text
 */
function getDefinitionWord(dictEl, termBody, termTitle) {
    var definition = cleanTermDef(termBody.innerHTML, '<br>');
    var dupHeader = dictEl.querySelector('.dupHeadCB input').checked;
    var terms = termTitle.getElementsByClassName('mainword');
    var stars = termTitle.getElementsByClassName('starcount')[0].textContent;
    var word = '';
    var term1 = terms[0].textContent;
    var term2 = terms[1].textContent;
    if (term1 != '' && term2 != '') {
        word = term1 + ', ' + term2;
    } else if (term1 != '') {
        word = term1;
    } else if (term2 != '') {
        word = term2;
    }
    if (!dupHeader) {
        var wordPron = termTitle.querySelector('.tpCont').textContent;
        definition = wordPron + '<br>' + definition;
    } else {
        if (definition.indexOf('】') !== -1) {
            definition = definition.replace(/】/, '】' + stars + ' ');
        } else {
            definition = definition.replace(/<br>/, stars + '<br>');
        }
    }
    return [word, definition];
}

/**
 * Display entry in the dictionary interface
 */
function displayEntry(entry) {
    console.log("Raw definitions:", entry.definitions);
    var formattedDefinitions = entry.definitions.join('<br>');
    console.log("Formatted definitions:", formattedDefinitions);
    var html = `<div class="definitionBlock">
                    <b>${entry.word}</b><br>
                    ${formattedDefinitions}
                </div>`;
    console.log("Generated HTML:", html);
    var defBox = document.getElementById('defBox');
    defBox.innerHTML += html;
}

/**
 * Export definitions to Anki
 */
function getDefExport(event, dictName) {
    var definition = getSelectionText();
    var termTitle = event.target.parentElement.parentElement.parentElement;
    var termBody = termTitle.nextElementSibling;
    var dictionaryElement = termTitle.previousElementSibling;
    while (!dictionaryElement.classList.contains('dictionaryTitleBlock')) {
        dictionaryElement = dictionaryElement.previousElementSibling;
    }
    var wordDefinition = getDefinitionWord(dictionaryElement, termBody, termTitle);
    if (!definition) {
        definition = wordDefinition[1];
    } else {
        definition = cleanTermDef(termTitle.textContent) + '<br>' + definition.replace(/\n/g, '<br>');
    }
    pycmd('addDef:' + dictName + '◳◴' + wordDefinition[0] + '◳◴' + definition);
}

/**
 * Export images to Anki
 */
function getImageExport(event, dictName) {
    var termTitle = event.target.parentElement.parentElement.parentElement
    var defBlock = termTitle.nextElementSibling;
    var word = cleanTermDef(termTitle.querySelector('.terms').innerHTML)
    var selImgs = defBlock.getElementsByClassName('selectedImage')
    var urls = [];

    if (selImgs.length > 0) {
        for (var i = 0; i < selImgs.length; i++) {
            urls.push(selImgs[i].dataset.url)
        }
        pycmd('imgExport:' + word + '◳◴' + JSON.stringify(urls));
    }
}

/**
 * Main export function - routes to appropriate export method
 */
function ankiExport(ev, dictName) {
    if (dictName == 'Images') {
        getImageExport(event, dictName)
    } else {
        getDefExport(event, dictName.replace(/ /g, '_'))
    }
}

/**
 * Get word pronunciation
 */
function getWordPron(dictEl, termBody, termTitle) {
    var dupHeader = dictEl.querySelector('.dupHeadCB input').checked;
    var terms = termTitle.getElementsByClassName('mainword');
    var stars = termTitle.getElementsByClassName('starcount')[0].textContent;
    var word = '';
    var term1 = terms[0].textContent;
    var term2 = terms[1].textContent;
    if (term1 != '' && term2 != '') {
        word = term1 + ', ' + term2
    } else if (term1 != '') {
        word = term1
    } else if (term2 != '') {
        word = term2
    }

    wordPron = termTitle.querySelector('.tpCont').textContent + '\n';
    return wordPron;
}

/**
 * Copy text to clipboard
 */
function clipText(ev) {
    var definition = getSelectionText();
    var termTitle = event.target.parentElement.parentElement
    var termBody = termTitle.nextElementSibling
    var dictionaryElement = termTitle.previousElementSibling
    while (!dictionaryElement.classList.contains('dictionaryTitleBlock')) {
        dictionaryElement = dictionaryElement.previousElementSibling
    }
    if (!definition) {
        var wordDefinition = getDefinitionWord(dictionaryElement, termBody, termTitle)
        definition = wordDefinition[1]
    } else {
        var wordDefinition = getWordPron(dictionaryElement, termBody, termTitle)
        definition = wordDefinition + definition
    }
    pycmd('clipped:' + definition.replace('&lt', '<').replace('&gt;', '>'));
}

/**
 * Send definition to field
 */
function getDefForField(event, dictName) {
    var definition = getSelectionText();
    var termTitle = event.target.parentElement.parentElement
    if (!definition) {
        var termBody = termTitle.nextElementSibling
        var dictionaryElement = termTitle.previousElementSibling
        while (!dictionaryElement.classList.contains('dictionaryTitleBlock')) {
            dictionaryElement = dictionaryElement.previousElementSibling
        }
        var wordDefinition = getDefinitionWord(dictionaryElement, termBody, termTitle)
        definition = wordDefinition[1]
    } else {
        definition = cleanTermDef(termTitle.textContent) + '<br>' + definition.replace(/\n/g, '<br>')
    }
    pycmd('sendToField:' + dictName + '◳◴' + definition);
}

/**
 * Send image to field
 */
function getImageForField(event, dictName) {
    var defBlock = event.target.parentElement.parentElement.nextElementSibling;
    var selImgs = defBlock.getElementsByClassName('selectedImage')
    var urls = []
    if (selImgs.length > 0) {
        for (var i = 0; i < selImgs.length; i++) {
            urls.push(selImgs[i].dataset.url)
        }
        pycmd('sendImgToField:' + JSON.stringify(urls));
    }
}

/**
 * Main send to field function
 */
function sendToField(event, dictName) {
    if (dictName == 'Images') {
        getImageForField(event, dictName)
    } else {
        getDefForField(event, dictName.replace(/ /g, '_'))
    }
}

/**
 * Navigate dictionary entries
 */
function navigateDict(ev, next, def = false) {
    var dict = ev.target.parentElement.parentElement.parentElement;
    var wanted = 'dictionaryTitleBlock';
    var w = dict.closest('#defBox');
    if (def) {
        wanted = 'termPronunciation'
    }
    if (next) {
        var nextEl = dict;
        while (nextEl = nextEl.nextElementSibling) {
            if (nextEl.classList && nextEl.classList.contains(wanted)) {
                w.scrollTop = nextEl.offsetTop;
                break;
            }
        }
    } else if (parseInt(dict.dataset.index) > 0) {
        var nextEl = dict;
        while (nextEl = nextEl.previousElementSibling) {
            if (nextEl.classList && nextEl.classList.contains(wanted)) {
                w.scrollTop = nextEl.offsetTop;
                break;
            }
        }
    }
}

/**
 * Navigate definitions
 */
function navigateDef(ev, next) {
    navigateDict(ev, next, true);
}

/**
 * Mouse movement tracking
 */
document.onmousemove = updateMouseX
function updateMouseX(e) {
    mouseX = (window.Event) ? e.pageX : event.clientX + (document.documentElement.scrollLeft ? document.documentElement.scrollLeft : document.body.scrollLeft);
}

/**
 * Window resize handling
 */
window.addEventListener('mouseup', stopResize);

/**
 * Horizontal resize functionality
 */
function hresize(ev) {
    document.getElementById('userSelect').innerHTML = 'body{-webkit-touch-callout: none;  -webkit-user-select: none;-khtml-user-select: none;-moz-user-select: none;-ms-user-select: none;user-select: none;}';
    var sidebar = ev.target.parentElement;
    var ws = document.getElementById('widthSpecs');
    hresizeInt = setInterval(function () {
        ws.innerHTML = '.sidebarOpenedDisplay{margin-left:' + mouseX + 'px !important;}.sidebarOpenedSideBar{width:' + mouseX + 'px;}';
    }, 10);
}

/**
 * Stop resize operation
 */
function stopResize() {
    clearInterval(hresizeInt);
    document.getElementById('userSelect').innerHTML = '';
    if (mouseX > window.innerWidth) {
        document.getElementById('widthSpecs').innerHTML = '.sidebarOpenedDisplay{margin-left:' + (innerWidth - 20) + 'px !important;}.sidebarOpenedSideBar{width:' + (innerWidth - 20) + 'px;}';
    } else if (mouseX < 0) {
        document.getElementById('widthSpecs').innerHTML = '.sidebarOpenedDisplay{margin-left:20px !important;}.sidebarOpenedSideBar{width:20px;}';
    }
}

/**
 * Add custom font for languages that need special fonts
 */
function addCustomFont(fontFile, fontName) {
    try {
        // console.log('Adding custom font:', fontName, 'from', fontFile);
        
        // Create a new style element for the font
        const style = document.createElement('style');
        style.textContent = `
            @font-face {
                font-family: '${fontName}';
                src: url('${fontFile}');
            }
        `;
        document.head.appendChild(style);
        
    } catch (error) {
        console.error('Error adding custom font:', error);
    }
}

/**
 * Load new images into the interface from a new search
 */
function loadNewImages(htmlContent, button) {
    console.log('loadNewImages called with:', typeof htmlContent, htmlContent ? htmlContent.length : 0);
    
    var defBox = button.parentElement;
    
    if (htmlContent && htmlContent.trim() !== '') {
        // Create a temporary div to parse the HTML
        var tempDiv = document.createElement('div');
        try {
            tempDiv.innerHTML = htmlContent;
        } catch(e) {
            console.error('Error parsing HTML:', e);
            button.textContent = 'Error loading images';
            button.disabled = true;
            return;
        }
        
        // Get all new image boxes
        var newImages = tempDiv.querySelectorAll('.imgBox');
        
        if (newImages.length > 0) {
            // Find the existing image container
            var existingContainer = defBox.querySelector('.imageCont.horizontal-layout');
            
            if (existingContainer) {
                // Append new images to existing container
                newImages.forEach(function(imgBox) {
                    existingContainer.appendChild(imgBox.cloneNode(true));
                });
            } else {
                // Create new container if none exists
                var newContainer = document.createElement('div');
                newContainer.className = 'imageCont horizontal-layout';
                newImages.forEach(function(imgBox) {
                    newContainer.appendChild(imgBox.cloneNode(true));
                });
                defBox.insertBefore(newContainer, button);
            }
            
            // Re-enable the button
            button.disabled = false;
            button.textContent = 'Load More';
            
            // Scroll to show new images
            setTimeout(function () {
                var w = button.closest('#defBox');
                if (w) {
                    w.scrollTop = button.offsetTop - 500;
                }
            }, 300);
        } else {
            // No more images found
            button.textContent = 'No more images';
            button.disabled = true;
        }
    } else {
        // No more images found
        button.textContent = 'No more images';
        button.disabled = true;
    }
}

/**
 * Handle body click events
 */
function handleBodyClick(ev) {
    var targ = ev.target;
    var classes = targ.classList;
    if (expanded && classes && (!classes.contains('inCheckBox'))) {
        hideCheckBoxes();
    }
}

/**
 * Body click event listener
 */
document.body.addEventListener("click", function (ev) {
    handleBodyClick(ev);
}, false);

/**
 * Navigate to dictionary or entry
 */
function navDictOrEntry() {
    var w = this.closest('#defBox');
    var mD = this.closest('.definitionSideBar').nextSibling;
    var idx = this.dataset.index;
    if (this.nodeName === 'LI') {
        var el = mD.querySelectorAll('.termPronunciation[data-index="' + idx + '"]')[0];
    } else {
        var el = mD.querySelectorAll('.dictionaryTitleBlock[data-index="' + idx + '"]')[0];
    }
    w.scrollTop = el.offsetTop;
}

/**
 * Toggle dictionary entries
 */
function toggleDictEntries(ev) {
    ev.preventDefault();
    var ol = this.nextSibling;
    if (ol.classList.contains('hiddenOl')) {
        ol.classList.remove('hiddenOl')
    } else {
        ol.classList.add('hiddenOl')
    }
}

/**
 * Add sidebar listeners
 */
function addSidebarListeners(parent) {
    var sb = parent.getElementsByClassName('definitionSideBar')[0];
    if (!sb) return;
    var titles = sb.getElementsByClassName('listTitle');
    for (var i = 0; i < titles.length; i++) {
        titles[i].addEventListener("click", navDictOrEntry);
        titles[i].addEventListener("contextmenu", toggleDictEntries);
    }
    var items = sb.getElementsByTagName("LI");
    for (var i = 0; i < items.length; i++) {
        items[i].addEventListener("click", navDictOrEntry);
    }
}

/**
 * Remove focus from tabs
 */
function removeFocus() {
    var scroll = document.getElementById('defBox').scrollTop
    var i, tabContent, tablinks;
    tabContent = document.getElementsByClassName("tabContent");
    for (i = 0; i < tabContent.length; i++) {
        tabContent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("active");
    for (i = 0; i < tablinks.length; i++) {
        if (tabs.length > 0) {
            index = parseInt(tablinks[i].dataset.index);
            tabs[index][2] = scroll
        }
        tablinks[i].classList.remove("active");
    }
}

/**
 * Focus a specific tab
 */
function focusTab(tab) {
    var index = parseInt(tab.dataset.index)
    tab.classList.add("active");
    tabs[index][1].style.display = "block";
    document.getElementById('defBox').scrollTop = tabs[index][2]
}

/**
 * Load tab event handler
 */
function loadTab() {
    removeFocus();
    focusTab(this);
    resizer();
    pycmd('updateTerm:' + this.textContent);
}

/**
 * Close tab event handler
 */
function closeTab(ev) {
    ev.preventDefault();
    var index = parseInt(this.dataset.index);
    closeTabAtIndex(index);
    return false;
}

/**
 * Close all tabs
 */
function closeAllTabs() {
    for (let i = tabs.length; i > 0; i--) {
        closeTabAtIndex(i - 1)
    }
}

/**
 * Close tab at specific index
 */
function closeTabAtIndex(index) {
    focusAnotherTab(index);
    tabs[index][0].remove();
    tabs[index][1].remove();
    tabs[index] = false;
    cleanTabsArray();
}

/**
 * Clean up tabs array
 */
function cleanTabsArray() {
    var empty = true;
    for (var i = 0; i < tabs.length; i++) {
        if (tabs[i]) {
            empty = false;
            break;
        }
    }
    if (empty) tabs = [];
}

/**
 * Focus another tab when closing current
 */
function focusAnotherTab(index) {
    var counter, toFocus, tablink = document.getElementsByClassName("active")[0];
    if (parseInt(tablink.dataset.index) === index) {
        toFocus = false;
        counter = index;
        while (!toFocus && counter > 0) {
            counter = counter - 1;
            toFocus = tabs[counter]
        }
        if (toFocus) {
            focusTab(toFocus[0]);
            return;
        }
        counter = index;
        while (!toFocus && counter < tabs.length - 1) {
            counter = counter + 1;
            toFocus = tabs[counter]
        }
        if (toFocus) {
            focusTab(toFocus[0]);
            return;
        }
    }
}

/**
 * Resize interface elements
 */
function resizer() {
    try {
        const tabsElement = document.getElementById('tabs');
        const defBox = document.getElementById('defBox');
        
        if (!tabsElement || !defBox) {
            // If elements don't exist, skip resizing
            return;
        }
        
        // Check if the element has valid dimensions before accessing offsetHeight
        let height = 0;
        if (tabsElement.offsetHeight !== undefined && tabsElement.offsetHeight !== null) {
            height = tabsElement.offsetHeight;
        }
        
        const wHeight = window.innerHeight || 600; // Fallback height
        
        defBox.style.top = height + 'px';
        defBox.style.height = Math.max(wHeight - height, 100) + 'px'; // Ensure minimum height
        
        const sidebars = document.getElementsByClassName('definitionSideBar');
        for (let i = 0; i < sidebars.length; i++) {
            if (sidebars[i] && sidebars[i].style) {
                sidebars[i].style.height = Math.max(wHeight - 14 - height, 100) + 'px';
            }
        }
    } catch (error) {
        console.error('Error in resizer:', error);
    }
}

/**
 * Window resize event
 */
window.onresize = resizer;
resizer();

/**
 * Fetch current tab
 */
function fetchCurrentTab(term) {
    var newTab;
    var curTabs = document.getElementsByClassName('active')
    if (curTabs.length > 0) {
        newTab = curTabs[0]
        newTab.innerHTML = term;
    } else {
        var curTabs = document.getElementsByClassName('tablinks')
        if (curTabs.length > 0) {
            newTab = curTabs[curTabs.length - 1]
            newTab.innerHTML = term;
        } else {
            newTab = false;
        }
    }
    return newTab;
}

/**
 * Fetch current tab content
 */
function fetchCurrentTabContent(html) {
    var contents = document.getElementsByClassName('tabContent')
    var content;
    if (contents.length > 0) {
        for (var i = contents.length - 1; i >= 0; i--) {
            if (contents[i].style.display == "block") {
                content = contents[i];
                content.innerHTML = html;
                break;
            }
        }
        // If no active content found, use the last one
        if (!content && contents.length > 0) {
            content = contents[contents.length - 1];
            content.innerHTML = html;
        }
    }
    
    if (!content) {
        content = fetchNewTabContent(html)
    }
    return content
}

/**
 * Create new tab
 */
function fetchNewTab(term) {
    var newTab = document.createElement("BUTTON");
    newTab.innerHTML = term;
    newTab.classList.add("tablinks");
    newTab.dataset.index = tabs.length;
    newTab.addEventListener("click", loadTab);
    newTab.addEventListener("contextmenu", closeTab);
    return newTab
}

/**
 * Create new tab content
 */
function fetchNewTabContent(html) {
    var content = document.createElement("DIV");
    content.classList.add('tabContent');
    content.innerHTML = html;
    content.dataset.index = tabs.length;
    return content
}

/**
 * Attempt to close first tab if it's Welcome
 */
function attemptCloseFirstTab() {
    var curTabs = document.getElementsByClassName('active');
    if (curTabs.length == 1) {
        if (curTabs[0].textContent == 'Welcome') {
            closeTabAtIndex(0);
        }
    }
}

/**
 * Load more images for a search term
 * Called when the Load More button is clicked
 */
function loadMoreImages(button, term) {
    try {
        // console.log('loadMoreImages called with term:', term);
        
        // Disable the button during loading
        button.disabled = true;
        button.textContent = 'Loading...';
        
        // Call Python backend to get more images
        if (typeof pycmd !== 'undefined') {
            pycmd('getMoreImages::' + term);
        } else {
            console.error('pycmd not available');
            button.disabled = false;
            button.textContent = 'Load More';
        }
    } catch (error) {
        console.error('Error in loadMoreImages:', error);
        button.disabled = false;
        button.textContent = 'Load More';
    }
}

/**
 * Add new images to the existing image container
 * Called from Python after more images are loaded
 */
function appendNewImages(html) {
    try {
        // console.log('appendNewImages called');
        
        // Find the image container
        const container = document.querySelector('.imageCont.horizontal-layout');
        if (!container) {
            console.error('Image container not found');
            return false;
        }
        
        // Store the current scroll position
        const scrollContainer = container.closest('#defBox') || container.parentElement;
        const currentScrollTop = scrollContainer ? scrollContainer.scrollTop : 0;
        
        // Create a temporary div to parse the new HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Find new images in the temporary div
        const newImages = tempDiv.querySelectorAll('.imgBox');
        
        // Append new images to the existing container
        newImages.forEach(img => {
            container.appendChild(img);
        });
        
        // Re-enable the Load More button if it exists in the new HTML
        const newButton = tempDiv.querySelector('.imageLoader');
        if (newButton) {
            // Replace the old button with the new one
            const oldButton = document.querySelector('.imageLoader');
            if (oldButton) {
                oldButton.parentNode.replaceChild(newButton.cloneNode(true), oldButton);
            }
        } else {
            // If no new button found, re-enable existing button
            const existingButton = document.querySelector('.imageLoader');
            if (existingButton) {
                existingButton.disabled = false;
                existingButton.textContent = 'Load More';
            }
        }
        
        // Ensure the container maintains scrolling capability
        if (scrollContainer) {
            scrollContainer.style.overflowY = 'auto';
            scrollContainer.style.overflowX = 'hidden';
        }
        
        // Trigger a resize to ensure layout is correct
        if (typeof resizer === 'function') {
            resizer();
        }
        
        // Ensure scrolling is still enabled on the container
        const parentScrollContainer = container.closest('#defBox') || 
                               container.closest('.mainDictDisplay') || 
                               document.getElementById('defBox');
        if (parentScrollContainer) {
            parentScrollContainer.style.overflowY = 'auto';
            parentScrollContainer.style.overflowX = 'hidden';
        }
        
        // console.log('Successfully appended', newImages.length, 'new images');
        return true;
    } catch (error) {
        console.error('Error in appendNewImages:', error);
        
        // Re-enable the Load More button on error
        const button = document.querySelector('.imageLoader');
        if (button) {
            button.disabled = false;
            button.textContent = 'Load More';
        }
        return false;
    }
}

/**
 * Wait for pycmd to load and signal ready
 */
function awaitPycmdToLoad() {
    let awaitPycmd = setInterval(() => {
        if (pycmd) {
            clearInterval(awaitPycmd);
            // console.log("AnkiDictionaryLoaded");
            pycmd('AnkiDictionaryLoaded')
        }
    }, 5);
}

/**
 * Initialize when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', awaitPycmdToLoad, false);

/**
 * Add a new tab with search results
 */
function addNewTab(html, term, singleTab) {
    try {
        // Handle undefined parameters gracefully
        if (typeof html === 'undefined' || html === null) {
            console.warn('addNewTab called with undefined html, skipping');
            return;
        }
        
        if (typeof term === 'undefined' || term === null) {
            console.warn('addNewTab called with undefined term');
            term = '';
        }
        
        if (typeof singleTab === 'undefined') {
            singleTab = true; // Default to single tab mode
        }
        
        // Convert singleTab to boolean if it's a string
        if (typeof singleTab === 'string') {
            singleTab = singleTab === 'true';
        }
        
        // Ensure required DOM elements exist
        let tabsContainer = document.getElementById('tabs');
        let defBox = document.getElementById('defBox');
        
        if (!tabsContainer || !defBox) {
            console.error('Required tab elements not found in DOM');
            return;
        }
        
        if (singleTab) {
            // Single tab mode: replace current content
            let currentTab = fetchCurrentTab(term);
            let currentContent = fetchCurrentTabContent(html);
            
            if (!currentTab) {
                // No tabs exist, create the first one
                let newTab = fetchNewTab(term);
                let newContent = fetchNewTabContent(html);
                
                tabsContainer.appendChild(newTab);
                defBox.appendChild(newContent);
                
                tabs.push([newTab, newContent, 0]);
                focusTab(newTab);
            }
        } else {
            // Multi-tab mode: create new tab
            attemptCloseFirstTab();
            
            let newTab = fetchNewTab(term);
            let newContent = fetchNewTabContent(html);
            
            tabsContainer.appendChild(newTab);
            defBox.appendChild(newContent);
            
            tabs.push([newTab, newContent, 0]);
            removeFocus();
            focusTab(newTab);
        }
        
        // Initialize any interactive elements
        initializeInteractiveElements();
        
        // Call resizer to ensure proper layout
        if (typeof resizer === 'function') {
            setTimeout(() => {
                try {
                    resizer();
                } catch (error) {
                    console.warn('Resizer error (non-critical):', error);
                }
            }, 100);
        }
        
    } catch (error) {
        console.error('Error in addNewTab:', error);
    }
}

/**
 * Initialize interactive elements after content is loaded
 */
function initializeInteractiveElements() {
    // Initialize image selection
    initializeImageSelection();
    
    // Initialize sidebar listeners
    addSidebarListeners(document);
    
    // Initialize any other interactive elements as needed
    // This can be expanded based on what functionality is needed
}

/**
 * Initialize image selection functionality
 */
function initializeImageSelection() {
    const imageBoxes = document.querySelectorAll('.imgBox');
    imageBoxes.forEach(box => {
        const highlight = box.querySelector('.imageHighlight');
        if (highlight) {
            // Re-attach click handlers if needed
            highlight.onclick = function() {
                toggleImageSelect(this);
            };
        }
    });
}

/**
 * Toggle image selection
 */
function toggleImageSelect(element) {
    try {
        const imgBox = element.closest('.imgBox');
        if (!imgBox) return;
        
        if (imgBox.classList.contains('selected')) {
            imgBox.classList.remove('selected');
            element.style.background = 'rgba(0,0,0,0.3)';
        } else {
            imgBox.classList.add('selected');
            element.style.background = 'rgba(66, 165, 245, 0.7)';
        }
    } catch (error) {
        console.error('Error in toggleImageSelect:', error);
    }
}

/**
 * Handle checkbox changes for field selection
 */
function handleFieldCheck(checkbox) {
    try {
        const container = checkbox.closest('.fieldCheckboxes');
        if (!container) return;
        
        const dictName = container.getAttribute('data-dictname');
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        const selectedFields = [];
        
        checkboxes.forEach(cb => {
            if (cb.checked) {
                selectedFields.push(cb.value);
            }
        });
        
        // Send the selection back to Python
        if (typeof pycmd !== 'undefined') {
            const data = {
                dictName: dictName,
                fields: selectedFields
            };
            pycmd('fieldsSetting:' + JSON.stringify(data));
        }
        
    } catch (error) {
        console.error('Error in handleFieldCheck:', error);
    }
}

/**
 * Handle add type checkbox changes
 */
function handleAddTypeCheck(radio) {
    try {
        const dictName = radio.className.match(/radio([^\s]+)/)?.[1];
        if (!dictName) return;
        
        const value = radio.value;
        
        // Send the selection back to Python
        if (typeof pycmd !== 'undefined') {
            const data = {
                name: dictName,
                type: value
            };
            pycmd('overwriteSetting:' + JSON.stringify(data));
        }
        
    } catch (error) {
        console.error('Error in handleAddTypeCheck:', error);
    }
}

/**
 * Show/hide checkboxes for field/type selection
 */
function showCheckboxes(event) {
    try {
        const target = event.target;
        const container = target.parentElement;
        const checkboxContainer = container.querySelector('.fieldCheckboxes, .overwriteCheckboxes');
        
        if (checkboxContainer) {
            if (checkboxContainer.style.display === 'none' || !checkboxContainer.style.display) {
                checkboxContainer.style.display = 'block';
            } else {
                checkboxContainer.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error in showCheckboxes:', error);
    }
}

/**
 * Handle duplicate header change
 */
function handleDupChange(checkbox, className) {
    try {
        const container = checkbox.closest('.dupHeadCB');
        const dictName = container?.getAttribute('data-dictname');
        
        if (dictName && typeof pycmd !== 'undefined') {
            const value = checkbox.checked ? 1 : 0;
            pycmd('setDup:' + value + '◳' + dictName);
        }
    } catch (error) {
        console.error('Error in handleDupChange:', error);
    }
}

/**
 * Scale font size
 */
function scaleFont(increase) {
    try {
        const currentSize = parseInt(getComputedStyle(document.body).fontSize) || 14;
        const newSize = increase ? currentSize + 1 : Math.max(currentSize - 1, 8);
        
        document.body.style.fontSize = newSize + 'px';
        
        // Save the font size
        if (typeof pycmd !== 'undefined') {
            pycmd('saveFS:' + newSize + ':' + newSize);
        }
        
    } catch (error) {
        console.error('Error in scaleFont:', error);
    }
}

/**
 * Open/close sidebar
 */
function openSidebar() {
    try {
        const sidebar = document.querySelector('.definitionSideBar');
        
        if (sidebar) {
            // Check both computed style and inline style to determine visibility
            const computedStyle = window.getComputedStyle(sidebar);
            const isHidden = computedStyle.display === 'none' || sidebar.style.display === 'none';
            
            if (isHidden) {
                // Show sidebar
                sidebar.style.display = 'block';
                sidebar.classList.add('sidebarOpenedSideBar');
                
                // Apply layout adjustment to main content
                const mainDisplay = document.querySelector('.mainDictDisplay');
                if (mainDisplay) {
                    mainDisplay.classList.add('sidebarOpenedDisplay');
                }
            } else {
                // Hide sidebar
                sidebar.style.display = 'none';
                sidebar.classList.remove('sidebarOpenedSideBar');
                
                // Remove layout adjustment from main content
                const mainDisplay = document.querySelector('.mainDictDisplay');
                if (mainDisplay) {
                    mainDisplay.classList.remove('sidebarOpenedDisplay');
                }
            }
        }
    } catch (error) {
        console.error('Error in openSidebar:', error);
    }
}

/**
 * Wait for pycmd to load and signal ready
 */
