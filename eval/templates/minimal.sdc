# Minimal SDC template for combinational mac16x16p32 evaluation.
# Adjust port names and period for your target.

create_clock -name VCLK -period 2.000 [get_ports A[0]]
set_input_delay 0.100 -clock VCLK [get_ports {A[*] B[*] C[*]}]
set_output_delay 0.100 -clock VCLK [get_ports {D[*]}]

