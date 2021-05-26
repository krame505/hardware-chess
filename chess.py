import sys
sys.path.append("../bsc-contrib/Libraries/GenC/GenCMsg")
sys.path.append("bin")

import json
import msgclient
from _chess import ffi, lib

def cdata_dict(cd, ty=None):
    if isinstance(cd, ffi.CData):
        ty = ffi.typeof(cd)
    if ty.kind == 'array':
        return [cdata_dict(x, ty.item) for x in cd]
    elif ty.kind == 'struct':
        fields = dict(ty.fields)
        if 'tag' in fields:
            tagName = ffi.string(ffi.cast(fields['tag'].type, cd.tag))[len(ty.cname.split("struct ")[1]) + 1:]
            if 'contents' in fields:
                unionFields = dict(fields['contents'].type.fields)
                if tagName in unionFields:
                    return {'tag': tagName, 'contents': cdata_dict(getattr(cd.contents, tagName), unionFields[tagName].type)}
            return tagName
        else:
            return {k: cdata_dict(getattr(cd, k), f.type) for k, f in ty.fields}
    elif ty.kind == 'enum':
        return ffi.string(ffi.cast(ty, cd))
    elif ty.kind == 'primitive':
        return cd
    else:
        raise ValueError("C type {} cannot be converted to dict representation".format(ty.cname))

class ChessClient(msgclient.Client):
    def __init__(self, serial, callback):
        super().__init__("ChessMsgs", ffi, lib, serial)
        self.callback = callback
        self.event = "Initialized"
        self.state = None
        self._movesAccum = []
        self.moves = []

    def start(self):
        super().start()
        self.put("command", ffi.new("Command *", {'tag': lib.Command_GetState})[0])

    def notify(self):
        updated = False
        while state := self.get("state"):
            self.state = state
            updated = True
        while move := self.get("moves"):
            if move.tag == lib.MoveResponse_NextMove:
                self._movesAccum.append(ffi.new("Move *", move.contents.NextMove)[0])
            elif move.tag == lib.MoveResponse_NoMove:
                self.moves = self._movesAccum
                self._movesAccum = []
                self.callback(self.event)

    def jsonStatus(self):
        if self.state:
            return json.dumps({'state': cdata_dict(self.state), 'moves': list(map(cdata_dict, self.moves))})

    def move(self, i):
        self.event = "Move " + str(i)
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Move, 'contents': {'Move': self.moves[i]}})[0])

    def reset(self):
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Reset})[0])
        self.event = "Game reset"
