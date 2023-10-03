import yaml
import records

class Formatter:
    def __init__(self):
        self.default = lambda x: ""
        self.formatters = {}
        self.rules = []
        self.parameters = {}
        self.overrides = {}

    def get(self, typename):
        if typename in self.formatters:
            return self.formatters[typename]
        for r in self.rules:
            f = r(typename)
            if f != None:
                return f
        return self.default

    def streamformatter(self, stream):
        return 'A stream'

    def addformatters(self, formatters):
        for name, formatter in formatters.items():
            self.formatters[name] = formatter.format
            for pname, param in self.parameters.items():
                if hasattr(formatter, pname):
                    param.append(formatter)

    def load(self, filename, strdef):
        with open(filename) as fmtfile:
            yfmt = yaml.load(fmtfile, Loader=yaml.Loader)
            pyfile = records.loadpyfile(strdef, filename)
            if pyfile != None and 'options' in yfmt:
                pyfile.loadformatters(self, yfmt['options'])
            if 'formatters' in yfmt:
                for yobject, yformatter in yfmt['formatters'].items():
                    self.overrides[yobject] = self.formatters[yformatter]

    def apply(self, data):
        context = data.getfields()
        for oref, formatter in self.overrides.items():
            eval(oref, context)._meta.formatter = formatter

class StreamFormatter:
    def __init__(self):
        self.pos = 0
        self.size = 256
        self.line = 16

    def format(self, datafile):
        ret = ''
        datafile.seek(self.pos)
        data = datafile.read(self.size)
        for i in range( min(self.size,len(data)) ):
            if i%self.line == 0:
                ret += '{:08X}'.format(self.pos+i)
            if i%4 == 0:
                 ret += ' '
            ret += ' {:02X}'.format(data[i])
            if i%self.line == (self.line-1):
                ret += '\n'
        return ret

class RecordStreamFormatter:
    def __init__(self):
        self.pos = 0
        self.size = 16

    def format(self, datafile, record=None):
        ret = ''
        datafile.seek(self.pos)
        data = datafile.read(self.size)
        if record is None:
            record = str
        for i in range( min(self.size,len(data)) ):
            ret += '{:08X}'.format(self.pos+i) + indent(record(data[i])) + '\n'
        return ret

def arrayformatter(a, base):
    if len(a) <= 10:
        return '[' + ' '.join( map( base, a )) + ']'
    return '[' + ' '.join( map( base, a[:5] )) + ' ... ' + ' '.join( map( base, a[-5:] ))+ ']'

def indent(text):
    if '\n' not in text:
        return '    '+text
    return '\n    '+'\n'.join(  map(lambda x: '    '+x, text.split('\n'))  )[4:]

def formatsub(data, formatter):
    return indent(formatter(data))

def freeformatter(f):
    return 'free'

def checkarray(formatter, typename):
    if '[' not in typename:
        return None
    base = typename[:typename.find('[')]
    if base == 'free':
        return freeformatter
    return lambda x: arrayformatter(x, formatter.get(base))

class FormatterParameter:
    def __init__(self, name, *formatters):
        self.name = name
        self.formatters = [ *formatters ]

    def append(self, formatter):
        self.formatters.append(formatter)

    def set(self, value):
        for s in self.formatters:
            setattr(s, self.name, value)

def createdefault():
    form = Formatter()
    form.default = lambda x: str(x)
    stream = StreamFormatter()
    recordstream = RecordStreamFormatter()
    form.formatters = { 'uint8':lambda x:'{:02X}'.format(x), 'uint16':lambda x:'{:04X}'.format(x),
                        'uint32':lambda x:'{:08X}'.format(x), 'uint64':lambda x:'{:016X}'.format(x),
                        'stream' :lambda x: stream.format(x), 'recordstream' :lambda x, **kv: recordstream.format(x, **kv),
                        'bytes':lambda x:'{:02X}'.format(x) }
    form.rules.extend( [ lambda x: checkarray(form, x) ] )
    form.parameters['pos'] = FormatterParameter('pos', stream, recordstream )
    form.parameters['size'] = FormatterParameter('size', stream, recordstream )
    return form

default = createdefault()

def getdefault():
    return default