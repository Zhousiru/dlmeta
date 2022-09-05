import os
import re
import io
import subprocess
from bs4 import BeautifulSoup
from PIL import Image
from urllib.parse import urlparse

import requests
from internal import config

ID_REGEX = r"RJ(.*?)(?=-)"               # for `RJ000000-xxxxx`
# ID_REGEX = r"(?<=\[)RJ(.*?)(?=\])"     # for `[RJ000000]xxxxx`
# ID_REGEX = r"RJ(.*)"                  # for `RJ000000`
PROXY = {
    "http_proxy": "http://127.0.0.1:7890"
}
DLSITE_URL = "https://www.dlsite.com/home/work/=/product_id/{0}.html"

MP3_BITRATE = "320k"


def isLocal(url):
    parsed = urlparse(url)
    if parsed.scheme in ('file', ''):
        return os.path.exists(parsed)

    return False


def getFileExt(filename):
    return os.path.splitext(filename)[-1][1:]


def getRelPath(basePath, dirpath, filename):
    return os.path.relpath(os.path.join(dirpath, filename), basePath)


def getInfo(path):
    c = config.Config()

    # Status
    c.status = "ready"

    basename = os.path.basename(path)
    c.id = re.search(ID_REGEX, basename).group()

    for dirpath, _, filenames in os.walk(path):
        for i in filenames:
            fileType = getFileExt(i)

            # audio
            if fileType in ("wav", "flac", "mp3"):
                aid = os.path.splitext(i)[0]
                source = getRelPath(path, dirpath, i)
                try:
                    c.addAudioSource(aid, source=source)
                except KeyError:
                    c.addAudioMap(aid, aid)
                    c.addAudioSource(aid, source=source)

            # image
            if fileType in ("png", "jpg"):
                c.imageMap.append(getRelPath(path, dirpath, i))

    r = requests.get(DLSITE_URL.format(c.id), timeout=5, proxies=PROXY)
    if r.status_code != 200:
        raise RuntimeError("status_code isn't 200")

    soup = BeautifulSoup(r.text, features="html.parser")

    # Title
    rawTitle = soup.select("#work_name")[0].contents[0]
    c.title = rawTitle
    # c.title = filterFilename(re.sub(r'【(.*?)】', '', rawTitle))     # maybe...

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

    # Album Art(Default)
    c.albumArt = c.dlImage[0]

    return c


def convert(inputPath, outputPath):
    outputType = getFileExt(outputPath)

    if outputType in ["mp3", "flac"]:
        os.makedirs(os.path.dirname(outputPath), exist_ok=True)
    else:
        raise RuntimeError("invalid outputType")

    if outputType == "mp3":
        p = subprocess.Popen(r'ffmpeg -y -i "{0}" -map_metadata -1 -vn -c:a libmp3lame -b:a {1} "{2}"'.format(inputPath, MP3_BITRATE, outputPath),
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.STDOUT)
        p.wait()
    elif outputType == "flac":
        p = subprocess.Popen(r'ffmpeg -y -i "{0}" -map_metadata -1 -vn -c:a flac "{1}"'.format(inputPath, outputPath),
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.STDOUT)
        p.wait()

    return


def cropCover(imageData, resize=0):
    image = Image.open(io.BytesIO(imageData))

    width, height = image.size
    left = (width - height)/2
    top = 0
    right = (width + height)/2
    bottom = height

    image = image.crop((left, top, right, bottom))
    if resize:
        image = image.resize((resize, resize), resample=Image.BICUBIC)

    coverData = io.BytesIO()
    image.save(coverData, format="JPEG")

    return coverData.getvalue()


def filterFilename(s):
    # for Windows
    filter = {
        '\\': '＼',
        '/': '／',
        ':': '：',
        '*': '＊',
        '?': '？',
        '"': '\'\'',
        '<': '＜',
        '>': '＞',
        '|': '｜'
    }
    l = list(s)
    for i, j in enumerate(l):
        if j in filter:
            l[i] = filter[j]

    return ''.join(l)
