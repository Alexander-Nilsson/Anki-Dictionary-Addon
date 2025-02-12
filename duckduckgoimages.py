# -*- coding: utf-8 -*-
# 
import argparse
import json
import os
import urllib
from aqt.utils import  showInfo
from bs4 import BeautifulSoup
import requests
import time
import re
from aqt.qt import  QRunnable, QObject, pyqtSignal
from urllib.parse import quote_plus

# Add at bottom of file
countryCodes = {
    'Japan': 'countryJP',
    'US': 'countryUS',
    # Add more as needed
}

class DuckDuckGoSignals(QObject):
    resultsFound = pyqtSignal(tuple)
    noResults = pyqtSignal()

class DuckDuckGo(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = DuckDuckGoSignals()
        self.term = ""
        self.idName = ""
        
    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName
        
    def run(self):
        try:
            results = self.search(self.term)
            if results and len(results) > 0:
                self.signals.resultsFound.emit((results, self.idName))
            else:
                self.signals.noResults.emit()
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            self.signals.noResults.emit()
            
    # Update search method in DuckDuckGo class
    def search(self, term):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://duckduckgo.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        try:
            # First get token
            search_url = f"https://duckduckgo.com/"
            response = session.get(search_url, timeout=10)
            session.cookies.update(response.cookies)
            
            # Now search
            params = {
                'q': term,
                'iax': 'images',
                'ia': 'images'
            }
            response = session.get(search_url, params=params, timeout=10)
            
            # Extract vqd token
            vqd = re.search(r'vqd=[\d-]+', response.text)
            if not vqd:
                return []
                
            # Make API request
            api_url = "https://duckduckgo.com/i.js"
            params = {
                'l': 'wt-wt',
                'o': 'json',
                'q': term,
                'vqd': vqd.group().split('=')[1],
                'f': ',,,',
                'p': '-1',
            }
            
            response = session.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                return [img['image'] for img in response.json()['results']]
                
        except Exception as e:
            print(f"Error: {str(e)}")
        return []


class GoogleSignals(QObject):
    resultsFound = pyqtSignal(list)
    noResults = pyqtSignal(str)
    finished = pyqtSignal()

class Google(QRunnable):

    
    # finished = pyqtSignal()

    def __init__(self):
        super(Google, self).__init__()
        self.GOOGLE_SEARCH_URL = "https://www.google.com/search"
        self.term = False
        self.signals = GoogleSignals()
        self.initSession()

    def initSession(self):
        self.session = requests.session()
        self.session.headers.update(
            {
                "User-Agent": 'Mozilla/5.0 (Linux; Android 9; SM-G960F '\
'Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) '\
'Version/4.0 Chrome/74.0.3729.157 Mobile Safari/537.36'
            }
        )

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName

    def run(self):
        if self.term:
            resultList = self.getPreparedResults(self.term, self.idName)
            self.signals.resultsFound.emit(resultList)
        self.signals.finished.emit()

    def search(self, keyword, maximum, region = False):
        query = self.query_gen(keyword) 

        return self.image_search(query, maximum, region)

    def query_gen(self, keyword):
        page = 0
        while True:
            queryDict = {"q": keyword, "tbm": "isch"}
            if self.safeSearch:
                queryDict["safe"] = "active"
            params = urllib.parse.urlencode(
                queryDict
            )
            if self.region == 'Japan':
                url = 'https://www.google.co.jp/search'
            else:
                url = self.GOOGLE_SEARCH_URL
            yield url + "?" + params
            page += 1

    def setSearchRegion(self, region):
        self.region = region


    def setSafeSearch(self, safe):
        self.safeSearch = safe

    def getResultsFromRawHtml(self, html):
        pattern = r"AF_initDataCallback[\s\S]+AF_initDataCallback\({key: '[\s\S]+?',[\s\S]+?data:(\[[\s\S]+\])[\s\S]+?<\/script><script id="
        matches = re.findall(pattern, html)
        results = []
        try:
            if len(matches) > 0:
                decoded = json.loads(matches[0])[31][0][12][2]
                for d in decoded:
                    d1 = d[1]
                    if d1:
                        results.append(str(d1[3][0]))   
            return results
        except:
            return []

    def getHtml(self, term):
        images = self.search(term, 80)
        if not images or len(images) < 1:
            return 'No Images Found. This is likely due to a connectivity error.'
        firstImages = []
        tempImages = []
        for idx, image in enumerate(images):
            tempImages.append(image) 
            if len(tempImages) > 2 and len(firstImages) < 1:
                firstImages += tempImages
                tempImages = []
            if len(tempImages) > 2 and len(firstImages) > 1:
                break
        html = '<div class="googleCont">'
        for img in firstImages:
            html+= '<div class="imgBox"><div onclick="toggleImageSelect(this)" data-url="'+ img +'" class="googleHighlight"></div><img class="googleImage"  ankiDict="' + img + '"></div>'
        html += '</div><div class="googleCont">'
        for img in tempImages:
            html+= '<div class="imgBox"><div onclick="toggleImageSelect(this)" data-url="'+ img +'" class="googleHighlight"></div><img class="googleImage"  ankiDict="' + img + '"></div>'
        html += '</div><button class="imageLoader" onclick="loadMoreImages(this, \\\'' + '\\\' , \\\''.join(self.getCleanedUrls(images)) +'\\\')">Load More</button>'
        return html

    def getPreparedResults(self, term, idName):
        html = self.getHtml(term)
        return [html, idName]
    
    def getCleanedUrls(self, urls):
        return [x.replace('\\', '\\\\') for x in urls]

    def image_search(self, query_gen, maximum, region = False):
        results = []
        if not region:
            region = countryCodes[self.region]
        total = 0
        finished = False
        while True:
            try:
                count = 0
                while not finished:
                    count+= 1
                    hr = self.session.get(next(query_gen)+ '&ijn=0&cr=' + region)
                    html = hr.text
                    if not html and not '<!doctype html>' in html:
                        if count > 5:
                            finished = True
                            break
                        self.initSession()
                        time.sleep(.1)
                    else:
                        finished = True
                        break
            except:
                self.signals.noResults.emit('The Google Image Dictionary could not establish a connection. Please ensure you are connected to the internet and try again. If you will be without internet for some time, consider using a template that does not include the Google Images Dictionary in order to prevent this message appearing everytime a search is performed. ')
                return False
            results = self.getResultsFromRawHtml(html)
            if len(results) == 0:
                soup = BeautifulSoup(html, "html.parser")
                elements = soup.select(".rg_meta.notranslate")
                jsons = [json.loads(e.get_text()) for e in elements]

                image_url_list = [js["ou"] for js in jsons]
                if not len(image_url_list):
                    
                    break
                elif len(image_url_list) > maximum - total:
                    results += image_url_list[: maximum - total]
                    break
                else:
                    results += image_url_list
                    total += len(image_url_list)
            else:
                break
        return results

def search(target, number):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument("-t", "--target", help="target name", type=str, required=True)
    parser.add_argument(
        "-n", "--number", help="number of images", type=int, required=True
    )
    parser.add_argument(
        "-d", "--directory", help="download location", type=str, default="./data"
    )
    parser.add_argument(
        "-f",
        "--force",
        help="download overwrite existing file",
        type=bool,
        default=False,
    )

    args = parser.parse_args()

    data_dir = "./data"
    target_name = target

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, target_name), exist_ok=args.force)

    google = Google()

    results = google.search(target_name, maximum=number)
    return results
