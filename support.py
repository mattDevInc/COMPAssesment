import time
import requests
from bs4 import BeautifulSoup as bsSoup
import warnings
import pandas as pd
import os

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

categoriesUrls = [publicationsIndex] + getLinks(publicationsIndex)

def scrapePublicationWebpageLinks (urls: list, replace : str) -> dict :
    scrapedData = {}
    seenPages = set()
    sitePrefix = "https://sitescrape.awh.durham.ac.uk/comp42315/"

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

                span = publicationText.find("span")

                publicationLink = span.find("a").get("href")

                listToAdd = [title, sitePrefix + publicationLink]
                scrapedData[value].append(listToAdd)

    return scrapedData

initialScrape = scrapePublicationWebpageLinks(categoriesUrls, "type")

# extract the urls of the publications' sites
publicationUrls : str = []

for k in initialScrape :
    for n in initialScrape[k] :
        publicationUrls.append(n[1])

def scrapeAdditionalInformation (urls: list) -> dict :
    addtionalInfo = {}
    # make a request

    # find the title, find number of citations and the impact score
    for url in urls :
        time.sleep(0)
        
        infoPage = requests.get(url, verify = False)

        if (infoPage.status_code != 200) :
            print(f"Failed for link {url}, status code: {infoPage.status_code}, continuing execution for the remaining links")
            continue

        infoPageSoup = bsSoup(infoPage.content, "html.parser").body

        if (infoPageSoup == None) :
            print (f"Found nothing to parse on site {url}, continuing execution for the remaining links")
            continue

        infoPageSoupDiv = infoPageSoup.find_all("div", style = "margin-left: var(--size-marginleft)")[1]

        # check for None

        infoPageSoupP = infoPageSoupDiv.find("p")
        
        title = infoPageSoupP.text.split("by")[0].strip()

        # so that is going to have the number of citations and impact score IF the publication had any
        infoPageSoupDiv2 = infoPageSoupDiv.find_all("div")[2].text
        # then add to dictionary
        addtionalInfo[title] = infoPageSoupP.text + infoPageSoupDiv2

    return addtionalInfo
 

supportingInfo = scrapeAdditionalInformation(publicationUrls)

# convert to a nice dictionary and a dataframe

def dictConverter (dataDict : dict) -> dict :
    convertedDict = {}

    for k in dataDict :
        for n in dataDict[k] :
            convertedDict[n[0]] = k

    return convertedDict

typeDictClean = dictConverter(initialScrape)

# combine two dictionaries into one with all the raw data

def dictCombine (dict1 : dict, dict2 : dict) -> dict :
    combined = {}

    if (len(dict1) != len(dict2)) :
        return {}

    for k in dict1 :
        if (k not in dict1 or k not in dict2) :
            continue

        combined[k] = [dict1[k], dict2[k]]

    return combined

rawDataFinal = dictCombine(typeDictClean, supportingInfo)

publications = {}
authorsListConcat : str = []
publicationsData : pd.DataFrame

for k in rawDataFinal :
    title : str = k
    allData : str = rawDataFinal[k][0] + "REST " + rawDataFinal[k][1]
    remainder = ""

    initialClean = allData.translate({ord(i): None for i in '\t\r\n'})
    splitAt = initialClean.find("REST")

    typeOfPublication = initialClean[:splitAt]
    remainder = initialClean[splitAt + 4:]

    # remove title
    splitAt = initialClean.find("by")
    remainder = initialClean[splitAt + 3:]

    # find authors
    splitAt = remainder.find(" in ")
    authors = remainder[:splitAt]

    year = int(remainder[splitAt + 4:splitAt + 8])
    remainder = remainder[splitAt + 8:]

    authorsListConcat.append(authors)

    # splitting authors into a list of names
    authorList1 = authors.split(",")
    authorList2 = authorList1[-1].split("and")
    authorList1Strip = [n.strip() for n in authorList1]
    authorList2Strip = [n.strip() for n in authorList2]

    authorList = authorList1Strip[:-1] + authorList2Strip

    # split into publication venue, citations and imact factor if it got one
    splitAt = remainder.find("Citation")
    publicationVenue = remainder[:splitAt]
    remainder = remainder[splitAt + len("Citation: "):]

    split = remainder.split("##")
    citations = int(split[0])

    remainder = split[1]

    impactFactorRaw = remainder.split(": ")
    impactFactor = 0

    if (len(impactFactorRaw) > 1) :
        impactFactor = float(impactFactorRaw[1][:-1])

    publications[title] = [authorList, year, publicationVenue, typeOfPublication, citations, impactFactor]

# create a pandas dataframe from it
_data = {"title" : [k for k in publications], 
         "authors" : [n for n in authorsListConcat], 
         "year" : [publications[k][1] for k in publications], 
         "publication venue" : [publications[k][2] for k in publications],
         "impact" : [publications[k][3] for k in publications],
         "type" : [publications[k][4] for k in publications],
         "number of citations" : [publications[k][5] for k in publications]}

publicationsData = pd.DataFrame(data = _data)

# print publications dictionary to the console
def printScrapedDataToConsole () -> None :
    s = 1
    for k in publications :
        print ("---")
        print (s)
        print (f"Title: {k}\n")
        print("Authors: ")

        count = 0
        for n in publications[k][0] :
            if (len(publications[k][0]) == 1 and n == "") :
                print("No authors found")
            elif (count == len(publications[k][0]) - 1) :
                print("and " + n + ".") 
            else :
                print(n + ", ")
            count += 1
            
        print (f"\nYear published: {publications[k][1]}")
        print (f"Publication venue: {publications[k][2]}")
        print (f"Type: {publications[k][3]}")
        print (f"Number of citations: {publications[k][4]}")
        print (f"Impact Factor: {publications[k][5]}")
        print ("---\n")

        s += 1

#printScrapedDataToConsole()

# export as a csv
def exportToCsv (fileName : str, _data : pd.DataFrame) -> None :
    if (_data.empty) :
        print ("Provide correct Data Frame")
        return

    if (not isinstance(fileName, str)) :
        fileName = str(fileName)
        
    if (os.path.exists(f"./{fileName}.csv")) :
        warnings.warn ("This file already exists")
        return
    
    if (fileName[-4:] != ".csv") :
        fileName = fileName + ".csv"
    
    _data.to_csv(f"{fileName}", index = False)

def exportToTxt (fileName : str, _data : dict) -> None :
    if (not isinstance(fileName, str)) :
        fileName = str(fileName)

    if (os.path.exists(f"./{fileName}.txt")) :
        warnings.warn ("This file already exists")
        return

    if (fileName[-4:] != ".txt") :
        fileName = fileName + ".txt"

    with open (fileName, "w") as f :
        for k in _data :
            f.write(f"{k}\n")

            f.write("by")
            s = 0
            for n in _data[k][0] :
                if (s == len(_data) - 1) :
                    f.write(n)
                else :
                    f.write(n + ", ")
                s += 1

            f.write(f". {_data[k][1]}, {_data[k][2]}, {_data[k][3]}, number of citations: {_data[k][4]}, impact factor: {_data[k][5]}\n")
            f.write("\n")
            
def sortDataFrame (_data : pd.DataFrame,    sortBy : str, asc : bool = True) -> None :
    _data.sort_values(by = [sortBy], ascending = asc).head(20)