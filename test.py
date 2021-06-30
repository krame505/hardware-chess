#!/usr/bin/env python3

import sys
sys.path.append("../bsc-contrib/Libraries/GenC/GenCMsg")
sys.path.append("bin")

import msgclient
from _chess_test import ffi, lib

import serial
import time
import random

class ChessTestClient(msgclient.Client):
    def __init__(self, serial, depth):
        super().__init__("ChessTestMsgs", ffi, lib, serial)
        self.depth = depth
        self.config1 = None
        self.config2 = None
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

    def config(self, config1, config2):
        self.config1 = config1
        self.config2 = config2
        self.wins1 = 0
        self.wins2 = 0
        self.draws = 0
        self.errors = 0

    def runTrial(self):
        self.awaiting += 1
        config = {
            'depth': self.depth,
            'white': self.config1 if self.white1 else self.config2,
            'black': self.config2 if self.white1 else self.config1
        }
        self.put("command", ffi.new("Command *", {'tag': lib.Command_Config, 'contents': {'Config': config}})[0])

        trialConfig = {
            'rid': 1 if self.white1 else 0,
            'initMoves': [random.randrange(20), random.randrange(20)]
        }
        self.put("command", ffi.new("Command *", {'tag': lib.Command_RunTrial, 'contents': {'RunTrial': trialConfig}})[0])
        self.white1 = not self.white1

    def runTrials(self, trials, config1, config2):
        self.config(config1, config2)
        for i in range(trials):
            self.runTrial()
        while self.awaiting:
            time.sleep(0.5)
        return self.wins1, self.wins2, self.draws, self.errors

def optimize(client, config, trials):
    while True:
        newConfig = config.copy()
        newConfig[random.choice(list(config.keys()))] += random.choice((1, -1))
        print("Trying config", newConfig)
        w1, w2, d, e = client.runTrials(trials, config, newConfig)
        if w2 > w1:
            config = newConfig
        print("Best config", config)

initialConfig = {'checkValue': 1, 'centerControlValue': 8, 'castleValue': 12, 'pawnStructureValue': 4}
depth = 7
trials = 100

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit("Expected serial port name")

    ser = serial.Serial(sys.argv[1], 115200)
    client = ChessTestClient(ser, depth)
    client.start()
    random.seed(time.time())
    optimize(client, initialConfig, trials)
