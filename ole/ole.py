class SectorChainStream:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)


class SectorChainStreamReader:
    def __init__(self):
        pass

    def read(self, filename):
        return SectorChainStream(self)

    def prettyprint(self, data):
        return self.formatter(data)

    @classmethod
    def getreader(cls, loader):
        reader = SectorChainStreamReader()
        reader.formatter = loader.formatter.get('stream')
        return reader

def loadtypes(loader):
    loader.addtypes( { 'sectorchain': SectorChainStreamReader.getreader } )
