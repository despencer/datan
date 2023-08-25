class Formatter:
    def __init__(self):
        self.default = lambda x: ""
        self.formatters = {}
        self.rules = []
        self.parameters = {}

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
            ret += '{:08X}\n'.format(self.pos+i) + indent(record(data[i])) + '\n'
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
    form.parameters['stream'] = stream
    return form

default = createdefault()

def getdefault():
    return default