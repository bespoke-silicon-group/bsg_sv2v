export TOP_DIR :=$(shell git rev-parse --show-toplevel)

#===============================================================================
# CAD TOOL SETUP
#
# You can either include a makefile that has the environment setup or you can
# set the variables below to the correct values. The LM_LICENSE_FILE should be
# set to a valid synopsys licenese server and DC_SHELL should point to the
# Synopsys DesignCompiler dc_shell bin.
#===============================================================================

# If the machine you are working on is bsg_cadenv complient, then you do not
# need to setup the cad tools, simply put bsg_cadenv in the same root dir.
-include $(TOP_DIR)/../bsg_cadenv/cadenv.mk

# License file
export LM_LICENSE_FILE ?=

# DesignCompiler dc_shell binary
export DC_SHELL ?=

#===============================================================================
# DESIGN SETUP
#
# The DESIGN_NAME variable is used to set the name of the top-level module
# you would like to elaborate in DesignCompiler.
#
# The DESIGN_FILELIST is the path to the filelist object for this design. The
# filelist is responsible for linking all files, include directories, macros
# and top-level parameters for the design. The filelist is a VCS style filelist
# that can contain 5 things:
#   1. Comments        -- begging in the # character
#   2. +incdir+<path>  -- adding a search directory for includes
#   3. +define+<macro> -- adding a macro definition at compile time
#   4. -pvalue+<param> -- top-level parametes
#   5. <file>          -- verilog files
#===============================================================================

export DESIGN_NAME :=gcd

export DESIGN_FILELIST :=$(TOP_DIR)/examples/gcd/gcd.flist

#===============================================================================
# ADDITIONAL TOOL SETUP
#
# These are additonal tools that we will need to use this flow. Run 'make
# tools' to download and build these. The additional tools are pretty small
# and should not take to long to build.
#===============================================================================

# Additional Tool directories
PYPY3_BUILD_DIR      :=$(TOP_DIR)/tools/pypy3
VIRTUALENV_BUILD_DIR :=$(TOP_DIR)/tools/virtual_env
PYVERILOG_BUILD_DIR  :=$(TOP_DIR)/tools/pyverilog
IVERILOG_BUILD_DIR   :=$(TOP_DIR)/tools/iverilog

# Use these in place for your normal python and pip commands. This will use the
# virtualenv python and pip which has the installed dependancies.
PYTHON :=source $(VIRTUALENV_BUILD_DIR)/bin/activate; python
PIP    :=source $(VIRTUALENV_BUILD_DIR)/bin/activate; pip

# Update path variable as needed
export PATH:=$(PATH):$(IVERILOG_BUILD_DIR)/install/bin

#===============================================================================
# MAIN TARGET
#===============================================================================

export OUTPUT_DIR       :=$(CURDIR)/results
export OUTPUT_ELAB_FILE :=$(OUTPUT_DIR)/$(DESIGN_NAME).elab.v
export OUTPUT_SV2V_FILE :=$(OUTPUT_DIR)/$(DESIGN_NAME).sv2v.v

#LOGLVL:=debug
LOGLVL:=info
#LOGLVL:=warning
#LOGLVL:=error
#LOGLVL:=critical

convert_sv2v:
	mkdir -p $(OUTPUT_DIR)
	$(DC_SHELL) -64bit -f $(TOP_DIR)/scripts/tcl/run_dc.tcl 2>&1 | tee -i $(OUTPUT_DIR)/$(DESIGN_NAME).synth.log
	$(PYTHON) $(TOP_DIR)/scripts/py/bsg_elab_to_rtl.py -i $(OUTPUT_ELAB_FILE) -o $(OUTPUT_SV2V_FILE) -loglvl $(LOGLVL) 2>&1 | tee -i $(OUTPUT_DIR)/$(DESIGN_NAME).elab_to_rtl.log

#===============================================================================
# TOOLS
#===============================================================================

tools: $(IVERILOG_BUILD_DIR) $(PYPY3_BUILD_DIR) $(VIRTUALENV_BUILD_DIR) $(PYVERILOG_BUILD_DIR)

$(IVERILOG_BUILD_DIR):
	mkdir -p $(@D)
	git clone git://github.com/steveicarus/iverilog.git $@
	cd $@; git checkout v10_2
	cd $@; sh autoconf.sh
	cd $@; ./configure --prefix=$@/install
	cd $@; make -j4
	cd $@; make install

$(PYPY3_BUILD_DIR):
	mkdir -p $@/download
	cd $@/download; wget https://bitbucket.org/squeaky/portable-pypy/downloads/pypy3.5-7.0.0-linux_x86_64-portable.tar.bz2
	cd $@; tar xvf download/pypy3.5-7.0.0-linux_x86_64-portable.tar.bz2
	cd $@; mv pypy3.5-7.0.0-linux_x86_64-portable/* .
	cd $@; rmdir pypy3.5-7.0.0-linux_x86_64-portable

$(VIRTUALENV_BUILD_DIR): $(PYPY3_BUILD_DIR)
	mkdir -p $(@D)
	virtualenv -p $(PYPY3_BUILD_DIR)/bin/pypy3 $@
	$(PIP) install jinja2 pytest pytest-pythonpath

$(PYVERILOG_BUILD_DIR): $(VIRTUALENV_BUILD_DIR) $(IVERILOG_BUILD_DIR)
	mkdir -p $(@D)
	git clone https://github.com/PyHDI/Pyverilog.git $@
	cd $@; git checkout 1.1.3
	cd $@; $(PYTHON) setup.py install

clean_tools:
	rm -rf $(PYPY3_BUILD_DIR)
	rm -rf $(VIRTUALENV_BUILD_DIR)
	rm -rf $(PYVERILOG_BUILD_DIR)
	rm -rf $(IVERILOG_BUILD_DIR)

#===============================================================================
# CLEAN UP
#===============================================================================

deep_clean: clean_tools clean

clean:
	rm -rf $(OUTPUT_DIR)
	rm -rf __pycache__
	rm -f  parser.out parsetab.py

