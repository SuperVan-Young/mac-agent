// Baseline MAC: DesignWare-oriented implementation for DC.
// For Synopsys DC, ensure DesignWare synthetic library is configured.
module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);

wire [31:0] mult_out;

`ifdef SYNOPSYS
    DW02_mult #(
        .A_width(16),
        .B_width(16)
    ) u_mult (
        .A(A),
        .B(B),
        .TC(1'b0),
        .PRODUCT(mult_out)
    );

    DW01_add #(
        .width(32)
    ) u_add (
        .A(mult_out),
        .B(C),
        .CI(1'b0),
        .SUM(D),
        .CO()
    );
`else
    // Fallback for environments without DesignWare models.
    assign mult_out = A * B;
    assign D = mult_out + C;
`endif

endmodule
