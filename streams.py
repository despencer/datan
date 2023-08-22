import os
import formatter

class StreamReader():
    def prettyprint(self, data):
        return formatter.formatsub(data, self.formatter)

    @classmethod
    def getreader(cls, loader):
        reader = cls()
        reader.formatter = loader.formatter.get('stream')
        return reader

class RecordStream:
    def __init__(self, meta):
        self._meta = meta
        self.pos = 0

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            self.pos = len(self.source)
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.checkpos()
        return self.pos

    def read(self, size):
        acc = self.source[self.pos:self.pos+size]
        self.pos += len(acc)
        self.checkpos()
        return acc

    def checkpos(self):
        if self.pos > len(self.source):
            self.pos = len(self.source)
        if self.pos < 0:
            self.pos = 0

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        pass

class RecordStreamReader(StreamReader):
    def read(self, datafile):
        return ByteStream(self)

