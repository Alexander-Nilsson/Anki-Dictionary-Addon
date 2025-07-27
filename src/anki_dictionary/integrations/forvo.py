# -*- coding: utf-8 -*-
import argparse
import json
import os
import urllib
from aqt.utils import showInfo
from bs4 import BeautifulSoup
import requests
import re
import base64
from aqt.qt import QRunnable, QObject, pyqtSignal
from aqt import mw

languages = {"German" : "de",
 "Tatar" : "tt",
 "Russian" : "ru",
 "English" : "en",
 "Spanish" : "es",
 "Japanese" : "ja",
 "French" : "fr",
 "Portuguese" : "pt",
 "Polish" : "pl",
 "Dutch" : "nl",
 "Italian" : "it",
 "Mandarin Chinese" : "zh",
 "Ancient Greek" : "grc",
 "Swedish" : "sv",
 "Turkish" : "tr",
 "Arabic" : "ar",
 "Hungarian" : "hu",
 "Korean" : "ko",
 "Luxembourgish" : "lb",
 "Czech" : "cs",
 "Ukrainian" : "uk",
 "Greek" : "el",
 "Catalan" : "ca",
 "Hebrew" : "he",
 "Persian" : "fa",
 "Mari" : "chm",
 "Finnish" : "fi",
 "Cantonese" : "yue",
 "Urdu" : "ur",
 "Esperanto" : "eo",
 "Danish" : "da",
 "Bulgarian" : "bg",
 "Latin" : "la",
 "Lithuanian" : "lt",
 "Romanian" : "ro",
 "Min Nan" : "nan",
 "Norwegian Bokmål" : "no",
 "Vietnamese" : "vi",
 "Icelandic" : "is",
 "Croatian" : "hr",
 "Irish" : "ga",
 "Basque" : "eu",
 "Wu Chinese" : "wuu",
 "Belarusian" : "be",
 "Latvian" : "lv",
 "Bashkir" : "ba",
 "Kabardian" : "kbd",
 "Hindi" : "hi",
 "Slovak" : "sk",
 "Punjabi" : "pa",
 "Low German" : "nds",
 "Serbian" : "sr",
 "Hakka" : "hak",
 "Uyghur" : "ug",
 "Azerbaijani" : "az",
 "Thai" : "th",
 "Indonesian" : "ind",
 "Estonian" : "et",
 "Slovenian" : "sl",
 "Tagalog" : "tl",
 "Venetian" : "vec",
 "Northern Sami" : "sme",
 "Yiddish" : "yi",
 "Galician" : "gl",
 "Bengali" : "bn",
 "Afrikaans" : "af",
 "Welsh" : "cy",
 "Interlingua" : "ia",
 "Armenian" : "hy",
 "Chuvash" : "cv",
 "Kurdish" : "ku"}

class AnkiAudioObject:
    def __init__(self, word, id, link, votes=0):
        self.word = self.clean_filename(word)
        self.id = id
        self.link = link
        self.votes = votes
    
    def getFilename(self):
        return self.word + "-" + str(self.id) + "-" + self.votes + "." + self.link.split(".")[-1]
        
    def getBucketFilename(self):
        from anki_dictionary.utils.config import get_addon_config
        config = get_addon_config()
        fileExtension = (config.get("audioFileExtension") or self.link.split(".")[-1])
        return self.word + "-" + str(self.id) + "." + fileExtension
    
    def getVotes(self):
        return int(self.votes.replace("votes", ""))

    def clean_filename(self, filename, replacement_char='_'):
        """Remove illegal characters from a filename"""
        illegal_chars = r'[\/:*?"<>|]'
        cleaned_filename = re.sub(illegal_chars, replacement_char, filename)
        return cleaned_filename

class ForvoSignals(QObject):
    resultsFound = pyqtSignal(list)
    noResults = pyqtSignal(str) 
    finished = pyqtSignal()

class Forvo(QRunnable):
    def __init__(self, language):
        super(Forvo, self).__init__()
        self.selLang = "English" #language
        self.term = False
        self.signals = ForvoSignals()
        self.langShortCut = languages[self.selLang]
        self.session = requests.session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName

    def run(self):
        if self.term:
            resultList = [self.attemptFetchForvoLinks(self.term), self.idName]
            self.signals.resultsFound.emit(resultList)
        self.signals.finished.emit()

    def search(self, term, lang=False):
        if lang and self.selLang != lang:
            self.selLang = lang
            self.langShortCut = languages[self.selLang]
        
        # Construct Forvo API URL - removed language from path
        query = f"https://forvo.com/word/{urllib.parse.quote(term)}/"
        
        return self.forvo_search(query)

    def decodeURL(self, onclick_data):
        """Extract and decode Forvo audio URL"""
        try:
            # Parse the Play function arguments
            parts = onclick_data.split(',')
            if len(parts) >= 3:
                # Get the OGG base64 string (more reliable than MP3)
                base64_audio = parts[2].replace('\'', "").strip()
                decoded_link = base64.b64decode(base64_audio.encode('ascii')).decode('ascii')
                return f"https://audio00.forvo.com/ogg/{decoded_link}"
            return None
        except Exception as e:
            print(f"Error decoding URL: {e}")
            return None

    def generateURLS(self, content):
        """Extract audio URLs and pronunciation info from Forvo page"""
        soup = BeautifulSoup(content, 'html.parser') 
        results = []
        
        # Find the language container
        lang_container = soup.select_one(f"div#language-container-{self.langShortCut}")
        if not lang_container:
            print(f"No language container found for {self.langShortCut}")
            return results
            
        # Remove phrase pronunciations and extra info (noise)
        for noise in lang_container.select(f"ul#phrase-pronunciations-list-{self.langShortCut}-"):
            noise.decompose()
        for noise in lang_container.select("div.extra-info-container"):
            noise.decompose()
            
        # Find all play divs
        for play_div in lang_container.select("div[id^='play_']"):
            try:
                username = "Unknown"
                origin = ""
                votes = "0votes"
                
                # Try to get username info if available
                user_span = play_div.find_previous("span", class_="ofLink")
                if user_span:
                    username = user_span.text.strip()
                    
                origin_span = play_div.find_previous("span", class_="from")
                if origin_span:
                    origin = origin_span.text.strip()
                    
                # Try to get votes
                votes_span = play_div.find_previous("span", class_="num_votes")
                if votes_span:
                    votes = votes_span.text.strip() + "votes"
                
                # Get audio URL
                audio_url = self.decodeURL(play_div["onclick"])
                if audio_url:
                    # Format: [username, origin, audio_url, audio_url]
                    result_item = [username, origin, audio_url, audio_url] 
                    results.append(result_item)
                    
                    # For debugging
                    print(f"Found pronunciation by {username} from {origin}")
            except Exception as e:
                print(f"Error parsing pronunciation: {e}")
                continue
                
        return results

    def forvo_search(self, url):
        """Search Forvo and extract audio URLs"""
        try:
            print(f"Searching Forvo URL: {url}")
            response = self.session.get(url)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                results = self.generateURLS(response.text)
                print(f"Found {len(results)} pronunciations")
                return results
            else:
                print(f"Failed with status code: {response.status_code}")
                self.signals.noResults.emit(f'Forvo returned status code {response.status_code}')
        except Exception as e:
            self.signals.noResults.emit(f'Could not connect to Forvo: {str(e)}')
            print(f"Forvo error: {str(e)}")
        return []

    def attemptFetchForvoLinks(self, term):
        urls = self.search(term)
        if urls:
            return json.dumps(urls)
        self.signals.noResults.emit(f'No pronunciations found for "{term}" in {self.selLang}')
        return False