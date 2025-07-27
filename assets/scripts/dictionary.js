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
 * Load image and Forvo HTML content
 */
function loadImageForvoHtml(html, idName) {
    document.getElementById(idName).innerHTML = html;
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
    text = text.replace(/<br>/g, '---NL---');
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
 * Export audio to Anki
 */
function getAudioExport(event, dictName) {
    var termTitle = event.target.parentElement.parentElement.parentElement
    var defBlock = termTitle.nextElementSibling;
    var toExport = [];
    var word = cleanTermDef(termTitle.querySelector('.terms').innerHTML)
    var audio = defBlock.getElementsByTagName('input');
    for (var i = 0; i < audio.length; i++) {
        if (audio[i].checked) {
            toExport.push(audio[i].parentElement.getElementsByClassName('forvo-play')[0].currentSrc);
        }
    }
    pycmd('audioExport:' + word + '◳◴' + JSON.stringify(toExport));
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
    if (dictName == 'Google Images') {
        getImageExport(event, dictName)
    } else if (dictName == 'Forvo') {
        getAudioExport(event, dictName)
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
 * Send audio to field
 */
function getAudioForField(event, dictName) {
    var defBlock = event.target.parentElement.parentElement.nextElementSibling;
    var toExport = [];
    var audio = defBlock.getElementsByTagName('input');
    for (var i = 0; i < audio.length; i++) {
        if (audio[i].checked) {
            toExport.push(audio[i].parentElement.getElementsByClassName('forvo-play')[0].currentSrc);
        }
    }
    pycmd('sendAudioToField:' + JSON.stringify(toExport));
}

/**
 * Main send to field function
 */
function sendToField(event, dictName) {
    if (dictName == 'Google Images') {
        getImageForField(event, dictName)
    } else if (dictName == 'Forvo') {
        getAudioForField(event, dictName)
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
 * Add custom font
 */
function addCustomFont(font, name) {
    var cf = document.getElementById('customFonts');
    cf.innerHTML += ' @font-face { font-family: ' + name + '; src: url(user_files/fonts/' + font + ');}\n '
}

/**
 * Scale font size
 */
function scaleFont(plus) {
    var fs = document.getElementById('fontSpecs');
    if (plus) {
        fefs += 2;
        dbfs += 2;
    } else {
        fefs -= 2;
        dbfs -= 2;
    }
    fs.innerHTML = '.foundEntriesList{font-size:' + fefs + 'px;}.termPronunciation,.definitionBlock{font-size:' + dbfs + 'px;  white-space: pre-line;}.ankiExportButton img{height:' + dbfs + 'px; width:' + dbfs + 'px;}'
    pycmd('saveFS:' + fefs + ':' + dbfs);
}

/**
 * Show checkboxes dropdown
 */
function showCheckboxes(event) {
    var el = event.target;
    if (expanded !== el) {
        hideCheckBoxes();
        showCheckBoxes(el);
    } else {
        hideCheckBoxes();
    }
    event.stopPropagation();
}

/**
 * Show specific checkbox
 */
function showCheckBoxes(el) {
    var checkboxes = el.nextSibling;
    el.classList.add('currentCheckbox')
    checkboxes.classList.add('displayedCheckBoxes');
    expanded = el;
}

/**
 * Hide checkboxes
 */
function hideCheckBoxes() {
    var boxes = document.getElementsByClassName("displayedCheckBoxes");
    if (boxes) {
        for (var i = 0; i < boxes.length; i++) {
            boxes[i].classList.remove('displayedCheckBoxes');
        }
    }
    if (current) {
        var current = document.getElementsByClassName("currentCheckbox");
        for (var i = 0; i < current.length; i++) {
            current[i].classList.remove('currentCheckbox');
        }
    }
    expanded = false;
}

/**
 * Toggle image selection
 */
function toggleImageSelect(img) {
    if (img.classList.contains('selectedImage')) {
        img.classList.remove('selectedImage');
    } else {
        img.classList.add('selectedImage');
    }
}

/**
 * Load more images
 */
function loadMoreImages(button, ...rest) {
    var urls = rest;
    var defBox = button.parentElement;
    var imageCount = defBox.getElementsByClassName('googleImage').length;
    if (imageCount > urls.length) return;
    var toLoad = urls.slice(imageCount, imageCount + 3);
    loadNewImages(toLoad, defBox, button);
}

/**
 * Load new images into the interface
 */
function loadNewImages(toLoad, defBox, button) {
    console.log('URLs to load:', toLoad);
    var cont = document.createElement('div')
    cont.classList.add('googleCont')
    var html = '<div class="googleCont">'
    for (var i = 0; i < toLoad.length; i++) {
        img = toLoad[i]
        console.log('Processing URL:', img);

        html += `
        <div class="imgBox">
            <div onclick="toggleImageSelect(this)" 
                 data-url="${img}" 
                 class="googleHighlight"></div>
            <img class="googleImage" 
                 src="${img}" 
                 src="${img}"
                 onerror="console.error('Failed to load:', this.src)"
                 onload="console.log('Loaded:', this.src)">
        </div>`;
    }
    html += '</div>';
    cont.innerHTML = html;
    defBox.insertBefore(cont, button);
    setTimeout(function () {
        var w = button.closest('#defBox');
        w.scrollTop = button.offsetTop - 500;
    }, 650)
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
 * Handle duplicate header changes
 */
function handleDupChange(cb, className) {
    var check;
    var dictName = cb.parentElement.parentElement.parentElement.getElementsByClassName('dictionaryTitle')[0].textContent.replace(/ /g, '_');
    var checkbs = document.getElementsByClassName(className);
    if (cb.checked) {
        check = '1';
        for (var i = 0; i < checkbs.length; i++) {
            checkbs[i].checked = true
        }
    } else {
        check = '0';
        for (var i = 0; i < checkbs.length; i++) {
            checkbs[i].checked = false
        }
    }
    pycmd('setDup:' + check + '◳' + dictName);
}

/**
 * Body click event listener
 */
document.body.addEventListener("click", function (ev) {
    handleBodyClick(ev);
}, false);

/**
 * Handle field checkbox changes
 */
function handleFieldCheck(el) {
    var dictName = el.parentElement.parentElement.dataset.dictname;
    if (dictName != 'Google Images') {
        dictName = dictName.replace(/ /g, '_');
    }
    var conts = document.querySelectorAll('.fieldCheckboxes[data-dictname="' + dictName + '"')
    var fields = {};
    fields.dictName = dictName;
    fields.fields = [];
    for (var i = 0; i < conts.length; i++) {
        var checks = conts[i].getElementsByTagName('INPUT');
        var selCount = 0;
        for (var x = 0; x < checks.length; x++) {
            if (el.value === checks[x].value) {
                checks[x].checked = el.checked
            }
            if (checks[x].checked === true) {
                selCount++;
                if (fields.fields.indexOf(checks[x].value) == -1) {
                    fields.fields.push(checks[x].value);
                }
            }
        }
        var header = '&nbsp;' + selCount + " Selected";
        if (selCount === 0) {
            header = '&nbsp;Select Fields ▾';
        }
        conts[i].parentElement.firstChild.innerHTML = header;
    }
    pycmd('fieldsSetting:' + JSON.stringify(fields));
}

/**
 * Handle add type checkbox changes
 */
function handleAddTypeCheck(el) {
    var radios = document.getElementsByClassName(el.classList[1]);
    var dictName = el.parentElement.parentElement.dataset.dictname;
    var addType = { 'name': dictName, 'type': el.value };
    for (var i = 0; i < radios.length; i++) {
        if (radios[i].value === el.value) {
            radios[i].checked = true;
            var cont = radios[i].closest('.overwriteSelectCont');
            var title = cont.getElementsByClassName('overwriteSelect')[0]
            title.innerHTML = '&nbsp;' + el.parentElement.textContent;
        }
    }
    hideCheckBoxes();
    pycmd('overwriteSetting:' + JSON.stringify(addType));
}

/**
 * Open/close sidebar
 */
function openSidebar() {
    if (sidebarOpened === false) {
        var sidebars = document.getElementsByClassName('definitionSideBar');
        for (var i = 0; i < sidebars.length; i++) {
            sidebars[i].classList.add('sidebarOpenedSideBar')
        }
        var mains = document.getElementsByClassName('mainDictDisplay');
        for (var i = 0; i < mains.length; i++) {
            mains[i].classList.add('sidebarOpenedDisplay')
        }
        sidebarOpened = true;
    } else {
        var sidebars = document.getElementsByClassName('definitionSideBar');
        for (var i = 0; i < sidebars.length; i++) {
            sidebars[i].classList.remove('sidebarOpenedSideBar')
        }
        var mains = document.getElementsByClassName('mainDictDisplay');
        for (var i = 0; i < mains.length; i++) {
            mains[i].classList.remove('sidebarOpenedDisplay')
        }
        sidebarOpened = false;
    }
}

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
    var height = document.getElementById('tabs').offsetHeight;
    var wHeight = window.innerHeight;
    var defB = document.getElementById('defBox');
    defB.style.top = height + 'px';
    defB.style.height = wHeight - height + 'px';
    var sidebars = document.getElementsByClassName('definitionSideBar');
    for (var i = 0; i < sidebars.length; i++) {
        sidebars[i].style.height = wHeight - 14 - height + 'px';
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
            newTab = curTabs[curtabs.length - 1]
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
    } else {
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
 * Load more Forvo pronunciations
 */
function loadMoreForvos(button) {
    var forvoParent = button.parentElement;
    var forvos = forvoParent.getElementsByClassName('hidden-forvo');

    if (forvos.length < 1) {
        return;
    }
    var max = 3;
    if (forvos.length < 3) {
        max = forvos.length;
    }
    for (var i = 0; i < max; i++) {
        forvos[0].classList.remove('hidden-forvo')
    }
    return
}

/**
 * Load Forvo dictionary content
 */
function loadForvoDict(content, id = false) {
    if (id) {
        content = document.getElementById(id);
    }
    var forvos = content.getElementsByClassName('forvo');

    if (forvos.length > 0) {
        var forvo = forvos[0];
        var urls = JSON.parse(forvo.dataset.urls)
        var html = '<div class="forvo-flex">'
        var max = 3;
        if (urls.length < max) max = urls.length;
        for (var i = 0; i < max; i++) {
            html += '<div class="forvo-play-box" ><input type="checkbox"><audio class="forvo-play" controls controlsList="nodownload"><source src="' + urls[i][3] + '" type="audio/mpeg"><source src="' + urls[i][2] + '" type="audio/mpeg"></audio></input><div class="forvo-name-origin"><div class="forvo-name"><b>' + urls[i][0] + '</b></div> <div class="forvo-origin">' + urls[i][1] + '</div></div></div>';
        }
        var buttonHtml = ''
        if (urls.length > 6) {
            for (var i = 6; i < urls.length; i++) {
                html += '<div class="forvo-play-box hidden-forvo" ><input type="checkbox"><audio class="forvo-play" controls controlsList="nodownload"><source src="' + urls[i][3] + '" type="audio/mpeg"><source src="' + urls[i][2] + '" type="audio/mpeg"></audio></input><div class="forvo-name-origin"><div class="forvo-name"><b>' + urls[i][0] + '</b></div> <div class="forvo-origin">' + urls[i][1] + '</div></div></div>';
            }
            buttonHtml = '<button class="forvoLoader" onclick="loadMoreForvos(this)">Load More</button>'
        }
        html += buttonHtml + '</div>'
        forvo.innerHTML = html;
    }
}

/**
 * Add new tab to the interface
 */
function addNewTab(html, term = 'Welcome', singleTabMode = false, forvo = false) {
    if (singleTabMode) {
        var newTab = fetchCurrentTab(term);
        if (newTab) {
            var content = fetchCurrentTabContent(html);
            addSidebarListeners(content);
            document.getElementById("defBox").scrollTop = 0;
        }
    }
    if (!newTab) {
        attemptCloseFirstTab()
        var newTab = fetchNewTab(term);
        var content = fetchNewTabContent(html);
        document.getElementById("defBox").appendChild(content);
        tabBar = document.getElementById("tabs")
        tabBar.appendChild(newTab);
        tabBar.scrollLeft = 99999
        removeFocus();
        tabs.push([newTab, content, 0])
        addSidebarListeners(content);
        focusTab(newTab);
    }

    if (sidebarOpened) {
        content.getElementsByClassName('definitionSideBar')[0].classList.add('sidebarOpenedSideBar')
        content.getElementsByClassName('mainDictDisplay')[0].classList.add('sidebarOpenedDisplay')
    }
    resizer();
    if (nightMode) {
        applyIcon(nightMode)
    }
    loadForvoDict(content)
}

/**
 * Apply icons based on night mode
 */
function applyIcon(night) {
    var imgConts = document.getElementsByClassName('ankiExportButton');
    if (night) {
        for (var i = imgConts.length - 1; i >= 0; i--) {
            imgConts[i].getElementsByTagName('img')[0].src = 'assets/icons/blackAnki.png'
        }
    } else {
        for (var i = imgConts.length - 1; i >= 0; i--) {
            imgConts[i].getElementsByTagName('img')[0].src = 'assets/icons/anki.png'
        }
    }
}

/**
 * Toggle night mode
 */
function nightModeToggle(night) {
    var cf = document.getElementById('nightModeCss');
    if (night) {
        nightMode = true
        cf.innerHTML = 'body, .definitionSideBar, .defTools{color: white !important;background: black !important;} .termPronunciation{background: black !important;border-top:1px solid white !important;border-bottom:1px solid white !important;} .overwriteSelect, .fieldSelect, .overwriteCheckboxes, .fieldCheckboxes{background: black !important;} .fieldCheckboxes label:hover, .overwriteCheckboxes label:hover {background-color:   #282828 !important;} #tabs{background:black !important; color: white !important;} .tablinks:hover{background:gray !important;} .tablinks{color: white !important;} .active{background-image: linear-gradient(#272828, black); border-left: 1px solid white !important;border-right: 1px solid white !important;} .dictionaryTitleBlock{border-top: 2px solid white;border-bottom: 1px solid white;} .imageLoader, .forvoLoader{background-image: linear-gradient(#272828, black); color: white; border: 1px solid gray;}.definitionSideBar{border: 2px solid white;}';
        applyIcon(nightMode);
    } else {
        nightMode = false
        cf.innerHTML = '';
        applyIcon(nightMode);
    }
}

/**
 * Copy selected text
 */
function copyText() {
    var copied = window.getSelectionText()
    if (copied) pycmd('clipped:' + copied.replace('&lt', '<').replace('&gt;', '>'));
}

/**
 * Keyboard event handling
 */
document.documentElement.addEventListener('keydown', function (e) {
    if (e.keyCode === 67 && e.ctrlKey) {
        copyText();
        e.preventDefault();
    }
}, false)

/**
 * Wait for pycmd to load and signal ready
 */
function awaitPycmdToLoad() {
    let awaitPycmd = setInterval(() => {
        if (pycmd) {
            clearInterval(awaitPycmd);
            console.log("AnkiDictionaryLoaded");
            pycmd('AnkiDictionaryLoaded')
        }
    }, 5);
}

/**
 * Initialize when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', awaitPycmdToLoad, false);
