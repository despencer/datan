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
        self.datafile.seek(self.sectors[isect] + (self.pos % self.posbase) )
        while size >= 0:
            acc += self.datafile.read( min(size, self.posbase) )
            self.pos += min(size, self.posbase)
            size -= self.posbase
            isect += 1
            if isect >= len(self.sectors):
                break
            self.datafile.seek(self.sectors[isect])
        return acc

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        if not self.sectors is None:
            return
        self.sectsize = 1 << self.header.sectorshift
        self.sectors = [ self.sectorpos(self.header.firstdifatsect) ]
        self.posbase = self.sectsize - 4

    def checkpos(self):
        if self.pos is None:
            self.acquiresectors(-1)
            self.pos = len(self.sectors) * self.posbase
        else:
            if self.pos >= ( len(self.sectors) * self.posbase ):
                self.getfullchain()
            if self.pos >= ( len(self.sectors) * self.posbase ):
                self.pos = ( len(self.sectors) * self.posbase ) - 1
        if self.pos < 0:
            self.pos = 0

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

    def sectorpos(self, isect):
            return (isect+1)*self.sectsize

class SectorChainStreamReader(StreamReader):
    def read(self, datafile):
        return SectorChainStream(self, datafile)

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

def loadtypes(loader):
    loader.addtypes( { 'sectorchain': SectorChainStreamReader.getreader, 'bytestream': ByteStreamReader.getreader } )
