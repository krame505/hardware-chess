BSC ?= $(abspath ../bsc)
BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= build
PYTHON ?= python3
override BSCFLAGS += -p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+
override BSCFLAGS += -bdir $(BUILDDIR) -vdir $(BUILDDIR) -fdir $(BUILDDIR) -simdir $(BUILDDIR) -cpp
override BSCFLAGS += +RTS -K1G -RTS -steps-warn-interval 1000000

XDC := Arty_Master.xdc

# From f4pga-examples/common/common.mk:
DEVICE := xc7a100t_test
BITSTREAM_DEVICE := artix7
PARTNAME := xc7a100tcsg324-1
OFL_BOARD := arty_a7_100t

CONF ?= rel

ifeq ($(CONF), rel)
  $(info Building release config)
  TOP := mkTop
  SIMTOP := sysChessSim
  LIBNAME := chess
else ifeq ($(CONF), test)
  $(info Building test config)
  TOP := mkTestTop
  SIMTOP := sysChessTestSim
  LIBNAME := chess_test
else
  $(error Invalid build config $(CONF))
endif

all: rtl sim ffi # vsim bitstream

rtl: $(BUILDDIR)/$(TOP).v
sim: $(SIMTOP).out
vsim: sysChessVSim.out
ffi: .$(LIBNAME)_ffi

.contrib:
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/GenC install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/COBS install
	$(MAKE) MAKEOVERRIDES= -C $(BSCCONTRIB)/Libraries/FPGA/Misc install
	touch $@

$(BUILDDIR):
	mkdir -p $@

$(BUILDDIR)/%.bo: %.bs .contrib | $(BUILDDIR)
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -verilog -elab $<

$(BUILDDIR)/PTY.bo: PTY.bsv | $(BUILDDIR)
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -sim $<

%.out: $(BUILDDIR)/%.ba pty.c
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -sim -e $* -o $@ pty.c

%VSim.out: $(BUILDDIR)/%VSim.ba
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -verilog -e $*VSim -o $@

.%_ffi: $(BUILDDIR)/%.c $(BUILDDIR)/%.h
	cd $(BUILDDIR) && $(PYTHON) $(BSCCONTRIB)/Libraries/GenC/build_ffi.py $*
	touch $@

GEN_SOURCES := $(addprefix $(BUILDDIR)/,$(shell sed -n -e 's/^{-\# verilog \([[:alnum:]]\+\) \#-}/\1.v/p' *.bs))
BSC_SOURCES := SizedFIFO.v Counter.v MakeResetA.v SyncFIFO.v ClockDiv.v FIFO2.v SyncResetA.v FIFO1.v
SOURCES := $(GEN_SOURCES) $(addprefix $(BSC)/src/Verilog/,$(BSC_SOURCES))
XDC_CMD := -x $(abspath ${XDC})

# From f4pga-examples/common/common.mk:
${BUILDDIR}/${TOP}.eblif: ${SOURCES} ${XDC} ${SDC} ${PCF} | ${BUILDDIR}
	cd ${BUILDDIR} && symbiflow_synth -t ${TOP} ${SURELOG_OPT} -v $(abspath ${SOURCES}) -d ${BITSTREAM_DEVICE} -p ${PARTNAME} -x ${XDC_CMD}

${BUILDDIR}/${TOP}.net: ${BUILDDIR}/${TOP}.eblif
	cd ${BUILDDIR} && symbiflow_pack -e ${TOP}.eblif -d ${DEVICE} ${SDC_CMD}

${BUILDDIR}/${TOP}.place: ${BUILDDIR}/${TOP}.net
	cd ${BUILDDIR} && symbiflow_place -e ${TOP}.eblif -d ${DEVICE} ${PCF_CMD} -n ${TOP}.net -P ${PARTNAME} ${SDC_CMD}

${BUILDDIR}/${TOP}.route: ${BUILDDIR}/${TOP}.place
	cd ${BUILDDIR} && symbiflow_route -e ${TOP}.eblif -d ${DEVICE} ${SDC_CMD}

${BUILDDIR}/${TOP}.fasm: ${BUILDDIR}/${TOP}.route
	cd ${BUILDDIR} && symbiflow_write_fasm -e ${TOP}.eblif -d ${DEVICE}

${BUILDDIR}/${TOP}.bit: ${BUILDDIR}/${TOP}.fasm
	cd ${BUILDDIR} && symbiflow_write_bitstream -d ${BITSTREAM_DEVICE} -f ${TOP}.fasm -p ${PARTNAME} -b ${TOP}.bit

bitstream: ${BUILDDIR}/${TOP}.bit

download: ${BUILDDIR}/${TOP}.bit
	openFPGALoader -b ${OFL_BOARD} $<

depends.mk: | $(BUILDDIR)
	bluetcl -exec makedepend $(BSCFLAGS) "*.bs*" > depends.mk
	for file in *.bs; do sed -n -e "s/^{-\# verilog \([[:alnum:]_]\+\) \#-}/$(BUILDDIR)\/\1.v: $(BUILDDIR)\/$${file%.bs}.bo/p" $$file; done >> depends.mk
	for file in *.bs; do sed -n -e "s/^{-\# verilog \([[:alnum:]_]\+\) \#-}/$(BUILDDIR)\/\1.ba: $(BUILDDIR)\/$${file%.bs}.bo/p" $$file; done >> depends.mk
	for file in *.bs; do sed -n -e "s/^\s\+writeCMsgDecls \"\([[:alnum:]_]\+\)\".*/$(BUILDDIR)\/\1.c $(BUILDDIR)\/\1.h: $(BUILDDIR)\/$${file%.bs}.bo/p" $$file; done >> depends.mk

include depends.mk

clean:
	rm -rf *~ *.o *.so *.out *.sched .contrib .*_ffi depends.mk $(BUILDDIR) __pycache__/

.PHONY: all rtl sim vsim ffi bitstream download clean
