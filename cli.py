import operator
import os
import shutil
import fire
import requests
from internal import util
from internal import config
from internal import meta


def gen(path):
    configPath = os.path.join(path, ".dlmeta.json")
    util.getInfo(path).write(configPath)
    print("info: meta config generated. at \"{0}\".".format(configPath))


def convert(path, target="mp3", copy=True, output="./dlmeta-output"):
    c = config.Config()
    c.read(os.path.join(path, ".dlmeta.json"))

    for i in c.audioMap:
        if i["ignore"]:
            print("info: \"{0}\": ignored.".format(i["aid"]))
            continue

        available = {}
        for j in i["source"]:
            available[util.getFileExt(j)] = j

        if copy and (target in available):
            # copy raw
            print("info: \"{0}\": copying raw...".format(i["aid"]))
            outputPath = os.path.join(
                output, c.title, i["title"]+"."+target)

            os.makedirs(os.path.dirname(outputPath), exist_ok=True)
            shutil.copyfile(available[target], outputPath)

            continue

        elif list(available.keys()) == ["mp3"]:     # mp3 only
            # copy raw(mp3)
            print("warn: \"{0}\": it's mp3 only, but target = {1}, copy = {2}. copying mp3 instead...".format(
                i["aid"], target, copy))

            outputPath = os.path.join(
                output, c.title, i["title"]+".mp3")

            os.makedirs(os.path.dirname(outputPath), exist_ok=True)
            shutil.copyfile(available["mp3"], outputPath)

            continue

        print("info: \"{0}\": converting...".format(i["aid"]))
        source = ""
        if "wav" in available:
            source = available["wav"]     # preferred
        else:
            source = available["flac"]

        util.convert(source, os.path.join(
            output, c.title, i["title"]+"."+target))


def addMeta(path, output="./dlmeta-output", coverPath=""):
    c = config.Config()
    c.read(os.path.join(path, ".dlmeta.json"))

    outputDir = os.path.join(
        output, c.title)
    convertMap = {}
    for i in os.listdir(outputDir):
        convertMap[os.path.splitext(i)[0]] = i

    coverData = b''
    if coverPath:
        print("info: use specified cover.")
        with open(coverPath, "rb") as f:
            coverData = f.read()
    else:
        print("info: downloading cover from DLsite...")
        coverData = requests.get(c.dlImage[0], stream=True, timeout=10).content

    coverData = util.cropCover(coverData, resize=800)

    sort = sorted(c.audioMap, key=operator.itemgetter('order'))
    trackNum = 1
    for i in sort:
        if i["ignore"]:
            print("info: \"{0}\": ignored.".format(i["aid"]))
            continue

        print("info: \"{0}\": adding meta...".format(i["aid"]))
        title = i["title"]

        m = meta.Meta()
        m.title = title
        m.artist = [c.circle] + c.cv
        m.album = c.title
        m.trackNum = trackNum
        m.desc = c.id
        m.coverData = coverData
        if util.getFileExt(convertMap[title]) == "mp3":
            m.writeMp3(os.path.join(outputDir, convertMap[title]))
        else:
            m.writeFlac(os.path.join(outputDir, convertMap[title]))

        trackNum = trackNum + 1

def single(path, target="mp3", copy=True, output="./dlmeta-output", coverPath=""):
    gen(path)
    convert(path, target, copy, output)
    addMeta(path, output, coverPath)


if __name__ == '__main__':
    fire.Fire()
