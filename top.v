`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07/04/2021 04:03:46 PM
// Design Name: 
// Module Name: top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module top(
    input CLK,
    input RST_N,
    output tx,
    input rx,
    input statusEnable,
    output [15:0] status
    );
  
  wire slowClock;
  clk_wiz_0 divider
   (
    // Clock out ports
    .clk_out1(slowClock),     // output clk_out1
    // Status and control signals
    .reset(RST_N), // input reset
    //.locked(locked),       // output locked
   // Clock in ports
    .clk_in1(CLK));

  mkTop top(slowClock, RST_N, CLK, RST, tx, rx, statusEnable, status);
endmodule
