module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);
    MY_MACRO_U32 u0 (.A(A), .B(B), .C(C), .D(D));
endmodule
