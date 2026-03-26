`timescale 1ns/1ps

module tb_mac;
    reg  [15:0] A;
    reg  [15:0] B;
    reg  [31:0] C;
    wire [31:0] D;

    reg  [31:0] exp_d;
    integer fd;
    integer rc;
    integer vec_idx;
    reg [8*15:1] vec_kind;
    reg [1023:0] vec_file;
    reg [1023:0] dut_name;

    mac16x16p32 dut (
        .A(A),
        .B(B),
        .C(C),
        .D(D)
    );

    initial begin
        A = 16'h0000;
        B = 16'h0000;
        C = 32'h00000000;
        exp_d = 32'h00000000;
        vec_idx = 0;

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
                #1;
                if (D !== exp_d) begin
                    $display("RESULT: FAIL");
                    $display("DUT=%0s IDX=%0d KIND=%0s A=0x%04h B=0x%04h C=0x%08h EXP=0x%08h GOT=0x%08h",
                             dut_name, vec_idx, vec_kind, A, B, C, exp_d, D);
                    $fclose(fd);
                    $fatal(1);
                end
                vec_idx = vec_idx + 1;
            end else if (rc != -1) begin
                $display("ERROR: malformed vector line near index %0d", vec_idx);
                $fclose(fd);
                $fatal(1);
            end
        end

        $fclose(fd);
        $display("RESULT: PASS");
        $display("DUT=%0s VECTORS=%0d", dut_name, vec_idx);
        $finish;
    end
endmodule
