#!/usr/bin/env python3

import chess
import serial
import sys
import queue

if len(sys.argv) <= 1:
    sys.exit("Expected serial port name")

ser = serial.Serial(sys.argv[1], 115200)

eventQueues = []
def putEvent(e):
    for q in eventQueues:
        q.put(e)

client = chess.ChessClient(ser, putEvent)
client.start()

from flask import Flask, render_template, redirect, Response
app = Flask(__name__)
app.debug = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status.json")
def status():
    if s := client.jsonStatus():
        return s
    else:
        return Response(status=503)

@app.route("/move/<i>")
def move(i):
    client.move(int(i))
    return ""

@app.route("/reset")
def reset():
    client.reset()
    return ""

@app.route("/events")
def events():
    def eventStream():
        eventQueue = queue.Queue()
        eventQueues.append(eventQueue)
        while True:
            # wait for event to be available, then push it
            event = eventQueue.get()
            yield 'data: {}\n\n'.format(event)
    return Response(eventStream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, use_reloader=False)
