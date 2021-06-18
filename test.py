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
        self.config1 = config1
        self.config2 = config2
        self.randSteps = randSteps
        self.depth = depth
        self.awaiting = 0
        self.wins1 = 0
        self.wins2 = 0
        self.draws = 0
        self.errors = 0
        self.white1 = True

    def notify(self):
        while result := self.get("result"):
            outcome = result.outcome
            if outcome.tag == lib.TrialOutcome_Win:
                if (outcome.contents.Win.tag == lib.Color_White) == (result.rid == 1):
                    self.wins1 += 1
                else:
                    self.wins2 += 1
            elif outcome.tag == lib.TrialOutcome_Draw:
                self.draws += 1
            elif outcome.tag == lib.TrialOutcome_Error:
                self.errors += 1
            self.awaiting -= 1
            print("{:3d} {:3d} {:3d} {:3d}".format(self.wins1, self.wins2, self.draws, self.errors))

    def runTrial(self):
        self.awaiting += 1
        config = {
            'randSteps': self.randSteps, 'depth': self.depth,
            'white': self.config1 if self.white1 else self.config2,
            'black': self.config2 if self.white1 else self.config1
        }
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Config, 'contents': {'Config': config}})[0])
        self.put("command", ffi.new("Command *", {'tag': lib.Command_RunTrial, 'contents': {'RunTrial': 1 if self.white1 else 0}})[0])
        self.white1 = not self.white1


config1 = {'checkValue': 3, 'centerControlValue': 1, 'castleValue': 2, 'pawnStructureValueDiv': 2}
config2 = {'checkValue': 0, 'centerControlValue': 0, 'castleValue': 0, 'pawnStructureValueDiv': 2}
randSteps = 2
depth = 7
trials = 100

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
