BSC ?= $(abspath ../bsc)
BSCCONTRIB ?= $(abspath ../bsc-contrib)
BUILDDIR ?= bin
PYTHON ?= python3
override BSCFLAGS += -p $(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCRepr:$(BSCCONTRIB)/inst/lib/Libraries/GenC/GenCMsg:$(BSCCONTRIB)/inst/lib/Libraries/FPGA/Misc:$(BSCCONTRIB)/inst/lib/Libraries/COBS:+
override BSCFLAGS += -bdir $(BUILDDIR) -fdir $(BUILDDIR) -simdir $(BUILDDIR) -cpp
override BSCFLAGS += +RTS -K1G -RTS -steps-warn-interval 1000000

TOP := mkTop
XDC := Arty_Master.xdc

# From f4pga-examples/common/common.mk:
DEVICE := xc7a100t_test
BITSTREAM_DEVICE := artix7
PARTNAME := xc7a100tcsg324-1
OFL_BOARD := arty_a7_100t

CONF ?= rel

ifeq ($(CONF), rel)
  $(info Building release config)
  LIBNAME = chess
else ifeq ($(CONF), test)
  $(info Building test config)
  LIBNAME = chess_test
  override BSCFLAGS += -Xcpp -DTEST
endif

all: rtl sim ffi # vsim bitstream

rtl: $(TOP).v
sim: sysChessSim.out
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

sysChessSim.out: $(BUILDDIR)/sysChessSim.ba pty.c
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -sim -e sysChessSim -o sysChessSim.out pty.c

sysChessVSim.out: $(BUILDDIR)/sysChessVSim.ba
	$(BSC)/inst/bin/bsc $(BSCFLAGS) -verilog -e sysChessVSim -o sysChessVSim.out

$(BUILDDIR)/chess.c $(BUILDDIR)/chess.h: $(BUILDDIR)/GameDriver.bo
$(BUILDDIR)/chess_test.c $(BUILDDIR)/chess_test.h: $(BUILDDIR)/TestDriver.bo

.%_ffi: $(BUILDDIR)/%.c $(BUILDDIR)/%.h
	cd $(BUILDDIR) && $(PYTHON) $(BSCCONTRIB)/Libraries/GenC/build_ffi.py $*
	touch $@


BOARD_BUILDDIR := ${BUILDDIR}

GEN_SOURCES := $(shell sed -n -e 's/^{-\# verilog \([[:alnum:]]\+\) \#-}/\1.v/p' *.bs)
BSC_SOURCES := SizedFIFO.v Counter.v MakeResetA.v SyncFIFO.v ClockDiv.v FIFO2.v SyncResetA.v FIFO1.v
SOURCES := $(abspath $(GEN_SOURCES)) $(addprefix $(BSC)/src/Verilog/,$(BSC_SOURCES))
XDC_CMD := -x $(abspath ${XDC})

# From f4pga-examples/common/common.mk:
${BOARD_BUILDDIR}/${TOP}.eblif: ${GEN_SOURCES} ${XDC} ${SDC} ${PCF} | ${BOARD_BUILDDIR}
	cd ${BOARD_BUILDDIR} && symbiflow_synth -t ${TOP} ${SURELOG_OPT} -v ${SOURCES} -d ${BITSTREAM_DEVICE} -p ${PARTNAME} -x ${XDC_CMD}

${BOARD_BUILDDIR}/${TOP}.net: ${BOARD_BUILDDIR}/${TOP}.eblif
	cd ${BOARD_BUILDDIR} && symbiflow_pack -e ${TOP}.eblif -d ${DEVICE} ${SDC_CMD}

${BOARD_BUILDDIR}/${TOP}.place: ${BOARD_BUILDDIR}/${TOP}.net
	cd ${BOARD_BUILDDIR} && symbiflow_place -e ${TOP}.eblif -d ${DEVICE} ${PCF_CMD} -n ${TOP}.net -P ${PARTNAME} ${SDC_CMD}

${BOARD_BUILDDIR}/${TOP}.route: ${BOARD_BUILDDIR}/${TOP}.place
	cd ${BOARD_BUILDDIR} && symbiflow_route -e ${TOP}.eblif -d ${DEVICE} ${SDC_CMD}

${BOARD_BUILDDIR}/${TOP}.fasm: ${BOARD_BUILDDIR}/${TOP}.route
	cd ${BOARD_BUILDDIR} && symbiflow_write_fasm -e ${TOP}.eblif -d ${DEVICE}

${BOARD_BUILDDIR}/${TOP}.bit: ${BOARD_BUILDDIR}/${TOP}.fasm
	cd ${BOARD_BUILDDIR} && symbiflow_write_bitstream -d ${BITSTREAM_DEVICE} -f ${TOP}.fasm -p ${PARTNAME} -b ${TOP}.bit

bitstream: ${BOARD_BUILDDIR}/${TOP}.bit

download: bitstream
	openFPGALoader -b ${OFL_BOARD} ${BOARD_BUILDDIR}/${TOP}.bit

depends.mk: | $(BUILDDIR)
	bluetcl -exec makedepend $(BSCFLAGS) "*.bs*" > depends.mk
	for file in *.bs; do sed -n -e "s/^{-\# verilog \([[:alnum:]]\+\) \#-}/\1.v: $(BUILDDIR)\/$${file%.bs}.bo/p" $$file; done >> depends.mk
	for file in *.bs; do sed -n -e "s/^{-\# verilog \([[:alnum:]]\+\) \#-}/$(BUILDDIR)\/\1.ba: $(BUILDDIR)\/$${file%.bs}.bo/p" $$file; done >> depends.mk

include depends.mk

clean:
	rm -rf *~ *.h *.o *.so *.cxx *.v *.out .contrib .*_ffi depends.mk $(BUILDDIR) __pycache__/

.PHONY: all common rtl sim vsim ffi bitstream download clean
