import yaml
import os
import importlib

class FieldReader:
    def __init__(self):
        self.postread = []

    def __repr__(self):
        return self.name

class PlainRecord:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)

    def getfields(self):
        return self._meta.getfields(self)

class PlainRecordReader:
    def __init__(self):
        self.fields = []

    def read(self, datafile):
        data = PlainRecord(self)
        for f in self.fields:
            fvalue = f.reader(datafile)
            for pr in f.postread:
                pr(fvalue)
            setattr(data, f.name, fvalue)
        return data

    def prettyprint(self, data):
        return self.name + ":\n"+"\n".join( map( lambda x: "    {0}: {1}".format(x.name, self.printfield(x, getattr(data, x.name)) ), self.fields) )

    def printfield(self, field, data):
        ff = field.formatter(data)
        if '\n' in ff:
            return '\n'.join(  map(lambda x: '    '+x, ff.split('\n'))  )[4:]
        return ff

    def getfields(self, data):
        ret = {}
        for f in self.fields:
            ret[f.name] = getattr(data, f.name)
        return ret

    @classmethod
    def loadreader(cls, name, yrec, loader):
        prec = PlainRecordReader()
        prec.name = loader.structure.namespace + name
        for yfield in yrec:
            field = FieldReader()
            field.name = yfield['field']
            field.reader = loader.getreader(yfield['type'], LoaderXRef(field, 'reader'))
            field.formatter = loader.formatter.get(yfield['type'])
            if 'params' in yfield:
                for yparam in yfield['params']:
                    cls.loadparam(loader, field, yparam)
            prec.fields.append(field)
        return prec

    @classmethod
    def loadparam(cls, loader, field, yparam):
        ll = LazyLoader(yparam['name'], yparam['reference'])
        loader.addlazy(ll)
        field.postread.append( lambda value: setattr(value.__class__, yparam['name'], ll)  )

    @classmethod
    def skipfree(cls, stream, count):
        stream.seek(count, os.SEEK_CUR)
        return None

    @classmethod
    def readbytes(cls, stream, count):
        return stream.read(count)

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
        self.lazies = []

    def read(self, datafile):
        root = self.start.read(datafile)
        rf = root.getfields()
        for ll in self.lazies:
            ll.root = rf
        return root

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

class LoaderXRef:
    def __init__(self, field, reader):
        self.field = field
        self.reader = reader

    def resolve(self, records):
        if self.typename not in records:
            raise Exception('Type ' + self.typename + ' not found')
        setattr(self.field, self.reader, records[self.typename].read)

class LazyLoader:
    def __init__(self, name, xref):
        self.name = name
        self.root = None
        self.xref = xref

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = eval(self.xref, self.root)
            setattr(instance, self.name, value)
            return value

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
            if self.structure.module != None:
                self.structure.module.loadtypes(self)
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
            return self.structure.records[stype].read
        xref.typename = stype
        self.xrefs.append(xref)
        return None

    def getarrayreader(self, stype):
        simple = stype[:stype.find('[')]
        count = int( stype[stype.find('[')+1:stype.find(']')] )
        if simple == 'free':
            return lambda x: PlainRecordReader.skipfree(x, count)
        elif simple == 'bytes':
            return lambda x: PlainRecordReader.readbytes(x, count)
        array = ArrayReader(count)
        array.simple = self.getreader(simple, LoaderXRef(array, 'simple'))
        return array.read

    def addtypes(self, readers):
        for typename, loader in readers.items():
            self.structure.records[self.structure.namespace + typename] = loader(self)

    def addlazy(self, lazy):
        self.structure.lazies.append(lazy)

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
