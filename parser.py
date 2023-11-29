class Collector:
    def __init__(self, first):
        self.data = [ first ]

    def append(self, item):
        self.data.append(item)

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

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
        self.nodes = []

    def transform(self, environ, data=None, operands=None):
        self.stream = StreamLookAhead(eval(self.source, environ))
        if self.context != None and data == None:
            data = eval(self.context, environ)
        self.nodes = [ Node(self.start, data) ]
        while len(self.nodes) > 0:
            top = self.nodes[-1]
            action = top.state.default
            for a in top.state.actions:
                y = eval(a.condition, {'self':self})
                if eval(a.condition, {'self':self}):
                    action = a
                    break
            top.call(action.function, self.stream[0])
            if action.push != None:
                self.push(action.push)
            action.action()

    def pop(self):
        if len(self.nodes) > 1:
            self.nodes[-2].call(self.nodes[-1].onpop, self.nodes[-1].context)
        self.nodes.pop()

    def push(self, pushst):
        node = Node(pushst.nextstate, self.nodes[-1].call(pushst.context, self.stream[0]) )
        node.onpop = pushst.onpop
        self.nodes.append(node)

    def stall(self):
        ''' The parser expects something but haven't got it '''
        raise Exception(f'Parser get unexpected {self.stream[0]} in state {self.state.name}')

    def next(self):
        ''' Shifts to a next position in input stream '''
        self.stream.next()

    def stop(self):
        ''' Stops the parsing '''
        while(len(self.nodes)):
            self.pop()

class State:
    def __init__(self, name):
        self.name = name
        self.default = None
        self.actions = []

class Node:
    def __init__(self, state, context):
        self.state = state
        self.context = context
        self.onpop = None

    def call(self, function, operand):
        if self.context != None and function != None:
            return getattr(self.context, function)(operand)

class Push:
    def __init__(self):
        self.nextstate = None
        self.context = None
        self.onpop = None

class Action:
    def __init__(self):
        self.condition = ""
        self.action = None
        self.function = None
        self.push = None

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

    def loadpush(self, action, ypush):
        action.push = Push()
        action.push.nextstate = self.states[ypush['next']]
        action.push.context = ypush['with']
        if 'pop' in ypush:
            action.push.onpop = ypush['pop']

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
            if 'push' in yact:
                self.loadpush(action, yact['push'])
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

def collector(first):
    return Collector(first)