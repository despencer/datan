class Formatter:
    def __init__(self):
        self.default = lambda x: ""
        self.formatters = {}

    def get(self, typename):
        if typename in self.formatters:
            return self.formatters[typename]
        return self.default


def createdefault():
    form = Formatter()
    form.default = lambda x: str(x)
    form.formatters = { 'uint8':lambda x:'{:02X}'.format(x), 'uint16':lambda x:'{:04X}'.format(x), 
                        'uint32':lambda x:'{:08X}'.format(x), 'uint64':lambda x:'{:016X}'.format(x) }
    return form

default = createdefault()

def getdefault():
    return default