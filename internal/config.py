import json


class Config(object):
    def __init__(self):
        self.id = ""
        self.status = ""
        self.title = ""
        self.circle = ""
        self.cv = []
        self.dlImage = []
        self.albumArt = ""
        self.audioMap = []
        self.imageMap = []

        return

    def addAudioMap(self, aid, title, ignore=False):
        self.audioMap.append({
            "aid": aid,
            "title": title,
            "order": len(self.audioMap),
            "ignore": ignore,
            "source": []
        })
        return

    def addAudioSource(self, aid, source, ignore=False):
        for i in self.audioMap:
            if i["aid"] == aid:
                i["source"].append({"path": source, "ignore": ignore})
                return

        raise KeyError("can't find spcified aid")

    def write(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, ensure_ascii=False)

        return

    def read(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)

        for k in d:
            setattr(self, k, d[k])

        return
