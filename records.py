import os

class FieldMeta:
    def __init__(self):
        pass

    def __repr__(self):
        return self.name

class PlainRecordMeta:
    def __init__(self):
        self.fields = []

    @classmethod
    def loadmeta(cls, name, yrec):
        prec = PlainRecordMeta()
        prec.name = name
        for yfield in yrec:
            field = FieldMeta()
            field.name = yfield['field']
            field.extractor = cls.getextractor(yfield['type'])
            prec.fields.append(field)
        return prec

    @classmethod
    def getextractor(cls, stype):
        if stype.find('[') >=0 :
            return cls.getarrayextractor(stype)
        return { 'uint8': lambda x: int.from_bytes(x.read(1)),
            'uint16': lambda x: int.from_bytes(x.read(2), 'little'),
            'uint32': lambda x: int.from_bytes(x.read(4), 'little'),
            'uint64': lambda x: int.from_bytes(x.read(8), 'little') }[stype]

    @classmethod
    def getarrayextractor(cls, stype):
        simple = stype[:stype.find('[')]
        count = int( stype[stype.find('[')+1:stype.find(']')] )
        if simple == 'free':
            return lambda x: cls.skipfree(x, count)
        return lambda x: cls.extractarray(x, cls.getextractor(simple), count)

    @classmethod
    def skipfree(cls, stream, count):
        stream.seek(count, os.SEEK_CUR)
        return None

    @classmethod
    def extractarray(cls, stream, simple, count):
        ret = []
        for i in range(count):
            ret.append( simple(stream) )
        return ret

    def __repr__(self):
        return "Record {0}\n    ".format(self.name) + "\n    ".join( map(str, self.fields) )

class Structure:
    def __init__(self):
        self.records = {}

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

def loadmeta(ymeta):
    strmeta = Structure()
    for yrname, yrec in ymeta['records'].items():
        strmeta.records[yrname] = PlainRecordMeta.loadmeta(yrname, yrec)
    return strmeta
