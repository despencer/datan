import os

class FieldMeta:
    def __init__(self):
        pass

    def __repr__(self):
        return self.name

class PlainRecord:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)

class PlainRecordMeta:
    def __init__(self):
        self.fields = []

    def extract(self, datafile):
        data = PlainRecord(self)
        for f in self.fields:
            setattr(data, f.name, f.extractor(datafile))
        return data

    def prettyprint(self, data):
        return self.name + ":\n"+"\n".join( map( lambda x: "    {0}: {1}".format(x.name, x.formatter(getattr(data, x.name))), self.fields) )

    @classmethod
    def loadmeta(cls, name, yrec, formatter):
        prec = PlainRecordMeta()
        prec.name = name
        for yfield in yrec:
            field = FieldMeta()
            field.name = yfield['field']
            field.extractor = cls.getextractor(yfield['type'])
            field.formatter = formatter.get(yfield['type'])
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
        self.start = None

    def extract(self, datafile):
        return self.start.extract(datafile)

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

def loadmeta(ymeta, formatter):
    strmeta = Structure()
    for yrname, yrec in ymeta['records'].items():
        strmeta.records[yrname] = PlainRecordMeta.loadmeta(yrname, yrec, formatter)
        if strmeta.start == None:
            strmeta.start = strmeta.records[yrname]
    return strmeta
