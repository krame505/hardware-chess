BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= bin
override BSCFLAGS += -p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+
override BSCFLAGS += -bdir $(BUILDDIR) -fdir $(BUILDDIR)

all: rtl sim ffi

contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install

$(BUILDDIR):
	mkdir -p $@

rtl: | contrib $(BUILDDIR)
	bsc $(BSCFLAGS) -u -verilog HwTop.bs

ffi: | rtl $(BUILDDIR)
	cd $(BUILDDIR) && python3 $(BSCCONTRIB)/Libraries/GenC/build_ffi.py "chess"

sim: | contrib $(BUILDDIR)
	bsc $(BSCFLAGS) -u -sim SimTop.bs
	bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

clean:
	rm -rf *~ *.h *.o *.so *.cxx *.v *.out bin/ __pycache__/

.PHONY: all contrib rtl sim ffi clean
