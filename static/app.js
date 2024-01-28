
var events = new EventSource('/events')
events.onmessage = function (e) {
  console.log("Got event", e)
  lastEvent.innerHTML = e.data
  update()
}
events.onerror = function() {
  console.log("EventSource failed.")
}

const whitePieces = {'King': '♔', 'Queen': '♕', 'Rook': '♖', 'Bishop': '♗', 'Knight': '♘', 'Pawn': '♙'}
const blackPieces = {'King': '♚', 'Queen': '♛', 'Rook': '♜', 'Bishop': '♝', 'Knight': '♞', 'Pawn': '♟'}

var state = null
var moves = []

function moveFrom(move) {
  if (move.tag == 'Move' || move.tag == 'EnPassant' || move.tag == 'Promote') {
    return move.contents.from
  } else if (move.tag == 'Castle') {
    return {rank: state.turn == 'Black'? 0 : 7, file: 4}
  }
}

function moveTo(move) {
  if (move.tag == 'Move' || move.tag == 'EnPassant' || move.tag == 'Promote') {
    return move.contents.to
  } else if (move.tag == 'Castle') {
    return {rank: state.turn == 'Black'? 0 : 7, file: move.contents.kingSide? 6 : 2}
  }
}

function update() {
  $.ajax({url: "status.json", cache: false, timeout: 3000}).done(
    function (json) {
      s = JSON.parse(json)
      console.log("Got status", s)
      state = s.state
      moves = s.moves

      whiteAI.checked = s.whiteAI
      blackAI.checked = s.blackAI
      timeout.value = s.timeout
      turn.innerHTML = state.turn + "'s turn"
      
      while (board.rows.length) {
        board.deleteRow(0)
      }
      for (i = 0; i < 10; i++) {
        board.insertRow()
        for (j = 0; j < 10; j++) {
          board.rows[i].insertCell(0)
        }
      }
      for (i = 0; i < 8; i++) {
        board.rows[0].cells[i + 1].innerHTML = (i + 10).toString(36)
        board.rows[0].cells[i + 1].className = "topBottomCell"
        board.rows[9].cells[i + 1].innerHTML = (i + 10).toString(36)
        board.rows[9].cells[i + 1].className = "topBottomCell"
        board.rows[i + 1].cells[0].innerHTML = 8 - i
        board.rows[i + 1].cells[0].className = "sideCell"
        board.rows[i + 1].cells[9].innerHTML = 8 - i
        board.rows[i + 1].cells[9].className = "sideCell"
      }
      for (rank = 0; rank < 8; rank++) {
        for (file = 0; file < 8; file++) {
          const pos = {rank: rank, file: file}
          var cell = board.rows[rank + 1].cells[file + 1]
          cell.style.backgroundColor = (rank + file) % 2? '#654321' : 'tan'
          cell.className = "boardCell"
          cell.onclick = function () { handleSelect(pos) }
          square = state.board[rank][file]
          if (square.tag == 'Valid') {
            cell.innerHTML = blackPieces[square.contents.kind]// + "\uFE0E"
            cell.style.color = 'transparent'
            cell.style.textShadow = '0 0 0 ' + square.contents.color
          }
        }
      }
    })
}

function doMove(i) {
  $.ajax({url: "move/" + i})
}

function reset() {
  $.ajax({url: "reset"})
}

function updateConfig() {
  $.ajax({url: "config/" + whiteAI.checked + "," + blackAI.checked})
}

function updateTimeout() {
  $.ajax({url: "timeout/" + timeout.value})
}

var selected = null
var candidates = []
function handleSelect(pos) {
  for (rank = 0; rank < 8; rank++) {
    for (file = 0; file < 8; file++) {
      cell = board.rows[rank + 1].cells[file + 1]
      cell.style.backgroundColor = (rank + file) % 2? '#654321' : 'tan'
    }
  }
  square = state.board[pos.rank][pos.file]
  if (square.tag == 'Valid' && square.contents.color == state.turn && pos != selected) {
    selected = pos
    board.rows[pos.rank + 1].cells[pos.file + 1].style.backgroundColor = 'cyan'
    candidates = []
    for (i = 0; i < moves.length; i++) {
      from = moveFrom(moves[i])
      if (from.rank == pos.rank && from.file == pos.file) {
        to = moveTo(moves[i])
        board.rows[to.rank + 1].cells[to.file + 1].style.backgroundColor = 'cyan'
        candidates.push(i)
      }
    }
  } else if (selected != null) {
    var narrowed = []
    candidates.forEach(function (i) {
      to = moveTo(moves[i])
      if (to.rank == pos.rank && to.file == pos.file) {
        narrowed.push(i)
      }
    })
    if (narrowed.length > 0 && moves[narrowed[0]].tag == 'Promote') {
      var promoKind = prompt("Enter kind of promoted piece", "Queen")
      narrowed = narrowed.filter(move => promoKind != null && moves[move].contents.kind.toLowerCase() == promoKind.toLowerCase())
    }
    if (narrowed.length > 0) {
      doMove(narrowed[0])
    }
    selected = null
  }
}
