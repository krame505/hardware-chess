#!/bin/bash

# Helper script to forward a local serial device to a pseudoterminal on a remote host via ssh.
# Example usage:
#   ./forward-serial-device /dev/ttyUSB* user@hostname.net
#
# A new pseudoterminal device will be created under /dev/pty/ on the remote host.

PORT=$1
HOST=$2

socat $PORT,nonblock,rawer EXEC:"ssh $HOST socat - PTY"
