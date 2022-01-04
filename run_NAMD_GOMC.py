import argparse
import sys
import os
import datetime
import subprocess
import pandas as pd
import numpy as np
import json

from warnings import warn

# MD/MC simulations (NAMD/GOMC) for the NPT, NVT, GEMC, and GCMC ensembles
# *************************************************
# Import the user variables from the json file (start)
# *************************************************


# *************************************************
# The python arguments that need to be selected to run the simulations (start)
# *************************************************
def _get_args():
    arg_parser = argparse.ArgumentParser()

    # get the filename with the user required input
    arg_parser.add_argument("-f", "--file",
                            help="Defines the variable inputs file used for the hybrid NAMD/GOMC simulation script. "
                                 "This file (i.e., the user_input_variables_NAMD_GOMC.json file) is required "
                                 "to run the hybrid simulation.",
                            type=str)

    arg_parser.add_argument("-namd_sims_order", "--namd_simulation_order",
                            help="This sets the NAMD simulation to be run in series or parallel. "
                                 "The data is entered only as series or parallel (default = series). "
                                 "This is only relevant for the GEMC ensemble when utilizing two (2) NAMD simulation "
                                 "boxes "
                                 "(i.e., only_use_box_0_for_namd_for_gemc = False  --> both box 0 and box 1)." 
                                 "The GCMC, NVT, NPT, or the GEMC ensembles when using only one (1) "
                                 "NAMD simulation box "
                                 "(i.e., only_use_box_0_for_namd_for_gemc = True --> only box 0) "
                                 "are always run in series, since there is nothing to run in parallel."
                                 "Note: this feature was added so the user can minimize the load on the GPU "
                                 "by running both NAMD simulations in parallel.",
                            type=str)

    parser_arguments = arg_parser.parse_args()

    # check to see if the file exists
    if parser_arguments.file :
        if os.path.exists(parser_arguments.file) :
            print("INFO: Reading data from <{}> file.".format(parser_arguments.file))
        else :
            print("ERROR: Console file <{}> does not exist!".format(parser_arguments.file))
            sys.exit(1)

    # set NAMD simulation order
    if parser_arguments.namd_simulation_order == 'parallel' or parser_arguments.namd_simulation_order == 'series':
        print("INFO: The NAMD simulations shall be run in  <{}>.".format(parser_arguments.namd_simulation_order))

    elif parser_arguments.namd_simulation_order != 'parallel' and parser_arguments.namd_simulation_order != 'series':
        parser_arguments.namd_simulation_order = 'series'
        print("WARNING: The NAMD simulations are not set to 'parallel' or 'series'.  Therefore, "
              "the NAMD simulations are being default set to <{}>.".format(parser_arguments.namd_simulation_order))

    print('arg_parser.file = ' + str(parser_arguments.file))
    print('parser_arguments.namd_simulation_order = ' + str(parser_arguments.namd_simulation_order))
    return [parser_arguments.file,  parser_arguments.namd_simulation_order]

# *************************************************
# The python arguments that need to be selected to run the simulations (end)
# *************************************************

# *************************************************
# Import read and check the user input file for errors (start)
# *************************************************
# import and read the users json file
[json_filename, namd_sim_order] = _get_args()
print('json_filename = ' +str(json_filename))
print('namd_sim_order = ' +str(namd_sim_order))

# just for testing , need to remove later
manual_testing_filename_input_override = False
if json_filename is None and manual_testing_filename_input_override is True:
    json_filename = "user_input_NAMD_GOMC.json"

json_file_data = json.load(open(json_filename)) # standard name is "user_input_NAMD_GOMC.json"
json_file_data_keys_list = json_file_data.keys()

# get the total_cycles_namd_gomc_sims variable from the json file
if "total_cycles_namd_gomc_sims" not in json_file_data_keys_list:
    raise TypeError("The total_cycles_namd_gomc_sims key is not provided.\n")
total_cycles_namd_gomc_sims = json_file_data["total_cycles_namd_gomc_sims"]
if not isinstance(total_cycles_namd_gomc_sims, int):
    raise TypeError("The total_cycles_namd_gomc_sims values must be an integer.\n")
else:
    if total_cycles_namd_gomc_sims < 0:
        raise TypeError("The total_cycles_namd_gomc_sims values must be an integer "
                        "greater than or equal to zero (>=0.\n")

# get the starting_at_cycle_namd_gomc_sims variable from the json file
if "starting_at_cycle_namd_gomc_sims" not in json_file_data_keys_list:
    raise TypeError("The starting_at_cycle_namd_gomc_sims key is not provided.\n")
starting_at_cycle_namd_gomc_sims = json_file_data["starting_at_cycle_namd_gomc_sims"]
if not isinstance(starting_at_cycle_namd_gomc_sims, int):
    raise TypeError("The starting_at_cycle_namd_gomc_sims values must be an integer.\n")
else:
    if starting_at_cycle_namd_gomc_sims < 0:
        raise TypeError("The starting_at_cycle_namd_gomc_sims values must be an integer "
                        "greater than or equal to zero (>=0.\n")

# get the use_CPU_or_GPU variable from the json file
if "gomc_use_CPU_or_GPU" not in json_file_data_keys_list:
    raise TypeError("The gomc_use_CPU_or_GPU key is not provided.\n")
gomc_use_CPU_or_GPU = json_file_data["gomc_use_CPU_or_GPU"]
if not isinstance(gomc_use_CPU_or_GPU, str):
    raise TypeError("The gomc_use_CPU_or_GPU is not a string.\n")
if gomc_use_CPU_or_GPU != 'CPU' and gomc_use_CPU_or_GPU != 'GPU':
    raise ValueError("The gomc_use_CPU_or_GPU is the string 'CPU' or 'GPU'.\n")

# get the simulation_type variable from the json file
if "simulation_type" not in json_file_data_keys_list:
    raise TypeError("The simulation_type key is not provided.\n")
simulation_type = json_file_data["simulation_type"]
if not isinstance(simulation_type, str):
    raise TypeError("The simulation_type is not a string.\n")
if simulation_type not in ['GEMC', 'GCMC', 'NPT', 'NVT']:
    raise ValueError("The simulation_type is the string 'GEMC', 'GCMC', 'NPT', or 'NVT'.\n")

# get the only_use_box_0_for_namd_for_gemc variable from the json file
if "only_use_box_0_for_namd_for_gemc" not in json_file_data_keys_list:
    raise TypeError("The only_use_box_0_for_namd_for_gemc key is not provided.\n")
only_use_box_0_for_namd_for_gemc = json_file_data["only_use_box_0_for_namd_for_gemc"]
if only_use_box_0_for_namd_for_gemc is not True and only_use_box_0_for_namd_for_gemc is not False:
    raise TypeError("The only_use_box_0_for_namd_for_gemc not true or false in the json file.\n")

# get the no_core_box_0 variable from the json file
if "no_core_box_0" not in json_file_data_keys_list:
    raise TypeError("The no_core_box_0 key is not provided.\n")
no_core_box_0 = json_file_data["no_core_box_0"]
if not isinstance(no_core_box_0, int):
    raise TypeError("The no_core_box_0 values must be an interger.\n")
else:
    if only_use_box_0_for_namd_for_gemc is False and simulation_type == "GEMC":
        if no_core_box_0 < 0:
            raise ValueError('The no_core_box_{} values must be an interger greater '
                             'than or equal to  zero (>=0)'.format(0))

# get the no_core_box_1 variable from the json file
if "no_core_box_1" not in json_file_data_keys_list:
    raise TypeError("The no_core_box_1 key is not provided.\n")
no_core_box_1 = json_file_data["no_core_box_1"]
if not isinstance(no_core_box_1, int):
    raise TypeError("The no_core_box_1 values must be an interger.\n")
else:
    if only_use_box_0_for_namd_for_gemc is False and simulation_type == "GEMC":
        if no_core_box_1 <= 0:
            raise ValueError('The no_core_box_{} values must be an interger greater than zero (>0) '
                             'when using only_use_box_0_for_namd_for_gemc is False and '
                             'simulation_type == "GEMC" .\n'.format(1))
        if no_core_box_1 < 0:
            raise ValueError('The no_core_box_{} values must be an interger greater '
                             'than or equal to  zero (>=0)'.format(1))

# get the simulation_temp_k variable from the json file
if "simulation_temp_k" not in json_file_data_keys_list:
    raise TypeError("The simulation_temp_k key is not provided.\n")
simulation_temp_k = json_file_data["simulation_temp_k"]
if not isinstance(simulation_temp_k, int) and not isinstance(simulation_temp_k, float):
    raise TypeError("The simulation_temp_k values must be an interger or float.\n")
else:
    if simulation_temp_k <= 0:
        raise ValueError('The simulation_temp_k value must be an interger or float greater than zero (>0)')

# get the simulation_pressure_bar variable from the json file
if "simulation_pressure_bar" not in json_file_data_keys_list:
    raise TypeError("The simulation_pressure_bar key is not provided.\n")
simulation_pressure_bar = json_file_data["simulation_pressure_bar"]
if simulation_type in ['NPT']:
    if not isinstance(simulation_pressure_bar, int) and not isinstance(simulation_pressure_bar, float):
        raise TypeError("The simulation_pressure_bar values must be an interger or float.\n")
    else:
        if simulation_pressure_bar < 0:
            raise ValueError('The simulation_pressure_bar value must be an interger or float greater '
                             'than or equal to zero (>=0)')
elif simulation_type in ['GEMC', 'GCMC', 'NVT']:
    if not isinstance(simulation_pressure_bar, int) and not isinstance(simulation_pressure_bar, float) \
            and simulation_pressure_bar is not None:
        raise TypeError("The simulation_pressure_bar values must be an interger or float (>=0) or null/None.\n")

if simulation_type in ['GCMC']:
    # get the GCMC_ChemPot_or_Fugacity variable from the json file
    if "GCMC_ChemPot_or_Fugacity" not in json_file_data_keys_list:
        raise TypeError("The GCMC_ChemPot_or_Fugacity key is not provided.\n")
    GCMC_ChemPot_or_Fugacity = json_file_data["GCMC_ChemPot_or_Fugacity"]
    if not isinstance(GCMC_ChemPot_or_Fugacity, str) or \
            (GCMC_ChemPot_or_Fugacity != "ChemPot" and GCMC_ChemPot_or_Fugacity != "Fugacity"):
        raise TypeError('The GCMC_ChemPot_or_Fugacity values must be the string "ChemPot" or "Fugacity".\n')

    # get the GCMC_ChemPot_or_Fugacity_dict variable from the json file
    if "GCMC_ChemPot_or_Fugacity_dict" not in json_file_data_keys_list:
        raise TypeError("The GCMC_ChemPot_or_Fugacity_dict key is not provided.\n")
    GCMC_ChemPot_or_Fugacity_dict = json_file_data["GCMC_ChemPot_or_Fugacity_dict"]
    if not isinstance(GCMC_ChemPot_or_Fugacity_dict, dict):
        raise TypeError('The GCMC_ChemPot_or_Fugacity_dict values must a dictionary.\n')

    GCMC_ChemPot_or_Fugacity_dict_to_list = GCMC_ChemPot_or_Fugacity_dict.keys()
    if GCMC_ChemPot_or_Fugacity == "ChemPot":
        for chempot_i in GCMC_ChemPot_or_Fugacity_dict_to_list:
            if not isinstance(GCMC_ChemPot_or_Fugacity_dict[chempot_i], int) \
                    and not isinstance(GCMC_ChemPot_or_Fugacity_dict[chempot_i], float):
                raise TypeError("The GCMC_ChemPot_or_Fugacity_dict values must be floats or integers.\n")
    if GCMC_ChemPot_or_Fugacity == "Fugacity":
        for fugacity_i in GCMC_ChemPot_or_Fugacity_dict_to_list:
            if not isinstance(GCMC_ChemPot_or_Fugacity_dict[fugacity_i], int) \
                    and not isinstance(GCMC_ChemPot_or_Fugacity_dict[fugacity_i], float):
                raise TypeError("The GCMC_ChemPot_or_Fugacity_dict values must be floats or integers.\n")
            if GCMC_ChemPot_or_Fugacity_dict[fugacity_i] < 0:
                raise ValueError('The GCMC_ChemPot_or_Fugacity_dict values when using '
                                 'GCMC_ChemPot_or_Fugacity != "Fugacity", must be floats or integers '
                                 'greater than of equal to zero (>=) .\n')
else:
    GCMC_ChemPot_or_Fugacity = None
    GCMC_ChemPot_or_Fugacity_dict = None

# get the gomc_run_steps variable from the json file
if "gomc_run_steps" not in json_file_data_keys_list:
    raise TypeError("The gomc_run_steps key is not provided.\n")
gomc_run_steps = json_file_data["gomc_run_steps"]
if not isinstance(gomc_run_steps, int):
    raise TypeError("The gomc_run_steps values must be an interger.\n")

# get the namd_run_steps variable from the json file
if "namd_run_steps" not in json_file_data_keys_list:
    raise TypeError("The namd_run_steps key is not provided.\n")
namd_run_steps = json_file_data["namd_run_steps"]
if not isinstance(namd_run_steps, int):
    raise TypeError("The namd_run_steps values must be an interger.\n")

# get the namd_minimize_mult_scalar variable from the json file
if "namd_minimize_mult_scalar" not in json_file_data_keys_list:
    raise TypeError("The namd_minimize_mult_scalar key is not provided.\n")
namd_minimize_mult_scalar = json_file_data["namd_minimize_mult_scalar"]
if not isinstance(namd_run_steps, int):
    raise TypeError("The namd_minimize_mult_scalar values must be an interger.\n")

# get the set_x_dim_box_0 variable from the json file
if "set_dims_box_0_list" not in json_file_data_keys_list:
    raise TypeError("The set_dims_box_0_list key is not provided.\n")
set_dims_box_0_list = json_file_data["set_dims_box_0_list"]
if set_dims_box_0_list is not None:
    print_error_text = "The set_dims_box_0_list must be a null/None or list and contain three (3) integers or floats"\
                       "greater than zero (>0).\n"
    if isinstance(set_dims_box_0_list, list):
        if len(set_dims_box_0_list) == 3:
            for dims_box_i in set_dims_box_0_list:
                if isinstance(dims_box_i, int) is False and isinstance(dims_box_i, float) is False \
                        and dims_box_i != None:
                    raise TypeError(print_error_text)
                else:
                    if dims_box_i != None:
                        if dims_box_i <= 0:
                            raise TypeError(print_error_text)
        else:
            raise TypeError(print_error_text)
    else:
        raise TypeError(print_error_text)
elif set_dims_box_0_list is None:
    set_dims_box_0_list = [None, None, None]

# get the set_x_dim_box_1 variable from the json file
if "set_dims_box_1_list" not in json_file_data_keys_list:
    raise TypeError("The set_dims_box_1_list key is not provided.\n")
set_dims_box_1_list = json_file_data["set_dims_box_1_list"]
if set_dims_box_1_list is not None:
    print_error_text = "The set_dims_box_1_list must be a null/None or list and contain three (3) integers or floats"\
                       "greater than zero (>0).\n"
    if isinstance(set_dims_box_1_list, list):
        if len(set_dims_box_1_list) == 3:
            for dims_box_i in set_dims_box_1_list:
                if isinstance(dims_box_i, int) is False and isinstance(dims_box_i, float) is False \
                        and dims_box_i != None:
                    raise TypeError(print_error_text)
                else:
                    if dims_box_i != None:
                        if dims_box_i <= 0:
                            raise TypeError(print_error_text)
        else:
            raise TypeError(print_error_text)
    else:
        raise TypeError(print_error_text)
elif set_dims_box_1_list is None:
    set_dims_box_1_list = [None, None, None]

# get the set_angle_box_0_list variable from the json file
if "set_angle_box_0_list" not in json_file_data_keys_list:
    raise TypeError("The set_angle_box_0_list key is not provided.\n")
set_angle_box_0_list = json_file_data["set_angle_box_0_list"]
if set_angle_box_0_list is not None:
    print_error_text = "The set_angle_box_0_list must be a null/None or 90 (in degrees). Currently," \
                       "only orthogonal boxes are available.\n"
    if isinstance(set_angle_box_0_list, list):
        if len(set_angle_box_0_list) == 3:
            for angles_box_i in set_angle_box_0_list:
                if isinstance(angles_box_i, int) is False and isinstance(angles_box_i, float) is False \
                        and angles_box_i != None:
                    raise TypeError(print_error_text)
                else:
                    if angles_box_i != None:
                        if angles_box_i != 90:
                            raise TypeError(print_error_text)
        else:
            raise TypeError(print_error_text)
    else:
        raise TypeError(print_error_text)
elif set_angle_box_0_list is None:
    set_angle_box_0_list = [None, None, None]

# get the set_angle_box_1_list variable from the json file
if "set_angle_box_1_list" not in json_file_data_keys_list:
    raise TypeError("The set_angle_box_1_list key is not provided.\n")
set_angle_box_1_list = json_file_data["set_angle_box_1_list"]
if set_angle_box_1_list is not None:
    print_error_text = "The set_angle_box_1_list must be a null/None or 90 (in degrees). Currently," \
                       "only orthogonal boxes are available.\n"
    if isinstance(set_angle_box_1_list, list):
        if len(set_angle_box_1_list) == 3:
            for angles_box_i in set_angle_box_1_list:
                if isinstance(angles_box_i, int) is False and isinstance(angles_box_i, float) is False \
                        and angles_box_i != None:
                    raise TypeError(print_error_text)
                else:
                    if angles_box_i != None:
                        if angles_box_i != 90:
                            raise TypeError(print_error_text)
        else:
            raise TypeError(print_error_text)
    else:
        raise TypeError(print_error_text)
elif set_angle_box_1_list is None:
    set_angle_box_1_list = [None, None, None]

# get the starting_ff_file_list_gomc variable from the json file
if "starting_ff_file_list_gomc" not in json_file_data_keys_list:
    raise TypeError("The starting_ff_file_list_gomc key is not provided.\n")
starting_ff_file_list_gomc = json_file_data["starting_ff_file_list_gomc"]
if not isinstance(starting_ff_file_list_gomc, list):
    raise TypeError("The starting_ff_file_list_gomc values must be a list of strings.\n")
else:
    for start_ff_gomc_i in starting_ff_file_list_gomc:
        if not isinstance(start_ff_gomc_i, str):
            raise TypeError("The starting_ff_file_list_gomc list values must be strings.\n")

# get the starting_ff_file_list_namd variable from the json file
if "starting_ff_file_list_namd" not in json_file_data_keys_list:
    raise TypeError("The starting_ff_file_list_namd key is not provided.\n")
starting_ff_file_list_namd = json_file_data["starting_ff_file_list_namd"]
if not isinstance(starting_ff_file_list_namd, list):
    raise TypeError("The starting_ff_file_list_namd values must be a list of strings.\n")
else:
    for start_ff_gomc_i in starting_ff_file_list_namd:
        if not isinstance(start_ff_gomc_i, str):
            raise TypeError("The starting_ff_file_list_namd list values must be strings.\n")

# get the starting_pdb_box_0_file variable from the json file
if "starting_pdb_box_0_file" not in json_file_data_keys_list:
    raise TypeError("The starting_pdb_box_0_file key is not provided.\n")
starting_pdb_box_0_file = json_file_data["starting_pdb_box_0_file"]
if not isinstance(starting_pdb_box_0_file, str):
    raise TypeError("The starting_pdb_box_0_file is not a string.\n")

# get the starting_psf_box_0_file variable from the json file
if "starting_psf_box_0_file" not in json_file_data_keys_list:
    raise TypeError("The starting_psf_box_0_file key is not provided.\n")
starting_psf_box_0_file = json_file_data["starting_psf_box_0_file"]
if not isinstance(starting_psf_box_0_file, str):
    raise TypeError("The starting_psf_box_0_file is not a string.\n")

if simulation_type in ['GCMC', 'GEMC']:
    # get the starting_pdb_box_1_file variable from the json file
    if "starting_pdb_box_1_file" not in json_file_data_keys_list:
        raise TypeError("The starting_pdb_box_1_file key is not provided.\n")
    starting_pdb_box_1_file = json_file_data["starting_pdb_box_1_file"]
    if not isinstance(starting_pdb_box_0_file, str):
        raise TypeError("The starting_pdb_box_1_file is not a string.\n")

    # get the starting_psf_box_1_file variable from the json file
    if "starting_psf_box_1_file" not in json_file_data_keys_list:
        raise TypeError("The starting_psf_box_1_file key is not provided.\n")
    starting_psf_box_1_file = json_file_data["starting_psf_box_1_file"]
    if not isinstance(starting_psf_box_1_file, str):
        raise TypeError("The starting_psf_box_1_file is not a string.\n")
else:
    starting_pdb_box_1_file = ''
    starting_psf_box_1_file = ''
# get the namd2_bin_directory variable from the json file
# json file specifies relative path to the directory where the namd2 is located
if "namd2_bin_directory" not in json_file_data_keys_list:
    raise TypeError("The namd2_bin_directory key is not provided.\n")
namd2_bin_directory = json_file_data["namd2_bin_directory"]
if isinstance(namd2_bin_directory, str) is False:
    raise TypeError("The namd2_bin_directory values must be an string.\n")
else:
    namd_bin_file = '{}/{}/{}'.format(str(os.getcwd()), namd2_bin_directory, "namd2")

# get the gomc_bin_directory variable from the json file
# json file specifies relative path to the directory where the GOMC_XXX_XXX binary files are located
if "gomc_bin_directory" not in json_file_data_keys_list:
    raise TypeError("The gomc_bin_directory key is not provided.\n")
gomc_bin_directory = json_file_data["gomc_bin_directory"]
if isinstance(gomc_bin_directory, str) is False:
    raise TypeError("The gomc_bin_directory values must be an string.\n")
else:
    gomc_bin_file = '{}/{}/GOMC_{}_{}'.format(str(os.getcwd()), gomc_bin_directory, gomc_use_CPU_or_GPU, simulation_type)

# *************************************************
# Import read and check the user input file for errors (end)
# *************************************************


# *************************************************
# Potential changable variables in the future (start)
# *************************************************
allowable_error_fraction_vdw_plus_elec = 5 * 10**(-3)
allowable_error_fraction_potential = 5 * 10**(-3)
max_absolute_allowable_kcal_fraction_vdw_plus_elec = 0.5

gomc_console_blkavg_hist_steps = int(gomc_run_steps)
gomc_rst_coor_ckpoint_steps = int(gomc_run_steps)

if gomc_run_steps/10 > 500:
    gomc_hist_sample_steps = int(500)
elif gomc_run_steps/10 <= 500:
    gomc_hist_sample_steps = int(gomc_run_steps/10)

namd_rst_dcd_xst_steps = int(namd_run_steps)
namd_console_blkavg_e_and_p_steps = int(namd_run_steps)

# *************************************************
# Potential changable variables in the future (end)
# *************************************************

# *************************************************
# check for existing and create NAMD and GOMC folders (start)
# *************************************************
if os.path.isdir('NAMD') or os.path.isdir('GOMC'):
    warn('INFORMATION: if the system fails to start (with errors) from the beginning of a simulation, '
         'you may need to delete the main GOMC and NAMD folders.  '
         'The failure to start/restart may be caused by the last simulation not finishing correctly.'
         )
    warn('INFORMATION: If the system fails to restart a previous run (with errors), '
         'you may need to delete the last subfolders under the main '
         'NAMD and GOMC (i.e., folders NAMD = 00000000_a or GOMC = 00000001). '
         'The failure to start/restart may be caused by the last simulation not finishing properly.'
         )

path_namd_runs = "NAMD"
os.makedirs(path_namd_runs, exist_ok=True)

path_gomc_runs = "GOMC"
os.makedirs(path_gomc_runs, exist_ok=True)
# *************************************************
# create NAMD and GOMC folders (end)
# *************************************************

# *************************************************
# create NAMD and GOMC config file templates locations (start)
# *************************************************
path_namd_template = 'required_data/config_files/NAMD.conf'

path_gomc_template = 'required_data/config_files/GOMC_'+str(simulation_type) + '.conf'
# *************************************************
# create NAMD and GOMC config file templates locations (end)
# *************************************************

gomc_ff_error_message = "ERROR: The GOMC force field(s) need to be provided as a list of string(s).\n"
namd_ff_error_message = "ERROR: The GOMC force field(s) need to be provided as a list of string(s).\n"
if isinstance(starting_ff_file_list_gomc, list) is False:
    raise TypeError(gomc_ff_error_message)
if isinstance(starting_ff_file_list_namd, list) is False:
    raise TypeError(namd_ff_error_message)

for gomc_ff_i in starting_ff_file_list_gomc:
    if isinstance(gomc_ff_i, str) is False:
        raise TypeError(gomc_ff_error_message)
for namd_ff_i in starting_ff_file_list_namd:
    if isinstance(namd_ff_i, str) is False:
        raise TypeError(namd_ff_error_message)

if simulation_type in ['GCMC']:
    if isinstance(GCMC_ChemPot_or_Fugacity_dict, dict) is False:
        raise TypeError("ERROR: enter the chemical potential or fugacity data (GCMC_ChemPot_or_Fugacity_dict)"
                        "as a dictionary when using the GCMC ensemble.\n")

    if GCMC_ChemPot_or_Fugacity is None:
        raise ValueError("The GCMC_ChemPot_or_Fugacity can not be None when running the GCMC ensemble.\n")
    if GCMC_ChemPot_or_Fugacity != 'ChemPot' and GCMC_ChemPot_or_Fugacity != 'Fugacity':
        raise ValueError('The GCMC_ChemPot_or_Fugacity can either be the string '
                         '"ChemPot" or "Fugacity" when running the GCMC ensemble.\n')

    GCMC_ChemPot_or_Fugacity_dict_keys = GCMC_ChemPot_or_Fugacity_dict.keys()
    for keys_i in GCMC_ChemPot_or_Fugacity_dict_keys:
        if isinstance(GCMC_ChemPot_or_Fugacity_dict[keys_i], int) is False \
                and isinstance(GCMC_ChemPot_or_Fugacity_dict[keys_i], float) is False:
            raise TypeError("The GCMC_ChemPot_or_Fugacity_dict values must be an interger or float.\n")

        if isinstance(keys_i, str) is False:
            raise TypeError("The GCMC_ChemPot_or_Fugacity_dict keys must be a string.\n")

        if GCMC_ChemPot_or_Fugacity == 'Fugacity' and GCMC_ChemPot_or_Fugacity_dict[keys_i] < 0:
            raise ValueError('When using Fugacity, the GCMC_ChemPot_or_Fugacity values must be '
                             'greater than or equal to zero (>=0).\n')
        
# check the pressure values and set to atomospheric if not used
if simulation_type in ['NPT'] and (isinstance(simulation_pressure_bar, float) is False
                                   and isinstance(simulation_pressure_bar, int) is False):
    raise TypeError("The simulation pressure needs to be set for the NPT simulation type (int or float). \n")
if simulation_type in ['NPT'] and (
        isinstance(simulation_pressure_bar, float) is True or isinstance(simulation_pressure_bar, int) is True):
    if simulation_pressure_bar < 0:
        raise ValueError("The simulation pressure needs to be set to a positive or zero [(int of float) >=0 bar] "
                         "value for the NPT simulation type. \n")
elif simulation_type in ['NVT', 'GEMC', 'GCMC']:
    # set pressure to atomospheric as it needs a number and it is not used
    simulation_pressure_bar = 1.01325

K_to_kcal_mol = 1.98720425864083 * 10**(-3)

python_file_directory = os.getcwd()

log_template_file = open("{}/NAMD_GOMC_started_at_cycle_No_{}.log".format(str(python_file_directory),
                                                                          str(starting_at_cycle_namd_gomc_sims)), 'w')

start_time = datetime.datetime.today()
start_time_s = datetime.datetime.today()
write_log_data = "*************************************************\n" \
                 "date and time (start) = {} \n" \
                 "************************************************* \n".format(str(start_time))
log_template_file.write(str(write_log_data))
print(str(write_log_data))

write_log_data = "*************************************************\n" + \
                 "namd_bin_file = {} \n" \
                 "************************************************* \n".format(str(namd_bin_file))
log_template_file.write(str(write_log_data))
print(str(write_log_data))

write_log_data = "*************************************************\n" + \
                 "gomc_bin_file = {} \n" \
                 "************************************************* \n".format(str(gomc_bin_file))
log_template_file.write(str(write_log_data))
print(str(write_log_data))


namd_minimize_steps = int(int(namd_run_steps) * int(namd_minimize_mult_scalar))
if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
    total_no_cores = no_core_box_0 + no_core_box_1

    if no_core_box_1 == 0:
        write_log_data = '*************************************************\n' \
                         'no_core_box_0 = {} \n' \
                         'WARNING: the number of CPU cores listed for box 1 is zero (0), and should be an ' \
                         'interger > 0, or the NAMD simulation for box 1 will not run and the python script ' \
                         'will crash \n, no_core_box_1 = {} \n' \
                         '*************************************************' \
                         ' \n'.format(str(no_core_box_0), str(no_core_box_1))
        log_template_file.write(str(write_log_data))
        warn(str(write_log_data))

    else:
        write_log_data = "*************************************************\n" \
                         "no_core_box_0 = {} \n" \
                         "no_core_box_1 = {} \n" \
                         "*************************************************" \
                         " \n".format(str(no_core_box_0), str(no_core_box_1))

        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

else:
    if no_core_box_1 != 0:
        write_log_data = "*************************************************\n" \
                         "no_core_box_0 = {} .\n" \
                         "WARNING: the number of CPU cores listed for box 1 are not being used, \n" \
                         "no_core_box_1 = {}\n" \
                         "*************************************************" \
                         " \n".format(str(no_core_box_0), str(no_core_box_1))
        log_template_file.write(str(write_log_data))
        warn(str(write_log_data))
        no_core_box_1 = 0

    total_no_cores = no_core_box_0

# Check total cores vs per box cores
if isinstance(no_core_box_0, int) is False:
    write_log_data = "*************************************************\n" \
                     "Enter no_core_box_0 as an interger, no_core_box_0 = {} \n" \
                     "************************************************* \n".format(str(no_core_box_0))
    log_template_file.write(str(write_log_data))
    print(str(write_log_data))

    if no_core_box_0 == 0:
        write_log_data = "*************************************************\n" \
                         "Enter no_core_box_0 as a non-zero number, no_core_box_0 = {} \n" \
                         "************************************************* \n".format(str(no_core_box_0))
        log_template_file.write(str(write_log_data))
        raise ValueError(str(write_log_data))

if simulation_type in ['GEMC', 'GCMC']:
    if isinstance(no_core_box_1, int) is False:
        write_log_data = "*************************************************\n" \
                         "Enter no_core_box_1 as an interger, no_core_box_1 = {} \n" \
                         "************************************************* \n".format(str(no_core_box_1))
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        if no_core_box_1 == 0:
            write_log_data = "*************************************************\n" \
                             "Enter no_core_box_1 as a non-zero number, no_core_box_1 = {} \n" \
                             "************************************************* \n".format(str(no_core_box_1))
            log_template_file.write(str(write_log_data))
            raise ValueError(str(write_log_data))


def calc_folder_zeros(run_number):
    """
    Adds zeros to fill in the left side of the run number to total 10 digits.

    Parameters
    ----------
    run_number : int
        Simulation run number

    Returns
    ---------
    add_number_of_zeros_at_start_run_no_str : str
        The zeros to add to the left side of the digit run number (run_number)
        to total 10 digits with the run number (run_number)
    """

    total_run_no_digits = 10
    add_no_zeros_at_start_run_no = int(total_run_no_digits - len(str(run_number)))
    add_number_of_zeros_at_start_run_no_str = ""
    for z in range(0, add_no_zeros_at_start_run_no):
        add_number_of_zeros_at_start_run_no_str += '0'
    return add_number_of_zeros_at_start_run_no_str


# run the GOMC and NAMD simulations
total_sims_namd_gomc = int(2 * total_cycles_namd_gomc_sims)
starting_sims_namd_gomc = int(2 * starting_at_cycle_namd_gomc_sims)


default_namd_e_titles = ['ETITLE:', 'TS', 'BOND', 'ANGLE', 'DIHED', 'IMPRP', 'ELECT', 'VDW', 'BOUNDARY',
                         'MISC', 'KINETIC', 'TOTAL', 'TEMP', 'POTENTIAL', 'TOTAL3', 'TEMPAVG', 'PRESSURE',
                         'GPRESSURE', 'VOLUME', 'PRESSAVG', 'GPRESSAVG']


def get_namd_run_0_pme_dim(box_number):
    """
    Gets the number of points for the NAMD PME grid in the x, y, and z-dimensions.
    It also provides the run 0 (1st NAMD simulation) run directory.

    Parameters
    ----------
    box_number : int
        The simulation box number, which can only be 0 or 1

    Returns
    ---------
    namd_x_pme_grid_dim : int
        The number of points for the NAMD PME grid in the x-dimension.
    namd_y_pme_grid_dim : int
        The number of points for the NAMD PME grid in the y-dimension.
    namd_z_pme_grid_dim : int
        The number of points for the NAMD PME grid in the z-dimension.
    namd_box_x_run_0_dir : str
        The run 0 (1st NAMD simulation) run directory.
    """

    if isinstance(box_number, int) is False and (box_number != 0 and box_number != 1):
        raise ValueError("ERROR: Enter an interger of 0 or 1 for box_number "
                         "in the get_namd_run_0_pme_dim function. \n")

    namd_first_run_no = int(0)
    add_zeros_for_box_x_run_0 = calc_folder_zeros(namd_first_run_no)

    if box_number == 0:
        namd_box_x_run_0_dir = "{}/{}/{}{}_a".format(str(python_file_directory),
                                                     path_namd_runs,
                                                     str(add_zeros_for_box_x_run_0),
                                                     str(namd_first_run_no)
                                                     )

    elif box_number == 1:
        namd_box_x_run_0_dir = "{}/{}/{}{}_b".format(str(python_file_directory),
                                                     path_namd_runs,
                                                     str(add_zeros_for_box_x_run_0),
                                                     str(namd_first_run_no)
                                                     )

    try:
        read_namd_box_x_run_0_log_file = open("{}/out.dat".format(namd_box_x_run_0_dir), 'r').readlines()

        for i, line in enumerate(read_namd_box_x_run_0_log_file):
            split_line = line.split()
            if len(split_line) >= 7:
                if split_line[0] == 'Info:' and split_line[1] == 'PME' and \
                        split_line[2] == 'GRID' and split_line[3] == 'DIMENSIONS':
                    namd_x_pme_grid_dim = int(split_line[4])
                    namd_y_pme_grid_dim = int(split_line[5])
                    namd_z_pme_grid_dim = int(split_line[6])

    except:
        namd_x_pme_grid_dim = None
        namd_y_pme_grid_dim = None
        namd_z_pme_grid_dim = None

    return namd_x_pme_grid_dim,  namd_y_pme_grid_dim, namd_z_pme_grid_dim, namd_box_x_run_0_dir


def get_namd_run_0_fft_filename(box_number):
    """
    Provides the run 0 (1st NAMD simulation) FFT filename.

    Parameters
    ----------
    box_number : int
        The simulation box number, which can only be 0 or 1

    Returns
    ---------
    namd_box_x_run_0_fft_namd_filename : str
       The run 0 (1st NAMD simulation) FFT filename.
    """

    if isinstance(box_number, int) is False and (box_number != 0 and box_number != 1):
        raise ValueError("ERROR: Enter an interger of 0 or 1  for box_number in "
                         "the get_namd_run_0_pme_dim function. \n")

    namd_first_run_no = int(0)
    add_zeros_for_box_x_run_0 = calc_folder_zeros(namd_first_run_no)

    if box_number == 0:
        namd_box_x_run_0_dir = "{}/{}/{}{}_a".format(str(python_file_directory),
                                                     path_namd_runs,
                                                     str(add_zeros_for_box_x_run_0),
                                                     str(namd_first_run_no)
                                                     )

    elif box_number == 1:
        namd_box_x_run_0_dir = "{}/{}/{}{}_b".format(str(python_file_directory),
                                                     path_namd_runs,
                                                     str(add_zeros_for_box_x_run_0),
                                                     str(namd_first_run_no)
                                                     )
    try:
        namd_box_x_run_0_file_list = sorted(os.listdir(namd_box_x_run_0_dir))
    except:
        namd_box_x_run_0_file_list = None

    try:
        for q in range(0, len(namd_box_x_run_0_file_list)):
            namd_box_x_run_0_fft_1st_9_char_filename = str(namd_box_x_run_0_file_list[q])[0:9]
            if namd_box_x_run_0_fft_1st_9_char_filename == 'FFTW_NAMD':
                namd_box_x_run_0_fft_namd_filename = namd_box_x_run_0_file_list[q]

        return namd_box_x_run_0_fft_namd_filename, namd_box_x_run_0_dir

    except:
        write_log_data = "*************************************************\n" \
                         "The NAMD FFT file not deteted from Run 0 in Box {} \n" \
                         "************************************************* \n".format(str(box_number))
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))


def delete_namd_run_0_fft_file(box_number):
    """
    Deletes the run 0 (1st NAMD simulation) FFT filename.

    Parameters
    ----------
    box_number : int
        The simulation box number, which can only be 0 or 1
    """
    if isinstance(box_number, int) is False and (box_number != 0 and box_number != 1):
        raise ValueError("ERROR Enter an interger of 0 or 1  for box_number in "
                         "the get_namd_run_0_pme_dim function. \n")

    write_log_data = "*************************************************\n" \
                     "The NAMD FFT file was deleted from Run 0 in Box {} \n" \
                     "************************************************* \n".format(str(box_number))
    try:
        namd_box_x_run_0_fft_namd_filename,\
        namd_box_x_run_0_dir = get_namd_run_0_fft_filename(box_number)

        # delete the FFT file in the run 0 box
        rm_namd_fft_box_0_command = "rm {}/{}".format(str(namd_box_x_run_0_dir),
                                                      str(namd_box_x_run_0_fft_namd_filename)
                                                      )

        exec_rm_namd_fft_box_0_command = subprocess.Popen(rm_namd_fft_box_0_command,
                                                          shell=True, stderr=subprocess.STDOUT)
        os.waitpid(exec_rm_namd_fft_box_0_command.pid, os.WSTOPPED)

        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

    except:
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))


def check_for_pdb_dims_and_override(dim_axis, run_no, read_dim, set_dim=None, only_on_run_no=0):
    """
    Sets the x, y, or z dimension based on the pdb file values or the user input.

    Parameters
    ----------
    dim_axis : str
        The dimension of the axis (only x, y, or z)
    run_no : int
        Simulation run number
    read_dim : int or float
        The dimension read from the pdb file or the set dim_axis.
    set_dim : int or float or None, (default = None)
        The user set dimension is use instead of the dimension
        read from the pdb file set dim_axis. The set_dim overrides
        the dimension read from the pdb file (read_dim).
    only_on_run_no : int, (default = 0)
        This only overrides the only set dimension on the the set value.

    Returns
    ---------
    used_dim : int or float:
        The used dimension.  This is the dimension read from the pdb file
        (if available) and if no set_dim is provided.  It is the set_dim,
        if the set_dim is provided.
    """

    # check user override dimensions
    if run_no == only_on_run_no:
        if read_dim is None:
            if set_dim is not None and (isinstance(set_dim, float) or isinstance(set_dim, int)):
                used_dim = set_dim
            else:
                write_log_data = "ERROR: The user defined {}-dimension is None " \
                                 "or not an integer or a float, and the PDB file has no dimension information " \
                                 " \n".format(str(dim_axis))
                log_template_file.write(str(write_log_data))
                raise TypeError(str(write_log_data))

        elif read_dim is not None and set_dim != read_dim and (isinstance(set_dim, float) or isinstance(set_dim, int)):
            write_log_data = "WARNING: The user defined {}-dimension is different " \
                             "than the one read from the starting PDB file {}-dim_PDB = {}, " \
                             "{}-dim_user_set = {}. The code is setting the user defined {}-dimension." \
                             " \n".format(str(dim_axis), str(dim_axis), str(read_dim),
                                          str(dim_axis), str(set_dim), str(dim_axis))
            log_template_file.write(str(write_log_data))
            warn(str(write_log_data))
            used_dim = set_dim

        else:
            used_dim = read_dim

    else:
        used_dim = read_dim

    return used_dim


def write_namd_conf_file(python_file_directory, path_namd_template, path_namd_runs, gomc_newdir,
                         run_no, box_number, namd_run_steps, namd_minimize_steps, namd_rst_dcd_xst_steps,
                         namd_console_blkavg_e_and_p_steps, simulation_temp_k, simulation_pressure_bar,
                         starting_pdb_box_x_file, starting_psf_box_x_file,
                         namd_x_pme_grid_dim, namd_y_pme_grid_dim, namd_z_pme_grid_dim,
                         set_x_dim=None, set_y_dim=None, set_z_dim=None,
                         set_angle_alpha=90, set_angle_beta=90, set_angle_gamma=90,
                         fft_add_namd_ang_to_box_dim=0):
    """
    Writes the NAMD control file in the NAMD run numbered folder

    Parameters
    ----------
    python_file_directory : str
        The path/directory where this file is located.
    path_namd_template : str
        The relative path to the namd template file from where this file is
        located (he directory where this file is located (python_file_director).
    path_namd_runs: str
        The path/directory to the main NAMD folder.
    gomc_newdir: str
        The path/dirctory to the GOMC directory that the NAMD control will use
        to start the on new NAMD simulation.
    run_no : int
        Simulation run number
    box_number : int
        The simulation box number, which can only be 0 or 1
    namd_run_steps : int
        The number of steps to run the NAMD simulation.
    namd_minimize_steps : int
        The number of minimization steps to run the NAMD simulation.
    namd_rst_dcd_xst_steps : int
        The number of steps which the restart, dcd, xst files will be created.
    namd_console_blkavg_e_and_p_steps : int
        The number of steps which the energies and pressure data will be output.
    simulation_temp_k : int or float
        The NAMD simulation temperature in Kelvin.
    simulation_pressure_bar : int or float
        The NAMD simulation pressure in bar.
    starting_pdb_box_x_file : str
        The pdb path/filename for box number (box_number) which is written
        to the NAMD control file.
    starting_psf_box_x_file : str
        The psf path/filename for box number (box_number) which is written
        to the NAMD control file.
    namd_x_pme_grid_dim : int
        The number of points for the NAMD PME grid in the x-dimension.
    namd_y_pme_grid_dim : int
        The number of points for the NAMD PME grid in the y-dimension.
    namd_z_pme_grid_dim : int
        The number of points for the NAMD PME grid in the z-dimension.
    set_x_dim : int or float or None (optional: default = None)
        Sets the x dimension from the simulation.
    set_y_dim : int or float or None (optional: default = None)
        Sets the y dimension from the simulation.
    set_z_dim : int or float or None (optional: default = None)
        Sets the z dimension from the simulation.
    set_angle_alpha : int of float (default = 90)
        Sets the alpha angle in degrees, for the orthogonal (90) or
        non-orthogonal (not 90) box.
    set_angle_beta : int of float (default = 90)
        Sets the beta angle in degrees, for the orthogonal (90) or
        non-orthogonal (not 90) box.
    set_angle_gamma : int of float (default = 90)
        Sets the gamma angle in degrees, for the orthogonal (90) or
        non-orthogonal (not 90) box.
    fft_add_namd_ang_to_box_dim : int
        The number of extra point to add to the boxes fft points

    Returns
    ---------
    namd_box_x_newdir : str
        The full path/directory of the created NAMD run/box number,
        which contains the control file.

    Notes
    ---------
    The box angles are not currently available and are default set to 90 degress.
    they can be added later, but for now all simulation but be orthoganol boxes
    """

    if isinstance(box_number, int) is False and (box_number != 0 or box_number != 1):
        raise ValueError("Enter an interger of 0 or 1  for box_number in the get_namd_run_0_pme_dim function. \n")

    # get NAMD box_x directory
    add_zeros_at_start_run_no_str = calc_folder_zeros(run_no)
    if box_number == 0:
        namd_box_x_newdir = "{}/{}/{}{}_a".format(str(python_file_directory), path_namd_runs,
                                                  str(add_zeros_at_start_run_no_str), str(run_no))
    elif box_number == 1:
        namd_box_x_newdir = "{}/{}/{}{}_b".format(str(python_file_directory), path_namd_runs,
                                                  str(add_zeros_at_start_run_no_str), str(run_no))
    os.makedirs(namd_box_x_newdir, exist_ok=True)
    generate_namd_file = open("{}/in.conf".format(namd_box_x_newdir), 'w')

    namd_template_file = open("{}/{}".format(str(python_file_directory), path_namd_template), 'r')
    namd_template_data = namd_template_file.read()
    namd_template_file.close()

    if run_no != 0:

        write_log_data = "************************************************* \n"
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        namd_starting_ff_files = ""
        for namd_ff_i in starting_ff_file_list_namd:
            namd_ff_i = os.path.relpath(namd_ff_i, namd_box_x_newdir)
            namd_starting_ff_files = namd_starting_ff_files + "parameters \t {}\n".format(namd_ff_i)

        new_namd_data = namd_template_data.replace("all_parameter_files", str(namd_starting_ff_files))

        gomc_rel_path = os.path.relpath(str(gomc_newdir), namd_box_x_newdir)

        new_namd_data = new_namd_data.replace("pdb_box_file",
                                              "{}/Output_data_BOX_{}_restart.pdb"
                                              "".format(gomc_rel_path, str(box_number))
                                              )
        new_namd_data = new_namd_data.replace("psf_box_file",
                                              "{}/Output_data_BOX_{}_restart.psf"
                                              "".format(gomc_rel_path, str(box_number))
                                              )

        new_namd_data = new_namd_data.replace("coor_file",
                                              "{}/Output_data_BOX_{}_restart.coor"
                                              "".format(gomc_rel_path, str(box_number))
                                              )
        new_namd_data = new_namd_data.replace("xsc_file",
                                              "{}/Output_data_BOX_{}_restart.xsc"
                                              "".format(gomc_rel_path, str(box_number))
                                              )
        new_namd_data = new_namd_data.replace("vel_file",
                                              "{}/Output_data_BOX_{}_restart.vel"
                                              "".format(gomc_rel_path, str(box_number))
                                              )
        new_namd_data = new_namd_data.replace("Bool_restart", str("true"))

        # Read the angles from the intital/starting PDB file
        read_pdb_file = open("{}/Output_data_BOX_{}_restart.pdb"
                             "".format(str(gomc_newdir), str(box_number)), 'r').readlines()

    else:
        namd_starting_ff_files = ""
        for namd_ff_i in starting_ff_file_list_namd:
            namd_ff_i = os.path.relpath(namd_ff_i, namd_box_x_newdir)
            namd_starting_ff_files = namd_starting_ff_files + "parameters \t {}\n".format(namd_ff_i)

        new_namd_data = namd_template_data.replace("all_parameter_files", str(namd_starting_ff_files))

        namd_starting_pdb_rel_path = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                       starting_pdb_box_x_file),
                                                        namd_box_x_newdir)
        new_namd_data = new_namd_data.replace("pdb_box_file",
                                              "{}".format(namd_starting_pdb_rel_path)
                                              )

        namd_starting_psf_rel_path = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                   starting_psf_box_x_file),
                                                    namd_box_x_newdir)
        new_namd_data = new_namd_data.replace("psf_box_file",
                                              "{}".format(namd_starting_psf_rel_path)
                                              )

        new_namd_data = new_namd_data.replace("coor_file", str("NA"))
        new_namd_data = new_namd_data.replace("xsc_file", str("NA"))
        new_namd_data = new_namd_data.replace("vel_file", str("NA"))
        new_namd_data = new_namd_data.replace("Bool_restart", str("false"))

        read_pdb_file = open("{}/{}".format(str(python_file_directory), starting_pdb_box_x_file), 'r').readlines()

    read_x_dim = None
    read_y_dim = None
    read_z_dim = None
    read_angle_alpha = None
    read_angle_beta = None
    read_angle_gamma = None
    # Read the angles from the intial/starting PDB file
    for i, line in enumerate(read_pdb_file):
        if 'CRYST1' in line:
            read_x_dim = read_pdb_file[i].split()[1:2]
            read_x_dim = float(read_x_dim[0])
            read_y_dim = read_pdb_file[i].split()[2:3]
            read_y_dim = float(read_y_dim[0])
            read_z_dim = read_pdb_file[i].split()[3:4]
            read_z_dim = float(read_z_dim[0])

            read_angle_alpha = read_pdb_file[i].split()[4:5]
            read_angle_alpha = float(read_angle_alpha[0])
            read_angle_beta = read_pdb_file[i].split()[5:6]
            read_angle_beta = float(read_angle_beta[0])
            read_angle_gamma = read_pdb_file[i].split()[6:7]
            read_angle_gamma = float(read_angle_gamma[0])

    # check user  override x-dimensions
    used_x_dim = check_for_pdb_dims_and_override("x", run_no, read_x_dim, set_dim=set_x_dim, only_on_run_no=0)

    # check user  override y-dimensions
    used_y_dim = check_for_pdb_dims_and_override("y", run_no, read_y_dim, set_dim=set_y_dim, only_on_run_no=0)

    # check user  override z-dimensions
    used_z_dim = check_for_pdb_dims_and_override("z", run_no, read_z_dim, set_dim=set_z_dim, only_on_run_no=0)

    # check box for othoganality
    # check the read_angle_alpha
    if read_angle_alpha is not None and read_angle_alpha != 90:
        if run_no == 0:
            write_log_data = "ERROR: The alpha angle is not 90 degress as read from the " \
                             "starting PDB file, read_angle_alpha_PDB = {}. " \
                             "Only alpha angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(read_angle_alpha))
            log_template_file.write(str(write_log_data))
            raise ValueError(str(write_log_data))

    if set_angle_alpha is not None and set_angle_alpha != 90:
        if run_no == 0:
            write_log_data = "ERROR: The alpha angle is not 90 degress as set by the user," \
                             "set_angle_alpha = {}. " \
                             "Only alpha angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(set_angle_alpha))
        log_template_file.write(str(write_log_data))
        raise ValueError(str(write_log_data))

    # check the read_angle_beta
    if read_angle_beta is not None and read_angle_beta != 90:
        if run_no == 0:
            write_log_data = "ERROR: The beta angle is not 90 degress as read from the " \
                             "starting PDB file, read_angle_beta_PDB = {}. " \
                             "Only beta angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(read_angle_beta))
            log_template_file.write(str(write_log_data))
            raise ValueError(str(write_log_data))

    if set_angle_beta is not None and set_angle_beta != 90:
        if run_no == 0:
            write_log_data = "ERROR: The beta angle is not 90 degress as set by the user " \
                             "set_angle_beta = {}. Only beta angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(set_angle_beta))
        log_template_file.write(str(write_log_data))
        raise ValueError(str(write_log_data))

    # check the read_angle_gamma
    if read_angle_gamma is not None and read_angle_gamma != 90:
        if run_no == 0:
            write_log_data = "ERROR: The gamma angle is not 90 degress as read from the " \
                             "starting PDB file read_angle_gamma_PDB = {}. " \
                             "Only gamma angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(read_angle_gamma))
            log_template_file.write(str(write_log_data))
            raise ValueError(str(write_log_data))

    if set_angle_gamma is not None and set_angle_gamma != 90:
        if run_no == 0:
            write_log_data = "ERROR: The gamma angle is not 90 degress as set by the user " \
                             "set_angle_gamma = {}. Only gamma angle of 90 degress or None is currently " \
                             "allowed. \n".format(str(set_angle_gamma))
        log_template_file.write(str(write_log_data))
        raise ValueError(str(write_log_data))

    new_namd_data = new_namd_data.replace("x_dim_box", str(used_x_dim))
    new_namd_data = new_namd_data.replace("y_dim_box", str(used_y_dim))
    new_namd_data = new_namd_data.replace("z_dim_box", str(used_z_dim))
    new_namd_data = new_namd_data.replace("x_origin_box", str(used_x_dim/2))
    new_namd_data = new_namd_data.replace("y_origin_box", str(used_y_dim/2))
    new_namd_data = new_namd_data.replace("z_origin_box", str(used_z_dim/2))

    new_namd_data = new_namd_data.replace("NAMD_Run_Steps", str((int(namd_run_steps))))
    new_namd_data = new_namd_data.replace("NAMD_Minimize", str(int(namd_minimize_steps)))
    new_namd_data = new_namd_data.replace("NAMD_RST_DCD_XST_Steps", str((int(namd_rst_dcd_xst_steps))))
    new_namd_data = new_namd_data.replace("NAMD_console_BLKavg_E_and_P_Steps",
                                          str(int(namd_console_blkavg_e_and_p_steps)))

    new_namd_data = new_namd_data.replace("current_step", str((int(0))))
    new_namd_data = new_namd_data.replace("System_temp_set", str(simulation_temp_k))
    new_namd_data = new_namd_data.replace("System_press_set", str(simulation_pressure_bar))

    if run_no != 0:
        new_namd_data = new_namd_data.replace("X_PME_GRID_DIM", str(namd_x_pme_grid_dim))
        new_namd_data = new_namd_data.replace("Y_PME_GRID_DIM", str(namd_y_pme_grid_dim))
        new_namd_data = new_namd_data.replace("Z_PME_GRID_DIM", str(namd_z_pme_grid_dim))

    else:
        # add x number times more point to the PME grid for "GEMC", "NPT".
        # scalar_dim_mult = 1.3 --> allows for 2x change in volume,
        # allowable volume change = scalar_dim_mult^3 = 1.3^3
        if simulation_type in ["GEMC", "NPT"]:
            scalar_dim_mult = 1.3
            used_and_scaled_namd_pme_x_dim = (used_x_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult
            used_and_scaled_namd_pme_y_dim = (used_y_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult
            used_and_scaled_namd_pme_z_dim = (used_z_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult
        else:
            scalar_dim_mult = 1
            used_and_scaled_namd_pme_x_dim = (used_x_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult
            used_and_scaled_namd_pme_y_dim = (used_y_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult
            used_and_scaled_namd_pme_z_dim = (used_z_dim + fft_add_namd_ang_to_box_dim) * scalar_dim_mult

        new_namd_data = new_namd_data.replace("X_PME_GRID_DIM", str(int(used_and_scaled_namd_pme_x_dim + 1)))
        new_namd_data = new_namd_data.replace("Y_PME_GRID_DIM", str(int(used_and_scaled_namd_pme_y_dim + 1)))
        new_namd_data = new_namd_data.replace("Z_PME_GRID_DIM", str(int(used_and_scaled_namd_pme_z_dim + 1)))

    generate_namd_file.write(new_namd_data)
    generate_namd_file.close()

    write_log_data = "NAMD simulation data for simulation number {} in box {} is " \
                     "completed \n".format(str(run_no), str(box_number))
    log_template_file.write(str(write_log_data))
    print(str(write_log_data))

    return namd_box_x_newdir


def get_namd_energy_data(read_namd_box_x_energy_file, e_default_namd_titles):
    """
    Gets the NAMD run energy data (electrostatic, potential, and VDW energies)
    in kcal/mol.

    Parameters
    ----------
    read_namd_box_x_energy_file : str
        The full path/filename of the NAMD energy file for the selected box.
    e_default_namd_titles : list
        The default NAMD energy output strings, which are split into a
        list of strings.

    Returns
    ---------
    namd_e_electro_box_x : list
        The list of electrostatic energies as strings, as extracted from the
        the NAMD run data ('ELECT').
    namd_e_electro_box_x_initial_value : float
        The initial electrostatic energy as a float, as extracted from the
        the NAMD run data ('ELECT').
    namd_e_electro_box_x_final_value : float
        The final electrostatic energy as a float, as extracted from the
        the NAMD run data ('ELECT').
    namd_e_potential_box_x : str
        The list of potential energies as strings, as extracted from the
        the NAMD run data ('POTENTIAL').
    namd_e_potential_box_x_initial_value : float
        The initial potential energy as a float, as extracted from the
        the NAMD run data ('POTENTIAL').
    namd_e_potential_box_x_final_value : float
        The final potential energy as a float, as extracted from the
        the NAMD run data ('POTENTIAL').
    namd_e_vdw_plus_elec_box_x : str
        The list of VDW + electrostatic energies as strings, as extracted from the
        the NAMD run data ('VDW' + 'ELECT').
    namd_e_vdw_plus_elec_box_x_initial_value : float
        The intitial VDW + electrostatic energy as a float, as extracted from the
        the NAMD run data ('VDW' + 'ELECT').
    namd_e_vdw_plus_elec_box_x_final_value : float
        The final VDW + electrostatic energy as a float, as extracted from the
        the NAMD run data ('VDW' + 'ELECT').
    """

    get_e_titles = True
    e_values_namd_list = []
    for i, line in enumerate(read_namd_box_x_energy_file):
        if line.startswith('ETITLE:') is True and get_e_titles is True:
            e_titles_namd_iteration = read_namd_box_x_energy_file[i]
            e_titles_namd_iteration = e_titles_namd_iteration.split()
            e_titles_namd_iteration = e_titles_namd_iteration[:]
            if get_e_titles is True:
                get_e_titles = False

        if line.startswith('ENERGY:') is True:
            e_values_namd_iteration = read_namd_box_x_energy_file[i]
            e_values_namd_iteration = e_values_namd_iteration.split()
            e_values_namd_list.append(e_values_namd_iteration)

    try:
        e_titles_namd_iteration
    except:
        e_titles_namd_iteration = e_default_namd_titles

    namd_energy_data_box_x_df = pd.DataFrame(data=e_values_namd_list, columns=e_titles_namd_iteration)

    # extract energy data from box 0
    namd_e_electro_box_x = namd_energy_data_box_x_df.loc[:, 'ELECT']
    namd_e_electro_box_x_initial_value = float(namd_e_electro_box_x.values.tolist()[0])
    namd_e_electro_box_x_final_value = float(namd_e_electro_box_x.values.tolist()[-1])
    namd_e_potential_box_x = namd_energy_data_box_x_df.loc[:, 'POTENTIAL']
    namd_e_potential_box_x_initial_value = float(namd_e_potential_box_x.values.tolist()[0])
    namd_e_potential_box_x_final_value = float(namd_e_potential_box_x.values.tolist()[-1])
    namd_e_vdw_box_x = namd_energy_data_box_x_df.loc[:, 'VDW']
    namd_e_vdw_box_x_initial_value = float(namd_e_vdw_box_x.values.tolist()[0])
    namd_e_vdw_box_x_final_value = float(namd_e_vdw_box_x.values.tolist()[-1])

    namd_e_vdw_plus_elec_box_x = [float(namd_e_vdw_box_x[k_i]) + float(namd_e_electro_box_x[k_i])
                                  for k_i in range(0, len(namd_e_vdw_box_x))]

    namd_e_vdw_plus_elec_box_x_initial_value = float(namd_e_vdw_plus_elec_box_x[0])
    namd_e_vdw_plus_elec_box_x_final_value = float(namd_e_vdw_plus_elec_box_x[-1])


    return namd_e_electro_box_x, namd_e_electro_box_x_initial_value, namd_e_electro_box_x_final_value,\
           namd_e_potential_box_x, namd_e_potential_box_x_initial_value, namd_e_potential_box_x_final_value, \
           namd_e_vdw_plus_elec_box_x, namd_e_vdw_plus_elec_box_x_initial_value, namd_e_vdw_plus_elec_box_x_final_value


def compare_namd_gomc_energies(e_potential_box_x_final_value, e_potential_box_x_initial_value,
                               e_vdw_plus_elec_box_x_final_value, e_vdw_plus_elec_box_x_initial_value,
                               run_no, box_number):
    """
    Compares the NAMD and GOMC energies when switching between
    simulation engines.  GOMC does not currently (2-26-21)
    have impropers, so if a simulation in NAMD is using impropers
    You will recieve warnings since GOMC does not calculate the
    impropers. Otherwise, they should be the same or nearly the same
    between GOMC and NAMD.  The data is printing on the screen and
    the Hybrid GOMC-NAMD log file.  One GOMC and one NAMD file must 
    either be the initial or last values.

    Parameters
    ----------
    e_potential_box_x_final_value : float
        The final potential energy as a float, as extracted from the
        the NAMD run data ('POTENTIAL').
    e_potential_box_x_initial_value : float
        The initial potential energy as a float, as extracted from the
        the NAMD run data ('POTENTIAL').
    e_vdw_plus_elec_box_x_final_value : float
        The final VDW + electrostatic energy energy as a float, as extracted from the
        the NAMD run data ('VDW' + 'ELECT').
    e_vdw_plus_elec_box_x_initial_value : float
        The initial VDW + electrostatic energy as a float, as extracted from the
        the NAMD run data ('VDW' + 'ELECT').
    run_no : int
        Simulation run number
    box_number : int
        The simulation box number, which can only be 0 or 1
    """

    # calc error in potential energies box x
    try:
        error_fract_in_potential_box_x = np.abs((e_potential_box_x_final_value -  e_potential_box_x_initial_value) /
                                                e_potential_box_x_final_value)
    except:
        if e_potential_box_x_final_value == 0 and e_potential_box_x_initial_value == 0:
            error_fract_in_potential_box_x = 0
        else:
            error_fract_in_potential_box_x = 'NA'

    if error_fract_in_potential_box_x != 'NA' and error_fract_in_potential_box_x <= \
            allowable_error_fraction_potential:
        write_log_data = "PASSED: Box {}: Potential energies error fraction between the check " \
                         "between the last point in run {}" \
                         " and the first point in run {}, error fraction = {}" \
                         " \n".format(str(box_number), str(int(run_no - 1)),
                                      str(int(run_no)), str(error_fract_in_potential_box_x)
                                      )
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

    else:
        write_log_data = "FAILED: Box {}: Potential energies error fraction between the last " \
                         "point in run {} and the first point in run {}, error fraction =  {}" \
                         " \n".format(str(box_number), str(int(run_no - 1)),
                                      str(int(run_no)), str(error_fract_in_potential_box_x)
                                      )
        log_template_file.write('WARNING: ' + str(write_log_data))
        warn(write_log_data)


    # calc error in VDW + Electrostatics box x
    try:
        error_fract_in_vdw_plus_elec_box_x = np.abs((e_vdw_plus_elec_box_x_final_value -
                                                     e_vdw_plus_elec_box_x_initial_value) /
                                                    e_vdw_plus_elec_box_x_final_value)
    except:
        if e_vdw_plus_elec_box_x_final_value == 0 and e_vdw_plus_elec_box_x_initial_value == 0:
            error_fract_in_vdw_plus_elec_box_x = 0
        else:
            error_fract_in_vdw_plus_elec_box_x = 'NA'

    abs_diff_in_vdw_plus_elec_box_x = np.abs(e_vdw_plus_elec_box_x_final_value - e_vdw_plus_elec_box_x_initial_value)

    if error_fract_in_vdw_plus_elec_box_x != 'NA' and error_fract_in_vdw_plus_elec_box_x <= \
            allowable_error_fraction_vdw_plus_elec:
        write_log_data = "PASSED: Box {}: VDW + electrostatic fraction between the last point in run {}" \
                         " and the first point in run {}, error fraction = {}" \
                         " \n".format(str(box_number), str(int(run_no - 1)),
                                      str(int(run_no)), str(error_fract_in_vdw_plus_elec_box_x)
                                      )
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

    elif abs_diff_in_vdw_plus_elec_box_x <= max_absolute_allowable_kcal_fraction_vdw_plus_elec:
        write_log_data = "PASSED: Box {}: The VDW + electrostatic energy error fraction between the last point in run {} " \
                         "and the first point in run {}, absolute difference is = {} kcal/mol." \
                         " \n".format(str(box_number), str(int(run_no - 1)),
                                      str(int(run_no)), str(abs_diff_in_vdw_plus_elec_box_x),
                                      )
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))
    else:
        write_log_data = "FAILED: Box {}: vdw_plus_elec energy  error fraction between the last point in run {} " \
                         "and the first point in run {}, error fraction = {} or the absolute " \
                         "difference is = {} kcal/mol." \
                         " \n".format(str(box_number), str(int(run_no - 1)),
                                      str(int(run_no)), str(error_fract_in_vdw_plus_elec_box_x),
                                      str(abs_diff_in_vdw_plus_elec_box_x)
                                      )
        log_template_file.write('WARNING: ' + str(write_log_data))
        warn(str(write_log_data))


def write_gomc_conf_file(python_file_directory, path_gomc_runs, run_no, gomc_run_steps,
                         gomc_rst_coor_ckpoint_steps, gomc_console_blkavg_hist_steps, gomc_hist_sample_steps,
                         simulation_temp_k, simulation_pressure_bar,
                         starting_pdb_box_0_file, starting_pdb_box_1_file,
                         starting_psf_box_0_file, starting_psf_box_1_file):
    """
    Writes the NAMD control file in the NAMD run numbered folder

    Parameters
    ----------
    python_file_directory : str
        The path/directory where this file is located.
    path_gomc_template : str
        The relative path to the GOMC template file from where this file is
        located (he directory where this file is located (python_file_director).
    run_no : int
        Simulation run number
    gomc_run_steps : int
        The number of steps to run the GOMC simulation.
    gomc_rst_coor_ckpoint_steps : int
        The number of steps which the GOMC restart, dcd, xst, checkpoint and
        coordinates files will be created.
    gomc_console_blkavg_hist_steps : int
        The number of steps which the GOMC consol output (energies and pressure),
        block average, and histogram data will be output.
    gomc_hist_sample_steps : int
        The sample frequency (steps) which the GOMC histogram data
        will be sampled.
    simulation_temp_k : int or float
        The NAMD simulation temperature in Kelvin.
    simulation_pressure_bar : int or float
        The NAMD simulation pressure in bar.
    starting_pdb_box_0_file : str
        The pdb path/filename for box 0 which is written
        to the GOMC control file.
    starting_pdb_box_1_file : str
        The psf path/filename for box 1 which is written
        to the GOMC control file.
    starting_psf_box_0_file : str
        The psf path/filename for box 0 which is written
        to the GOMC control file.
    starting_psf_box_1_file : str
        The psf path/filename for box 1 which is written
        to the GOMC control file.

    Returns
    ---------
    gomc_newdir : str
        The full path/directory of the created GOMC run/box number,
        which contains the control file.

    Notes
    ---------
    The box angles are not currently available and are default set to 90 degress.
    they can be added later, but for now all simulation but be orthoganol boxes
    """

    # Create the GOMC configuration file
    gomc_template_file = open("{}/{}".format(str(python_file_directory), path_gomc_template), 'r')
    gomc_template_data = gomc_template_file.read()
    gomc_template_file.close()
    gomc_newdir = "{}/{}/{}{}".format(str(python_file_directory), path_gomc_runs,
                                      str(add_zeros_at_start_run_no_str), str(run_no))

    os.makedirs(gomc_newdir, exist_ok=True)

    previous_namd_box_0_rel_path = os.path.relpath(namd_box_0_newdir, gomc_newdir)

    write_log_data = "*************************************************" + ' \n'
    log_template_file.write(str(write_log_data))
    print(str(write_log_data))

    generate_gomc_file = open("{}/in.conf".format(gomc_newdir), 'w')

    gomc_starting_ff_files = ""
    for gomc_ff_i in starting_ff_file_list_gomc:
        gomc_ff_i = os.path.relpath(gomc_ff_i, gomc_newdir)
        gomc_starting_ff_files = gomc_starting_ff_files + "Parameters \t {}\n".format(gomc_ff_i)

    new_gomc_data = gomc_template_data.replace("all_parameter_files", str(gomc_starting_ff_files))

    new_gomc_data = new_gomc_data.replace("coor_box_0_file",
                                          '{}/namdOut.restart.coor'.format(previous_namd_box_0_rel_path)
                                          )
    new_gomc_data = new_gomc_data.replace("xsc_box_0_file", '{}/namdOut.restart.xsc'
                                                            ''.format(previous_namd_box_0_rel_path)
                                          )
    new_gomc_data = new_gomc_data.replace("vel_box_0_file", '{}/namdOut.restart.vel'
                                                            ''.format(previous_namd_box_0_rel_path)
                                          )

    if previous_gomc_dir == 'NA':
        new_gomc_data = new_gomc_data.replace("Restart_Checkpoint_file",
                                              "false {}"
                                              "".format("Output_data_restart.chk"))

        gomc_starting_pdb_rel_path_box_0 = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                          starting_pdb_box_0_file),
                                                           gomc_newdir)
        new_gomc_data = new_gomc_data.replace("pdb_file_box_0_file",
                                              '{}'.format(gomc_starting_pdb_rel_path_box_0)
                                              )

        gomc_starting_psf_rel_path_box_0 = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                          starting_psf_box_0_file),
                                                           gomc_newdir)
        new_gomc_data = new_gomc_data.replace("psf_file_box_0_file",
                                              '{}'.format(gomc_starting_psf_rel_path_box_0)
                                              )
    else:
        previous_gomc_rel_path = os.path.relpath(previous_gomc_dir, gomc_newdir)
        new_gomc_data = new_gomc_data.replace("pdb_file_box_0_file",
                                              '{}/Output_data_BOX_0_restart.pdb'.format(previous_gomc_rel_path)
                                              )
        new_gomc_data = new_gomc_data.replace("psf_file_box_0_file",
                                              '{}/Output_data_BOX_0_restart.psf'.format(previous_gomc_rel_path)
                                              )

    # Read the angles from the intial/starting PDB file
    namd_xsc_box_0_file = "{}/namdOut.restart.xsc".format(namd_box_0_newdir)
    read_namd_xsc_box_0_file = open(namd_xsc_box_0_file, 'r').readlines()

    read_x_dim_box_0 = read_namd_xsc_box_0_file[-1].split()[1:2]
    read_x_dim_box_0 = float(read_x_dim_box_0[0])
    read_y_dim_box_0 = read_namd_xsc_box_0_file[-1].split()[5:6]
    read_y_dim_box_0 = float(read_y_dim_box_0[0])
    read_z_dim_box_0 = read_namd_xsc_box_0_file[-1].split()[9:10]
    read_z_dim_box_0 = float(read_z_dim_box_0[0])

    read_x_dim_origin_box_0 = read_namd_xsc_box_0_file[-1].split()[10:11]
    read_x_dim_origin_box_0 = float(read_x_dim_origin_box_0[0])
    read_y_dim_origin_box_0 = read_namd_xsc_box_0_file[-1].split()[11:12]
    read_y_dim_origin_box_0 = float(read_y_dim_origin_box_0[0])
    read_z_dim_origin_box_0 = read_namd_xsc_box_0_file[-1].split()[12:13]
    read_z_dim_origin_box_0 = float(read_z_dim_origin_box_0[0])

    new_gomc_data = new_gomc_data.replace("x_dim_box_0", str(read_x_dim_box_0))
    new_gomc_data = new_gomc_data.replace("y_dim_box_0", str(read_y_dim_box_0))
    new_gomc_data = new_gomc_data.replace("z_dim_box_0", str(read_z_dim_box_0))

    if simulation_type in ["GEMC", "GCMC"]:
        readlines_gomc_template_file = open("{}/{}".format(str(python_file_directory),
                                                           path_gomc_template), 'r').readlines()
        if simulation_type in ["GCMC"] or (simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is True):
            if previous_gomc_dir == "NA":
                for i, line in enumerate(readlines_gomc_template_file):
                    split_line = line.split()
                    if line.startswith('binCoordinates') is True or line.startswith('extendedSystem') is True \
                            or line.startswith('binVelocities') :
                        if split_line[0] == 'binCoordinates' and split_line[1] == '1':
                            new_gomc_data = new_gomc_data.replace(line, '')
                        elif split_line[0] == 'extendedSystem' and split_line[1] == '1':
                            new_gomc_data = new_gomc_data.replace(line, '')
                        elif split_line[0] == 'binVelocities' and split_line[1] == '1':
                            new_gomc_data = new_gomc_data.replace(line, '')

                read_pdb_file = open("{}/{}".format(str(python_file_directory),
                                                    starting_pdb_box_1_file),
                                     'r').readlines()

                read_x_dim_box_1 = None
                read_y_dim_box_1 = None
                read_z_dim_box_1 = None
                read_angle_alpha = None
                read_angle_beta = None
                read_angle_gamma = None
                # Read the angles from the intial/starting PDB file
                for i, line in enumerate(read_pdb_file):
                    if 'CRYST1' in line:
                        read_x_dim_box_1 = read_pdb_file[i].split()[1:2]
                        read_x_dim_box_1 = float(read_x_dim_box_1[0])
                        read_x_dim_box_1_origin = read_x_dim_box_1 / 2
                        read_y_dim_box_1 = read_pdb_file[i].split()[2:3]
                        read_y_dim_box_1 = float(read_y_dim_box_1[0])
                        read_y_dim_box_1_origin = read_y_dim_box_1 / 2
                        read_z_dim_box_1 = read_pdb_file[i].split()[3:4]
                        read_z_dim_box_1 = float(read_z_dim_box_1[0])
                        read_z_dim_box_1_origin = read_z_dim_box_1 / 2

                        read_angle_alpha = read_pdb_file[i].split()[4:5]
                        read_angle_alpha = read_angle_alpha[0]
                        read_angle_beta = read_pdb_file[i].split()[5:6]
                        read_angle_beta = read_angle_beta[0]
                        read_angle_gamma = read_pdb_file[i].split()[6:7]
                        read_angle_gamma = read_angle_gamma[0]

                gomc_used_x_dim = check_for_pdb_dims_and_override("x", run_no, read_x_dim_box_1,
                                                                  set_dim=set_dims_box_1_list[0],
                                                                  only_on_run_no=1)
                gomc_used_y_dim = check_for_pdb_dims_and_override("y", run_no, read_y_dim_box_1,
                                                                  set_dim=set_dims_box_1_list[1],
                                                                  only_on_run_no=1)
                gomc_used_z_dim = check_for_pdb_dims_and_override("z", run_no, read_z_dim_box_1,
                                                                  set_dim=set_dims_box_1_list[2],
                                                                  only_on_run_no=1)

                new_gomc_data = new_gomc_data.replace("x_dim_box_1", str(gomc_used_x_dim))
                new_gomc_data = new_gomc_data.replace("y_dim_box_1", str(gomc_used_y_dim))
                new_gomc_data = new_gomc_data.replace("z_dim_box_1", str(gomc_used_z_dim))

            else:
                new_gomc_data = new_gomc_data.replace("coor_box_1_file",
                                                      "{}/Output_data_BOX_1_restart.coor".format(previous_gomc_rel_path)
                                                      )
                new_gomc_data = new_gomc_data.replace("xsc_box_1_file",
                                                      "{}/Output_data_BOX_1_restart.xsc".format(previous_gomc_rel_path)
                                                      )
                new_gomc_data = new_gomc_data.replace("vel_box_1_file",
                                                      "{}/Output_data_BOX_1_restart.vel".format(previous_gomc_rel_path)
                                                      )

                previous_gomc_xsc_box_1_file = "{}/Output_data_BOX_1_restart.xsc".format(previous_gomc_dir)
                read_previous_gomc_xsc_box_1_file = open(previous_gomc_xsc_box_1_file, 'r').readlines()

                read_x_dim_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[1:2]
                read_x_dim_box_1 = float(read_x_dim_box_1[0])
                read_y_dim_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[5:6]
                read_y_dim_box_1 = float(read_y_dim_box_1[0])
                read_z_dim_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[9:10]
                read_z_dim_box_1 = float(read_z_dim_box_1[0])

                read_x_dim_origin_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[10:11]
                read_x_dim_origin_box_1 = float(read_x_dim_origin_box_1[0])
                read_y_dim_origin_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[11:12]
                read_y_dim_origin_box_1 = float(read_y_dim_origin_box_1[0])
                read_z_dim_origin_box_1 = read_previous_gomc_xsc_box_1_file[-1].split()[12:13]
                read_z_dim_origin_box_1 = float(read_z_dim_origin_box_1[0])

                new_gomc_data = new_gomc_data.replace("x_dim_box_1", str(read_x_dim_box_1))
                new_gomc_data = new_gomc_data.replace("y_dim_box_1", str(read_y_dim_box_1))
                new_gomc_data = new_gomc_data.replace("z_dim_box_1", str(read_z_dim_box_1))

        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            namd_xsc_box_1_file = "{}/namdOut.restart.xsc".format(namd_box_1_newdir)
            read_namd_xsc_box_1_file = open(namd_xsc_box_1_file, 'r').readlines()

            previous_namd_box_1_rel_path = os.path.relpath(namd_box_1_newdir, gomc_newdir)
            new_gomc_data = new_gomc_data.replace("coor_box_1_file",
                                                  '{}/namdOut.restart.coor'.format(previous_namd_box_1_rel_path)
                                                  )
            new_gomc_data = new_gomc_data.replace("xsc_box_1_file", '{}/namdOut.restart.xsc'
                                                                    ''.format(previous_namd_box_1_rel_path)
                                                  )
            new_gomc_data = new_gomc_data.replace("vel_box_1_file", '{}/namdOut.restart.vel'
                                                                    ''.format(previous_namd_box_1_rel_path)
                                                  )

            read_x_dim_box_1 = read_namd_xsc_box_1_file[-1].split()[1:2]
            read_x_dim_box_1 = float(read_x_dim_box_1[0])
            read_y_dim_box_1 = read_namd_xsc_box_1_file[-1].split()[5:6]
            read_y_dim_box_1 = float(read_y_dim_box_1[0])
            read_z_dim_box_1 = read_namd_xsc_box_1_file[-1].split()[9:10]
            read_z_dim_box_1 = float(read_z_dim_box_1[0])

            read_x_dim_origin_box_1 = read_namd_xsc_box_1_file[-1].split()[10:11]
            read_x_dim_origin_box_1 = float(read_x_dim_origin_box_1[0])
            read_y_dim_origin_box_1 = read_namd_xsc_box_1_file[-1].split()[11:12]
            read_y_dim_origin_box_1 = float(read_y_dim_origin_box_1[0])
            read_z_dim_origin_box_1 = read_namd_xsc_box_1_file[-1].split()[12:13]
            read_z_dim_origin_box_1 = float(read_z_dim_origin_box_1[0])

            new_gomc_data = new_gomc_data.replace("x_dim_box_1", str(read_x_dim_box_1))
            new_gomc_data = new_gomc_data.replace("y_dim_box_1", str(read_y_dim_box_1))
            new_gomc_data = new_gomc_data.replace("z_dim_box_1", str(read_z_dim_box_1))

    if simulation_type in ["GEMC", "GCMC"]:
        if simulation_type in ["GCMC"] and previous_gomc_dir == "NA":
            new_gomc_data = new_gomc_data.replace("restart_true_or_false", 'false')
        elif simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is True and previous_gomc_dir == "NA":
            new_gomc_data = new_gomc_data.replace("restart_true_or_false", 'false')
        else:
            new_gomc_data = new_gomc_data.replace("restart_true_or_false", 'true')
    else:
        new_gomc_data = new_gomc_data.replace("restart_true_or_false", 'true')

    new_gomc_data = new_gomc_data.replace("GOMC_Run_Steps", str((int(gomc_run_steps))))
    new_gomc_data = new_gomc_data.replace("GOMC_RST_Coor_CKpoint_Steps",
                                          str((int(gomc_rst_coor_ckpoint_steps))))
    new_gomc_data = new_gomc_data.replace("GOMC_console_BLKavg_Hist_Steps",
                                          str((int(gomc_console_blkavg_hist_steps))))
    new_gomc_data = new_gomc_data.replace("GOMC_Hist_sample_Steps", str(gomc_hist_sample_steps))
    new_gomc_data = new_gomc_data.replace("System_temp_set", str(simulation_temp_k))
    new_gomc_data = new_gomc_data.replace("System_press_set", str(simulation_pressure_bar))

    # add the Chempot or fugacity data for the GOMC control file
    if simulation_type in ["GCMC"]:
        if GCMC_ChemPot_or_Fugacity is None:
            new_gomc_data = new_gomc_data.replace("mu_ChemPot_K_or_P_Fugacitiy_bar_all",  str(''))

        elif GCMC_ChemPot_or_Fugacity == 'ChemPot':
            print('GOMC GCMC simulation is using {} --> Residues and values = {}'.format(GCMC_ChemPot_or_Fugacity,
                                                                                         GCMC_ChemPot_or_Fugacity_dict)
                  )

            chempot_conf_data = ""
            for GCMC_keys_i in GCMC_ChemPot_or_Fugacity_dict_keys:
                chempot_conf_data = chempot_conf_data + "ChemPot \t {} \t {}" \
                                                        "\n".format(GCMC_keys_i,
                                                                    GCMC_ChemPot_or_Fugacity_dict[GCMC_keys_i]
                                                                    )

            new_gomc_data = new_gomc_data.replace("mu_ChemPot_K_or_P_Fugacitiy_bar_all", str(chempot_conf_data))

        elif GCMC_ChemPot_or_Fugacity == 'Fugacity':
            print('GOMC GCMC simulation is using {} --> Residues and values = {}'.format(GCMC_ChemPot_or_Fugacity,
                                                                                         GCMC_ChemPot_or_Fugacity_dict)
                  )

            fugacity_conf_data = ""
            for GCMC_keys_i in GCMC_ChemPot_or_Fugacity_dict_keys:
                fugacity_conf_data = fugacity_conf_data + "Fugacity \t {} \t {}" \
                                                         "\n".format(GCMC_keys_i,
                                                                     GCMC_ChemPot_or_Fugacity_dict[GCMC_keys_i]
                                                                     )

            new_gomc_data = new_gomc_data.replace("mu_ChemPot_K_or_P_Fugacitiy_bar_all", str(fugacity_conf_data))

        else:
            write_log_data = "Warning: There is in error in the chemical potential settings for GCMC simulation. \n"
            log_template_file.write(str(write_log_data))
            print(str(write_log_data))
            warn(str(write_log_data))

    set_max_steps_equib_adj = 10 * 10 ** 6
    if gomc_run_steps >= set_max_steps_equib_adj:
        new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int((set_max_steps_equib_adj / 10))))

        if gomc_run_steps / 10 >= 1000:
            new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(1000)))
        else:
            new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(gomc_run_steps / 10)))

    elif int(gomc_run_steps / 10) > 0:
        # make equal to 1000 until the restart true can be enabled
        new_gomc_data = new_gomc_data.replace("GOMC_Equilb_Steps", str((int(gomc_run_steps / 10))))
        new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(gomc_run_steps / 10)))

        if gomc_run_steps / 10 >= 1000:
            new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(1000)))
        else:
            new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(gomc_run_steps / 10)))

    else:
        # make equal to 1000 until the restart true can be enabled
        new_gomc_data = new_gomc_data.replace("GOMC_Adj_Steps", str(int(1)))
        new_gomc_data = new_gomc_data.replace("GOMC_Equilb_Steps", str((int(1))))

    if simulation_type in ["GEMC", "GCMC"]:
        if previous_gomc_dir == 'NA':
            # marked as "Restart_Checkpoint_file", 'false' for now until checkpoint is setup
            new_gomc_data = new_gomc_data.replace("Restart_Checkpoint_file",
                                                  "false {}"
                                                  "".format("Output_data_restart.chk"))

            gomc_starting_pdb_rel_path_box_1 = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                              starting_pdb_box_1_file),
                                                               gomc_newdir)
            new_gomc_data = new_gomc_data.replace("pdb_file_box_1_file",
                                                  '{}'.format(gomc_starting_pdb_rel_path_box_1)
                                                  )

            gomc_starting_psf_rel_path_box_1 = os.path.relpath("{}/{}".format(str(python_file_directory),
                                                                              starting_psf_box_1_file),
                                                               gomc_newdir)
            new_gomc_data = new_gomc_data.replace("psf_file_box_1_file",
                                                  '{}'.format(gomc_starting_psf_rel_path_box_1)
                                                  )

        else:
            new_gomc_data = new_gomc_data.replace("pdb_file_box_1_file",
                                                  "{}/Output_data_BOX_1_restart.pdb".format(previous_gomc_rel_path)
                                                  )
            new_gomc_data = new_gomc_data.replace("psf_file_box_1_file",
                                                  "{}/Output_data_BOX_1_restart.psf".format(previous_gomc_rel_path)
                                                  )

    else:
        if previous_gomc_dir == 'NA':
            # marked as "Restart_Checkpoint_file", 'false' for now until checkpoint is setup
            new_gomc_data = new_gomc_data.replace("Restart_Checkpoint_file",
                                                  "false {}"
                                                  "".format("Output_data_restart.chk"))

    # make checkpoint true and restart
    if previous_gomc_dir != 'NA':
        new_gomc_data = new_gomc_data.replace("Restart_Checkpoint_file",
                                              "true {}/{}"
                                              "".format(str(previous_gomc_rel_path), "Output_data_restart.chk"))

    generate_gomc_file.write(new_gomc_data)
    generate_gomc_file.close()

    return gomc_newdir


def get_gomc_energy_data(read_gomc_box_x_log_file, box_number):
    """
        Generated the energy and system file data for specified
        box number.  GOMC energy units are in kcal/mol.

        Parameters
        ----------
        read_gomc_box_x_log_file : str
            The path/filename of the GOMC log file.
        box_number : int
            The simulation box number, which can only be 0 or 1

        Returns
        ---------
        gomc_energy_data_box_x_df : pandas.dataframe
            The GOMC log file data in a pandas.dataframe

        Notes
        ---------
        GOMC energy units are in K
        """

    get_e_titles = True
    get_v_p_totmol_rho_titles = True
    e_values_gomc_list = []
    v_p_totmol_rho_values_list = []
    for i, line in enumerate(read_gomc_box_x_log_file):
        if line.startswith('ETITLE:') is True and get_e_titles is True:
            e_titles_gomc_iteration = read_gomc_box_x_log_file[i]
            e_titles_gomc_iteration = e_titles_gomc_iteration.split()
            e_titles_gomc_iteration = e_titles_gomc_iteration[:]
            if get_e_titles is True:
                get_e_titles = False
        if line.startswith('ENER_' + str(box_number) + ':') is True:
            e_values_gomc_iteration_list = []
            e_values_gomc_iteration = read_gomc_box_x_log_file[i]
            e_values_gomc_iteration = e_values_gomc_iteration.split()

            for j in range(0, len(e_values_gomc_iteration)):
                if e_titles_gomc_iteration[j] == 'ETITLE:':
                    e_values_gomc_iteration_list.append(e_values_gomc_iteration[j])
                elif e_titles_gomc_iteration[j] == 'STEP':
                    e_values_gomc_iteration_list.append(int(int(e_values_gomc_iteration[j]) + current_step))
                else:
                    e_values_gomc_iteration_list.append(float(e_values_gomc_iteration[j]) * K_to_kcal_mol)
            e_values_gomc_list.append(e_values_gomc_iteration_list)

        if line.startswith('STITLE:') is True and get_v_p_totmol_rho_titles is True:
            v_p_totmol_rho_titles_iteration = read_gomc_box_x_log_file[i]
            v_p_totmol_rho_titles_iteration = v_p_totmol_rho_titles_iteration.split()
            v_p_totmol_rho_titles_iteration = v_p_totmol_rho_titles_iteration[:]
            if get_v_p_totmol_rho_titles is True:
                get_v_p_totmol_rho_titles = False

        if line.startswith('STAT_' + str(box_number) + ':') is True:
            v_p_totmol_rho_values_iteration_list = []
            v_p_totmol_rho_values_iteration = read_gomc_box_x_log_file[i]
            v_p_totmol_rho_values_iteration = v_p_totmol_rho_values_iteration.split()

            for j in range(0, len(v_p_totmol_rho_values_iteration)):
                if v_p_totmol_rho_titles_iteration[j] == 'STITLE:':
                    v_p_totmol_rho_values_iteration_list.append(v_p_totmol_rho_values_iteration[j])
                elif v_p_totmol_rho_titles_iteration[j] == 'STEP':
                    v_p_totmol_rho_values_iteration_list.append(int(int(v_p_totmol_rho_values_iteration[j])
                                                                    + current_step))
                else:
                    v_p_totmol_rho_values_iteration_list.append(float(v_p_totmol_rho_values_iteration[j]))
            v_p_totmol_rho_values_list.append(v_p_totmol_rho_values_iteration_list)

    gomc_energy_data_box_x_df = pd.DataFrame(data=e_values_gomc_list, columns=e_titles_gomc_iteration)

    return gomc_energy_data_box_x_df


def get_gomc_energy_data_kcal_per_mol(gomc_energy_data_box_x_df):
    """
    Gets the GOMC run energy data (electrostatic, potential, and VDW energies)
    in kcal/mol.

    Parameters
    ----------
    read_namd_box_x_energy_file : str
        The full path/filename of the NAMD energy file for the selected box.
    e_default_namd_titles : list
        The default NAMD energy output strings, which are split into a
        list of strings.

    Returns
    ---------
    gomc_e_electro_box_x_kcal_per_mol : list
        The list of electrostatic energies as strings, as extracted from the
        the GOMC run data ('TOTAL_ELECT').
    gomc_e_electro_box_x_initial_value_kcal_mol : float
        The initial electrostatic energy as a float, as extracted from the
        the GOMC run data ('TOTAL_ELECT').
    gomc_e_electro_box_x_final_value_kcal_mol : float
        The final electrostatic energy as a float, as extracted from the
        the GOMC run data ('TOTAL_ELECT').
    gomc_e_potential_box_x_kcal_per_mol : str
        The list of potential energies as strings, as extracted from the
        the GOMC run data ('TOTAL').
    gomc_e_potential_box_x_initial_value_kcal_mol : float
        The initial potential energy as a float, as extracted from the
        the GOMC run data ('TOTAL').
    gomc_e_potential_box_x_final_value_kcal_mol : float
        The final potential energy as a float, as extracted from the
        the GOMC run data ('TOTAL').
    gomc_e_vdw_plus_elec_box_x_kcal_per_mol : str
        The list of VDW + electrostatic energies as strings, as extracted from the
        the GOMC run data ('INTRA(NB)' + 'INTER(LJ)' + 'TOTAL_ELECT').
    gomc_e_vdw_plus_elec_box_x_initial_value_kcal_per_mol : float
        The intitial VDW + electrostatic energy as a float, as extracted from the
        the GOMC run data ('INTRA(NB)' + 'INTER(LJ)' + 'TOTAL_ELECT').
    gomc_e_vdw_plus_elec_box_x_initial_value_kcal_per_mol : float
        The final VDW + electrostatic energy as a float, as extracted from the
        the GOMC run data ('INTRA(NB)' + 'INTER(LJ)' + 'TOTAL_ELECT').
        Generated the energy and system file data for specified
        box number.

    Notes
    ---------
    GOMC energy units are in kcal/mol
    """

    gomc_e_electro_box_x_kcal_per_mol = gomc_energy_data_box_x_df.loc[:, 'TOTAL_ELECT'].tolist()
    gomc_e_electro_box_x_initial_value_kcal_mol = float(gomc_e_electro_box_x_kcal_per_mol[0])
    gomc_e_electro_box_x_final_value_kcal_mol = float(gomc_e_electro_box_x_kcal_per_mol[-1])

    gomc_e_potential_box_x_kcal_per_mol = gomc_energy_data_box_x_df.loc[:, 'TOTAL'].tolist()
    gomc_e_potential_box_x_initial_value_kcal_mol = float(gomc_e_potential_box_x_kcal_per_mol[0])
    gomc_e_potential_box_x_final_value_kcal_mol = float(gomc_e_potential_box_x_kcal_per_mol[-1])

    gomc_e_intra_nb_box_x_kcal_per_mol = gomc_energy_data_box_x_df.loc[:, 'INTRA(NB)'].tolist()
    gomc_e_intra_nb_box_x_initial_value = float(gomc_e_intra_nb_box_x_kcal_per_mol[0])
    gomc_e_intra_nb_box_x_final_value = float(gomc_e_intra_nb_box_x_kcal_per_mol[-1])

    gomc_e_inter_lj_box_x_kcal_per_mol = gomc_energy_data_box_x_df.loc[:, 'INTER(LJ)'].tolist()
    gomc_e_inter_lj_box_x_initial_value = float(gomc_e_inter_lj_box_x_kcal_per_mol[0])
    gomc_e_inter_lj_box_x_final_value = float(gomc_e_inter_lj_box_x_kcal_per_mol[-1])

    gomc_e_vdw_plus_elec_box_x_kcal_per_mol = []
    for vwd_elec_i in range(0, len(gomc_e_intra_nb_box_x_kcal_per_mol)):
        gomc_e_vdw_plus_elec_box_x_kcal_per_mol.append(float(gomc_e_intra_nb_box_x_kcal_per_mol[vwd_elec_i]) +
                                                       float(gomc_e_inter_lj_box_x_kcal_per_mol[vwd_elec_i])
                                                       + float(gomc_e_electro_box_x_kcal_per_mol[vwd_elec_i]))
    gomc_e_vdw_plus_elec_box_x_initial_value_kcal_mol = float(gomc_e_vdw_plus_elec_box_x_kcal_per_mol[0])
    gomc_e_vdw_plus_elec_box_x_final_value_kcal_mol = float(gomc_e_vdw_plus_elec_box_x_kcal_per_mol[-1])

    return gomc_e_electro_box_x_kcal_per_mol, gomc_e_electro_box_x_initial_value_kcal_mol, \
           gomc_e_electro_box_x_final_value_kcal_mol, \
           gomc_e_potential_box_x_kcal_per_mol, gomc_e_potential_box_x_initial_value_kcal_mol, \
           gomc_e_potential_box_x_final_value_kcal_mol, \
           gomc_e_vdw_plus_elec_box_x_kcal_per_mol, gomc_e_vdw_plus_elec_box_x_initial_value_kcal_mol, \
           gomc_e_vdw_plus_elec_box_x_final_value_kcal_mol


for run_no in range(starting_sims_namd_gomc, total_sims_namd_gomc):
    # *************************************************
    # *************************************************
    # Simulation initial running or restart setup and run (Start)
    # *************************************************
    # *************************************************

    # get the cycle start runtime.  it can only be even as the runs always start with NAMD
    if run_no % 2 == 0:
        cycle_start_time = datetime.datetime.today()
    # set_box_numbers
    box_number_0 = 0
    box_number_1 = 1

    try:
        print("current step = {} (negative (-) for minimize "
              "steps)".format(str(int(current_step - namd_minimize_steps))))
    except:
        print("current step = NA (negative (-) for minimize steps)")

    add_zeros_at_start_run_no_str = calc_folder_zeros(run_no)

    # setting the past file name in a restart
    if run_no == starting_sims_namd_gomc and starting_sims_namd_gomc != 0:
        add_zeros_at_start_run_no_str = calc_folder_zeros(int(starting_sims_namd_gomc - 2))
        namd_box_0_newdir = "{}/{}/{}{}_a".format(str(python_file_directory),
                                                  path_namd_runs,
                                                  str(add_zeros_at_start_run_no_str),
                                                  str(int(starting_sims_namd_gomc - 2))
                                                  )

        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            namd_box_1_newdir = "{}/{}/{}{}_b".format(str(python_file_directory),
                                                      path_namd_runs,
                                                      str(add_zeros_at_start_run_no_str),
                                                      str(int(starting_sims_namd_gomc - 2))
                                                      )

        add_zeros_at_start_run_no_str = calc_folder_zeros(int(starting_sims_namd_gomc - 1))
        gomc_newdir = "{}/{}/{}{}".format(str(python_file_directory), path_gomc_runs,
                                          str(add_zeros_at_start_run_no_str),
                                          str(int(starting_sims_namd_gomc - 1))
                                          )

        # steps in number of cycles
        current_step = (namd_run_steps + gomc_run_steps) * starting_at_cycle_namd_gomc_sims + namd_minimize_steps

    elif run_no == starting_sims_namd_gomc and starting_sims_namd_gomc == 0:
        current_step = 0

    # Delete FFT info from NAMD if starting a new simulation (i.e., run_no at start of running == 0)
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False and run_no == 0:
        delete_namd_run_0_fft_file(box_number_0)
        delete_namd_run_0_fft_file(box_number_1)

    elif run_no == 0:
        delete_namd_run_0_fft_file(box_number_0)

    # Get the NAMD_PME_GRID_DIMs upon restarting a simulation
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False and \
            (run_no == starting_sims_namd_gomc):
        namd_x_pme_grid_box_0_dim, \
        namd_y_pme_grid_box_0_dim, \
        namd_z_pme_grid_box_0_dim, \
        namd_box_0_run_0_dir = get_namd_run_0_pme_dim(box_number_0)
        namd_x_pme_grid_box_1_dim, \
        namd_y_pme_grid_box_1_dim, \
        namd_z_pme_grid_box_1_dim, \
        namd_box_1_run_0_dir = get_namd_run_0_pme_dim(box_number_1)

    elif starting_sims_namd_gomc == run_no and (run_no == starting_sims_namd_gomc):
        namd_x_pme_grid_box_0_dim, \
        namd_y_pme_grid_box_0_dim, \
        namd_z_pme_grid_box_0_dim, \
        namd_box_0_run_0_dir = get_namd_run_0_pme_dim(box_number_0)

    write_log_data = "*************************************************\n" \
                     "*************************************************\n" \
                     "run_no = {} (START)\n" \
                     "************************************************* \n".format(str(run_no))
    log_template_file.write(str(write_log_data))
    print(str(write_log_data))

    if run_no != 0:
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False \
                and starting_sims_namd_gomc == run_no:
            namd_box_0_run_0_fft_namd_filename,\
            namd_box_0_run_0_dir = get_namd_run_0_fft_filename(box_number_0)

            namd_box_1_run_0_fft_namd_filename,\
            namd_box_1_run_0_dir = get_namd_run_0_fft_filename(box_number_1)

        else:
            namd_box_0_run_0_fft_namd_filename,\
            namd_box_0_run_0_dir = get_namd_run_0_fft_filename(box_number_0)
    # *************************************************
    # *************************************************
    # Simulation initial or restart setup (end)
    # *************************************************
    # *************************************************

    # *************************************************
    # *************************************************
    # RUN THE NAMD PORTION of the CODE (Start)
    # *************************************************
    # *************************************************
    if run_no % 2 == 0:  # NAMD's staring run.  NAMD starts simulation series with energy minimization
        # *************************************************
        # build input file from template for box 0 (start)
        # *************************************************

        try:
            gomc_newdir
        except:
            gomc_newdir = "NA"

        namd_box_0_newdir = write_namd_conf_file(python_file_directory, path_namd_template,  path_namd_runs,
                                                 gomc_newdir, run_no, box_number_0, namd_run_steps,
                                                 namd_minimize_steps, namd_rst_dcd_xst_steps,
                                                 namd_console_blkavg_e_and_p_steps,
                                                 simulation_temp_k, simulation_pressure_bar,
                                                 starting_pdb_box_0_file, starting_psf_box_0_file,
                                                 namd_x_pme_grid_box_0_dim,
                                                 namd_y_pme_grid_box_0_dim,
                                                 namd_z_pme_grid_box_0_dim,
                                                 set_x_dim=set_dims_box_0_list[0],
                                                 set_y_dim=set_dims_box_0_list[1],
                                                 set_z_dim=set_dims_box_0_list[2])

        # *************************************************
        # build input file from template for box 0 (end)
        # *************************************************

        # *************************************************
        # build input file from template for box 1 (start)
        # *************************************************
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:

            namd_box_1_newdir = write_namd_conf_file(python_file_directory, path_namd_template, path_namd_runs,
                                                     gomc_newdir, run_no, box_number_1, namd_run_steps,
                                                     namd_minimize_steps, namd_rst_dcd_xst_steps,
                                                     namd_console_blkavg_e_and_p_steps,
                                                     simulation_temp_k, simulation_pressure_bar,
                                                     starting_pdb_box_1_file, starting_psf_box_1_file,
                                                     namd_x_pme_grid_box_1_dim,
                                                     namd_y_pme_grid_box_1_dim,
                                                     namd_z_pme_grid_box_1_dim,
                                                     set_x_dim=set_dims_box_1_list[0],
                                                     set_y_dim=set_dims_box_1_list[1],
                                                     set_z_dim=set_dims_box_1_list[2],
                                                     fft_add_namd_ang_to_box_dim=0)
            # *************************************************
            # build input file from template for box 1 (end)
            # *************************************************

        # *************************************************
        # Run the intitial NAMD simulations box 0 and 1 (start)
        # *************************************************
        write_log_data = "*************************************************\n" \
                         "Running the initial NAMD simulations now. \n"
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        # copy the old FFT files into the new folder
        if run_no != 0:
            # copy the FFT grid.txt file from the first NAMD simulation (i.e., Run 0) to the current dir
            # for box_0
            cp_namd_box_0_fft_run_0_new_dir_cmd = "ln -sf {}/{} {}".format(str(namd_box_0_run_0_dir),
                                                                           str(namd_box_0_run_0_fft_namd_filename),
                                                                           str(namd_box_0_newdir)
                                                                           )

            exec_namd_box_0_cp_fft_run_0_new_dir_cmd = subprocess.Popen(cp_namd_box_0_fft_run_0_new_dir_cmd,
                                                                        shell=True, stderr=subprocess.STDOUT)
            os.waitpid(exec_namd_box_0_cp_fft_run_0_new_dir_cmd.pid, os.WSTOPPED)
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            # find the FFT grid.txt file from the first NAMD simulation (i.e., Run 0) and copy it to
            # to the current dir for box 0
            if run_no != 0:
                # copy the FFT grid.txt file from the first NAMD simulation (i.e., Run 0) to the current dir
                # for box_0 and box_1

                cp_namd_box_1_fft_run_0_new_dir_cmd = "ln -sf {}/{} {}".format(str(namd_box_1_run_0_dir),
                                                                               str(namd_box_1_run_0_fft_namd_filename),
                                                                               str(namd_box_1_newdir)
                                                                               )

                exec_namd_box1_cp_fft_run_0_new_dir_cmd = subprocess.Popen(cp_namd_box_1_fft_run_0_new_dir_cmd,
                                                                           shell=True, stderr=subprocess.STDOUT)
                os.waitpid(exec_namd_box1_cp_fft_run_0_new_dir_cmd.pid, os.WSTOPPED)


        # run NAMD for box 0
        if simulation_type in ['GCMC', 'NVT', 'NPT'] or \
                (simulation_type in ['GEMC'] and only_use_box_0_for_namd_for_gemc is True) \
                or namd_sim_order == 'series':
            run_box_0_command = "cd {} && {} +p{} in.conf > out.dat".format(str(namd_box_0_newdir),
                                                                            str(namd_bin_file),
                                                                            str(int(total_no_cores))
                                                                            )

        elif simulation_type in ['GEMC'] and only_use_box_0_for_namd_for_gemc is False \
                and namd_sim_order == 'parallel':
            run_box_0_command = "cd {} && {} +p{} in.conf > out.dat".format(str(namd_box_0_newdir),
                                                                            str(namd_bin_file),
                                                                            str(int(no_core_box_0))
                                                                            )

        namd_box_0_exec_start_time = datetime.datetime.today()
        exec_run_box_0_command = subprocess.Popen(run_box_0_command, shell=True, stderr=subprocess.STDOUT)

        if namd_sim_order == 'series':
            write_log_data = 'Waiting for initial NAMD simulation to finish. \n'
            log_template_file.write(str(write_log_data))
            print(str(write_log_data))

            os.waitpid(exec_run_box_0_command.pid, os.WSTOPPED)  # pauses python until box 0 sim done
            namd_box_0_exec_end_time = datetime.datetime.today()

        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            # Run NAMD for box_1
            if namd_sim_order == 'series':
                run_box_1_command = "cd {} && {} +p{} in.conf > out.dat".format(str(namd_box_1_newdir),
                                                                                str(namd_bin_file),
                                                                                str(int(total_no_cores))
                                                                                )
            elif namd_sim_order == 'parallel':
                run_box_1_command = "cd {} && {} +p{} in.conf > out.dat".format(str(namd_box_1_newdir),
                                                                                str(namd_bin_file),
                                                                                str(int(no_core_box_1))
                                                                                )

            namd_box_1_exec_start_time = datetime.datetime.today()
            exec_run_box_1_command = subprocess.Popen(run_box_1_command, shell=True, stderr=subprocess.STDOUT)
            if namd_sim_order == 'series':
                os.waitpid(exec_run_box_1_command.pid, os.WSTOPPED)  # pauses python until box 1 sim done
                namd_box_1_exec_end_time = datetime.datetime.today()

        if namd_sim_order == 'parallel':
            write_log_data = 'Waiting for initial NAMD simulation to finish. \n'
            log_template_file.write(str(write_log_data))
            print(str(write_log_data))

            os.waitpid(exec_run_box_0_command.pid, os.WSTOPPED)  # pauses python until box 0 sim done
            namd_box_0_exec_end_time = datetime.datetime.today()

            if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
                os.waitpid(exec_run_box_1_command.pid, os.WSTOPPED)  # pauses python until box 1 sim done
                namd_box_1_exec_end_time = datetime.datetime.today()

        namd_box_0_cycle_time_s = (namd_box_0_exec_end_time - namd_box_0_exec_start_time).total_seconds()
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            namd_box_1_cycle_time_s = (namd_box_1_exec_end_time - namd_box_1_exec_start_time).total_seconds()
            if namd_sim_order == 'series':
                max_namd_cycle_time_s = round(namd_box_0_cycle_time_s + namd_box_1_cycle_time_s, 6)
            elif namd_sim_order == 'parallel':
                max_namd_cycle_time_s = round(np.maximum(namd_box_0_cycle_time_s, namd_box_1_cycle_time_s), 6)
        else:
            max_namd_cycle_time_s = round(namd_box_0_cycle_time_s, 6)

        write_log_data = 'The NAMD simulation are finished. \n'
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        # *************************************************
        # Run the intitial NAMD simulations box 0 and 1 (end)
        # *************************************************

        # *****************************************************
        # get final system energies for box 0 and 1 (start)
        # ***********************initial_Energies**************
        read_namd_box_0_energy_file = open("{}/out.dat".format(str(namd_box_0_newdir)), 'r').readlines()
        # note NAMD energy units in kcal/mol (no modifications required)
        # generate energy file data for box 0

        namd_e_electro_box_0, \
        namd_e_electro_box_0_initial_value, \
        namd_e_electro_box_0_final_value, \
        namd_e_potential_box_0, \
        namd_e_potential_box_0_initial_value, \
        namd_e_potential_box_0_final_value, \
        namd_e_vdw_plus_elec_box_0, \
        namd_e_vdw_plus_elec_box_0_initial_value, \
        namd_e_vdw_plus_elec_box_0_final_value = get_namd_energy_data(read_namd_box_0_energy_file,
                                                            default_namd_e_titles)

        # note NAMD energy units in kcal/mol (no modifications required)
        # generate energy file data for box 1
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            read_namd_box_1_energy_file = open("{}/out.dat".format(str(namd_box_1_newdir)), 'r').readlines()

            namd_e_electro_box_1, \
            namd_e_electro_box_1_initial_value, \
            namd_e_electro_box_1_final_value, \
            namd_e_potential_box_1, \
            namd_e_potential_box_1_initial_value, \
            namd_e_potential_box_1_final_value, \
            namd_e_vdw_plus_elec_box_1, \
            namd_e_vdw_plus_elec_box_1_initial_value, \
            namd_e_vdw_plus_elec_box_1_final_value = get_namd_energy_data(read_namd_box_1_energy_file,
                                                                default_namd_e_titles)

        if run_no != 0 and run_no != starting_sims_namd_gomc:
            # Compare the Last GOMC and first NAMD value to confirm the simulation data
            # VMD comparison between NAMD and GOMC data box 0

            compare_namd_gomc_energies(gomc_e_potential_box_0_final_value,
                                       namd_e_potential_box_0_initial_value,
                                       gomc_e_vdw_plus_elec_box_0_final_value,
                                       namd_e_vdw_plus_elec_box_0_initial_value,
                                       run_no, box_number_0)
            if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
                compare_namd_gomc_energies(gomc_e_potential_box_1_final_value,
                                           namd_e_potential_box_1_initial_value,
                                           gomc_e_vdw_plus_elec_box_1_final_value,
                                           namd_e_vdw_plus_elec_box_1_initial_value,
                                           run_no, box_number_1)

        # get the NAMD FFT file name to copy for future NAMD simulations if starting a new NAMD/GOMC simulation
        if run_no == 0:
            if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False \
                    and starting_sims_namd_gomc == run_no:
                namd_box_0_run_0_fft_namd_filename,\
                namd_box_0_run_0_dir = get_namd_run_0_fft_filename(box_number_0)
                namd_box_1_run_0_fft_namd_filename,\
                namd_box_1_run_0_dir = get_namd_run_0_fft_filename(box_number_1)
            else:
                namd_box_0_run_0_fft_namd_filename, \
                namd_box_0_run_0_dir = get_namd_run_0_fft_filename(box_number_0)

        # Get the NAMD_PME_GRID_DIMs upon finishing a new simulation
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False and \
                (run_no == starting_sims_namd_gomc):
            namd_x_pme_grid_box_0_dim, namd_y_pme_grid_box_0_dim, \
            namd_z_pme_grid_box_0_dim, namd_box_0_run_0_dir = get_namd_run_0_pme_dim(box_number_0)
            namd_x_pme_grid_box_1_dim, namd_y_pme_grid_box_1_dim, \
            namd_z_pme_grid_box_1_dim, namd_box_1_run_0_dir = get_namd_run_0_pme_dim(box_number_1)

        elif starting_sims_namd_gomc == run_no and (run_no == starting_sims_namd_gomc):
            namd_x_pme_grid_box_0_dim, namd_y_pme_grid_box_0_dim, \
            namd_z_pme_grid_box_0_dim, namd_box_0_run_0_dir = get_namd_run_0_pme_dim(box_number_0)

        if run_no != 0:
            current_step += namd_run_steps
        else:
            current_step += namd_run_steps + namd_minimize_steps
        # *************************************
        # get final system energies for box 0 and 1 (end)
        # *************************************
    # *************************************************
    # *************************************************
    # RUN THE NAMD PORTION of the CODE (End)
    # *************************************************
    # *************************************************

    # *************************************************
    # *************************************************
    # RUN THE GOMC PORTION of the CODE (Start)
    # *************************************************
    # *************************************************
    elif run_no % 2 == 1:  # GOMC's run time.  GOMC starts simulation series
        # GOMC runs
        # *************************************************
        # build input file from template the GOMC simulation (start)
        # *************************************************
        try:
            previous_gomc_dir = gomc_newdir
        except:
            previous_gomc_dir = "NA"

        gomc_newdir = write_gomc_conf_file(python_file_directory, path_gomc_runs, run_no, gomc_run_steps,
                                           gomc_rst_coor_ckpoint_steps, gomc_console_blkavg_hist_steps,
                                           gomc_hist_sample_steps,
                                           simulation_temp_k, simulation_pressure_bar,
                                           starting_pdb_box_0_file, starting_pdb_box_1_file,
                                           starting_psf_box_0_file, starting_psf_box_1_file)

        write_log_data = "GOMC simulation data for simulation number {} is completed. \n".format(str(run_no))
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        # *************************************************
        # build input file from template the GOMC simulation (end)
        # *************************************************

        # *************************************************
        # Copy file and Run the GOMC simulations (start)
        # *************************************************

        write_log_data = "*************************************************\n" \
                         "Running the GOMC simulations now. \n"
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))
        run_gomc_command = "cd {} && {} +p{} in.conf > out.dat".format(str(gomc_newdir),
                                                                       str(gomc_bin_file),
                                                                       str(int(total_no_cores))
                                                                       )

        previous_namd_dir = datetime.datetime.today()
        exec_gomc_run_command = subprocess.Popen(run_gomc_command, shell=True, stderr=subprocess.STDOUT)

        write_log_data = 'Waiting for initial GOMC simulation to finish.'
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))
        os.waitpid(exec_gomc_run_command.pid, os.WSTOPPED)  # pauses python until box 0 sim done
        gomc_exec_end_time = datetime.datetime.today()
        gomc_cycle_time_s = round((gomc_exec_end_time - previous_namd_dir).total_seconds(), 6)

        write_log_data = 'The GOMC simulation(s) are finished.'
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        write_log_data = "Completed simulation in GOMC command\n" \
                         "************************************************* \n"
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

        # *************************************************
        # Copy file and Run the GOMC simulations (end)
        # *************************************************

        # *******************************************************
        # get final system energies for box 0 and 1 (start)
        # ***********************initial_Energies**************
        read_gomc_log_file = open("{}/out.dat".format(str(gomc_newdir)), 'r').readlines()
        gomc_energy_data_box_0_df = get_gomc_energy_data(read_gomc_log_file, box_number_0)

        if simulation_type in ["GEMC", "GCMC"]:
            gomc_energy_data_box_1_df = get_gomc_energy_data(read_gomc_log_file, box_number_1)

        # retrieve energy data from the printed file for the first and last points for box 0
        # extrated in units of kcal per mol
        gomc_e_electro_box_0_kcal_per_mol, \
        gomc_e_electro_box_0_initial_value, \
        gomc_e_electro_box_0_final_value, \
        gomc_e_potential_box_0_kcal_per_mol, \
        gomc_e_potential_box_0_initial_value, \
        gomc_e_potential_box_0_final_value, \
        gomc_e_vdw_plus_elec_box_0_kcal_per_mol, \
        gomc_e_vdw_plus_elec_box_0_initial_value, \
        gomc_e_vdw_plus_elec_box_0_final_value = get_gomc_energy_data_kcal_per_mol(gomc_energy_data_box_0_df)

        # retrieve energy data from the printed file for the first and last points for box 1s
        if simulation_type in ["GEMC", "GCMC"]:  
            # extrated in units of kcal per mol
            gomc_e_electro_box_1_kcal_per_mol, \
            gomc_e_electro_box_1_initial_value, \
            gomc_e_electro_box_1_final_value, \
            gomc_e_potential_box_1_kcal_per_mol, \
            gomc_e_potential_box_1_initial_value, \
            gomc_e_potential_box_1_final_value, \
            gomc_e_vdw_plus_elec_box_1_kcal_per_mol, \
            gomc_e_vdw_plus_elec_box_1_initial_value, \
            gomc_e_vdw_plus_elec_box_1_final_value = get_gomc_energy_data_kcal_per_mol(gomc_energy_data_box_1_df)

        # *******************************************************
        # get final system energies for box 0 and 1 (end)
        # ***********************initial_Energies**************

        # Compare the Last NAMD and first GOMC value to confirm the simulation data
        # VMD comparison between NAMD and GOMC data box 0
        compare_namd_gomc_energies(namd_e_potential_box_0_final_value,
                                   gomc_e_potential_box_0_initial_value,
                                   namd_e_vdw_plus_elec_box_0_final_value,
                                   gomc_e_vdw_plus_elec_box_0_initial_value,
                                   run_no, box_number_0)
        if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
            compare_namd_gomc_energies(namd_e_potential_box_1_final_value,
                                       gomc_e_potential_box_1_initial_value,
                                       namd_e_vdw_plus_elec_box_1_final_value,
                                       gomc_e_vdw_plus_elec_box_1_initial_value,
                                       run_no, box_number_1)

        current_step += gomc_run_steps

    # get the cycle end runtime.  it can only be odd as the runs always ends with GOMC
    if run_no % 2 == 1:
        cycle_end_time = datetime.datetime.today()
        cycle_run_time_s = round((cycle_end_time - cycle_start_time).total_seconds(), 6)
        python_only_time_s = round(cycle_run_time_s - (max_namd_cycle_time_s + gomc_cycle_time_s), 6)
    # print the times stats for NAMD GOMC and total time header
    if run_no == starting_sims_namd_gomc + 1:
        write_log_data = "*************************************************\n" \
                         "TIME_STATS_TITLE:\t#Cycle_No\t\tNAMD_time_s\t\t" \
                         "GOMC_time_s\t\tPython_time_s\t\tTotal_time_s\n"
        log_template_file.write(str(write_log_data))
        print(str(write_log_data))

    # print the times stats for NAMD GOMC and total time if on the end of the first cycle
    if run_no >= starting_sims_namd_gomc + 1 and run_no % 2 == 1:
        # cycle number will start at zero
        cycle_no = int(run_no / 2)
        if run_no != starting_sims_namd_gomc + 1:
            write_log_data = "*************************************************\n"
            log_template_file.write(str(write_log_data))
            print(str(write_log_data))
        write_log_data = "TIME_STATS_DATA:\t{}\t\t{}\t\t{}\t\t{}\t\t{}\n".format(cycle_no,
                                                                                 max_namd_cycle_time_s,
                                                                                 gomc_cycle_time_s,
                                                                                 python_only_time_s,
                                                                                 cycle_run_time_s
                                                                                 )
        log_template_file.write(write_log_data)
        print(write_log_data)
    # *************************************************
    # *************************************************
    # Simulation initial running or restart setup and run (End)
    # *************************************************
    # *************************************************

    write_log_data = "*************************************************\n" \
                     "run_no = {} (End) \n".format(str(run_no))
    log_template_file.write(str(write_log_data))
    print(str(write_log_data))

end_time = datetime.datetime.today()
end_time_s = datetime.datetime.today()
total_time = (end_time - start_time)
total_time_s = (end_time_s - start_time_s).total_seconds()
write_log_data = "*************************************************\n" \
                 "date and time (end) = {} \n" \
                 "total simulation time = {} \n" \
                 "total simulation time (s) = {} \n" \
                 "************************************************* \n".format(str(end_time),
                                                                               str(total_time),
                                                                               str(total_time_s)
                                                                               )
log_template_file.write(str(write_log_data))
print(str(write_log_data))

log_template_file.close()
