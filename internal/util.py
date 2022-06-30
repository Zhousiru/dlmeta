import os
import re
from bs4 import BeautifulSoup

import requests
import config

ID_REGEX = r"RJ(.*)(?=-)"               # for `RJ000000-xxxxx`
# ID_REGEX = r"(?<=\[)RJ(.*)(?=\])"     # for `[RJ000000]xxxxx`
# ID_REGEX = r"RJ(.*)"                  # for `RJ000000`
PROXY = {
    "http_proxy": "http://127.0.0.1:7890"
}
DLSITE_URL = "https://www.dlsite.com/home/work/=/product_id/{0}.html"


def getFileExt(filename):
    return os.path.splitext(filename)[-1][1:]


def getInfo(path):
    c = config.Config()

    basename = os.path.basename(path)
    c.id = re.search(ID_REGEX, basename).group()

    for dirpath, _, filenames in os.walk(path):
        for i in filenames:
            fileType = getFileExt(i)

            # audio
            if fileType in ("wav", "flac", "mp3"):
                aid = os.path.splitext(i)[0]
                source = os.path.join(dirpath, i)
                try:
                    c.addAudioSource(aid, source=source)
                except KeyError:
                    c.addAudioMap(aid, aid, source=[source])

            # image
            if fileType in ("png", "jpg"):
                c.imageMap.append(os.path.join(dirpath, i))

    s = requests.Session()
    s.proxies.update(PROXY)

    r = s.get(DLSITE_URL.format(c.id))
    if r.status_code != 200:
        raise RuntimeError("status_code isn't 200")

    soup = BeautifulSoup(r.text, features="html.parser")

    # Title
    rawTitle = soup.select("#work_name")[0].contents[0]
    c.title = re.sub(r'【(.*?)】', '', rawTitle)     # maybe...

    # Circle
    c.circle = soup.select("#work_maker .maker_name a")[0].contents[0]

    # CVs
    rawMeta = soup.select("#work_outline tr")
    for i in rawMeta:
        if i.select("th")[0].contents[0] == "声優":
            for j in i.select("td a"):
                c.cv.append(j.contents[0])

    # DLsite images
    for i in soup.select(".product-slider-data div"):
        c.dlImage.append("https:" + i["data-src"])

    return c
