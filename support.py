import time
import requests
from bs4 import BeautifulSoup as bsSoup

publicationsIndex = "https://sitescrape.awh.durham.ac.uk/comp42315/publicationfull_year_characteranimation.htm"

def getLinks (url: str) -> list :
    sitePrefix = "https://sitescrape.awh.durham.ac.uk/comp42315/"

    if (not isinstance(url, str)) :
        print("The URL needs to be a string!")
        return []

    # wait a little so we don't overload the server
    time.sleep(2)
    publicationsIndex = requests.get(url, verify = False)

    if (publicationsIndex.status_code != 200) :
        print (f"Error; status code returned: {publicationsIndex.status_code}")
        return []

    publicationsIndexSoup = bsSoup(publicationsIndex.content, "html.parser").body

    if (publicationsIndexSoup == None) :
        print ("Nothin to parse on the site")
        return []

    publicationLinksA = publicationsIndexSoup.find("p", class_ = "TextOption").find_all("a")

    if (publicationLinksA == None) :
        print ("No links found")
        return []
    
    links = [sitePrefix + n.get("href") for n in publicationLinksA]

    if (links[0] == None) :
        print("No links found")
        return []

    return links

publicationLinks = [publicationsIndex] + getLinks(publicationsIndex)
print ("hello world")

def scrapeAdditionalInformation (urls: list, replace : str) -> dict :
    scrapedData = {}
    seenPages = set()
    n = 0

    for url in urls :
        uniqueValuesOnPage = []
        time.sleep(0)
        url = url.replace("year", replace)

        page = requests.get(url, verify = False)

        if (page.status_code != 200) :
            print(f"Failed for link {url}, status code: {page.status_code}, continuing execution for the remaining links")
            continue

        pageSoup = bsSoup(page.content, "html.parser").body

        if (pageSoup == None) :
            print (f"Found nothing to parse on site {url}, continuing execution for the remaining links")
            continue

        pageSoupDiv = pageSoup.find("div", id = "divBackground")

        if (pageSoupDiv == None) :
            print (f"Couldn't find {replace} on the page {url}, continuing execution for the remaining links")
            continue

        pageSoupP = pageSoupDiv.find_all("p", class_ = "TextOption")

        if (pageSoupP == None) :
            print (f"Couldn't find {replace} on the page {url}, continuing execution for the remaining links")
            continue

        paragraphWithInfo = pageSoupP [2]

        valueTags = paragraphWithInfo.find_all("a")

        uniqueValuesOnPage = [n.text for n in valueTags]

        if (len(uniqueValuesOnPage) == 0) :
            print (f"Couldn't find {replace} on the page {url}, continuing execution for the remaining links")
            continue

        for value in uniqueValuesOnPage :
            currentH2 = pageSoup.find("h2", id = value)

            if (currentH2 == None) :
                continue

            if (value not in scrapedData) :
                scrapedData [value] = []

            div = currentH2.findNext()

            publicationsWithThisInfo = div.find_all("div", class_ = "w3-cell-row")

            if (publicationsWithThisInfo == None) :
                continue

            for publication in publicationsWithThisInfo :
                publicationText = publication.find("div", class_ = "w3-container w3-cell w3-mobile w3-cell-middle")

                title = publicationText.text.split("by")[0].strip()

                if (title in seenPages) :
                    continue

                seenPages.add(title)
                scrapedData[value].append(title)

    return scrapedData

typeDict = scrapeAdditionalInformation(publicationLinks, "type")
print (typeDict)
print(typeDict.keys())

referencesDict = scrapeAdditionalInformation(publicationLinks, "citation")
print (referencesDict)
print (referencesDict.keys())




