#!/bin/bash

# Helper script to forward a local serial device to a pseudoterminal on a remote machine via ssh

PORT=$1
HOST=$2

socat $PORT,nonblock,rawer EXEC:"ssh $HOST socat - PTY"
