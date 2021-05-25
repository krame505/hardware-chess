
function pieceChar(kind) {
  if (kind == 'King') return '♚'
  else if (kind == 'Queen') return '♛'
  else if (kind == 'Rook') return '♜'
  else if (kind == 'Bishop') return '♝'
  else if (kind == 'Knight') return '♞'
  else if (kind == 'Pawn') return '♟'
}

function update() {
  $.ajax({url: `status.json`, cache: false, timeout: 3000}).done(
    function (json) {
      s = JSON.parse(json)
      console.log("Got status", s)
      state = s.state
      moves = s.moves
      console.log(moves)

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
        board.rows[9].cells[i + 1].innerHTML = (i + 10).toString(36)
        board.rows[i + 1].cells[0].innerHTML = 8 - i
        board.rows[i + 1].cells[9].innerHTML = 8 - i
      }
      for (rank = 0; rank < 8; rank++) {
        for (file = 0; file < 8; file++) {
          cell = board.rows[rank + 1].cells[file + 1]
          cell.style.backgroundColor = (rank + file) % 2? '#654321' : 'tan'
          square = state.board[rank][file]
          if (square.occupied) {
            cell.innerHTML = pieceChar(square.piece.kind)
            cell.style.color = square.piece.color
          }
        }
      }
    })
}

var source = new EventSource('/events')
source.onmessage = function (event) {
  update()
}

function init() {
  update()
}
