import os
import re
import io
import subprocess
from bs4 import BeautifulSoup
from PIL import Image

import requests
from internal import config

ID_REGEX = r"RJ(.*)(?=-)"               # for `RJ000000-xxxxx`
# ID_REGEX = r"(?<=\[)RJ(.*)(?=\])"     # for `[RJ000000]xxxxx`
# ID_REGEX = r"RJ(.*)"                  # for `RJ000000`
PROXY = {
    "http_proxy": "http://127.0.0.1:7890"
}
DLSITE_URL = "https://www.dlsite.com/home/work/=/product_id/{0}.html"

MP3_BITRATE = "320k"


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


def convert(inputPath, outputPath):
    outputType = getFileExt(outputPath)
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
    else:
        raise RuntimeError("invalid outputType")

    return


def cropCover(imageData):
    image = Image.open(io.BytesIO(imageData))

    width, height = image.size
    left = (width - height)/2
    top = 0
    right = (width + height)/2
    bottom = height

    image = image.crop((left, top, right, bottom))

    coverData = io.BytesIO()
    image.save(coverData, format="JPEG")

    return coverData.getvalue()
