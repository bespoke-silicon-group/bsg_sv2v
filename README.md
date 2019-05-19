# BSG SystemVerilog to Verilog (SV2V) 

BSG SV2V takes a hardware design written in SystemVerilog and converts it into
a single HDL file that is Verilog-2005 compliant. The Verilog-2005 standard is
compatible with a much wider variety of CAD tools, thus this converter can help
bridge the gap between code bases employing advanced synthesizable
SystemVerilog features and older or less sophisticated tools.

The tool uses Synopsys Design Compiler (DC) to perform elaboration of the
design, and then post-processes to map DC's gtech/seqqen/datapath
representation back to standard Verilog. Thus a DC license is required by the
party running the tool, but is not required to use the converted file.

This approach maximizes compatibility with code that was written and targets
DC. Of course it would also be neat if somebody wrote a totally open source SV
to V!

## Setup

For this converter, you will need Synopsys Design Compiler installed (verified
on version M-2016.12-SP5-5) and access to a valid license file. If you have
access to *bsg_cadenv* and it is setup for the machine you are working on, then
you can simply clone *bsg_sv2v* and *bsg_cadenv* into the same directory and
the CAD tools should be setup automatically to run on our machines. For all
other users, you should open the Makefile in the root of the repository and set
the following two variables:

```
export LM_LICENSE_FILE ?= <YOUR LICENSE FILE HERE>
```

```
export DC_SHELL ?= <YOUR DC_SHELL BINARY HERE>
```

The BSG SV2V converter also depends on
[Icarus Verilog](http://iverilog.icarus.com/),
[Pyverilog](https://pypi.org/project/pyverilog/), and 
[pypy](https://pypy.org/). To download and build these tools, simply run:

```
$ make tools
```

## Usage

### Design Filelist

To use the BSG SV2V converter flow, first you must first create a filelist. The
filelist is the main way of linking together all of the bits to elaborate the
design. The format of the filelist is fairly basic and is based on Synopsys VCS
filelists.  Each line in the filelist can be 1 of 5 things:

- A comments starting with the `#` character
- A macro definition in the format `+define+NAME=VALUE`
- A top-level parameter definition in the format `-pvalue+NAME=VALUE`
- An include search directory in the format `+incdir+DIRECTORY`
- An HDL file path (no format, just the file path)

You may also use environment variables inside the filelist by using the `$`
character followed by the name of the environment variable.

Below is a mock filelist as an example:

```bash
### My Design Filelist
# Macros
+define+SYNTHESIS
+define+DEBUG=0
# Parameters
-pvalue+data_width=32
# Search paths
+incdir+$INCLUDE_DIR/vh/
+incdir+$INCLUDE_DIR/pkgs/
# Files
$SRC_DIR/top.v
$SRC_DIR/sub_design/file1.v
$SRC_DIR/sub_design/file2.v
$SRC_DIR/sub_design/file3.v
```

### Running the Flow

Now that you have setup the tools and created a design filelist, you are ready
to run the flow! The main target is: 

```
$ make convert_sv2v DESIGN_NAME=<top-module> DESIGN_FILELIST=<path-to-filelist> DESIGN_DIRECTORIES_MK=<optional-makefile-fragment>
```

If you'd prefer, you can modify the Makefile and set `DESIGN_NAME`,
`DESIGN_FILELIST`, and `DESIGN_DIRECTORIES_MK` rather than specifying them as
part of the makefile target. `DESIGN_NAME` should be set to the name of the
toplevel module in the design and `DESIGN_FILELIST` should be the filelist for
the design discussed in the previous section. `DESIGN_DIRECTORIES_MK` is
optional and can point to a makefile fragment that can setup environment
variables for use inside the design filelist.

This command will first launch Synopsys Design Compiler and elaborate the
design. It will then call a python script that will take the elaborated design
and turn it back into synthesizable RTL that is Verilog-05 compatible. All
output files can be found in the `results` directory. The main converted file
will be in:

```
./results/${DESIGN_NAME}.sv2v.v
```

### Example

A very simple example has been include in the `examples` directory. To test out
the example, run:

```
$ make convert_sv2v DESIGN_NAME=gcd DESIGN_FILELIST=examples/gcd/gcd.flist
```

To see the converted file, run:

```
$ cat ./results/gcd.sv2v.v
```

### Log Level

The `bsg_elab_to_rtl.py` script logs various information throughout the process
of converting the DC elaborated netlist to RTL. By default, the logger level is
set to `info` however you can change the log level. Available options are `debug`,
`info`,`warning`,`error`, and `critical`. Inside of the Makefile, you can set the
`LOGLVL` variable to the logging level desired.

### Optimization Passes

As part of the BSG SV2V flow, after all components have been swapped with their RTL
equivalents, additional passes of the netlist are performed to try and cleanup and
optimize the netlist. By default, every optimization pass is enabled, however every
optimization pass can be disabled using flags passed to the `bsg_elab_to_rtl.py`
script. In the Makefile, you can add these flags to the `SV2V_OPTIONS` variable to
disable these optimizations.

| Optimization Name    | Disable Flag           | Description                                                                                                        |
|:--------------------:|:----------------------:|:-------------------------------------------------------------------------------------------------------------------|
| Wire/Reg Declaration | no_wire_reg_decl_opt   | Takes individual wire and reg declarations and combines them into comma separated multi-variable declarations.     |
| Always@ Reduction    | no_always_at_redux_opt | Squashes always@ blocks based on sensitivity lists and conditional statements.                                     |
| Concat Reduction     | no_concat_redux_opt    | Squashes bits in large concats that share the same base bus name.                                                  |
