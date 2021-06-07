BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= bin
override BSCFLAGS += -p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+
override BSCFLAGS += -bdir $(BUILDDIR) -fdir $(BUILDDIR) -simdir $(BUILDDIR)
override BSCFLAGS += +RTS -K1G -RTS -steps-warn-interval 1000000
override BSCFLAGS += -suppress-warnings S0028  # Warnings about impCondOf

all: rtl sim ffi

contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install

$(BUILDDIR):
	mkdir -p $@

rtl: | contrib $(BUILDDIR)
	bsc $(BSCFLAGS) -u -verilog -elab HwTop.bs

sim: | rtl contrib $(BUILDDIR)
	bsc $(BSCFLAGS) -sim PTY.bsv
	bsc $(BSCFLAGS) -sim SimTop.bs
	bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

vsim: | contrib $(BUILDDIR)
	bsc $(BSCFLAGS) -u -verilog VSimTop.bs
	bsc $(BSCFLAGS) -verilog -e sysChessVSim -o sysChessVSim.out

ffi: | rtl $(BUILDDIR)
	cd $(BUILDDIR) && python3 $(BSCCONTRIB)/Libraries/GenC/build_ffi.py "chess"

clean:
	rm -rf *~ *.h *.o *.so *.cxx *.v *.out bin/ __pycache__/

.PHONY: all contrib rtl sim vsim ffi clean
