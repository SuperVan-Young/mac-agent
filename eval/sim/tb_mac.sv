`timescale 1ns/1ps

`ifndef MAC_A_WIDTH
`define MAC_A_WIDTH 16
`endif

`ifndef MAC_B_WIDTH
`define MAC_B_WIDTH 16
`endif

`ifndef MAC_ACC_WIDTH
`define MAC_ACC_WIDTH 32
`endif

module tb_mac;
    reg  [`MAC_A_WIDTH-1:0] A;
    reg  [`MAC_B_WIDTH-1:0] B;
    reg  [`MAC_ACC_WIDTH-1:0] C;
    wire [`MAC_ACC_WIDTH-1:0] D;

    reg  [`MAC_ACC_WIDTH-1:0] exp_d;
    reg  [`MAC_ACC_WIDTH-1:0] exp_pipe [0:255];
    integer fd;
    integer rc;
    integer vec_idx;
    integer match_idx;
    integer flush_idx;
    integer i;
    integer pipeline_latency;
    integer valid_expected;
    reg [8*15:1] vec_kind;
    reg [1023:0] vec_file;
    reg [1023:0] dut_name;

`ifdef MAC_USE_CLK
    reg clk;
    always #1 clk = ~clk;
`endif

`ifdef MAC_USE_CLK
    mac16x16p32 dut (
        .A(A),
        .B(B),
        .C(C),
        .clk(clk),
        .D(D)
    );
`else
    mac16x16p32 dut (
        .A(A),
        .B(B),
        .C(C),
        .D(D)
    );
`endif

    initial begin
        A = {`MAC_A_WIDTH{1'b0}};
        B = {`MAC_B_WIDTH{1'b0}};
        C = {`MAC_ACC_WIDTH{1'b0}};
        exp_d = {`MAC_ACC_WIDTH{1'b0}};
        vec_idx = 0;
        match_idx = 0;
        flush_idx = 0;
        valid_expected = 0;
        pipeline_latency = 0;
        for (i = 0; i < 256; i = i + 1) begin
            exp_pipe[i] = {`MAC_ACC_WIDTH{1'b0}};
        end

`ifdef MAC_USE_CLK
        clk = 1'b0;
`endif

        if (!$value$plusargs("PIPELINE_LATENCY=%d", pipeline_latency)) begin
            pipeline_latency = 0;
        end
        if (pipeline_latency < 0 || pipeline_latency > 255) begin
            $display("ERROR: unsupported pipeline latency %0d (must be 0..255)", pipeline_latency);
            $fatal(1);
        end

        if (!$value$plusargs("VEC_FILE=%s", vec_file)) begin
            $display("ERROR: missing +VEC_FILE=<path>");
            $fatal(1);
        end

        if (!$value$plusargs("DUT_NAME=%s", dut_name)) begin
            dut_name = "mac16x16p32";
        end

        fd = $fopen(vec_file, "r");
        if (fd == 0) begin
            $display("ERROR: unable to open vector file: %0s", vec_file);
            $fatal(1);
        end

        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s %h %h %h %h\n", vec_kind, A, B, C, exp_d);
            if (rc == 5) begin
`ifdef MAC_USE_CLK
                @(posedge clk);
                if (pipeline_latency == 0) begin
                    if (D !== exp_d) begin
                        $display("RESULT: FAIL");
                        $display("DUT=%0s IDX=%0d KIND=%0s A=0x%h B=0x%h C=0x%h EXP=0x%h GOT=0x%h",
                                 dut_name, vec_idx, vec_kind, A, B, C, exp_d, D);
                        $fclose(fd);
                        $fatal(1);
                    end
                    match_idx = match_idx + 1;
                end else begin
                    if (valid_expected >= pipeline_latency) begin
                        if (D !== exp_pipe[pipeline_latency - 1]) begin
                            $display("RESULT: FAIL");
                            $display("DUT=%0s IDX=%0d KIND=%0s EXP=0x%h GOT=0x%h",
                                     dut_name, match_idx, vec_kind, exp_pipe[pipeline_latency - 1], D);
                            $fclose(fd);
                            $fatal(1);
                        end
                        match_idx = match_idx + 1;
                    end
                    for (i = pipeline_latency - 1; i > 0; i = i - 1) begin
                        exp_pipe[i] = exp_pipe[i - 1];
                    end
                    exp_pipe[0] = exp_d;
                    valid_expected = valid_expected + 1;
                end
`else
                #1;
                if (D !== exp_d) begin
                    $display("RESULT: FAIL");
                    $display("DUT=%0s IDX=%0d KIND=%0s A=0x%h B=0x%h C=0x%h EXP=0x%h GOT=0x%h",
                             dut_name, vec_idx, vec_kind, A, B, C, exp_d, D);
                    $fclose(fd);
                    $fatal(1);
                end
                match_idx = match_idx + 1;
`endif
                vec_idx = vec_idx + 1;
            end else if (rc != -1) begin
                $display("ERROR: malformed vector line near index %0d", vec_idx);
                $fclose(fd);
                $fatal(1);
            end
        end

`ifdef MAC_USE_CLK
        if (pipeline_latency > 0) begin
            A = {`MAC_A_WIDTH{1'b0}};
            B = {`MAC_B_WIDTH{1'b0}};
            C = {`MAC_ACC_WIDTH{1'b0}};
            for (flush_idx = 0; flush_idx < pipeline_latency; flush_idx = flush_idx + 1) begin
                @(posedge clk);
                if (D !== exp_pipe[pipeline_latency - 1]) begin
                    $display("RESULT: FAIL");
                    $display("DUT=%0s IDX=%0d KIND=FLUSH EXP=0x%h GOT=0x%h",
                             dut_name, match_idx, exp_pipe[pipeline_latency - 1], D);
                    $fclose(fd);
                    $fatal(1);
                end
                match_idx = match_idx + 1;
                for (i = pipeline_latency - 1; i > 0; i = i - 1) begin
                    exp_pipe[i] = exp_pipe[i - 1];
                end
                exp_pipe[0] = {`MAC_ACC_WIDTH{1'b0}};
            end
        end
`endif

        $fclose(fd);
        $display("RESULT: PASS");
        $display("DUT=%0s VECTORS=%0d", dut_name, vec_idx);
        $finish;
    end
endmodule
