class Formatter:
    def __init__(self):
        self.default = lambda x: ""
        self.formatters = {}
        self.rules = []

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

def arrayformatter(a, base):
    if len(a) <= 10:
        return '[' + ' '.join( map( base, a )) + ']'
    return '[' + ' '.join( map( base, a[:5] )) + ' ... ' + ' '.join( map( base, a[-5:] ))+ ']'

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
    form.formatters = { 'uint8':lambda x:'{:02X}'.format(x), 'uint16':lambda x:'{:04X}'.format(x), 
                        'uint32':lambda x:'{:08X}'.format(x), 'uint64':lambda x:'{:016X}'.format(x),
                        'stream' :lambda x: form.streamformatter(x) }
    form.rules.extend( [ lambda x: checkarray(form, x) ] )
    return form

default = createdefault()

def getdefault():
    return default