import os

class SectorChainStream:
    def __init__(self, meta, datafile):
        self._meta = meta
        self.datafile = datafile

    def seek(self, delta, postype=os.SEEK_SET):
        return self.datafile.seek(delta, postype)

    def read(self, size):
        return self.datafile.read(size)

    def __repr__(self):
        return self._meta.prettyprint(self)


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
