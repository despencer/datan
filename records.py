import yaml
import os
import importlib

class FieldReader:
    def __init__(self):
        pass

    def __repr__(self):
        return self.name

class PlainRecord:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)

class PlainRecordReader:
    def __init__(self):
        self.fields = []

    def read(self, datafile):
        data = PlainRecord(self)
        for f in self.fields:
            setattr(data, f.name, f.reader(datafile))
        return data

    def prettyprint(self, data):
        return self.name + ":\n"+"\n".join( map( lambda x: "    {0}: {1}".format(x.name, x.formatter(getattr(data, x.name))), self.fields) )

    @classmethod
    def loadreader(cls, name, yrec, loader):
        prec = PlainRecordReader()
        prec.name = loader.structure.namespace + name
        for yfield in yrec:
            field = FieldReader()
            field.name = yfield['field']
            field.reader = loader.getreader(yfield['type'], LoaderXRef(field, 'reader'))
            field.formatter = loader.formatter.get(yfield['type'])
            prec.fields.append(field)
        return prec

    @classmethod
    def skipfree(cls, stream, count):
        stream.seek(count, os.SEEK_CUR)
        return None


class ArrayReader:
    def __init__(self, count):
        self.count = count

    def read(self, stream):
        ret = []
        for i in range(self.count):
            ret.append( self.simple(stream) )
        return ret

class Structure:
    def __init__(self):
        self.records = {}
        self.start = None
        self.module = None

    def read(self, datafile):
        return self.start.read(datafile)

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

class LoaderXRef:
    def __init__(self, field, reader):
        self.field = field
        self.reader = reader

    def resolve(self, records):
        setattr(self.field, self.reader, records[self.typename].read)

class Loader:
    def __init__(self, filename, formatter):
        self.filename = filename
        self.formatter = formatter
        self.xrefs = []
        self.simple = { 'uint8': lambda x: int.from_bytes(x.read(1)),
            'uint16': lambda x: int.from_bytes(x.read(2), 'little'),
            'uint32': lambda x: int.from_bytes(x.read(4), 'little'),
            'uint64': lambda x: int.from_bytes(x.read(8), 'little') }

    def load(self):
        with open(self.filename) as strfile:
            ystr = yaml.load(strfile, Loader=yaml.Loader)
            self.structure = Structure()
            self.structure.module = self.loadpyfile(self.filename)
            self.structure.namespace = ystr['namespace']+'.' if 'namespace' in ystr else ''
            for yrname, yrec in ystr['types'].items():
                reader = PlainRecordReader.loadreader(yrname, yrec, self)
                self.structure.records[reader.name] = reader
                if self.structure.start == None:
                    self.structure.start = reader
        for xref in self.xrefs:
            xref.resolve(self.structure.records)
        return self.structure

    def getreader(self, stype, xref):
        if stype.find('[') >=0 :
            return self.getarrayreader(stype)
        if stype in self.simple:
            return self.simple[stype]
        stype = self.structure.namespace + stype
        if stype in self.structure.records:
            return self.structure.records[stype].reader
        xref.typename = stype
        self.xrefs.append(xref)
        return None

    def getarrayreader(self, stype):
        simple = stype[:stype.find('[')]
        count = int( stype[stype.find('[')+1:stype.find(']')] )
        if simple == 'free':
            return lambda x: PlainRecordReader.skipfree(x, count)
        array = ArrayReader(count)
        array.simple = self.getreader(simple, LoaderXRef(array, 'simple'))
        return array.read

    def loadpyfile(self, filename):
        pyfile = os.path.splitext(self.filename)[0] + '.py'
        pymodule = os.path.splitext(self.filename)[0].replace('/','.')
        if os.path.exists(pyfile):
            print(pyfile, 'loaded')
            return importlib.import_module(pymodule)
        else:
            print(pyfile, 'is not exist, skipped')
            return None


def loadmeta(filename, formatter):
    loader = Loader(filename, formatter)
    return loader.load()
