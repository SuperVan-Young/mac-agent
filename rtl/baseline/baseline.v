`ifndef MAC_A_WIDTH
`define MAC_A_WIDTH 16
`endif

`ifndef MAC_B_WIDTH
`define MAC_B_WIDTH 16
`endif

`ifndef MAC_ACC_WIDTH
`define MAC_ACC_WIDTH 32
`endif

`ifndef MAC_PIPELINE_CYCLES
`define MAC_PIPELINE_CYCLES 1
`endif

module mac16x16p32 (
    input  [`MAC_A_WIDTH-1:0] A,
    input  [`MAC_B_WIDTH-1:0] B,
    input  [`MAC_ACC_WIDTH-1:0] C,
`ifdef MAC_USE_CLK
    input  clk,
`endif
    output [`MAC_ACC_WIDTH-1:0] D
);

localparam integer A_WIDTH = `MAC_A_WIDTH;
localparam integer B_WIDTH = `MAC_B_WIDTH;
localparam integer ACC_WIDTH = `MAC_ACC_WIDTH;
localparam integer PIPELINE_CYCLES = `MAC_PIPELINE_CYCLES;

wire [A_WIDTH + B_WIDTH - 1:0] mult_raw;
wire [ACC_WIDTH - 1:0] mult_out;
wire [ACC_WIDTH - 1:0] sum_out;

assign mult_raw = A * B;
assign mult_out = $unsigned(mult_raw);
assign sum_out = mult_out + C;

generate
if (PIPELINE_CYCLES <= 1) begin : gen_no_pipeline
    assign D = sum_out;
end else begin : gen_pipeline
`ifdef MAC_USE_CLK
    reg [ACC_WIDTH - 1:0] pipe_regs [0:PIPELINE_CYCLES - 2];
    integer i;
    always @(posedge clk) begin
        pipe_regs[0] <= sum_out;
        for (i = 1; i < PIPELINE_CYCLES - 1; i = i + 1) begin
            pipe_regs[i] <= pipe_regs[i - 1];
        end
    end
    assign D = pipe_regs[PIPELINE_CYCLES - 2];
`else
    assign D = sum_out;
`endif
end
endgenerate

endmodule
