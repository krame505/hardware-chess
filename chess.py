import sys
sys.path.append("../bsc-contrib/Libraries/GenC/GenCMsg")
sys.path.append("bin")

import time
import threading
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
    return (whitePieces if p.color.tag == lib.Color_White else blackPieces)[pieceName] + '\uFE0E'

def strPosition(pos):
    return chr(ord('a') + pos.file) + str(8 - pos.rank)

def strMove(state, move):
    if move.tag == lib.Move_Move or move.tag == lib.Move_EnPassant or move.tag == lib.Move_Promote:
        if move.tag == lib.Move_Move:
            directMove = move.contents.Move
        elif move.tag == lib.Move_EnPassant:
            directMove = move.contents.EnPassant
        elif move.tag == lib.Move_Promote:
            directMove = move.contents.Promote
        fromPos = getattr(directMove, 'from')  # Can't write directMove.from since 'from' is a keyword in Python
        toPos = directMove.to
        fromSquare = state.board[fromPos.rank][fromPos.file]
        toSquare = state.board[toPos.rank][toPos.file]
        assert fromSquare.occupied
        assert fromSquare.piece.color.tag == state.turn.tag
        capture = toSquare.occupied or move.tag == lib.Move_EnPassant
        promo = strPiece(ffi.new("Piece *", {'color': fromSquare.piece.color, 'kind': directMove.kind})) if move.tag == lib.Move_Promote else ""
        ep = " e.p." if move.tag == lib.Move_EnPassant else ""
        return strPiece(fromSquare.piece) + strPosition(fromPos) + ("x" if capture else "-") + strPosition(toPos) + promo + ep
    elif move.tag == lib.Move_Castle:
        return "0-0" if move.contents.Castle.kingSide else "0-0-0"

def strOutcome(outcome):
    if outcome == lib.Outcome_Check:
        return " - Check"
    elif outcome == lib.Outcome_CheckMate:
        return " - Checkmate"
    elif outcome == lib.Outcome_Draw:
        return " - Draw"
    else:
        return ""

class ChessClient(msgclient.Client):
    def __init__(self, serial, callback, timeout=5):
        super().__init__("ChessMsgs", ffi, lib, serial)
        self.callback = callback
        self.event = "Initialized"
        self.state = None
        self._movesAccum = []
        self.moves = []
        self.outcome = None
        self.whiteAI = False
        self.blackAI = True
        self.timeout = timeout
        self.depth = 2
        self.bestMove = None
        self.depthBestMove = None
        self.depthBestScore = None
        self.moveScores = []
        self.searchTimer = None
        self.queryThread = None
        self.cancelQueries = False

    def start(self):
        super().start()
        self.updateState()
        self.event = "Server restarted"
        self.callback(self.event)

    def notify(self):
        update = False
        while state := self.get("state"):
            self.state = state
            print("Got state update")
            self.put("command", ffi.new("Command *", {'tag': lib.Command_Query, 'contents': {'Query': {'rid': 0, 'depth': 1, 'resetAlpha': True, 'getMoves': True}}})[0])
            #update = True  # No need to update when state is recieved, as there will be an update for moves/outcome
        while move := self.get("moves"):
            if move.tag == lib.MoveResponse_NextMove:
                #print("Got move", strMove(self.state, move.contents.NextMove))
                self._movesAccum.append(ffi.new("Move *", move.contents.NextMove)[0])
            elif move.tag == lib.MoveResponse_NoMove:
                #print("Got no more moves")
                self.moves = self._movesAccum
                self._movesAccum = []
                update = True
        while searchResult := self.get("searchResult"):
            if searchResult.rid == 0:
                self.outcome = searchResult.outcome.tag
                if self.outcome != lib.Outcome_NoOutcome:
                    update = True
                if ((self.outcome == lib.Outcome_NoOutcome or self.outcome == lib.Outcome_Check) and
                    ((self.state.turn.tag == lib.Color_Black and self.blackAI) or (self.state.turn.tag == lib.Color_White and self.whiteAI))):
                    self.startSearch()
            elif self.searchTimer is None:
                print("Ignoring post-cancellation search result")
            elif searchResult.outcome.tag == lib.Outcome_Invalid:
                print("Search depth out of bounds")
                self.searchTimer.cancel()
                self.searchTimer = None
                self.sendSearchMove()
            else:
                score = -searchResult.score
                move = self.moves[searchResult.rid - 1]
                print("Got search result", strMove(self.state, move), score)
                self.moveScores.append(score)
                if self.depthBestScore is None or score > self.depthBestScore:
                    self.depthBestScore = score
                    self.depthBestMove = move

                if self.queryThread is not None and searchResult.rid == len(self.moves):
                    print("Got all move results")
                    self.queryThread.join()
                    self.queryThread = None
                    self.bestMove = self.depthBestMove
                    print("Best move for depth", self.depth, "is", strMove(self.state, self.bestMove), self.depthBestScore)
                    self.depth += 1
                    self.moves = [m for _, m in sorted(zip(self.moveScores, self.moves), reverse=True)]
                    print("Deepening to depth", self.depth)
                    self.startDepthSearch()

        if update:
            self.callback(self.event + strOutcome(self.outcome))

    def startSearch(self):
        if self.searchTimer is None:
            print("Getting search move for", ffi.string(ffi.cast('enum Color_tag', self.state.turn.tag)))
            self.depth = 2
            self.bestMove = None
            self.startDepthSearch()
            self.searchTimer = threading.Timer(self.timeout, self.sendSearchMove)
            self.searchTimer.start()

    def startDepthSearch(self):
        self.queryThread = threading.Thread(target=self.sendQueries)
        self.queryThread.start()

    def sendQueries(self):
        self.depthBestMove = None
        self.depthBestScore = None
        self.moveScores = []
        self.cancelQueries = False

        for i, move in enumerate(self.moves):
            if self.cancelQueries:
                break
            self.put("command", ffi.new("Command *", {
                'tag': lib.Command_Query,
                'contents': {
                    'Query': {
                        'rid': i + 1,
                        'move': {'tag': lib.Maybe_Move_Valid, 'contents': {'Valid': move}},
                        'depth': self.depth - 1,
                        'resetAlpha': i == 0,
                        'getMoves': False
                    }
                }
            })[0])

    def sendSearchMove(self):
        self.searchTimer = None
        if self.bestMove is None:
            print("Search move not ready")
            self.cancelSearch()
            self.startSearch()  # Retry
        else:
            print("Sending best move")
            self.cancelSearch()
            self.put("command", ffi.new("Command *", {'tag': lib.Command_Move, 'contents': {'Move': self.bestMove}})[0])
            self.event = strMove(self.state, self.bestMove)
            self.bestMove = None
            self.outcome = None

    def cancelSearch(self):
        self.put("command", ffi.new("Command *", {'tag': lib.Command_CancelSearch})[0])
        if self.searchTimer is not None:
            self.searchTimer.cancel()
            self.searchTimer = None
        self.cancelQueries = True
        self.queryThread.join()
        self.queryThread = None

    def updateState(self):
        self.put("command", ffi.new("Command *", {'tag': lib.Command_GetState})[0])

    def jsonStatus(self):
        if self.state:
            return json.dumps({
                'state': cdata_dict(self.state),
                'moves': list(map(cdata_dict, self.moves)),
                'whiteAI': self.whiteAI,
                'blackAI': self.blackAI,
                'timeout': self.timeout,
            })

    def move(self, i):
        if (self.state.turn.tag == lib.Color_Black and not self.blackAI) or (self.state.turn.tag == lib.Color_White and not self.whiteAI):
            self.put("command", ffi.new("Command *", {'tag': lib.Command_Move, 'contents': {'Move': self.moves[i]}})[0])
            self.event = strMove(self.state, self.moves[i])
            self.outcome = None

    def reset(self):
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Reset})[0])
        self.updateState()
        self.event = "Game reset"
        self.outcome = None

    def config(self, whiteAI, blackAI):
        self.whiteAI = whiteAI
        self.blackAI = blackAI
        self.cancelSearch()
        self.updateState()
