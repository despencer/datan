class StreamLookAhead:
    def __init__(self, source):
        self.source = source
        self.buffer = []
        self.source.seek(0)

    def next(self):
        if len(self.buffer) > 0:
            self.buffer.pop(0)
            return True
        else:
            items = self.source.read(1)
            if len(items) == 0:
                return False
            self.buffer.append(items[0])
            return True

    def getpos(self):
        return self.source.getpos() - len(self.buffer)

    def __getitem__(self, key):
        if not isinstance(key, int) or key < 0:
            raise Exception(f'Bad index {key}')
        if key < len(self.buffer):
            return self.buffer[key]
        self.buffer.extend(self.source.read( key + 1 - len(self.buffer) ))
        if key < len(self.buffer):
            return self.buffer[key]
        return None

class Parser:
    def __init__(self):
        self.source = None
        self.context = None
        self.start = None
        self.stream = None
        self.finish = None

    def transform(self, environ, data=None, operands=None):
        self.stream = StreamLookAhead(eval(self.source, environ))
        self.state = self.start
        self.finish = False
        if self.context != None and data == None:
            data = eval(self.context, environ)
        while not self.finish:
            action = self.state.default
            for a in self.state.actions:
                y = eval(a.condition, {'self':self})
                if eval(a.condition, {'self':self}):
                    action = a
                    break
            if data != None and action.function != None:
                getattr(data, action.function)(self.stream[0])
            self.state = action.nextstate
            action.action()

    def stall(self):
        ''' The parser expects something but haven't got it '''
        raise Exception(f'Parser get unexpected {self.stream[0]} in state {self.state.name}')

    def next(self):
        ''' Shifts to a next position in input stream '''
        self.stream.next()

    def stop(self):
        ''' Stops the parsing '''
        self.finish = True

class State:
    def __init__(self, name):
        self.name = name
        self.default = None
        self.actions = []

class Action:
    def __init__(self):
        self.condition = ""
        self.nextstate = None
        self.action = None
        self.function = None

class ParserLoader:
    def __init__(self, module):
        self.parser = Parser()
        self.states = {}
        self.module = module

    def getaction(self, ydef, default):
        if 'action' in ydef:
            return getattr(self.parser, ydef['action'])
        else:
            return default

    def loadstatedefault(self, state, ydef):
        state.default.action = self.getaction(ydef, self.parser.stall)
        state.default.nextstate = state

    def loadstate(self, ystate):
        state = self.states[ystate['state']]
        state.default = Action()
        self.loadstatedefault(state, ystate['default'])
        for yact in ystate['actions']:
            action = Action()
            action.condition = 'self.stream' + yact['on']
            if 'do' in yact:
                action.function = yact['do']
            action.action = self.getaction(yact, self.parser.next)
            action.nextstate = state
            state.actions.append(action)

    def loadmachine(self, ymachine):
        for ydef in ymachine:
            if 'state' in ydef:
                state = State(ydef['state'])
                self.states[state.name] = state
                if self.parser.start == None:
                    self.parser.start = state
        for ydef in ymachine:
            if 'state' in ydef:
                self.loadstate(ydef)

    @classmethod
    def load(cls, ymeta, module):
        loader = cls(module)
        loader.parser.source = ymeta['parse']
        if 'with' in ymeta:
            loader.parser.context = ymeta['with']
        loader.loadmachine(ymeta['machine'])
        return loader.parser

def loadparser(ymeta, module):
    return ParserLoader.load(ymeta, module)
