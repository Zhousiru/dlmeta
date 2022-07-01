import mutagen.id3
import mutagen.flac

ID3_V2_VERSION = 3     # Groove does't support ID3v2.4


class Meta(object):
    def __init__(self):
        self.title = ""
        self.artist = []
        self.album = ""
        self.trackNum = -1
        self.desc = ""
        self.coverData = b''

    def writeMp3(self, path):
        audio = mutagen.id3.ID3(path)
        audio.clear()
        
        audio.add(mutagen.id3.TIT2(encoding=3, text=self.title))
        audio.add(mutagen.id3.TPE1(encoding=3, text='/'.join(self.artist)))
        audio.add(mutagen.id3.TALB(encoding=3, text=self.album))
        audio.add(mutagen.id3.TRCK(encoding=3, text=str(self.trackNum)))
        audio.add(mutagen.id3.COMM(encoding=3, text=self.desc))
        audio.add(mutagen.id3.APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            data=self.coverData
        ))
        audio.save(v2_version=ID3_V2_VERSION)

        return

    def writeFlac(self, path):
        audio = mutagen.flac.FLAC(path)
        audio.delete()
        audio.clear_pictures()

        audio["TITLE"] = self.title
        audio["ARTIST"] = '/'.join(self.artist)
        audio["ALBUM"] = self.album
        audio["TRACKNUMBER"] = str(self.trackNum)
        audio["DESCRIPTION"] = self.desc

        cover = mutagen.flac.Picture()

        cover.data = self.coverData
        cover.type = mutagen.id3.PictureType.COVER_FRONT
        cover.mime = "image/jpeg"

        audio.add_picture(cover)
        audio.save()

        return
