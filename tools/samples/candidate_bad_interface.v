module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [30:0] D
);
    buf u_d [30:0] (D, C[30:0]);
endmodule
