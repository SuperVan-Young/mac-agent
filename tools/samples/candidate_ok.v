module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);
    wire [31:0] c_buf;
    buf u_c [31:0] (c_buf, C);
    buf u_d [31:0] (D, c_buf);
endmodule
