
class PlainRecordMeta:
    def __init__(self):
        pass

    @classmethod
    def loadmeta(cls, name, yrec):
        prec = PlainRecordMeta()
        prec.name = name

    def __repr__(self):
        return "Record {0}".format(self.name)

class Structure:
    def __init__(self):
        self.records = {}

    def __repr__(self):
        return '\n'.join( map(str, self.records) )

def loadmeta(ymeta):
    strmeta = Structure()
    for yrname, yrec in ymeta['records'].items():
        strmeta.records[yrname] = PlainRecordMeta.loadmeta(yrname, yrec)
    return strmeta
