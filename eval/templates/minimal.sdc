# Minimal SDC template for combinational mac16x16p32 evaluation.
# Use a virtual clock so all I/O delays are referenced consistently.

create_clock -name VCLK -period 2.000
set_input_delay 0.100 -clock VCLK [get_ports {A[*] B[*] C[*]}]
set_output_delay 0.100 -clock VCLK [get_ports {D[*]}]
