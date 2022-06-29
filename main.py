import collections
import io
from operator import itemgetter
import subprocess
from PIL import Image
from mutagen import id3
from mutagen.id3 import TIT2, TPE1, TALB, TRCK, COMM, APIC
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
import os
from natsort.natsort import natsorted
import requests
from bs4 import BeautifulSoup
import re
import shutil
import natsort

LIB_PATH = "./ASMR"
DLSITE_URL = "https://www.dlsite.com/home/work/=/product_id/{0}.html"
PROXY = {
    "http_proxy": "http://127.0.0.1:7890"
}
ID3_V2_VERSION = 3     # Groove does't support ID3v2.4
TARGET_TYPE = ("flac", "mp3")[1]


def getFileExt(filename):
    return os.path.splitext(filename)[-1][1:]


asmrList = []
for i in os.listdir(LIB_PATH):
    path = os.path.join(LIB_PATH, i)
    if os.path.isdir(path):
        asmrList.append((i.split("-")[0], path))

# _TARGET_ASMR = asmrList[0] # DEBUG

for _TARGET_ASMR in asmrList:
    dltagPath = os.path.join("dltag", _TARGET_ASMR[0])
    
    print(" - - - - - PROCESSING [{0}] - - - - - ".format(_TARGET_ASMR[0]))
    flagProcessingPath = os.path.join(_TARGET_ASMR[1], "dltag_processing")
    flagProcessedPath = os.path.join(_TARGET_ASMR[1], "dltag_processed")

    if os.path.exists(flagProcessedPath):
        print("This ASMR seems to have been processed. Skip.")
        continue

    open(flagProcessingPath, "a").close()

    # Scan ASMR audio
    audioList = {}
    for dirpath, dirnames, filenames in os.walk(_TARGET_ASMR[1]):
        for i in filenames:
            fileType = getFileExt(i)
            if fileType in ("wav", "flac", "mp3"):
                audioName = os.path.splitext(i)[0]

                if audioName not in audioList:
                    audioList[audioName] = {}

                audioList[audioName].update({
                    fileType: os.path.join(dirpath, i)
                })

    # Convert
    converted = []
    for k, v in audioList.items():
        print("Processing [{0}]".format(k))

        if TARGET_TYPE in v:
            filename = os.path.join(
                dltagPath,
                k + "." + TARGET_TYPE
            )

            print(" - {0}: Copying to dltag folder...".format(TARGET_TYPE.upper()))
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            shutil.copyfile(v[TARGET_TYPE], filename)
            print(" - {0}: Complete.".format(TARGET_TYPE.upper()))

            converted.append((filename, os.path.dirname(v[TARGET_TYPE])))

            continue

        if "wav" in v:
            print(
                " - WAV: Found. Converting to {0}...".format(TARGET_TYPE.upper()))

            filename = os.path.join(
                dltagPath,
                k + "." + TARGET_TYPE
            )

            os.makedirs(os.path.dirname(filename), exist_ok=True)
            if TARGET_TYPE == "mp3":
                p = subprocess.Popen('ffmpeg -y -i "{0}" -map_metadata -1 -vn -c:a libmp3lame -b:a 320k "{1}"'.format(v["wav"], filename),
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT)
                p.wait()
            elif TARGET_TYPE == "flac":
                p = subprocess.Popen('ffmpeg -y -i "{0}" -map_metadata -1 -vn -c:a flac "{1}"'.format(v["wav"], filename),
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.STDOUT)
                p.wait()
            print(" - WAV: Complete.")

            converted.append((filename, os.path.dirname(v["wav"])))

            continue

        if "mp3" in v:
            print(" - MP3: Found. It's better not to convert to FLAC.")

            filename = os.path.join(
                dltagPath,
                k + ".mp3"
            )

            print(" - MP3: Copying to dltag folder...")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            shutil.copyfile(v["mp3"], filename)
            print(" - MP3: Complete.")

            converted.append((filename,  os.path.dirname(v["mp3"])))

            continue

    # Sort
    sort = []
    for i in converted:
        found = False
        for j,k in enumerate(sort):
            if k[0] == i[1]:
                sort[j][1].append(i[0])
                found = True
                break
        if not found:
            sort.append([i[1], [i[0]]])

    sort = natsort.natsorted(sort, key=itemgetter(0), alg=natsort.ns.PATH)

    sortedConverted = []
    for i, j in enumerate(sort):
        sortedConverted.extend(natsort.os_sorted(j[1])) # or natsorted()

    # Get DLsite details
    s = requests.Session()
    s.proxies.update(PROXY)

    print("Getting ASMR details from [{0}]...".format(
        DLSITE_URL.format(_TARGET_ASMR[0])))

    r = s.get(DLSITE_URL.format(_TARGET_ASMR[0]))
    if r.status_code != 200:
        print(" - Failed to download page. Status code:" + str(r.status_code))
        exit(1)

    soup = BeautifulSoup(r.text, features="html.parser")

    # rawTitle = soup.select("#work_name a")[0].contents[0]
    rawTitle = soup.select("#work_name")[0].contents[0]  # 2021/12/9: removed tag `a`
    title = re.sub(r'【(.*?)】', '', rawTitle)

    print(" - Title: [{0}]({1})".format(title, rawTitle))

    creator = []
    # elem = soup.select("#work_outline a")
    # for i in elem:
    #     if "keyword_creater" in i["href"]:
    #         creator.append(i.contents[0])
    #
    circle = soup.select("#work_maker .maker_name a")[0].contents[0]
    # if circle not in creator:
    #     creator.append(circle)
    creator.append(circle)

    print(" - Creators: " + ", ".join(creator))

    creator = [soup.select("#work_maker .maker_name a")[0].contents[0]]

    imageUrlList = []
    for i in soup.select(".product-slider-data div"):
        imageUrlList.append("https:" + i["data-src"])

    print(" - Images:\n - - " + "\n - - ".join(imageUrlList))

    print(" - Downloading main image...")

    r = s.get(imageUrlList[0], stream=True)

    print(" - Complete.")

    # Write metadatas
    print("Writing metadatas...")

    print(" - Cropping cover image...")

    image = Image.open(io.BytesIO(r.content))

    width, height = image.size
    left = (width - height)/2
    top = 0
    right = (width + height)/2
    bottom = height

    image = image.crop((left, top, right, bottom))

    coverData = io.BytesIO()
    image.save(coverData, format="JPEG")
    coverData = coverData.getvalue()

    cover = Picture()

    cover.data = coverData
    cover.type = id3.PictureType.COVER_FRONT
    cover.mime = u"image/jpeg"
    # cover.width = 420
    # cover.height = 420
    # cover.depth = 24

    print(" - Complete.")

    for i, j in enumerate(sortedConverted):
        basename = os.path.basename(j)
        name = os.path.splitext(basename)[0]

        print(" - Processing [{0}]".format(basename))

        if getFileExt(j) == "mp3":
            print(" - - Type: MP3.")
            audio = MP3(j)
            if audio.tags is None:
                audio.add_tags()
            else:
                audio.clear()
            audio.tags["TIT2"] = TIT2(encoding=3, text=name)
            audio.tags["TPE1"] = TPE1(encoding=3, text=creator)
            audio.tags["TALB"] = TALB(encoding=3, text=title)
            audio.tags["TRCK"] = TRCK(encoding=3, text=str(i + 1))
            audio.tags["COMM"] = COMM(encoding=3, text=_TARGET_ASMR[0])
            audio.tags['APIC'] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                data=coverData
            )
            audio.tags.update_to_v23()
            audio.save(v2_version=ID3_V2_VERSION)
            continue

        print(" - - Type: FLAC.")

        audio = FLAC(j)
        audio.delete()
        audio["TITLE"] = name
        audio["ARTIST"] = creator
        audio["ALBUM"] = title
        audio["TRACKNUMBER"] = str(i + 1)
        audio["DESCRIPTION"] = _TARGET_ASMR[0]
        # TODO: audio["DISCNUMBER"]
        # 根据文件夹为音频分配碟片号

        audio.add_picture(cover)

        audio.save()

        print(" - - Complete.")

    os.rename(flagProcessingPath, flagProcessedPath)
