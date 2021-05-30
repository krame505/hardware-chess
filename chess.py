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

whitePieces = {'King': '♔', 'Queen': '♕', 'Rook': '♖', 'Bishop': '♗', 'Knight': '♘', 'Pawn': '♙'}
blackPieces = {'King': '♚', 'Queen': '♛', 'Rook': '♜', 'Bishop': '♝', 'Knight': '♞', 'Pawn': '♟'}

def strPiece(p):
    pieceName = ffi.string(ffi.cast('enum PieceKind_tag', p.kind.tag))[len('PieceKind_'):]
    return (whitePieces if p.color.tag == lib.Color_White else blackPieces)[pieceName]

def strPosition(pos):
    return chr(ord('a') + pos.file) + str(8 - pos.rank)

def strMove(state, move):
    if move.tag == lib.Move_Move or move.tag == lib.Move_Promote:
        directMove = move.contents.Move if move.tag == lib.Move_Move else move.contents.Promote
        fromPos = getattr(directMove, 'from')
        toPos = directMove.to
        fromSquare = state.board[fromPos.rank][fromPos.file]
        toSquare = state.board[toPos.rank][toPos.file]
        assert fromSquare.occupied
        assert fromSquare.piece.color.tag == state.turn.tag
        capture = toSquare.occupied
        promo = strPiece(ffi.new("Piece *", {'color': fromSquare.piece.color, 'kind': directMove.kind})) if move.tag == lib.Move_Promote else ""
        return strPiece(fromSquare.piece) + strPosition(fromPos) + ("x" if capture else "-") + strPosition(toPos) + promo
    elif move.tag == lib.Move_Castle:
        return "0-0" if move.contents.Castle.kingSide else "0-0-0"

class ChessClient(msgclient.Client):
    def __init__(self, serial, callback):
        super().__init__("ChessMsgs", ffi, lib, serial)
        self.callback = callback
        self.event = "Initialized"
        self.state = None
        self._movesAccum = []
        self.moves = []
        self.outcome = None
        self.whiteAI = False
        self.blackAI = False

    def start(self):
        super().start()
        self.put("command", ffi.new("Command *", {'tag': lib.Command_GetState})[0])

    def notify(self):
        update = False
        while state := self.get("state"):
            self.state = state
            #update = True  # No need to update when state is recieved, as there will be an update for moves/outcome
            if (state.turn.tag == lib.Color_Black and self.blackAI) or (state.turn.tag == lib.Color_Black and self.blackAI):
                self.put("command", ffi.new("Command *", {'tag': lib.Command_GetSearchMove})[0])
        while move := self.get("moves"):
            if move.tag == lib.MoveResponse_NextMove:
                self._movesAccum.append(ffi.new("Move *", move.contents.NextMove)[0])
            elif move.tag == lib.MoveResponse_NoMove:
                self.moves = self._movesAccum
                self._movesAccum = []
                update = True
        while outcome := self.get("outcome"):
            self.outcome = outcome.tag
            if self.outcome == lib.Outcome_Check:
                self.event += " - Check"
                update = True
            elif self.outcome == lib.Outcome_CheckMate:
                self.event += " - Checkmate"
                update = True
            elif self.outcome == lib.Outcome_Draw:
                self.event += " - Draw"
                update = True
        while searchMove := self.get("searchMove"):
            self.put("command", ffi.new("Command *", {'tag': lib.Command_Move, 'contents': {'Move': searchMove}})[0])
            self.event = strMove(self.state, searchMove)

        if update:
            self.callback(self.event)


    def jsonStatus(self):
        if self.state:
            return json.dumps({'state': cdata_dict(self.state), 'moves': list(map(cdata_dict, self.moves))})

    def move(self, i):
        self.event = strMove(self.state, self.moves[i])
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Move, 'contents': {'Move': self.moves[i]}})[0])

    def reset(self):
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Reset})[0])
        self.event = "Game reset"

    def config(self, whiteAI, blackAI):
        self.whiteAI = whiteAI
        self.blackAI = blackAI
