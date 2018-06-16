#!/usr/bin/python

import os
import argparse
import sys

script_loc = os.path.dirname(os.path.realpath(__file__))
vector_keyword = ["V", "W", "all_pins_"]
domain_td1_keyword = ["Domain", "TD1"]
domain_td1 = False
domain_norm_keyword = ["Domain", "NORM"]
domain_norm = False
opcode_nop = "{:>14}".format("NOP")
opcode_exit = "EXIT"
scan_shift = "scan_shift_scan_memory"
scan_capture = "scan_capture"
previous_tck_val = 9
current_tck_val = 9
vector_count = 0
lst_scl = []
list_norm = []
new_list_norm = []
#global next_vector_newlistnorm
scan_clk_dict = {
    "scan_clk_a" : 'C',
    "scan_clk_b" : 'c'
}
pin_dict = {
    "scan_clk_a" : 84,
    "scan_clk_b" : 123,
    "tck" : 8,
    "rst" : 12,
    "alert" : 124
}

# pin_scan_channel_link
pin_scl = {
    #SCANIN
    "SA_0": 16,
    "SA_1": 17,
    "SA_2": 18,
    "SDA": 15,
    "TRIG" : 38,
    "SXP_RST_N_4": 40,
    "SXP_RST_N_2": 168,
    "SCL": 14,
    "SXP_RST_N_5": 99,

    #SCANOUT
    "VISA_DQ_0": 27,
    "VISA_DQ_1": 28,
    "VISA_DQ_2": 29,
    "VISA_DQ_3": 30,
    "VISA_DQ_4": 31,
    "VISA_DQ_5": 32,
    "VISA_DQ_6": 33,
    "VISA_DQ_7": 34,
    "VISA_DQS_DP": 26,

    "SXP_RST_N_5_": 99
}

new_pat_file_template = """\
Version 1.0 ;
#---------------------------
# Main Pattern Definition
#---------------------------
MainPattern
{
    CommonSection
    {
        Timing "bwv_stuck_at.tim:bwv_stuck_at_tim";
        PinDescription "bwv.pin";
        Pxr "bwv_stuck_at.pxr";
        Domain TD1
        {
            $include "{1}";
        }
        Domain NORM
        {
            $include "{2}";
        }
    }
}
"""


def cmdline_parser():
    global pat_file, new_pat_file, new_pat_norm_file, new_pat_td1_file, rst, dbg
    parser = argparse.ArgumentParser(description="Compress a pattern file.")
    parser.add_argument("file_input", help = "pattern file to be compressed")
    parser.add_argument("--rst", action = "store_true", help = "enable rst mode")
    parser.add_argument("--debug", action="store_true", help="enable debug mode, don't do channel linking")
    try:
        args = parser.parse_args()
    except Exception as exc:
        print_error(str(exc), 2)
    else:
        pat_file = "{}/{}".format(script_loc, args.file_input)
        if not os.path.isfile(pat_file):
            print_error("{} not found".format(pat_file), 1)
        if pat_file.rstrip().endswith(".pat"):
            new_pat_norm_file = "{}".format(pat_file.replace(".pat", "_norm.pat.data"))
            new_pat_td1_file = "{}".format(pat_file.replace(".pat", "_td1.pat.data"))
            new_pat_file = "{}".format(pat_file.replace(".pat", "_output.pat"))
            output_file_list = [new_pat_norm_file, new_pat_td1_file, new_pat_file]
            for filename in output_file_list:
                if os.path.isfile(filename):
                    os.remove(filename)
        else:
            print_error("Input file is not a .pat file", 1)
        rst = args.rst
        dbg = args.debug


def mode_shift(line):
    lst1 = line.split("=")
    lst2 = list(lst1[1].lstrip())
    lst2[pin_dict["scan_clk_a"]] = scan_clk_dict["scan_clk_a"]
    lst2[pin_dict["scan_clk_b"]] = scan_clk_dict["scan_clk_b"]
    str1 = " " + "".join(lst2)
    lst1[1] = str1
    return "=".join(lst1)


def mode_capture(line, line_no):
    global previous_tck_val, current_tck_val, vector_count
    if line_no == 1:
        previous_tck_val = 9
        current_tck_val = 1
    else:
        if previous_tck_val == current_tck_val:
            current_tck_val ^= 1
        else:
            previous_tck_val = current_tck_val
    lst1 = line.split("=")
    lst2 = list(lst1[1].lstrip())
    lst2[pin_dict["tck"]] = str(current_tck_val)
    if rst:
        alert_val = lst2[pin_dict["alert"]]
        if alert_val == "1":
            vector_count += 1
            if vector_count > 12 and vector_count < 25:
                lst2[pin_dict["rst"]] = "0"
    str1 = " " + "".join(lst2)
    lst1[1] = str1
    return "=".join(lst1)


def print_error(err_msg, err_code):
    """
    error code: 1)  IO/file error
                2)  Command line argument parsing error
                3)  Keyboard interrupt
                -1) Misc/Other/Unknown errors
    """
    print(err_msg)
    sys.exit(err_code)


def main_process(pat_file):
    global vector_count, domain_td1, domain_norm, new_pat_file_template
    current_mode = ""
    line_no = 1
    try:
        f = open(pat_file, "r")
        f_new_pat = open(new_pat_file, "a")
        f_new_td1 = open(new_pat_td1_file, "a")
        f_new_norm = open(new_pat_norm_file, "a")
    except Exception as exc:
        print_error(str(exc), 1)
    else:
        f_new_pat.write(new_pat_file_template.replace("{1}", os.path.basename(new_pat_td1_file)).replace("{2}", os.path.basename(new_pat_norm_file)))
        for line in f:
            if all(each_keyword in line for each_keyword in domain_td1_keyword):
                domain_td1 = True
                continue
            elif all(each_keyword in line for each_keyword in domain_norm_keyword):
                domain_norm = True
                continue
            if domain_td1:
                if opcode_exit in line:
                    domain_td1 = False
                f_new_td1.write(line.lstrip())
            elif domain_norm:
                if all(each_keyword in line for each_keyword in vector_keyword):
                    mode = "".join(line.split()).split("all_pins_norm=")[2].split(";")[0]
                    if mode != current_mode:
                        line_no = 1
                        current_mode = mode
                        if rst:
                            vector_count = 0
                    if line_no % 2 != 0:
                        if scan_shift in line:
                            line = mode_shift(line)
                        elif scan_capture in line:
                            line = mode_capture(line, line_no)
                        if opcode_exit not in line:
                            line = "{} {}".format(opcode_nop, line.lstrip())
                        if dbg:
                            f_new_norm.write(line)
                        else:
                            list_norm.append(line)
                    if opcode_exit in line:
                        domain_norm = False
                        if line_no % 2 == 0:
                            if dbg:
                                f_new_norm.write(line)
                            else:
                                list_norm.append(line)
                    line_no += 1
                else:
                    if dbg:
                        f_new_norm.write(line)
                    else:
                        list_norm.append(line)
        f.close()
        f_new_pat.close()
        f_new_td1.close()
        f_new_norm.close()
        print("Compression completed!")


def mode_strip_scl(line):
    ls1 = line.split("=")
    ls2 = list(ls1[1].lstrip())

    ls3 = ls2[pin_scl["SA_0"]] + ls2[pin_scl["SA_1"]] + ls2[pin_scl["SA_2"]] + ls2[pin_scl["SA_2"]] \
          + ls2[pin_scl["SDA"]] + ls2[pin_scl["TRIG"]] + ls2[pin_scl["SXP_RST_N_4"]] + ls2[pin_scl["SXP_RST_N_2"]] \
          + ls2[pin_scl["SCL"]] + ls2[pin_scl["SXP_RST_N_5_"]] \
          + ls2[pin_scl["VISA_DQ_0"]] + ls2[pin_scl["VISA_DQ_1"]] + ls2[pin_scl["VISA_DQ_2"]] \
          + ls2[pin_scl["VISA_DQ_3"]] + ls2[pin_scl["VISA_DQ_4"]] + ls2[pin_scl["VISA_DQ_5"]] \
          + ls2[pin_scl["VISA_DQ_6"]] + ls2[pin_scl["VISA_DQ_7"]] + ls2[pin_scl["VISA_DQS_DP"]] \
          + ls2[pin_scl["SXP_RST_N_5_"]]

    joinstr = " " + "".join(ls3 + "; } W { all_pins_norm ")
    ls1[1] = joinstr
    final = "=".join(ls1)
    return final


# removed "W { all_pins_norm = scan_shift_scan_memory; }"
# and replaced "{ V { all_pins_norm", "{ S { scan_memory_norm"
def mode_smn(element):
    new_element = element.replace("W { all_pins_norm = scan_shift_scan_memory; }", "") \
        .replace("{ V { all_pins_norm", "{ S { scan_memory_norm")
    return new_element


def scan_channel_link():
    # if debug is enabled, scan channel link won't run. Thus checking the list_norm if empty, exit.
    if len(list_norm) == 0:
        print("Scan channel link is not run.")
        exit()
    else:
        pass

    line_num = 0
    try:
        f_new_norm = open(new_pat_norm_file, "a")
    except Exception as exc:
        print_error(str(exc), 1)
    else:
        for index, element in enumerate(list_norm):
            if "all_pins_norm" in element:
                new_list_norm.append(element)

            try:
                next_line = list_norm[index + 1]
                next_vector_newlistnorm = new_list_norm[index + 1]
                #print("".join(new_list_norm))

            except IndexError:
                pass

            # next_line = keep reassigning until it find a vector line
            #
            # assign that == next_line
            #
            # check current_state == next_line

            if scan_shift in element:
                line_num += 1

                if line_num == 1:
                    new_element = element.replace("NOP {", "JSC {")
                    lst_scl.append(new_element)

                elif line_num != 1 and "capture" in next_line:
                    element = mode_smn(mode_strip_scl(element))
                    new_element = element.replace("NOP {", "EXITSC {")
                    lst_scl.append(new_element)

                else:
                    element = mode_smn(mode_strip_scl(element))
                    lst_scl.append(element)

            else:
                lst_scl.append(element)
                line_num = 0

        #print("".join(new_list_norm))

        if len(list_norm) == len(lst_scl):
            print("Scan channel link completed!")
        else:
            print("Scan channel link failed!")
            print(len(list_norm), len(lst_scl))

        f_new_norm.write("".join(lst_scl))
        f_new_norm.close()


def new_list():
    for index, element in enumerate(list_norm):
        try:
            #next_line = list_norm[index + 1]
            new_list_norm = []
            if "all_pins_norm" in element:
                new_list_norm.append(element)
        except IndexError:
            # next_line = ""
            pass
        else:
            print(new_list_norm)


if __name__ == '__main__':
    try:
        cmdline_parser()
        main_process(pat_file)
        scan_channel_link()
        #new_list()


    except KeyboardInterrupt:
        print_error("Keyboard interrupt.", 3)
    except Exception as exc:
        print_error(str(exc), -1)

