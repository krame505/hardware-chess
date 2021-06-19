BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= bin
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

all: rtl ffi sim vsim

.contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install
	touch $@

$(BUILDDIR):
	mkdir -p $@

$(BUILDDIR)/%.bo: %.bs .contrib | $(BUILDDIR)
	bsc $(BSCFLAGS) -verilog -elab $<

common: $(BUILDDIR)/Driver.bo

rtl: common
ifeq ($(CONF), test)
	bsc $(BSCFLAGS) -verilog TestDriver.bs
endif
	bsc $(BSCFLAGS) -verilog HwTop.bs

sim: common
ifeq ($(CONF), test)
	bsc $(BSCFLAGS) -sim TestDriver.bs
endif
	bsc $(BSCFLAGS) -sim PTY.bsv
	bsc $(BSCFLAGS) -sim SimTop.bs
	bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

vsim: common
	bsc $(BSCFLAGS) -verilog VSimTop.bs
	bsc $(BSCFLAGS) -verilog -e sysChessVSim -o sysChessVSim.out

ffi: rtl
	cd $(BUILDDIR) && python3 $(BSCCONTRIB)/Libraries/GenC/build_ffi.py $(LIBNAME)

depends.mk: | $(BUILDDIR)
	bluetcl -exec makedepend $(BSCFLAGS) "*.bs*" > depends.mk

include depends.mk

clean:
	rm -rf *~ *.h *.o *.so *.cxx *.v *.out .contrib depends.mk bin/ __pycache__/

.PHONY: all common rtl sim vsim ffi clean
