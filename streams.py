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

    def find(self, condition):
        self.seek(0)
        while True:
            acc = self.read(1)
            if len(acc) == 0:
                break
            if condition(acc[0]):
                return acc[0]
        return None

class StructuredStreamReader(StreamReader):
    def loadmeta(self, module, yfield):
        self.record = module.getreader(yfield['record'], records.LoaderXRef(self, 'record'))
        self.recformatter = module.loader.formatter.get(yfield['record'])

    def getformatter(self, loader):
        return loader.formatter.get('recordstream')

    def prettyprint(self, data):
        return self.formatter(data, record=self.recformatter)


class RecordStreamReader(StructuredStreamReader):
    def read(self, datafile):
        return RecordStream(self, self.record)


class SerialStream:
    def __init__(self, meta, record):
        self._meta = meta
        self.record = record
        self.pos = 0
        self.size = None
        self.index = []
        self.step = 16

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            if self.size is None:
                self.pos = None
            else:
                self.pos = self.size
                return self.pos
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        if self.size != None:
            self.pos = min(self.pos, self.size)
            self.pos = max(self.pos, 0)
        self.syncpos()
        return self.pos

    def read(self, size):
        acc = []
        while size > 0:
            if self.source.getpos() == self.sourcesize:
                break
            acc.append( self.record.read(self.source) )
            self.pos += 1
            size -= 1
        return acc

    def reset(self):
        self.pos = 0
        self.size = None
        self.index = [0]
        self.sourcesize = len(self.source)

    def syncpos(self):
        if self.pos == None:
            self.syncatpos()
            while self.size is None:
                self.syncroll()
        else:
            target = self.pos
            self.syncatpos()
            while self.pos < target:
                if self.size != None and self.pos >= size:
                    return
                self.syncroll()

    def syncat(self):
        ''' Tries to synchronize either at last chunk observed or at the closest chunk '''
        pind = min( self.pos // self.step , len(self.index)-1 )
        self.pos = pind * self.step
        self.source.seek( self.index[self.pos] )
        if self.source.getpos() == self.sourcesize:
            self.size = self.sourcesize


    def syncroll(self):
        ''' Pre-condition - the position is not the end one and synchronized '''
        self.record.readsize(self.source)
        self.pos += 1
        if self.pos % self.step == 0:
            if (self.pos // self.step) >= len(self.index):
                self.index.append(self.source.getpos())
        if self.source.getpos() == self.sourcesize:
            self.size = self.sourcesize

class SerialStreamReader(StructuredStreamReader):
    def read(self, datafile):
        return SerialStream(self, self.record)


def loadtypes(module):
    module.addtypes( { 'recordstream': RecordStreamReader.getreader, 'serialstream': SerialStreamReader.getreader } )