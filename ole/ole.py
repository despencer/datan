import os
import formatter

ENDOFCHAIN = 0xFFFFFFFE

class StreamReader():
    def prettyprint(self, data):
        return formatter.formatsub(data, self.formatter)

    @classmethod
    def getreader(cls, loader):
        reader = cls()
        reader.formatter = loader.formatter.get('stream')
        return reader

class SectorChainStream:
    def __init__(self, meta, datafile):
        self._meta = meta
        self.datafile = datafile
        self.sectors = None
        self.pos = 0

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            self.pos = None
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.checkpos()
        return self.pos

    def read(self, size):
        acc = bytes()
        self.acquiresectors(self.pos+size)
        isect = self.pos // self.posbase
        istart = (self.pos % self.posbase)
        while size >= 0:
            self.datafile.seek(self.sectors[isect] + istart)
            chunk = min(size, self.posbase-istart)
            acc += self.datafile.read(chunk)
            self.pos += chunk
            size -= chunk
            isect += 1
            if isect >= len(self.sectors):
                break
            istart = 0
        return acc

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        if not self.sectors is None:
            return False
        self.sectsize = 1 << self.header.sectorshift
        return True

    def checkpos(self):
        if self.pos is None:
            self.acquiresectors(-1)
            self.pos = len(self.sectors) * self.posbase
        else:
            if self.pos >= ( len(self.sectors) * self.posbase ):
                self.acquiresectors(-1)
            if self.pos > ( len(self.sectors) * self.posbase ):
                self.pos = len(self.sectors) * self.posbase
        if self.pos < 0:
            self.pos = 0

    def sectorpos(self, isect):
            return (isect+1)*self.sectsize

class SectorChainStreamReader(StreamReader):
    def read(self, datafile):
        return SectorChainStream(self, datafile)

class DIFatSectorChainStream(SectorChainStream):
    def __init__(self, meta, datafile):
        super().__init__(meta, datafile)

    def reset(self):
        if not super().reset():
            return False
        self.sectors = [ self.sectorpos(self.header.firstdifatsect) ]
        self.posbase = self.sectsize - 4

    def acquiresectors(self, lastpos):
        if lastpos < 0:
            maxsect = self.header.numdifatsect
        else:
            maxsect = min( lastpos // self.posbase, self.header.numdifatsect)
        while len(self.sectors) < maxsect:
            self.datafile.seek( self.sectors[-1], os.SEEK_SET)
            sect = self.datafile.read(self.sectsize)
            nextsect = int.from_bytes(sect[-4:], 'little')
            if nextsect == ENDOFCHAIN:
                raise Exception('Unexpected end of chain')
            self.sectors.append( self.sectorpos(nextsect) )

class DIFatSectorChainStreamReader(StreamReader):
    def read(self, datafile):
        return DIFatSectorChainStream(self, datafile)

class ByteStream:
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

class ByteStreamReader(StreamReader):
    def read(self, datafile):
        return ByteStream(self)

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
        istart = 0
        for isource in range(len(self.sources)):
            if istart < self.sizes[isource]:
                return isource, istart
            istart -= self.size[isource]
        return len(self.sources), 0

    def reset(self):
        self.sizes = list(map( lambda s: s.seek(0, os.SEEK_END), self.sources))

class FatSectorStream(CombinedStream):
    def __init__(self, meta, inheader, chain):
        super().__init__(meta)
        self.inheader = inheader
        self.chain = chain
        self.sources = [ inheader, chain ]

    def reset(self):
        self.inheader.source = self.header.difat
        self.inheader.reset()
        self.chain.header = self.header
        self.chain.reset()
        super().reset()

class FatSectorStreamReader(StreamReader):
    def __init__(self):
        self.inheader = ByteStreamReader()
        self.chain = DIFatSectorChainStreamReader()

    def read(self, datafile):
        return FatSectorStream(self, self.inheader.read(datafile), self.chain.read(datafile) )

def loadtypes(loader):
    loader.addtypes( { 'sectorchain': SectorChainStreamReader.getreader, 'bytestream': ByteStreamReader.getreader,
                       'difatstream':  FatSectorStreamReader.getreader } )
