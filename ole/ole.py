import os
import streams

ENDOFCHAIN = 0xFFFFFFFE

class SectorChainStream:
    def __init__(self, meta, datafile):
        self._meta = meta
        self.datafile = datafile
        self.sectors = None
        self.pos = 0
        self.size = None

    def seek(self, delta, postype=os.SEEK_SET):
        if postype == os.SEEK_END:
            self.pos = None
        elif postype == os.SEEK_CUR:
            self.pos = self.pos + delta
        else:
            self.pos = delta
        self.checkpos()
        return self.pos

    def getpos(self):
        return self.pos

    def read(self, size):
        acc = bytes()
        self.acquiresectors(self.pos+size)
        isect = self.pos // self.posbase
        istart = (self.pos % self.posbase)
        while size >= 0:
            chunk = min(size, self.posbase-istart)
            if self.size != None:
                chunk = min(chunk, self.size-self.pos)
                if chunk <= 0:
                    break
            self.datafile.seek(self.sectors[isect] + istart)
            acc += self.datafile.read(chunk)
            self.pos += chunk
            size -= chunk
            isect += 1
            if isect >= len(self.sectors):
                break
            istart = 0
        return acc

    def __len__(self):
        if self.size is None:
            pos = self.pos
            len = self.seek(0, os.SEEK_END)
            self.pos = pos
            return len
        else:
            return self.size

    def __repr__(self):
        return self._meta.prettyprint(self)

    def reset(self):
        if not self.sectors is None:
            return False
        self.sectsize = 1 << self.header.sectorshift
        self.pos = 0
        return True

    def checkpos(self):
        if self.pos is None:
            self.acquiresectors(-1)
            self.pos = self.getmax()
        else:
            if self.pos >= self.getmax():
                self.acquiresectors(-1)
            if self.pos > self.getmax():
                self.pos = self.getmax()
        if self.pos < 0:
            self.pos = 0

    def getmax(self):
        if self.size is None:
            return len(self.sectors) * self.posbase
        return self.size

    def sectorpos(self, isect):
            return (isect+1)*self.sectsize

class SectorChainStreamReader(streams.StreamReader):
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
        return True

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

class DIFatSectorChainStreamReader(streams.StreamReader):
    def read(self, datafile):
        return DIFatSectorChainStream(self, datafile)

class FatStream(SectorChainStream):
    def __init__(self, meta, datafile, fatsectors):
        super().__init__(meta, datafile)
        self.fatsectors = fatsectors

    def reset(self):
        if not super().reset():
            return False
        self.fatsectors.header = self.header
        self.fatsectors.reset()
        self.fatsectors.seek(0, os.SEEK_SET)
        self.sectors = [ self.sectorpos(int.from_bytes(self.fatsectors.read(4), 'little')) ]
        self.posbase = self.sectsize
        return True

    def acquiresectors(self, lastpos):
        if lastpos < 0:
            maxsect = self.header.numfatsect
        else:
            maxsect = min( lastpos // self.posbase, self.header.numfatsect)
        self.fatsectors.seek( len(self.sectors) * 4, os.SEEK_SET )
        num = maxsect - len(self.sectors)
        sectors = self.fatsectors.read(num * 4)
        for i in range(num):
            self.sectors.append( self.sectorpos(int.from_bytes(sectors[i*4:i*4+4], 'little') ))

class FatStreamReader(streams.StreamReader):
    def __init__(self):
        self.fatsectors = FatSectorStreamReader()

    def read(self, datafile):
        return FatStream(self, datafile, self.fatsectors.read(datafile) )

class DataStream(SectorChainStream):
    def __init__(self, meta, datafile):
        super().__init__(meta, datafile)

    def reset(self):
        if not super().reset():
            return False
        self.sectors = [ self.sectorpos(self.start) ]
        self.isectors = [ self.start ]
        self.posbase = self.sectsize
        return True

    def acquiresectors(self, lastpos):
        if self.isectors[-1] == ENDOFCHAIN:
            return
        maxpos = len(self.isectors) * self.sectsize
        while maxpos < lastpos or lastpos < 0:
            self.fat.seek(self.isectors[-1], os.SEEK_SET)
            next = self.fat.read(1)[0]
            self.isectors.append(next)
            if next == ENDOFCHAIN:
                return
            self.sectors.append( self.sectorpos(next) )
            maxpos += self.sectsize

class DataStreamReader(streams.StreamReader):
    def read(self, datafile):
        return DataStream(self, datafile)

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

class FatSectorStreamReader(streams.StreamReader):
    def __init__(self):
        self.inheader = streams.ByteStreamReader()
        self.chain = DIFatSectorChainStreamReader()

    def read(self, datafile):
        return FatSectorStream(self, self.inheader.read(datafile), self.chain.read(datafile) )

def loadmeta(module):
    module.addtypes( { 'sectorchain': SectorChainStreamReader.getreader, 'difatstream': FatSectorStreamReader.getreader,
                       'fatstream': FatStreamReader.getreader, 'datastream': DataStreamReader.getreader } )
