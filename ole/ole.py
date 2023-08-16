import os

ENDOFCHAIN = 0xFFFFFFFE

class SectorChainStream:
    def __init__(self, meta, datafile):
        self._meta = meta
        self.datafile = datafile
        self.sectors = None
        self.pos = 0

    def seek(self, delta, postype=os.SEEK_SET):
        self.setup()
        if postype == os.SEEK_END:
            self.pos = None
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.checkpos()
        return self.pos

    def read(self, size):
        self.setup()
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

    def setup(self):
        if not self.sectors is None:
            return
        self.sectors = [ self.header.firstdifatsect ]
        self.sectsize = 1 << self.header.sectorshift
        self.posbase = self.sectsize - 4

    def checkpos(self):
        if self.pos is None:
            self.acquiresectors(-1)
            self.pos = ( len(self.sectors) * self.posbase ) - 1
        else:
            if self.pos >= ( len(self.sectors) * self.posbase ):
                self.getfullchain()
            if self.pos >= ( len(self.sectors) * self.posbase ):
                self.pos = ( len(self.sectors) * self.posbase ) - 1
        if self.pos < 0:
            self.pos = 0

    def acquiresectors(self, lastpos):
        if lastpos < 0:
            maxsect = self.header.numdifatsect+1
        else:
            maxsect = lastpos // self.posbase
        while len(self.sectors) <= maxsect:
            self.datafile.seek( self.sectors[-1], os.SEEK_SET)
            sect = self.datafile.read(self.sectsize)
            nextsect = int.from_bytes(sect[-4:].read(4), 'little')
            if nextsect == ENDOFCHAIN:
                raise Exception('Unexpected end of chain')
            self.sectors.append(nextsect)

class SectorChainStreamReader:
    def __init__(self):
        pass

    def read(self, datafile):
        return SectorChainStream(self, datafile)

    def prettyprint(self, data):
        return '\n    '+'\n'.join(  map(lambda x: '    '+x, self.formatter(data).split('\n'))  )[4:]

    @classmethod
    def getreader(cls, loader):
        reader = SectorChainStreamReader()
        reader.formatter = loader.formatter.get('stream')
        return reader

def loadtypes(loader):
    loader.addtypes( { 'sectorchain': SectorChainStreamReader.getreader } )
