import operator
import os
import shutil
import fire
import requests
import sys
from internal import util
from internal import config
from internal import meta

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def gen(path):
    configPath = os.path.join(path, ".dlmeta.json")
    util.getInfo(path).write(configPath)
    print("info: meta config generated. at \"{0}\".".format(configPath))


def conv(path, target="mp3", copy=True, output="./dlmeta-output"):
    c = config.Config()
    configPath = os.path.join(path, ".dlmeta.json")
    c.read(configPath)

    for i in c.audioMap:
        if i["ignore"]:
            print("info: \"{0}\": ignored.".format(i["aid"]))
            continue

        available = {}
        for j in i["source"]:
            if not j["ignore"]:
                available[util.getFileExt(j["path"])] = j["path"]

        if copy and (target in available):
            # copy raw
            print("info: \"{0}\": copying raw...".format(i["aid"]))
            outputPath = os.path.join(
                output, c.title, i["title"]+"."+target)

            os.makedirs(os.path.dirname(outputPath), exist_ok=True)
            shutil.copyfile(os.path.join(path, available[target]), outputPath)

            continue

        elif list(available.keys()) == ["mp3"]:     # mp3 only
            # copy raw(mp3)
            print("warn: \"{0}\": it's mp3 only, but target = {1}, copy = {2}. copying mp3 instead...".format(
                i["aid"], target, copy))

            outputPath = os.path.join(
                output, c.title, i["title"]+".mp3")

            os.makedirs(os.path.dirname(outputPath), exist_ok=True)
            shutil.copyfile(os.path.join(path, available["mp3"]), outputPath)

            continue

        print("info: \"{0}\": converting...".format(i["aid"]))
        source = ""
        if "wav" in available:
            source = available["wav"]     # preferred
        else:
            source = available["flac"]

        util.convert(os.path.join(path, source), os.path.join(
            output, c.title, i["title"]+"."+target))

    addMeta(path, c, output)

    c.status = "done"
    c.write(configPath)


def addMeta(path, c, output="./dlmeta-output"):
    outputDir = os.path.join(
        output, c.title)
    convertMap = {}
    for i in os.listdir(outputDir):
        convertMap[os.path.splitext(i)[0]] = i

    coverData = b''
    if util.isLocal(c.albumArt):
        print("info: use local cover.")
        coverPath = os.path.join(path, c.albumArt)
        with open(coverPath, "rb") as f:
            coverData = f.read()
    else:
        print("info: downloading remote cover...")

        coverData = requests.get(
            c.albumArt, stream=True, timeout=10, proxies=util.PROXY).content

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


# def single(path, target="mp3", copy=True, output="./dlmeta-output"):
#     gen(path)
#     convert(path, target, copy, output)
#     addMeta(path, output)
#     c = config.Config()
#     configPath = os.path.join(path, ".dlmeta.json")
#     c.read(configPath)
#     c.status = "done"
#     c.write(configPath)


# def batch(input="./raw", output="./dlmeta-output", target="mp3", copy=True):
#     for i in os.listdir(input):
#         path = os.path.join(input, i)
#         metaPath = os.path.join(path, ".dlmeta.json")
#         c = config.Config()
#         isProcessed = False
#         try:
#             c.read(metaPath)
#             if os.path.exists(os.path.join(output, c.title)):
#                 isProcessed = True
#         except:
#             isProcessed = False

#         if isProcessed:
#             print("info: \"{0}\": it has been processed. skip.".format(i))
#             continue

#         single(path, target=target, copy=copy)


if __name__ == '__main__':
    fire.Fire({
        'gen': gen,
        'conv': conv
    })
