BSCCONTRIB?=../bsc-contrib
override BSCFLAGS+=-p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+

all: rtl sim ffi

contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install

rtl: | contrib
	bsc $(BSCFLAGS) -u -verilog HwTop.bs

ffi: | rtl
	python3 $(BSCCONTRIB)/Libraries/GenC/build_ffi.py "chess"

sim: | contrib
	bsc $(BSCFLAGS) -u -sim SimTop.bs
	bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

clean:
	rm -rf *~ *.o *demo.c *demo_sim.c *.h *.cxx *.v *.bo *.ba *.so *.out __pycache__/

.PHONY: all contrib rtl sim ffi clean
