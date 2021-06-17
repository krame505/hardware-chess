#!/usr/bin/env python3

import sys
sys.path.append("../bsc-contrib/Libraries/GenC/GenCMsg")
sys.path.append("bin")

import msgclient
from _chess_test import ffi, lib

import serial
import time

class ChessTestClient(msgclient.Client):
    def __init__(self, serial, config1, config2, randSteps, depth):
        super().__init__("ChessTestMsgs", ffi, lib, serial)
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Config, 'contents': {'Config': {'white': config1, 'black': config2}}})[0])
        self.randSteps = randSteps
        self.depth = depth
        self.awaiting = 0
        self.wins1 = 0
        self.wins2 = 0
        self.draws = 0
        self.errors = 0

    def notify(self):
        while outcome := self.get("outcome"):
            if outcome.tag == lib.TrialOutcome_Win:
                if outcome.contents.Win.tag == lib.Color_White:
                    self.wins1 += 1
                elif outcome.contents.Win.tag == lib.Color_Black:
                    self.wins2 += 1
            elif outcome.tag == lib.TrialOutcome_Draw:
                self.draws += 1
            elif outcome.tag == lib.TrialOutcome_Error:
                self.errors += 1
            self.awaiting -= 1
            print("{:3d} {:3d} {:3d} {:3d}".format(self.wins1, self.wins2, self.draws, self.errors))

    def runTrial(self):
        self.awaiting += 1
        self.put("command", ffi.new("Command *", {'tag': lib.Command_RunTrial, 'contents': {'RunTrial': {'randSteps': self.randSteps, 'depth': self.depth}}})[0])


config1 = {'checkValue': 3, 'centerControlValue': 1, 'castleValue': 2, 'pawnStructureValueDiv': 2}
config2 = {'checkValue': 3, 'centerControlValue': 1, 'castleValue': 2, 'pawnStructureValueDiv': 2}
randSteps = 1
depth = 2
trials = 1000

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit("Expected serial port name")

    ser = serial.Serial(sys.argv[1], 115200)
    client = ChessTestClient(ser, config1, config2, randSteps, depth)
    client.start()
    for i in range(trials):
        client.runTrial()
    while client.awaiting:
        time.sleep(1)
