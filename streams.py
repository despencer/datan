import os
import formatter
import records

class StreamItem:
    def __init__(self, pos, item):
        self.pos = pos
        self.item = item

    def __repr__(self):
        return '{:08X}: '.format(self.pos) + formatter.indent(str(self.item)) + '\n'

class FixedStream:
    ''' A stream that operates on limited and fixed array of data '''
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

    def __len__(self):
        return len(self.source)

    def __getitem__(self, key):
        return self.source[key]

    def checkpos(self):
        if self.pos > len(self.source):
            self.pos = len(self.source)
        if self.pos < 0:
            self.pos = 0

    def getpos(self):
        return self.pos

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        pass

    def readall(self):
        return self.source

class SubSerialStream(FixedStream):
    def __init__(self, meta, source):
        super().__init__(meta)
        self.source = list(source)

    def selectrange(self, stop, start=0):
        self.seek(0)
        while True:
            if self.pos >= len(self.source):
                return
            if self.source[self.pos][0] >= start:
                break
            self.pos += 1
        size = stop - start
        while self.pos < len(self.source):
            if size == 0:
                break
            item = self.source[self.pos]
            self.pos += 1
            size -= 1
            yield item

    def readall(self):
        for item in self.source:
            yield item[1]

class StreamReader():
    def prettyprint(self, data):
        return formatter.formatsub(data, self.formatter)

    @classmethod
    def getreader(cls, loader):
        reader = cls()
        reader.formatter = reader.getformatter(loader)
        return reader

    def getformatter(self, loader):
        return loader.getformatter('stream')

class ByteStream(FixedStream):
    pass

class ByteStreamReader(StreamReader):
    def read(self, datafile):
        return ByteStream(self)

    def from_bytes(self, rawdata):
        stream = ByteStream(self)
        stream.source = rawdata
        return stream

class SubStream:
    ''' Reads a stream positioned inside other stream by a fixed offset '''
    def __init__(self, meta):
        self._meta = meta
        self.source = None
        self.offset = 0

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_SET:
            self.source.seek(self.offset+delta, postype)
        else:
            self.source.seek(delta, postype)

    def read(self, size):
        return self.source.read(size)

    def getpos(self):
        ret = self.source.getpos() - self.offset
        if ret < 0:
            ret = 0
        return ret

    def __len__(self):
        size = len(self.source) - self.offset
        if size < 0:
            size = 0
        return size

    def reset(self):
        self.source.seek(self.offset)

    @classmethod
    def make(cls, source, offset):
        ss = cls()
        ss.source = source
        ss.offset = offset
        return ss

class SubStreamReader(StreamReader):
    def read(self, datafile):
        return SubStream(self)

class RecordStream:
    ''' Reads a stream that consists of repeated records of equal size '''
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

    def selectrange(self, stop, start=0):
        self.seek(start)
        while self.pos < stop:
            if self.source.getpos() >= len(self.source):
                break
            item = self.record.read(self.source)
            self.pos += 1
            yield self.pos-1, item


class StructuredStreamReader(StreamReader):
    def loadmeta(self, module, yfield):
        self.record = module.getreader(yfield['record'], records.LoaderXRef(self, 'record'))
        self.recformatter = module.loader.formatter.get(yfield['record'])

    def getformatter(self, loader):
        return loader.getformatter('recordstream')

    def prettyprint(self, data):
        return self.formatter(data, record=self.recformatter)


class RecordStreamReader(StructuredStreamReader):
    def read(self, datafile):
        return RecordStream(self, self.record)


class SerialStream:
    ''' Reads a stream that consists of records of variable size '''
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
        return self.retrieve(size, None, False)

    def retrieve(self, size, condition, pointer):
        acc = []
        while True:
            if size != None and size <= 0:
                break
            if self.source.getpos() == self.sourcesize:
                break
            item = self.record.read(self.source)
            if condition == None or ( condition != None and condition(item) ):
                if pointer:
                    acc.append(StreamItem(self.pos, item))
                else:
                    acc.append(item)
            self.pos += 1
            if size != None:
                size -= 1
        return acc

    def selectiter(self, condition):
        self.seek(0)
        while True:
            if self.source.getpos() == self.sourcesize:
                break
            item = self.record.read(self.source)
            self.pos += 1
            if condition(item):
                yield self.pos-1, item

    def select(self, condition):
        return SubSerialStream(self._meta, self.selectiter(condition))

    def selectrange(self, stop, start=0):
        self.seek(start)
        while self.pos < stop:
            if self.source.getpos() == self.sourcesize:
                break
            item = self.record.read(self.source)
            self.pos += 1
            yield self.pos-1, item

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        self.pos = 0
        self.size = None
        self.index = [0]
        self.sourcesize = len(self.source)

    def getpos(self):
        return self.pos

    def syncpos(self):
        if self.pos == None:
            self.syncatpos()
            while self.size is None:
                self.syncroll()
        else:
            target = self.pos
            self.syncatpos()
            while self.pos < target:
                if self.size != None and self.pos >= self.size:
                    return
                self.syncroll()

    def syncatpos(self):
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

    def __getitem__(self, key):
        self.seek(key)
        ret = self.read(1)
        return ret[0] if len(ret) > 0 else None

class SerialStreamReader(StructuredStreamReader):
    def read(self, datafile):
        return SerialStream(self, self.record)

class CombinedStream:
    def __init__(self, meta):
        self._meta = meta
        self.sources = None
        self.sizes = None
        self.pos = 0

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            self.pos = sum(self.sizes)
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.pos = min (self.pos, sum(self.sizes) )
        self.pos = max (self.pos, 0)
        return self.pos

    def read(self, size):
        acc = bytes()
        isource, istart = self.mappos()
        while size >= 0:
            self.sources[isource].seek(istart)
            chunk = self.sizes[isource] - istart
            acc += self.sources[isource].read( min(size, chunk) )
            self.pos += min(size, chunk)
            size -= chunk
            isource += 1
            if isource >= len(self.sources):
                break
            istart = 0
        return acc

    def __repr__(self):
        return self._meta.prettyprint(self)

    def mappos(self):
        istart = self.pos
        for isource in range(len(self.sources)):
            if istart < self.sizes[isource]:
                return isource, istart
            istart -= self.sizes[isource]
        return len(self.sources), 0

    def __len__(self):
        return sum(self.sizes)

    def getpos(self):
        return self.pos

    def reset(self):
        self.sizes = list(map( lambda s: s.seek(0, os.SEEK_END), self.sources))

    @classmethod
    def fromstreams(cls, streams, meta):
        cs = cls(meta)
        cs.sources = [ *streams ]
        cs.reset()
        return cs

def loadmeta(module):
    module.addtypes( { 'bytestream': ByteStreamReader.getreader, 'recordstream': RecordStreamReader.getreader,
                       'serialstream': SerialStreamReader.getreader, 'substream': SubStreamReader.getreader } )