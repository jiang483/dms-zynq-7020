#=============================================================================
# add_hls_ip_template.tcl -- add an HLS AXI-Lite + AXI-Master IP to a BD
#
# ASCII only on purpose (Vivado Tcl on Windows + the project's own rule).
#
# CONFIGURE the block below, then:
#   vivado -mode batch -source add_hls_ip_template.tcl
#
# The script is deliberately conservative:
#   * backs up the BD source directory first
#   * refuses to run if the starting MI/SI counts are not what you expect
#   * wires the new Mxx_ACLK/Mxx_ARESETN (the silent-reset trap)
#   * after generate_target, reads the generated .hwh and asserts that the
#     existing AXI widths did not change (SmartConnect NUM_SI recalculation)
#   * exits 1 on any failed assertion
#=============================================================================

# ------------------------------- CONFIGURE ---------------------------------
set proj_dir   "<absolute path to the Vivado project directory>"
set proj_name  "<project name, e.g. my_project>"
set bd_name    "design_1"
set vlnv       "user.com:hls:my_accel:1.0"
set inst       "my_accel_0"
set base       "0x41A00000"

# Current and target counts. The script adds exactly one MI and one SI.
set old_mi 7
set new_mi 8
set old_si 4
set new_si 5

# Optional post-generate width checks: {{signal_name LEFT_value} ...}
# Example (64-bit = 63, 32-bit = 31):
#   set width_checks {
#       {axi_smc_S00_AXI_rdata 63}
#       {axi_smc_S01_AXI_wdata 63}
#       {axi_smc_S02_AXI_rdata 31}
#       {axi_smc_S03_AXI_rdata 63}
#       {axi_smc_S04_AXI_rdata 31}
#       {axi_smc_M00_AXI_rdata 63}
#   }
set width_checks {}
# ---------------------------------------------------------------------------

proc step {n text} { puts "\n--- \[$n\] $text" }

proc hwh_left {path signame} {
    if {![file isfile $path]} { return "MISSING" }
    set f [open $path r]
    set txt [read $f]
    close $f
    if {[regexp "<PORT\[^>\]*LEFT=\"(\[0-9\]+)\"\[^>\]*SIGNAME=\"$signame\"" \
             $txt -> left]} {
        return $left
    }
    return "MISSING"
}

set bd_src "$proj_dir/${proj_name}.srcs/sources_1/bd/$bd_name"
set stamp  [clock format [clock seconds] -format %Y%m%d_%H%M%S]
set bd_bak "$proj_dir/_bd_backup/${bd_name}_$stamp"
file mkdir "$proj_dir/_bd_backup"
file mkdir $bd_bak
foreach f [glob -nocomplain -directory $bd_src *] {
    file copy -force $f $bd_bak
}
puts "backup of $bd_name -> $bd_bak"

open_project "$proj_dir/$proj_name.xpr"
open_bd_design [get_files $bd_name.bd]

step 0 "sanity"
set xbar [get_bd_cells ps7_0_axi_periph]
set smc  [get_bd_cells axi_smc]
set mi [get_property CONFIG.NUM_MI $xbar]
set si [get_property CONFIG.NUM_SI $smc]
puts "  NUM_MI=$mi (expect $old_mi), NUM_SI=$si (expect $old_si)"
if {$mi != $old_mi || $si != $old_si} {
    puts "  ERROR: unexpected starting point. Restore the backup / edit CONFIGURE."
    exit 1
}
if {[llength [get_bd_cells -quiet $inst]]} {
    puts "  ERROR: $inst already exists"
    exit 1
}
if {![llength [get_ipdefs -quiet $vlnv]]} {
    puts "  ERROR: $vlnv not found. Package the IP and register the IP repo first."
    exit 1
}

step 1 "widen AXI-Lite interconnect $old_mi -> $new_mi"
set_property -dict [list CONFIG.NUM_MI [list $new_mi]] $xbar
set mi_idx [expr {$new_mi - 1}]
set mi_axi   [format "M%02d_AXI"    $mi_idx]
set mi_aclk  [format "M%02d_ACLK"   $mi_idx]
set mi_arst  [format "M%02d_ARESETN" $mi_idx]
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] \
               [get_bd_pins ps7_0_axi_periph/$mi_aclk]
connect_bd_net [get_bd_pins rst_ps7_0_50M/peripheral_aresetn] \
               [get_bd_pins ps7_0_axi_periph/$mi_arst]
puts "  wired $mi_aclk / $mi_arst"

step 2 "widen SmartConnect $old_si -> $new_si"
set_property -dict [list CONFIG.NUM_SI [list $new_si]] $smc
set si_idx [expr {$new_si - 1}]
set si_axi [format "S%02d_AXI" $si_idx]
if {![llength [get_bd_intf_pins -quiet axi_smc/$si_axi]]} {
    puts "  ERROR: $si_axi did not appear"
    exit 1
}
if {[llength [get_bd_intf_nets -quiet -of_objects \
                  [get_bd_intf_pins axi_smc/$si_axi]]]} {
    puts "  ERROR: $si_axi is already connected"
    exit 1
}

step 3 "create $inst"
set cnn [create_bd_cell -type ip -vlnv $vlnv $inst]
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins $cnn/ap_clk]
connect_bd_net [get_bd_pins rst_ps7_0_50M/peripheral_aresetn] [get_bd_pins $cnn/ap_rst_n]
connect_bd_intf_net [get_bd_intf_pins ps7_0_axi_periph/$mi_axi] \
                    [get_bd_intf_pins $cnn/s_axi_control]
connect_bd_intf_net [get_bd_intf_pins axi_smc/$si_axi] \
                    [get_bd_intf_pins $cnn/m_axi_gmem]

step 4 "address map"
assign_bd_address -offset $base -range 0x00010000 \
  -target_address_space [get_bd_addr_spaces processing_system7_0/Data] \
  [get_bd_addr_segs $cnn/s_axi_control/Reg] -force
set mspaces [get_bd_addr_spaces -quiet -of_objects $cnn]
foreach sp $mspaces {
    if {![llength [get_bd_addr_segs -quiet -of_objects $sp]]} {
        catch {assign_bd_address -quiet} err
        puts "  auto assign_bd_address: $err"
    }
}

step 5 "validate / save / generate"
if {[catch {validate_bd_design} err]} {
    puts "  VALIDATE ERROR: $err"
    exit 1
}
save_bd_design
generate_target all [get_files $bd_name.bd]
update_compile_order -fileset sources_1

step 6 "post-generate hwh width checks"
set hwh "$proj_dir/${proj_name}.gen/sources_1/bd/$bd_name/hw_handoff/$bd_name.hwh"
set bad 0
foreach chk $width_checks {
    set sig  [lindex $chk 0]
    set want [lindex $chk 1]
    set got  [hwh_left $hwh $sig]
    set ok   [expr {$got eq $want}]
    puts [format "  %-32s LEFT=%-8s want=%-3s %s" \
              $sig $got $want [expr {$ok ? "OK" : "**MISMATCH**"}]]
    if {!$ok} { incr bad }
}
if {$bad} {
    puts "\n  *** ABORT: generated netlist widths changed. ***"
    puts "  Restore the BD from: $bd_bak"
    exit 1
}
puts "\n=== DONE ==="
puts "  Next: run refresh_hls_ip_template.tcl after every build_ip, then"
puts "        build_bitstream.tcl. Check clk_fpga_0 WNS and resources."
