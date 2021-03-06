BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= bin
PYTHON ?= python3
override BSCFLAGS += -p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+
override BSCFLAGS += -bdir $(BUILDDIR) -fdir $(BUILDDIR) -simdir $(BUILDDIR) -cpp
override BSCFLAGS += +RTS -K1G -RTS -steps-warn-interval 1000000

CONF ?= rel

ifeq ($(CONF), rel)
  $(info Building release config)
  LIBNAME = chess
else ifeq ($(CONF), test)
  $(info Building test config)
  LIBNAME = chess_test
  override BSCFLAGS += -Xcpp -DTEST
endif

all: rtl sim ffi # vsim

.contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install
	touch $@

$(BUILDDIR):
	mkdir -p $@

$(BUILDDIR)/%.bo: %.bs .contrib | $(BUILDDIR)
	bsc $(BSCFLAGS) -verilog -elab $<

ifeq ($(CONF), rel)
common: $(BUILDDIR)/GameDriver.bo
else ifeq ($(CONF), test)
common: $(BUILDDIR)/TestDriver.bo
endif

rtl: common
	bsc $(BSCFLAGS) -verilog HwTop.bs

sim: common
	bsc $(BSCFLAGS) -sim PTY.bsv
	bsc $(BSCFLAGS) -sim SimTop.bs
	bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

ffi: common
	cd $(BUILDDIR) && $(PYTHON) $(BSCCONTRIB)/Libraries/GenC/build_ffi.py $(LIBNAME)

vsim: $(BUILDDIR)/VSimTop.bo
	bsc $(BSCFLAGS) -verilog -e sysChessVSim -o sysChessVSim.out

depends.mk: | $(BUILDDIR)
	bluetcl -exec makedepend $(BSCFLAGS) "*.bs*" > depends.mk

include depends.mk

clean:
	rm -rf *~ *.h *.o *.so *.cxx *.v *.out .contrib depends.mk bin/ __pycache__/

.PHONY: all common rtl sim vsim ffi clean
