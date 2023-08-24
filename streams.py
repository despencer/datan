import os
import formatter
import records

class StreamReader():
    def prettyprint(self, data):
        return formatter.formatsub(data, self.formatter)

    @classmethod
    def getreader(cls, loader):
        reader = cls()
        reader.formatter = reader.getformatter(loader)
        return reader

    def getformatter(self, loader):
        return loader.formatter.get('stream')

class RecordStream:
    def __init__(self, meta, record):
        self._meta = meta
        self.record = record
        self.pos = 0
        self.size = self.record.getsize()

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            self.pos = len(self.source) // self.size
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.checkpos()
        return self.pos

    def read(self, size):
        self.source.seek(self.pos * self.size, os.SEEK_SET)
        mx = len(self.source) // self.size
        acc = []
        while size > 0 and self.pos < mx:
            instance = self.record.read(self.source)
            self.pos += 1
            size -= 1
            acc.append(instance)
        self.checkpos()
        return acc

    def checkpos(self):
        mx = len(self.source) // self.size
        if self.pos > mx:
            self.pos = mx
        if self.pos < 0:
            self.pos = 0

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        pass

class RecordStreamReader(StreamReader):
    def read(self, datafile):
        return RecordStream(self, self.record)

    def loadmeta(self, loader, yfield):
        self.record = loader.getreader(yfield['record'], records.LoaderXRef(self, 'record'))

    def getformatter(self, loader):
        return loader.formatter.get('recordstream')


def loadtypes(loader):
    loader.addtypes( { 'recordstream': RecordStreamReader.getreader } )