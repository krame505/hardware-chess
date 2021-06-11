# Hardware Chess
A chess engine implemented in Bluespec.

## Setup instructions
1. Install [bsc](https://github.com/b-lang-org/bsc)
2. Clone the [bsc-contrib](https://github.com/b-lang-org/bsc-contrib) repository in the same top-level directory as this one
```
$ git clone https://github.com/b-lang-org/bsc-contrib
```
3. Install required python libraries
```
$ python3 -m pip install pyserial cffi eventfd cobs flask
```
On some systems you may need to manually install tkinter as well
```
$ sudo apt install python3-tk
```
4. Build everything by running `make`.  This will
   * Compile the Bluespec source files and libraries
   * Generate Verilog for the top-level `mkTop` module specified in `HwTop.bs`
   * Generate message library C source and header files `chess.c` and `chess.h`
   * Build a Python FFI wrapper module `_chess` for the C message library
   * Generate a Bluesim simulator for the top-level `sysChessSim` module specified in `SimTop.bs`

## Running the simulator
If you don't have access to an FPGA, the design can still be run as a BlueSim simulation.  The AI is still quite playable in this form, though significantly more beatable then on hardware as the search depth is several plies shallower.

1. Run `./sysChessSim.out` to start the simulator; this will print the name of the simulated serial device.
```
$ ./sysChessSim.out
Initialized simulated serial device at /dev/pts/44
```
2. Launch the server application with the specified device; this will print the URL on which the chess interface can be accessed.
```
$ ./server.py /dev/pts/44
 * Serving Flask app 'server' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on all addresses.
   WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://172.16.103.150:8000/ (Press CTRL+C to quit)
```
3. When finished, terminating the server will also cause the simulator to exit.


## Running on an FPGA
The design can also be run in hardware on an FPGA.  Vivado constraint and project files are included for use with the Arty A7 board, however it should be possible to configure the project for other FPGAs.

1. Install [Vivado and the Digilent board files](https://reference.digilentinc.com/vivado/installing-vivado/start).  Note that there are multiple versions available; ensure that the installed version supports Xilinx FPGAs.
2. Open the `hardware-chess.xpr` project file in Vivado
3. Generate a bitstream file and program the device.  A serial device corresponding to the FPGA board should appear, e.g. `/dev/ttyUSB1`
4. Run the server using the serial device
```
./server.py /dev/ttyUSB1
```
