module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);

wire [31:0] mult_out;

assign mult_out = A * B;
assign D = mult_out + C;

endmodule
