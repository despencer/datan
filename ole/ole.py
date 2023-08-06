class SectorChainStream:
    def __init__(self):
        pass

class SectorChainStreamReader:
    def __init__(self):
        pass

    def read(self, filename):
        return SectorChainStream()

    @classmethod
    def getreader(cls, loader):
        print('Hi')
        return SectorChainStreamReader()

def loadtypes(loader):
    loader.addtypes( { 'sectorchain': SectorChainStreamReader.getreader } )
