#!/usr/bin/env python3

import chess
import serial
import sys
import queue

if len(sys.argv) <= 1:
    sys.exit("Expected serial port name")

ser = serial.Serial(sys.argv[1], 115200)

eventQueue = queue.Queue()

client = chess.ChessClient(ser, eventQueue.put)
client.start()

from flask import Flask, render_template, redirect, Response
app = Flask(__name__)
app.debug = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status.json")
def status():
    return client.jsonStatus()

@app.route("/events")
def events():
    def eventStream():
        while True:
            # wait for event to be available, then push it
            yield 'data: {}\n\n'.format(eventQueue.get())
    return Response(eventStream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, use_reloader=False)
