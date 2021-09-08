import argparse
import sys
import os
import pandas as pd
import scipy as sp
import numpy as np
import subprocess
import json
import glob

from warnings import warn

# combines the data from the MD/MC simulations (NAMD/GOMC) for the NPT, NVT, GEMC, and GCMC ensembles
# or just combines the log files for the NAMD-only or GOMC-only simulations.

# *************************************************
# The python arguments that need to be selected to run the simulations (start)
# *************************************************
def _get_args():
    arg_parser = argparse.ArgumentParser()

    # get the filename with the user required input
    arg_parser.add_argument("-f", "--file",
                            help="str. Defines the variable inputs to the hybrid NAMD/GOMC, NAMD-only, or GOMC-only "
                                 "log or consol output combining scipt.",
                            type=str)

    # name the file folder in which the data will be combined.
    arg_parser.add_argument("-w", "--write_folder_name",
                            help="str. Defines the folder name in which the files containing the output variables "
                                 "will be combined and written in.",
                            type=str)

    # name the file folder in which the data will be combined.
    arg_parser.add_argument("-o", "--overwrite",
                            help="bool (True, true, T, t, False, false, F, or f). Overwrites the folder in which "
                                 "the output variables will be combined and added in, if the file already exists.",
                            type=str, default='False')

    parser_arguments = arg_parser.parse_args()

    # check to see if the file exists
    if parser_arguments.file:
        if os.path.exists(parser_arguments.file) :
            print("INFO: Reading data from <{}> file.".format(parser_arguments.file))
        else:
            raise FileNotFoundError("ERROR: Console file <{}> does not exist!".format(parser_arguments.file))
    else:
        raise IOError("ERROR: The user input file was not specified as -f or --file")

    # set check if overwrite is set to true, if not set to False
    if parser_arguments.overwrite in ['False', 'false', 'F', 'f']:
        print("INFO: By default, the combining folder will not be overwritten.")
        parser_arguments.overwrite = False
    elif parser_arguments.overwrite in ['True', 'true', 'T', 't']:
        print("INFO: The combining folder will be overwritten.")
        parser_arguments.overwrite = True
    else:
        raise TypeError("ERROR: -o or --overwrite flag is not a boolean.")

    # set check if the combining data file folder name is provided
    if isinstance(parser_arguments.write_folder_name, str) is True:
        print("INFO: The combining folder is named <{}>.".format(parser_arguments.write_folder_name))
    else:
        raise TypeError("ERROR: The -w or --write_folder_name flag was not provided.  This flag defines "
                        "the folder name which is created and will contain the combined data.")

    # check to see if the folder exists
    if os.path.exists(parser_arguments.write_folder_name) and parser_arguments.overwrite is False:
        raise IOError("ERROR: The file folder <{}> already exists. If you want to overwrite it, set the "
                      "-o or --overwrite flag as True.".format(parser_arguments.write_folder_name)
                      )
    elif os.path.exists(parser_arguments.write_folder_name) and parser_arguments.overwrite is True:
        print("INFO: The combining folder <{}> will be overwritten."
              "".format(parser_arguments.write_folder_name)
              )

    return [parser_arguments.file, parser_arguments.write_folder_name, parser_arguments.overwrite]

# *************************************************
# The python arguments that need to be selected to run the simulations (end)
# *************************************************



# *************************************************
# Import read and check the user input file for errors (start)
# *************************************************
# import and read the users json file
[json_filename, write_folder_name, overwrite_folder] = _get_args()
print('arg_parser.file = {}'.format(json_filename))
print('parser_arguments.write_folder_name = {}'.format(write_folder_name))
print('parser_arguments.overwrite = {}'.format(overwrite_folder))

json_file_data = json.load(open(json_filename))
#json_file_data = json.load(open("user_input_combine_data_NAMD_GOMC.json"))
json_file_data_keys_list = json_file_data.keys()

# *************************************************
# Changeable variables (start)
# *************************************************

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

# get the only_use_box_0_for_namd_for_gemc variable from the json file
# string 'Hybrid', 'NAMD-only', 'GOMC-only'  , 'Hybrid need to be in the directory
# with the 'NAMD' and 'GOMC' directories
if "simulation_engine_options" not in json_file_data_keys_list:
    raise TypeError("The simulation_engine_options key is not provided.\n")
simulation_engine_options = json_file_data["simulation_engine_options"]
if simulation_engine_options not in ["Hybrid", "GOMC-only", "NAMD-only"]:
    raise TypeError('The simulation_engine_options are only "Hybrid", "GOMC-only", or "NAMD-only", '
                    'which are entered in the json file.\n')

# get the gomc_or_namd_only_log_filename variable from the json file
if "gomc_or_namd_only_log_filename" not in json_file_data_keys_list:
    raise TypeError("The gomc_or_namd_only_log_filename key is not provided.\n")
gomc_or_namd_only_log_filename = json_file_data["gomc_or_namd_only_log_filename"]
if not isinstance(gomc_or_namd_only_log_filename, str):
    raise TypeError('The gomc_or_namd_only_log_filename must be entered as a string in the json file.\n')

# get the combine_namd_dcd_file variable from the json file
if "combine_namd_dcd_file" not in json_file_data_keys_list:
    raise TypeError("The combine_namd_dcd_file key is not provided.\n")
combine_namd_dcd_file = json_file_data["combine_namd_dcd_file"]
if combine_namd_dcd_file is not True and combine_namd_dcd_file is not False:
    raise TypeError("The combine_namd_dcd_file not true or false in the json file.\n")

# get the combine_gomc_dcd_file variable from the json file
if "combine_gomc_dcd_file" not in json_file_data_keys_list:
    raise TypeError("The combine_gomc_dcd_file key is not provided.\n")
combine_gomc_dcd_file = json_file_data["combine_gomc_dcd_file"]
if combine_gomc_dcd_file is not True and combine_gomc_dcd_file is not False:
    raise TypeError("The combine_gomc_dcd_file not true or false in the json file.\n")

# get the combine_dcd_files_cycle_freq variable from the json file
if "combine_dcd_files_cycle_freq" not in json_file_data_keys_list:
    raise TypeError("The combine_dcd_files_cycle_freq key is not provided.\n")
combine_dcd_files_cycle_freq = json_file_data["combine_dcd_files_cycle_freq"]
if not isinstance(combine_dcd_files_cycle_freq, int):
    raise TypeError("The combine_dcd_files_cycle_freq values must be an integer.\n")
else:
    if combine_dcd_files_cycle_freq < 1:
        raise TypeError("The combine_dcd_files_cycle_freq values must be an integer "
                        "greater than or equal to zero (>=1.\n")

# get the get_initial_gomc_dcd variable from the json file
if "get_initial_gomc_dcd" not in json_file_data_keys_list:
    raise TypeError("The get_initial_gomc_dcd key is not provided.\n")
get_initial_gomc_dcd = json_file_data["get_initial_gomc_dcd"]
if get_initial_gomc_dcd is not True and get_initial_gomc_dcd is not False:
    raise TypeError("The get_initial_gomc_dcd not true or false in the json file.\n")

# get the rel_path_to_combine_binary_catdcd variable from the json file
if "rel_path_to_combine_binary_catdcd" not in json_file_data_keys_list:
    raise TypeError("The rel_path_to_combine_binary_catdcd key is not provided.\n")
rel_path_to_combine_binary_catdcd = json_file_data["rel_path_to_combine_binary_catdcd"]
if not isinstance(rel_path_to_combine_binary_catdcd, str):
    raise TypeError('The rel_path_to_combine_binary_catdcd must be entered as a string in the json file.\n')

warn('If the combining file fails without a set reason/error, please check the '
     '"simulation_engine_options", "out.dat", and the "rel_path_to_combine_binary_catdcd" variables. '
     'The user needs to ensure that these are proper paths and file types, since these variables '
     'are currently only checked to confirm they are strings.')

# *************************************************
# Changable variables (end)
# *************************************************

# *************************************************
#  NAMD and GOMC folders name and create combined_data folder(start)
# *************************************************
python_file_directory = os.getcwd()
path_namd_runs = "NAMD"
path_gomc_runs = "GOMC"

path_combined_data_folder = write_folder_name
os.makedirs(path_combined_data_folder, exist_ok=True)

full_path_to_namd_data_folder = python_file_directory + "/" + str(path_namd_runs)
full_path_to_gomc_data_folder = python_file_directory + "/" + str(path_gomc_runs)
full_path_to_combined_data_folder = python_file_directory + "/" + str(path_combined_data_folder)
# *************************************************
# create NAMD and GOMC folders (end)
# *************************************************
K_to_kcal_mol = 1.98720425864083 * 10**(-3)

# get the number of directories in each NAMD or GOMC folder.  Note: for the NAMD simulations,  '
# the data is split between the liquid box (dir ending in '_a'), and the vapor box (dir ending in '_b')

if simulation_engine_options == 'Hybrid':
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        namd_directory_a_list = []
        namd_directory_b_list = []
        total_namd_directory_list = sorted(os.listdir(python_file_directory + '/' + str(path_namd_runs)))
        no_total_namd_directory_list = len(total_namd_directory_list)
        for i in range(0, len(total_namd_directory_list)):
            namd_directory_iter = str(total_namd_directory_list[i])
            if namd_directory_iter[-2:] == '_a':
                namd_directory_a_list.append(namd_directory_iter)
            elif namd_directory_iter[-2:] == '_b':
                namd_directory_b_list.append(namd_directory_iter)
        namd_directory_a_list = sorted(namd_directory_a_list)
        namd_directory_b_list = sorted(namd_directory_b_list)
        no_namd_directory_a = len(namd_directory_a_list)
        no_namd_directory_b = len(namd_directory_b_list)
        if no_namd_directory_a + no_namd_directory_b != no_total_namd_directory_list:
            warn("WARNING: The total NAMD directories does not match the '..._a (NAMD liq box"
                 "..._b (NAMD vap box)' directories")

    else:
        namd_directory_a_list = []
        total_namd_directory_list = sorted(os.listdir(python_file_directory + '/' + str(path_namd_runs)))
        no_total_namd_directory_list = len(total_namd_directory_list)
        for i in range(0, len(total_namd_directory_list)):
            namd_directory_iter = str(total_namd_directory_list[i])
            if namd_directory_iter[-2:] == '_a':
                namd_directory_a_list.append(namd_directory_iter)
        namd_directory_a_list = sorted(namd_directory_a_list)
        no_namd_directory_a = len(namd_directory_a_list)
        if no_namd_directory_a != no_total_namd_directory_list:
            print("WARNING: The total NAMD directories does not match the '..._a (NAMD liq box)' directories")

    gomc_directory_list = sorted(os.listdir(python_file_directory + '/' + str(path_gomc_runs)))
    no_gomc_directory = len(gomc_directory_list)

    # confirm there are the same number of directories for GOMC and NAMD (vap and liq , [i.e., _a and _b])
    try:
        no_namd_directory_b
        if no_gomc_directory != no_namd_directory_a or no_gomc_directory != no_namd_directory_b:
            warn("WARNING: The total NAMD directories and GOMC directories does not match!")
    except:
        if no_gomc_directory != no_namd_directory_a:
            warn("WARNING: The total NAMD directories and GOMC directories does not match!")

    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        try:
            namd_interation = str(namd_directory_b_list[namd_interation])
        except:
            raise ValueError("Box 1 data does not exist for NAMD, maybe use "
                             "only_use_box_0_for_namd_for_gemc == True")

    # get the total number of simulation = 2 * number of cycles or 1 * number of GOMC directories
    total_sims_namd_gomc = int(2 * no_gomc_directory)


# set all the filenames and paths
if simulation_engine_options in ['Hybrid', 'NAMD-only']:
    namd_box_0_data_filename = "{}/{}".format(full_path_to_combined_data_folder, 'NAMD_data_box_0.txt')
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        namd_box_1_data_filename = "{}/{}".format(full_path_to_combined_data_folder, 'NAMD_data_box_1.txt')


    namd_box_0_data_density_filename = "{}/{}".format(full_path_to_combined_data_folder, 'NAMD_data_density_box_0.txt')
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        namd_box_1_data_density_filename = "{}/{}".format(full_path_to_combined_data_folder, 'NAMD_data_density_box_1.txt')

if simulation_engine_options in ['Hybrid', 'GOMC-only']:
    gomc_box_0_data_filename = "{}/{}".format(full_path_to_combined_data_folder, 'GOMC_data_box_0.txt')
    gomc_box_0_energies_stat_filename = "{}/{}".format(full_path_to_combined_data_folder, 'GOMC_Energies_Stat_box_0.txt')
    gomc_box_0_energies_stat_kcal_per_mol_filename = "{}/{}".format(full_path_to_combined_data_folder,
                                                                    'GOMC_Energies_Stat_kcal_per_mol_box_0.txt')


    if simulation_type in ["GEMC", "GCMC"]:
        gomc_box_1_data_filename = "{}/{}".format(full_path_to_combined_data_folder,'GOMC_data_box_1.txt')
        gomc_box_1_energies_stat_filename = "{}/{}".format(full_path_to_combined_data_folder,
                                                           'GOMC_Energies_Stat_box_1.txt')
        gomc_box_1_energies_stat_kcal_per_mol_filename = "{}/{}".format(full_path_to_combined_data_folder,
                                                                        'GOMC_Energies_Stat_kcal_per_mol_box_1.txt')

    gomc_box_0_data_file = open(gomc_box_0_data_filename, 'w')
    if simulation_type in ["GEMC"]:
        gomc_box_1_data_file = open(gomc_box_1_data_filename, 'w')

    gomc_box_0_hist_filename = "{}/{}".format(full_path_to_combined_data_folder, 'GOMC_hist_data_box_0.txt')
    if simulation_type in ["GCMC"]:
        gomc_box_0_hist_file = open(gomc_box_0_hist_filename, 'w')

if simulation_engine_options in ['Hybrid', 'NAMD-only']:
    namd_box_0_data_file = open(namd_box_0_data_filename, 'w')
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        namd_box_1_data_file = open(namd_box_1_data_filename, 'w')
        e_values_namd_box_1_density_list = []

if simulation_engine_options in ['Hybrid']:
    combined_box_0_filename_only = 'combined_NAMD_GOMC_data_box_0.txt'
    combined_box_1_filename_only = 'combined_NAMD_GOMC_data_box_1.txt'

elif simulation_engine_options in ['GOMC-only']:
    combined_box_0_filename_only = 'combined_GOMC_data_box_0.txt'
    combined_box_1_filename_only = 'combined_GOMC_data_box_1.txt'
elif simulation_engine_options in ['NAMD-only']:
    combined_box_0_filename_only = 'combined_NAMD_data_box_0.txt'
    combined_box_1_filename_only = 'combined_NAMD_data_box_1.txt'

combined_box_0_data_filename = "{}/{}".format(full_path_to_combined_data_folder,
                                              combined_box_0_filename_only)
combined_box_1_data_filename = "{}/{}".format(full_path_to_combined_data_folder,
                                              combined_box_1_filename_only)

if simulation_engine_options in ['Hybrid']:
# starting point for the GOMC dist dicts for GCMC only
    if simulation_type in ['GCMC']:
        full_path_dist_files_only_run_0_list = glob.glob('{}/{}/{}/{}'.format(python_file_directory,
                                                                              path_gomc_runs,
                                                                              gomc_directory_list[0],
                                                                              "*dis1a.dat")
                                                         )

        no_dist_files_only_run_0_list = len(full_path_dist_files_only_run_0_list)
        dict_of_current_dist_dicts = {}
        for i in range(0, no_dist_files_only_run_0_list):
            dict_of_current_dist_dicts.update({i + 1: {}})


def get_namd_log_data(read_namd_box_x_log_file,
                      namd_box_x_data_file,
                      run_no,
                      e_values_namd_box_x_density_list=None,
                      e_titles_namd_box_x_iteration=None,
                      e_titles_namd_box_x_density_iteration=None):
    """
    Extracts the NAMD log data from every run (energy and state properties),
    combining it into a list while adding the system density,
    and also keeping the exact output lines from NAMD.

    Parameters
    ----------
    read_namd_box_x_log_file : readable opened file with .readlines()
        The read loaded namd log file with .readlines().
    namd_box_x_data_file : writeable opened file
        The writeable opened file, which is used to write the combined
        and compact data from the NAMD log file.
    run_no : int
        Simulation run number
    e_values_namd_box_x_density_list : list, default = []
        The NAMD log data output with the density added.
        If the default value (empty list) is not used, the
        provided list will be appended.  This needs provided not
        reading 1st NAMD simulation.
    e_titles_namd_box_x_iteration : list, default = None
        The titles of the NAMD energy and state data from the systems log file.
        This needs provided not reading 1st NAMD simulation.
    e_titles_namd_box_x_density_iteration : list, default = None
        The titles of the NAMD energy and state data from the systems log file,
        adding a # sybol on the first entry and 'DENSITY' at the end of the
        list. This needs provided not reading 1st NAMD simulation.

    Returns
    ---------
    e_titles_namd_box_x_iteration : list
        The titles of the NAMD energy and state data from the systems log file.
    e_titles_namd_box_x_density_iteration : list
        The titles of the NAMD energy and state data from the systems log file,
        adding a # sybol on the first entry and 'DENSITY' at the end of the
        list. This needs provided not reading 1st NAMD simulation.
    e_values_namd_box_x_iteration : list
        The NAMD log data output with the density added.
    e_values_namd_box_x_density_list : list
        The reorganized and combined NAMD log data from the current NAMD run,
        and the past runs that were entered via the flag ().

    e_property_values_namd_box_x_list list:
        The NAMD log data from the current NAMD run, which does not
        include the calculated density value.  This includes the first item
        in the list being 'ENERGY:'.

    Notes
    --------
    The timesteps are rescaled so that the NAMD and GOMC data are added
    properly in order.

    The 2 timestep 0 values will appear if system is minimized.
    The minimization timesteps are rescaled to 0 for the actual run start,
    not minimization.
    """

    error_for_bad_namd_input_file_data = "ERROR: This NAMD file output file does not contain all " \
                                         "the required information. The Energy titles/values " \
                                         "are missing from the NAMD output/log file(s) in " \
                                         "run number {}.".format(run_no)

    if e_values_namd_box_x_density_list is None:
        e_values_namd_box_x_density_list = []
    else:
        e_values_namd_box_x_density_list

    for i, line in enumerate(read_namd_box_x_log_file):
        split_line = line.split()
        if line.startswith('Info:') is True:
            if split_line[0] == 'Info:' and len(split_line) >= 6:
                if split_line[1] == 'TOTAL' and split_line[2] == 'MASS' and split_line[3] == '=':
                    namd_sim_total_mass_box_x_amu = float(split_line[4])
            if split_line[0] == 'Info:' and len(split_line) >= 5:
                if split_line[1] == 'ENERGY' and split_line[2] == 'OUTPUT' and split_line[3] == 'STEPS':
                    namd_sim_e_output_steps_box_x = float(split_line[4])

    # note NAMD energy units in kcal/mol (no modifications required)
    # generate energy file data for box X
    if run_no == 0:
        get_e_namd_box_x_titles = True
    else:
        get_e_namd_box_x_titles = False
    e_property_values_namd_box_x_list = []
    for i, line in enumerate(read_namd_box_x_log_file):
        if line.startswith('ETITLE:') is True and get_e_namd_box_x_titles is True:
            namd_box_x_data_file.write('%s' % read_namd_box_x_log_file[i])
            e_titles_namd_box_x_iteration = read_namd_box_x_log_file[i]
            e_titles_namd_box_x_iteration = e_titles_namd_box_x_iteration.split()
            e_titles_namd_box_x_iteration = e_titles_namd_box_x_iteration[:]

            e_titles_namd_box_x_density_iteration = read_namd_box_x_log_file[i]
            e_titles_namd_box_x_density_iteration = e_titles_namd_box_x_density_iteration.split()
            e_titles_namd_box_x_density_iteration = e_titles_namd_box_x_density_iteration[1:]
            e_titles_namd_box_x_density_iteration.append('DENSITY')

            if get_e_namd_box_x_titles is True:
                get_e_namd_box_x_titles = False

        if line.startswith('ENERGY:') is True:
            e_values_namd_box_x_iteration = read_namd_box_x_log_file[i]
            e_values_namd_box_x_iteration = e_values_namd_box_x_iteration.split()
            e_values_namd_box_x_iteration = e_values_namd_box_x_iteration[:]
            for y in range(0, len(e_titles_namd_box_x_iteration)):
                if e_titles_namd_box_x_iteration[y] == 'TS':
                    e_values_namd_box_x_iteration[y] = (str(int(int(e_values_namd_box_x_iteration[y]) + current_step)))
                    array_ts_location = y
                elif e_titles_namd_box_x_iteration[y] == 'VOLUME':
                    e_volume_data_namd_box_x_iteration = float(e_values_namd_box_x_iteration[y])
                    e_density_data_namd_box_x_iteration = 1.6605402 * namd_sim_total_mass_box_x_amu \
                                                          / e_volume_data_namd_box_x_iteration

            if int(e_values_namd_box_x_iteration[array_ts_location]) >= 0:
                namd_box_x_data_file.write('%s \n' % str('\t '.join(e_values_namd_box_x_iteration)))
                e_property_values_namd_box_x_list.append(e_values_namd_box_x_iteration)

                e_values_namd_box_x_density_iteration = e_values_namd_box_x_iteration[1:]
                e_values_namd_box_x_density_iteration.append(e_density_data_namd_box_x_iteration)
                e_values_namd_box_x_density_list.append(e_values_namd_box_x_density_iteration)

    if (e_titles_namd_box_x_iteration is None or e_titles_namd_box_x_density_iteration is None) and run_no != 0:
        warn("enter the e_titles_namd_box_x_iteration variable in the get_namd_log_data, as "
             " it is not in the NAMD log file to read.")
    else:
        e_titles_namd_box_x_iteration = e_titles_namd_box_x_iteration
        e_titles_namd_box_x_density_iteration = e_titles_namd_box_x_density_iteration

    # add a pound symbol (#) before some of the titles
    if str(e_titles_namd_box_x_density_iteration[0][0]) != '#':
        e_titles_namd_box_x_density_iteration[0] = '#' + str(e_titles_namd_box_x_density_iteration[0])

    try:
        isinstance(e_titles_namd_box_x_iteration, list)
        isinstance(e_titles_namd_box_x_density_iteration, list)
        isinstance(e_values_namd_box_x_iteration, list)
        isinstance(e_values_namd_box_x_density_list, list)
        isinstance(e_property_values_namd_box_x_list, list)
    except:
        raise ValueError(error_for_bad_namd_input_file_data)

    return e_titles_namd_box_x_iteration, e_titles_namd_box_x_density_iteration, \
           e_values_namd_box_x_iteration, \
           e_values_namd_box_x_density_list, e_property_values_namd_box_x_list


def get_gomc_hist_data(read_gomc_box_0_hist_file,
                       gomc_box_0_hist_file,
                       run_no):
    """
    This reads in the current simulation histogram (hist) data
    and appends it add to a histrogram file, which was created
    when the first GOMC simulation was read. In the end, this
    function writes and combines all the hist data from all
    the GOMC runs.

    Parameters
    ----------
    read_gomc_box_0_hist_file : readable opened file with .readlines()
        The read loaded GOMC hist file with .readlines().
    gomc_box_0_hist_file : writeable opened file
        The writeable opened file, which is used to write the combined
        and compact data from the GOMC hist files.
    run_no : int
        Simulation run number

    """

    # create the combined histogram
    for i, line in enumerate(read_gomc_box_0_hist_file):
        # if the first iteration for the GOMC hist file print the 1st line
        if run_no == 1 and i == 0:
            gomc_box_0_hist_file.write('%s' % read_gomc_box_0_hist_file[i])
        elif run_no >= 1 and i >= 1:
            gomc_box_0_hist_file.write('%s' % read_gomc_box_0_hist_file[i])


def get_gomc_dist_data(read_gomc_box_0_dist_file, current_dist_dict):
    """
    This reads in the current simulation distribution (dist) data
    and adds it to the current dist data dictionary which is also
    and input variable.

    Parameters
    ----------
    read_gomc_box_0_dist_file : readable opened file with .readlines()
        The read loaded GOMC dist file with .readlines().
    current_dist_dict : the current dist dictionary while reading
    thru all the files. This is an empty dictionary when the first GOMC
    simulation is started (i.e. simulation 1). The data is added to the
    dictionary every time the next GOMC distribution (dist) data is
    input here and the new data is read (see current_dist_dict
    definition in the return variables).

    Returns
    --------
    current_dist_dict : the updated current dist dictionary after reading
    and adding the current simulations distribution (dist) data.
    """

    # create the combined distribution dictionary
    for i, line in enumerate(read_gomc_box_0_dist_file):
        split_line = line.split()
        new_key = split_line[0]
        new_value = split_line[1]

        if new_key in current_dist_dict.keys():
            current_value = current_dist_dict[new_key]
            new_value = str(int(current_value) + int(new_value))
            current_dist_dict.update({new_key: new_value})
        else:
            current_dist_dict.update({new_key: new_value})

    return current_dist_dict


def get_gomc_log_data(read_gomc_box_x_log_file, gomc_box_x_data_file, run_no, box_no,
                      e_stat_values_gomc_box_x_list=None,
                      e_stat_values_gomc_kcal_per_mol_box_x_list=None):
    """
    Extracts the GOMC log data from every run (energy and state properties),
    combining it into a list while adding the system density,
    and also keeping the exact output lines from NAMD.

    Parameters
    ----------
    read_gomc_box_x_log_file : readable opened file with .readlines()
        The read loaded namd log file with .readlines().
    gomc_box_x_data_file : writeable opened file
        The writeable opened file, which is used to write the combined
        and compact data from the GOMC log file.
    run_no : int
        Simulation run number
    box_no : int
        The simulation box number, which can only be 0 or 1
    e_stat_values_gomc_box_x_list : list, default = []
        The GOMC log data (energy and stat values) output in the
        standard GOMC units (energy = K and density = kg/m^3).
        If the default value (empty list) is not used, the
        provided list will be appended.  This needs provided not
        reading 1st GOMC simulation.
    e_stat_values_gomc_kcal_per_mol_box_x_list : list, default = None
        The GOMC log data (energy and stat values) output in the
        NAMD units (energy = kcal/mol and density = g/cm^3).
        If the default value (empty list) is not used, the
        provided list will be appended.  This needs provided not
        reading 1st GOMC simulation.

    Returns
    --------
    e_titles_gomc_box_x_iteration : list
        The energy titles of the GOMC energy data from the systems,
        log file in GOMC units (energy = K and density = kg/m^3).
    e_stat_titles_gomc_box_x_iter_list : list
        The energy titles of the GOMC energy data from the systems
        log file in GOMC units (energy = K and density = kg/m^3).
    e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list :
        The scaled (NAMD units: energy = kcal/mol and density = g/cm^3 ),
        reorgainized, and combined titles from the GOMC log file.
    e_stat_values_gomc_box_x_iteration_list :
        The GOMC log file data output from this iteration
        (GOMC units:energy = K and density = kg/m^3).
    e_stat_values_gomc_kcal_per_mol_box_x_list :
        The scaled (NAMD units: energy = kcal/mol and density = g/cm^3 ),
        reorgainized, and combined data from the GOMC log file data output
        from the flag input and whatever is added in this iteration.

    Notes
    --------
    The timesteps are rescaled so that the NAMD and GOMC data are added
    properly in order.
    """
    error_for_bad_gomc_input_file_data = "ERROR: This GOMC file output file does not contain all " \
                                         "the required information. The Energy and Stat titles/values " \
                                         "are missing from the GOMC output/log file in "\
                                         "run number {} in box {}.".format(run_no, box_no)

    if e_stat_values_gomc_box_x_list is None:
        e_stat_values_gomc_box_x_list = []
    else:
        e_stat_values_gomc_box_x_list

    if e_stat_values_gomc_kcal_per_mol_box_x_list is None:
        e_stat_values_gomc_kcal_per_mol_box_x_list = []
    else:
        e_stat_values_gomc_kcal_per_mol_box_x_list

    energy_string_label = 'ENER_{}:'.format(str(box_no))
    stat_string_label = 'STAT_{}:'.format((box_no))

    get_e_gomc_box_x_titles = True
    get_stat_box_x_titles = True

    stat_values_box_x_list = []

    for i, line in enumerate(read_gomc_box_x_log_file):
        if line.startswith('ETITLE:') is True and get_e_gomc_box_x_titles is True:
            if run_no == 1:
                gomc_box_x_data_file.write('%s' % read_gomc_box_x_log_file[i])
            e_titles_gomc_box_x_iteration = read_gomc_box_x_log_file[i]
            e_titles_gomc_box_x_iteration = e_titles_gomc_box_x_iteration.split()
            e_titles_gomc_box_x_iteration = e_titles_gomc_box_x_iteration[:]
            if get_e_gomc_box_x_titles is True:
                get_e_gomc_box_x_titles = False

        if line.startswith(energy_string_label) is True:
            e_values_gomc_box_x_iteration_list = []
            e_values_kcal_per_mol_gomc_box_x_iteration_list = []
            e_values_gomc_box_x_iteration = read_gomc_box_x_log_file[i]
            e_values_gomc_box_x_iteration = e_values_gomc_box_x_iteration.split()

            for j in range(0, len(e_values_gomc_box_x_iteration)):
                if e_titles_gomc_box_x_iteration[j] == 'ETITLE:':
                    e_values_gomc_box_x_iteration_list.append(e_values_gomc_box_x_iteration[j])
                    e_values_kcal_per_mol_gomc_box_x_iteration_list.append(e_values_gomc_box_x_iteration[j])
                elif e_titles_gomc_box_x_iteration[j] == 'STEP':
                    e_values_gomc_box_x_iteration_list.append(str(int(int(e_values_gomc_box_x_iteration[j])
                                                                      + current_step)))
                    e_values_kcal_per_mol_gomc_box_x_iteration_list.append(str(int(int(e_values_gomc_box_x_iteration[j])
                                                                                   + current_step)))
                else:
                    e_values_gomc_box_x_iteration_list.append(str(float(e_values_gomc_box_x_iteration[j]) * 1))
                    e_values_kcal_per_mol_gomc_box_x_iteration_list.append(
                        str(float(e_values_gomc_box_x_iteration[j]) * K_to_kcal_mol))

            gomc_box_x_data_file.write('%s \n' % str('\t '.join(e_values_gomc_box_x_iteration_list)))

            # GOMC_box_X_Energies_Stat_file

        if line.startswith('STITLE:') is True and get_stat_box_x_titles is True:
            if run_no == 1:
                gomc_box_x_data_file.write('%s' % read_gomc_box_x_log_file[i])
            stat_titles_box_x_iteration = read_gomc_box_x_log_file[i]
            stat_titles_box_x_iteration = stat_titles_box_x_iteration.split()
            stat_titles_box_x_iteration = stat_titles_box_x_iteration[:]
            if get_stat_box_x_titles is True:
                get_stat_box_x_titles = False

        if line.startswith(stat_string_label) is True:
            stat_values_box_x_iteration_list = []
            stat_values_box_x_iteration = read_gomc_box_x_log_file[i]
            stat_values_box_x_iteration = stat_values_box_x_iteration.split()

            for j in range(0, len(stat_values_box_x_iteration)):
                if stat_titles_box_x_iteration[j] == 'STITLE:':
                    stat_values_box_x_iteration_list.append(stat_values_box_x_iteration[j])
                elif stat_titles_box_x_iteration[j] == 'STEP':
                    stat_values_box_x_iteration_list.append(str(int(int(stat_values_box_x_iteration[j])
                                                                    + current_step)))
                    # stat_values_box_x_iteration_list.append(int(int(stat_values_box_x_iteration[j]) \
                    # + current_step))
                else:
                    stat_values_box_x_iteration_list.append(str(float(stat_values_box_x_iteration[j])))

            gomc_box_x_data_file.write('%s \n' % str('\t '.join(stat_values_box_x_iteration_list)))
            stat_values_box_x_list.append(stat_values_box_x_iteration_list)

            # combine the energy and stat data (ENER_X and STAT_X) into 1 line and remove ENER_X and STAT_X) labels
            e_stat_values_gomc_box_x_iteration_list = e_values_gomc_box_x_iteration_list[1:]
            e_stat_values_gomc_kcal_per_mol_box_x_iteration_list = e_values_kcal_per_mol_gomc_box_x_iteration_list[1:]
            for z in range(2, len(stat_values_box_x_iteration_list)):
                e_stat_values_gomc_box_x_iteration_list.append(stat_values_box_x_iteration_list[z])
                if stat_titles_box_x_iteration[z] == 'TOT_DENSITY':
                    e_stat_values_gomc_kcal_per_mol_box_x_iteration_list.append(
                        str(float(stat_values_box_x_iteration_list[z]) / 10 ** 3))
                else:
                    e_stat_values_gomc_kcal_per_mol_box_x_iteration_list.append(stat_values_box_x_iteration_list[z])

            e_stat_values_gomc_box_x_list.append(e_stat_values_gomc_box_x_iteration_list)
            e_stat_values_gomc_kcal_per_mol_box_x_list.append(e_stat_values_gomc_kcal_per_mol_box_x_iteration_list)

            # combine the energy and stat titles (ENER_X and STAT_X) into 1 line and remove ENER_X and STAT_X) labels
    try:
        e_stat_titles_gomc_box_x_iter_list = e_titles_gomc_box_x_iteration[1:]
    except:
        raise ValueError(error_for_bad_gomc_input_file_data)
    try:
        e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list = e_titles_gomc_box_x_iteration[1:]
    except:
        raise ValueError(error_for_bad_gomc_input_file_data)

    try:
        isinstance(stat_titles_box_x_iteration,list)
    except:
        raise ValueError(error_for_bad_gomc_input_file_data)

    for z in range(2, len(stat_titles_box_x_iteration)):
        e_stat_titles_gomc_box_x_iter_list.append(stat_titles_box_x_iteration[z])
        e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list.append(stat_titles_box_x_iteration[z])

    # add a pound symbol (#) before some of the titles
    if str(e_stat_titles_gomc_box_x_iter_list[0][0]) != '#':
        e_stat_titles_gomc_box_x_iter_list[0] = '#' + str(e_stat_titles_gomc_box_x_iter_list[0])

        if str(e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list[0][0]) != '#':
            e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list[0] = '#{}'.format(str(e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list[0]))

    try:
        isinstance(e_titles_gomc_box_x_iteration, list)
        isinstance(e_stat_titles_gomc_box_x_iter_list, list)
        isinstance(e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list, list)
        isinstance(e_stat_values_gomc_box_x_iteration_list, list)
        isinstance(e_stat_values_gomc_box_x_list, list)
        isinstance(e_stat_values_gomc_kcal_per_mol_box_x_list, list)
    except:
        raise ValueError(error_for_bad_gomc_input_file_data)


    return e_titles_gomc_box_x_iteration, \
           e_stat_titles_gomc_box_x_iter_list, \
           e_titles_kcal_per_mol_stat_titles_gomc_box_x_iter_list, \
           e_stat_values_gomc_box_x_iteration_list, \
           e_stat_values_gomc_box_x_list, \
           e_stat_values_gomc_kcal_per_mol_box_x_list

    # ****************************************
    # ****************************************
    # GOMC-NAMD hybrid data extraction (start)
    # ****************************************
    # ****************************************


def combine_dcd_files(engine_name,
                      combine_dcd_files_cycle_freq,
                      engine_dcd_file_name,
                      engine_directory_list,
                      path_engine_runs,
                      box_no=0):
    """
    Extracts the GOMC or NAMD dcd data from every run,
    combining it into one dcd file.

    Parameters
    ----------
    engine_name : str (only "GOMC" or "NAMD" are valid)
        The simulation engine that is chosen to chosen to have it's
        dcd files combined.
    combine_dcd_files_cycle_freq : int
        The frequency to read through the individual
        NAMD or GOMC simulations and combine them.
        Example: 1 will yield every simulations dcd file is added together
        Example: 2 will yield every other simulations dcd file is added together
    engine_dcd_file_name : str
        The dcd file name in the NAMD or GOMC individual simulation folder.
        The name must be the same for all the simulation folders.
    engine_directory_list : list
        The list of all the individial NAMD or GOMC simulation directories,
        which is located under the path_engine_runs variable.
    path_engine_runs : str
        The main folder/directory in which the NAMD or GOMC individual
        run are stored
    box_no : int
        The simulation box number, which can only be 0 or 1
    """

    # ****************************************************************
    # combine the Engine dcd files (start)
    # ****************************************************************
    # make all the  dcd filenames (with paths) a list in string form for the dcdcat
    print('INFO: Starting the dcd combining for box {} the {} simulation.'.format(str(box_no), str(path_engine_runs)))

    # need to iterate thru the dcd files if combining greater than 1000
    max_no_engine_catdcd_per_run = 1000
    engine_directory_list_with_freq = engine_directory_list[:: combine_dcd_files_cycle_freq]

    if len(engine_directory_list_with_freq) == 0:
        engine_dcd_cat_iterations = int(0)
    else:
        engine_dcd_cat_iterations = int(len(engine_directory_list_with_freq) / max_no_engine_catdcd_per_run + 1)

    engine_dcd_iter_even_name_str = 'iter_0_box_{}_{}_dcd_files.dcd'.format(str(box_no), str(engine_name))
    engine_dcd_iter_odd_name_str = 'iter_1_box_{}_{}_dcd_files.dcd'.format(str(box_no), str(engine_name))
    engine_dcd_combined_for_mod_name_str = 'combined_box_for_mod_{}_{}_dcd_files.dcd'.format(str(box_no),
                                                                                             str(engine_name))
    engine_dcd_combined_name_str = 'combined_box_{}_{}_dcd_files.dcd'.format(str(box_no), str(engine_name))

    nested_list_engine_dcd_filenames = []
    for q in range(0, engine_dcd_cat_iterations):
        dcd_cat_engine_box_x_filename_str = ''
        if q == 0:
            dcd_starting_cat_engine_box_x_filename_str = ''
        elif q % 2 == 0 and q != 0:
            dcd_starting_cat_engine_box_x_filename_str = "{}/{}".format(str(path_combined_data_folder),
                                                                        engine_dcd_iter_odd_name_str)
        elif q % 2 == 1:
            dcd_starting_cat_engine_box_x_filename_str = "{}/{}".format(str(path_combined_data_folder),
                                                                        engine_dcd_iter_even_name_str)

        start_engine_file_no = q * max_no_engine_catdcd_per_run

        if (q + 1) * max_no_engine_catdcd_per_run >= len(engine_directory_list_with_freq):
            end_engine_file_no = len(engine_directory_list_with_freq)

        else:
            end_engine_file_no = (q + 1) * max_no_engine_catdcd_per_run

        for dcd_cat_Engine_box_X_file_i in range(start_engine_file_no, end_engine_file_no, 1):
            dcd_cat_engine_box_x_filename_str += ' {}/{}/{}'.format(path_engine_runs,
                                                                    str(engine_directory_list_with_freq[dcd_cat_Engine_box_X_file_i]),
                                                                    str(engine_dcd_file_name))
        nested_list_engine_dcd_filenames.append(dcd_cat_engine_box_x_filename_str)

        if q == (engine_dcd_cat_iterations - 1):
            # need to only read the last frame in each cycle as GOMC prints the an intial (step 1) and last frame
            engine_final_iter_dcdcat_command = "{} -o {}/{} {} {}" \
                                               "".format(str(rel_path_to_combine_binary_catdcd),
                                                         str(path_combined_data_folder),
                                                         engine_dcd_combined_for_mod_name_str,
                                                         dcd_starting_cat_engine_box_x_filename_str,
                                                         nested_list_engine_dcd_filenames[q]
                                                         )

            print('engine_final_iter_dcdcat_command = {}'.format(str(engine_final_iter_dcdcat_command)))
            exec_engine_final_iter_dcdcat_command = subprocess.Popen(engine_final_iter_dcdcat_command,
                                                                     shell=True, stderr=subprocess.STDOUT)
            os.waitpid(exec_engine_final_iter_dcdcat_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

        else:
            if q == 0:
                run_engine_dcdcat_box_x_command = "{} -o {}/{} {} {}" \
                                                  "".format(str(rel_path_to_combine_binary_catdcd),
                                                            str(path_combined_data_folder),
                                                            engine_dcd_iter_even_name_str,
                                                            dcd_starting_cat_engine_box_x_filename_str,
                                                            nested_list_engine_dcd_filenames[q]
                                                            )


            elif q % 2 == 0 and q != 0:
                run_engine_dcdcat_box_x_command = "{} -o {}/{} {} {}" \
                                                  "".format(str(rel_path_to_combine_binary_catdcd),
                                                            str(path_combined_data_folder),
                                                            engine_dcd_iter_even_name_str,
                                                            dcd_starting_cat_engine_box_x_filename_str,
                                                            nested_list_engine_dcd_filenames[q]
                                                            )

            elif q % 2 == 1:
                run_engine_dcdcat_box_x_command = "{} -o {}/{} {} {}" \
                                                  "".format(str(rel_path_to_combine_binary_catdcd),
                                                            str(path_combined_data_folder),
                                                            engine_dcd_iter_odd_name_str,
                                                            dcd_starting_cat_engine_box_x_filename_str,
                                                            nested_list_engine_dcd_filenames[q]
                                                            )

            exec_engine_dcdcat_box_x_command = subprocess.Popen(run_engine_dcdcat_box_x_command,
                                                                shell=True, stderr=subprocess.STDOUT)

            os.waitpid(exec_engine_dcdcat_box_x_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

    # the combined final Engine dcd file
    if engine_name == 'GOMC':

        if get_initial_gomc_dcd == True:
            # take only the last frame from GOMC.  Now GOMC only outputs the last frame so only need (i.e., -stride 1)
            initial_engine_dcd_combined_for_mod_name_str = 'initial_box_for_mod_{}_{}_dcd_files.dcd' \
                                                           ''.format(str(box_no),
                                                                     str(engine_name)
                                                                     )
            mod_engine_dcd_combined_for_mod_name_str = 'mod_box_for_mod_{}_{}_dcd_files.dcd' \
                                                       ''.format(str(box_no),
                                                                 str(engine_name)
                                                                 )

            run_initial_engine_dcdcat_box_x_command = "{} -o {}/{} -first 1 -last 1 {}/{}/{}" \
                                                      "".format(str(rel_path_to_combine_binary_catdcd),
                                                                str(path_combined_data_folder),
                                                                initial_engine_dcd_combined_for_mod_name_str,
                                                                str(engine_name),
                                                                str(engine_directory_list[0]),
                                                                str('Output_data_BOX_0.dcd')
                                                                )

            print("run_initial_engine_dcdcat_box_x_command = " +str(run_initial_engine_dcdcat_box_x_command ))
            print("nested_list_engine_dcd_filenames " + str(nested_list_engine_dcd_filenames))
            print("engine_directory_list = " + str(engine_directory_list))

            exec_run_initial_engine_dcdcat_box_x_command = subprocess.Popen(run_initial_engine_dcdcat_box_x_command,
                                                                    shell=True,
                                                                    stderr=subprocess.STDOUT)

            os.waitpid(exec_run_initial_engine_dcdcat_box_x_command.pid, os.WSTOPPED)

            run_mod_engine_dcdcat_box_x_command = "{} -o {}/{} -first 2 -stride 2 {}/{}" \
                                                      "".format(str(rel_path_to_combine_binary_catdcd),
                                                                str(path_combined_data_folder),
                                                                mod_engine_dcd_combined_for_mod_name_str,
                                                                str(path_combined_data_folder),
                                                                engine_dcd_combined_for_mod_name_str
                                                                )

            exec_run_mod_engine_dcdcat_box_x_command = subprocess.Popen(run_mod_engine_dcdcat_box_x_command,
                                                                           shell=True,
                                                                           stderr=subprocess.STDOUT)

            os.waitpid(exec_run_mod_engine_dcdcat_box_x_command.pid, os.WSTOPPED)

            run_engine_dcdcat_box_x_command = "{} -o {}/{} {}/{} {}/{}" \
                                              "".format(str(rel_path_to_combine_binary_catdcd),
                                                        str(path_combined_data_folder),
                                                        engine_dcd_combined_name_str,
                                                        str(path_combined_data_folder),
                                                        str(initial_engine_dcd_combined_for_mod_name_str),
                                                        str(path_combined_data_folder),
                                                        str(mod_engine_dcd_combined_for_mod_name_str)
                                                        )

        else:
            # take only the last frame from GOMC.  Now GOMC only outputs the last frame so only need (i.e., -stride 1)
            run_engine_dcdcat_box_x_command = "{} -o {}/{} -first 2 -stride 2 {}/{}" \
                                                      "".format(str(rel_path_to_combine_binary_catdcd),
                                                                str(path_combined_data_folder),
                                                                engine_dcd_combined_name_str,
                                                                str(path_combined_data_folder),
                                                                engine_dcd_combined_for_mod_name_str
                                                                )

    # take only the last frame from NAMD.  NAMD only outputs the last frame so only need (i.e., -stride 1)
    elif engine_name == 'NAMD':
        run_engine_dcdcat_box_x_command = "{} -o {}/{} -stride 1 {}/{}" \
                                                  "".format(str(rel_path_to_combine_binary_catdcd),
                                                            str(path_combined_data_folder),
                                                            engine_dcd_combined_name_str,
                                                            str(path_combined_data_folder),
                                                            engine_dcd_combined_for_mod_name_str
                                                            )
    else:
        warn('the variable engine_name in the function combine_dcd_files can only be a string'
             ' NAMD or GOMC.')

    exec_run_engine_dcdcat_box_x_command = subprocess.Popen(run_engine_dcdcat_box_x_command,
                                                            shell=True,
                                                            stderr=subprocess.STDOUT)

    os.waitpid(exec_run_engine_dcdcat_box_x_command.pid, os.WSTOPPED)

    run_gomc_rm_gomc_final_iter_dcdcat_command = "rm {}/{}".format(str(path_combined_data_folder),
                                                                   engine_dcd_combined_for_mod_name_str)

    exec_gomc_final_iter_dcdcat_command = subprocess.Popen(run_gomc_rm_gomc_final_iter_dcdcat_command,
                                                           shell=True,
                                                           stderr=subprocess.STDOUT)
    os.waitpid(exec_gomc_final_iter_dcdcat_command.pid, os.WSTOPPED)

    # remove the even iteration Engine dcd file
    run_engine_rm_dcd_iter_even_box_x_command = "rm {}/{}".format(str(path_combined_data_folder),
                                                                  engine_dcd_iter_even_name_str)

    exec_engine_rm_dcd_iter_even_box_x_command = subprocess.Popen(run_engine_rm_dcd_iter_even_box_x_command,
                                                                  shell=True,
                                                                  stderr=subprocess.STDOUT)

    os.waitpid(exec_engine_rm_dcd_iter_even_box_x_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

    # remove the odd iteration Engine dcd file
    run_engine_rm_dcd_iter_odd_box_x_command = "rm {}/{}".format(str(path_combined_data_folder),
                                                                 engine_dcd_iter_odd_name_str)

    exec_engine_rm_dcd_iter_odd_box_x_command = subprocess.Popen(run_engine_rm_dcd_iter_odd_box_x_command,
                                                                 shell=True,
                                                                 stderr=subprocess.STDOUT)

    os.waitpid(exec_engine_rm_dcd_iter_odd_box_x_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

    run_cp_gomc_box_x_psf_command = "cp {}/{}/{} {}/{}".format(str(path_gomc_runs),
                                                               str(gomc_directory_list[0]),
                                                               "Output_data_merged.psf",
                                                               str(path_combined_data_folder),
                                                               "Output_data_merged.psf"
                                                               )


    exec_cp_gomc_box_x_psf_command = subprocess.Popen(run_cp_gomc_box_x_psf_command,
                                                      shell=True, stderr=subprocess.STDOUT)
    os.waitpid(exec_cp_gomc_box_x_psf_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

    # remove the initial and mod (ever run not the start of run dcd) files
    if engine_name == 'GOMC':
        if get_initial_gomc_dcd == True:
            run_initial_engine_rm_dcd = "rm {}/{}".format(str(path_combined_data_folder),
                                                          str(initial_engine_dcd_combined_for_mod_name_str)
                                                          )
            exec_initial_engine_rm_dcd_command = subprocess.Popen(run_initial_engine_rm_dcd,
                                                                  shell=True,
                                                                  stderr=subprocess.STDOUT
                                                                  )
            os.waitpid(exec_initial_engine_rm_dcd_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

            run_mod_engine_rm_dcd = "rm {}/{}".format(str(path_combined_data_folder),
                                                      str(mod_engine_dcd_combined_for_mod_name_str)
                                                      )
            exec_mod_engine_rm_dcd_command = subprocess.Popen(run_mod_engine_rm_dcd,
                                                              shell=True,
                                                              stderr=subprocess.STDOUT
                                                              )
            os.waitpid(exec_mod_engine_rm_dcd_command.pid, os.WSTOPPED)  # pauses python until GOMC sim done

    print('INFO: Finished the dcd combining for box {} the {} simulation '.format(str(box_no), str(path_engine_runs)))


if simulation_engine_options == 'Hybrid':

    # ****************************************************************
    # combine the NAMD dcd files (start)
    # ****************************************************************

    if combine_namd_dcd_file is True:
        if simulation_type in ['NVT', 'NPT']:
            namd_name = 'NAMD'
            namd_directory_list = namd_directory_a_list
            namd_directory_dcd_filnames = 'namdOut.dcd'
            namd_path_engine_runs = path_namd_runs
            namd_box_no = 0
            combine_dcd_files(namd_name, combine_dcd_files_cycle_freq,
                              namd_directory_dcd_filnames, namd_directory_list,
                              namd_path_engine_runs,
                              namd_box_no)

        else:
            warn('WARNING: The NAMD dcd files can not be combined as they have different number or atoms '
                 'in the GCMC and GEMC simulations. ')

    # make all the box 0 and 1 dcd filenames (with paths) a list in string form for the dcdcat GOMC program'
    if combine_gomc_dcd_file is True:

        gomc_name = 'GOMC'
        gomc_directory_list = gomc_directory_list
        gomc_directory_dcd_filnames = 'Output_data_BOX_0.dcd'
        gomc_path_engine_runs = path_gomc_runs
        gomc_box_no = 0
        combine_dcd_files(gomc_name, combine_dcd_files_cycle_freq,
                          gomc_directory_dcd_filnames, gomc_directory_list,
                          gomc_path_engine_runs,
                          gomc_box_no)

        if simulation_type in ["GEMC"]:
            gomc_name = 'GOMC'
            gomc_directory_list = gomc_directory_list
            gomc_directory_dcd_filnames = 'Output_data_BOX_1.dcd'
            gomc_path_engine_runs = path_gomc_runs
            gomc_box_no = 1
            combine_dcd_files(gomc_name, combine_dcd_files_cycle_freq,
                              gomc_directory_dcd_filnames, gomc_directory_list,
                              gomc_path_engine_runs,
                              gomc_box_no)

    print("INFO: Started all data combined from the log files for the NAMD-GOMC hybrid simulations "
          "and exported into muliple files and types")
    current_step = 0
    # analyze and combine the data for the GOMC and NAMD simulations
    for run_no in range(0, total_sims_namd_gomc):

        if run_no % 2 == 0:  # NAMD's run time. :# NAMD's staring run.  NAMD starts simulation series with energy minimization
            # *************************************
            # get final system energies for box 0 and 1 (start)
            # ***********************initial_Energies**************
            namd_interation = int(run_no/2)
            no_namd_box_0_directory = str(namd_directory_a_list[namd_interation])

            read_namd_box_0_log_file = open(full_path_to_namd_data_folder + "/" + no_namd_box_0_directory
                                            + "/" + 'out.dat', 'r').readlines()

            for i, line in enumerate(read_namd_box_0_log_file):
                split_line = line.split()
                if line.startswith('TCL:') is True:
                    if split_line[0] == 'TCL:' and len(split_line) >= 5:
                        if split_line[1] == 'Minimizing' and split_line[2] == 'for' and split_line[4] == 'steps':
                            namd_minimizing_steps_box_0 = float(split_line[3])
                            current_step += (-1 * namd_minimizing_steps_box_0)

            if run_no == 0:
                e_titles_namd_box_0_iteration, \
                e_titles_namd_box_0_density_iteration, \
                e_values_namd_box_0_iteration, \
                e_values_namd_box_0_density_list, \
                e_property_values_namd_box_0_list = get_namd_log_data(read_namd_box_0_log_file,
                                                                      namd_box_0_data_file,
                                                                      run_no)

            else:
                e_titles_namd_box_0_iteration, \
                e_titles_namd_box_0_density_iteration, \
                e_values_namd_box_0_iteration, \
                e_values_namd_box_0_density_list, \
                e_property_values_namd_box_0_list = get_namd_log_data(read_namd_box_0_log_file,
                                                                       namd_box_0_data_file,
                                                                       run_no,
                                                                       e_values_namd_box_x_density_list=
                                                                                      e_values_namd_box_0_density_list,
                                                                       e_titles_namd_box_x_iteration=
                                                                                      e_titles_namd_box_0_iteration,
                                                                       e_titles_namd_box_x_density_iteration=
                                                                                      e_titles_namd_box_0_density_iteration)
            # note NAMD energy units in kcal/mol (no modifications required)
            # generate energy file data for box 1
            if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:

                namd_interation = str(namd_directory_b_list[namd_interation])

                read_namd_box_1_log_file = open(full_path_to_namd_data_folder + "/" + namd_interation
                                                + "/" + 'out.dat', 'r').readlines()

                if run_no == 0:
                    e_titles_namd_box_1_iteration, \
                    e_titles_namd_box_1_density_iteration, \
                    e_values_namdD_box_1_iteration, \
                    e_values_namd_box_1_density_iteration, \
                    e_values_namd_box_1_density_list, \
                    e_property_values_namd_box_1_list = get_namd_log_data(read_namd_box_1_log_file,
                                                                          namd_box_1_data_file,
                                                                          run_no)
                else:
                    e_titles_namd_box_1_iteration, \
                    e_titles_namd_box_1_density_iteration, \
                    e_values_namdD_box_1_iteration, \
                    e_values_namd_box_1_density_iteration, \
                    e_values_namd_box_1_density_list, \
                    e_property_values_namd_box_1_list = get_namd_log_data(read_namd_box_1_log_file,
                                                                          namd_box_1_data_file,
                                                                          run_no,
                                                                          e_values_namd_box_x_density_list=
                                                                                              e_values_namd_box_1_density_list,
                                                                          e_titles_namd_box_x_iteration=
                                                                                              e_titles_namd_box_1_iteration,
                                                                          e_titles_namd_box_x_density_iteration=
                                                                                              e_titles_namd_box_1_density_iteration)

            current_step = int(e_property_values_namd_box_0_list[-1][1])
            # print('NAMD current_step = ' + str(int(current_step)))
            # *************************************
            # get final system energies for box 0 and 1 (start)
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
        elif run_no % 2 == 1:
            # GOMC's run time.  GOMC starts simulation series
            gomc_interation = int(run_no/2)
            no_gomc_directory = str(gomc_directory_list[gomc_interation])

            read_gomc_box_0_log_file = open("{}/{}/{}".format(full_path_to_gomc_data_folder,
                                                              no_gomc_directory,
                                                              'out.dat')
                                            , 'r').readlines()

            # get box 0 data
            box_no_0 = int(0)
            if run_no == 1 :
                e_titles_gomc_box_0_iteration, \
                e_titles_Stat_titles_gomc_box_0_iteration_list, \
                e_titles_kcal_per_mol_stat_titles_gomc_box_0_iteration_list, \
                e_stat_values_gomc_box_0_iteration_list, \
                e_stat_values_gomc_box_0_list, \
                e_stat_values_gomc_kcal_per_mol_box_0_list = get_gomc_log_data(read_gomc_box_0_log_file,
                                                                               gomc_box_0_data_file,
                                                                               run_no, box_no_0)
            else:
                e_titles_gomc_box_0_iteration, \
                e_titles_Stat_titles_gomc_box_0_iteration_list, \
                e_titles_kcal_per_mol_stat_titles_gomc_box_0_iteration_list, \
                e_stat_values_gomc_box_0_iteration_list, \
                e_stat_values_gomc_box_0_list, \
                e_stat_values_gomc_kcal_per_mol_box_0_list = get_gomc_log_data(read_gomc_box_0_log_file,
                                                                               gomc_box_0_data_file,
                                                                               run_no, box_no_0,
                                                                               e_stat_values_gomc_box_x_list=
                                                                               e_stat_values_gomc_box_0_list,
                                                                               e_stat_values_gomc_kcal_per_mol_box_x_list=
                                                                               e_stat_values_gomc_kcal_per_mol_box_0_list)

            # note GOMC energy units in kcal/mol
            # generate energy and system file data for box 1
            if simulation_type in ["GEMC"]:
                read_gomc_box_1_log_file = open("{}/{}/{}".format(full_path_to_gomc_data_folder,
                                                              no_gomc_directory,
                                                              'out.dat')
                                            , 'r').readlines()

                box_no_1 = int(1)
                if run_no == 1:
                    e_titles_gomc_box_1_iteration, \
                    e_titles_stat_titles_gomc_box_1_iteration_list, \
                    e_titles_kcal_per_mol_stat_titles_gomc_box_1_iteration_list, \
                    e_stat_values_gomc_box_1_iteration_list, \
                    e_stat_values_gomc_box_1_list, \
                    e_stat_values_gomc_kcal_per_mol_box_1_list = get_gomc_log_data(read_gomc_box_1_log_file,
                                                                                   gomc_box_1_data_file,
                                                                                   run_no, box_no_1)
                else:
                    e_titles_gomc_box_1_iteration, \
                    e_titles_stat_titles_gomc_box_1_iteration_list, \
                    e_titles_kcal_per_mol_stat_titles_gomc_box_1_iteration_list, \
                    e_stat_values_gomc_box_1_iteration_list, \
                    e_stat_values_gomc_box_1_list, \
                    e_stat_values_gomc_kcal_per_mol_box_1_list  = get_gomc_log_data(read_gomc_box_1_log_file,
                                                                                    gomc_box_1_data_file,
                                                                                    run_no, box_no_1,
                                                                                    e_stat_values_gomc_box_x_list=
                                                                                    e_stat_values_gomc_box_1_list,
                                                                                    e_stat_values_gomc_kcal_per_mol_box_x_list=
                                                                                    e_stat_values_gomc_kcal_per_mol_box_1_list)

            # get histogram data
            if simulation_type in ["GCMC"]:
                read_gomc_box_0_hist_file = open("{}/{}/{}".format(full_path_to_gomc_data_folder,
                                                                   no_gomc_directory,
                                                                   'his1a.dat')
                                                 , 'r').readlines()

                box_no_0 = 0
                # output the combined histogram data
                get_gomc_hist_data(read_gomc_box_0_hist_file,
                                   gomc_box_0_hist_file,
                                   run_no)

                full_path_dist_files_only_list = glob.glob("{}/{}/{}".format(full_path_to_gomc_data_folder,
                                                                             no_gomc_directory,
                                                                             "*dis1a.dat" )
                                                           )

                for dist_i in range(0, len(full_path_dist_files_only_list)):
                    read_gomc_box_0_dist_file = open("{}".format(full_path_dist_files_only_list[dist_i])
                                                     , 'r').readlines()

                    dict_of_current_dist_dicts[dist_i + 1] = get_gomc_dist_data(read_gomc_box_0_dist_file,
                                                                                dict_of_current_dist_dicts[dist_i + 1])

            current_step = int(e_stat_values_gomc_box_0_iteration_list[0])
            # print('GOMC current_step = ' + str(int(current_step)))
        # *************************************************
        # *************************************************
        # RUN THE NAMD PORTION of the CODE (End)
        # *************************************************
        # *************************************************

    # print the combined dist file from the dict_of_current_dist_dicts
    if simulation_type in ["GCMC"]:
        residue_or_mol_no_dist_key_list = list(dict_of_current_dist_dicts.keys())
        no_residue_mol_dist = len(residue_or_mol_no_dist_key_list)
        for residue_j in residue_or_mol_no_dist_key_list:
            gomc_box_0_dist_filename_iter = "{}/GOMC_dist_data_box_0_res_or_mol_no_{}.txt" \
                                            "".format(full_path_to_combined_data_folder,
                                                      str(residue_j))
            gomc_box_0_dist_file_iter = open(gomc_box_0_dist_filename_iter, 'w')
            res_dict_of_current_dist_dicts = dict_of_current_dist_dicts[residue_j]
            sorted_current_dist_key_list = sorted(res_dict_of_current_dist_dicts)
            for key in sorted_current_dist_key_list:
                gomc_box_0_dist_file_iter.write("{} {}\n".format(key, res_dict_of_current_dist_dicts[key]))

    e_values_density_namd_box_0_df = pd.DataFrame(data=e_values_namd_box_0_density_list,
                                                  columns=e_titles_namd_box_0_density_iteration)
    e_values_density_namd_box_0_df.to_csv(namd_box_0_data_density_filename, sep="	", index=False)

    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        e_values_density_namd_box_1_df = pd.DataFrame(data=e_values_namd_box_1_density_list,
                                                      columns=e_titles_namd_box_1_density_iteration)
        e_values_density_namd_box_1_df.to_csv(namd_box_1_data_density_filename, sep="	", index=False)

    e_stat_gomc_box_0_df = pd.DataFrame(data=e_stat_values_gomc_box_0_list,
                                        columns=e_titles_Stat_titles_gomc_box_0_iteration_list)
    e_stat_gomc_box_0_df.to_csv(gomc_box_0_energies_stat_filename, sep="	", index=False)

    e_stat_kcal_per_mol_gomc_box_0_df = pd.DataFrame(data=e_stat_values_gomc_kcal_per_mol_box_0_list,
                                                     columns=e_titles_kcal_per_mol_stat_titles_gomc_box_0_iteration_list)
    e_stat_kcal_per_mol_gomc_box_0_df.to_csv(gomc_box_0_energies_stat_kcal_per_mol_filename, sep="	", index=False)

    if simulation_type in ["GEMC"]:
        e_stat_gomc_box_1_df = pd.DataFrame(data=e_stat_values_gomc_box_1_list,
                                            columns=e_titles_stat_titles_gomc_box_1_iteration_list)
        e_stat_gomc_box_1_df.to_csv(gomc_box_1_energies_stat_filename, sep="	", index=False)
        e_stat_kcal_per_mol_gomc_box_1_df = pd.DataFrame(data=e_stat_values_gomc_kcal_per_mol_box_1_list,
                                                         columns=e_titles_kcal_per_mol_stat_titles_gomc_box_1_iteration_list)
        e_stat_kcal_per_mol_gomc_box_1_df.to_csv(gomc_box_1_energies_stat_kcal_per_mol_filename, sep="	", index=False)

    # ****************************************
    # write the combined NAMD and GOMC data  (Start)
    # ****************************************

    e_values_density_namd_box_0_STEP_list = e_values_density_namd_box_0_df.loc[:, '#TS'].tolist()
    # add 0.1 to the NAMD modified timestep for easy sorting later
    e_values_density_namd_box_0_MOD_STEP_list = [str(float(i) + 0.2) for i in e_values_density_namd_box_0_STEP_list]
    e_values_density_namd_box_0_ENGINE_list = ["NAMD" for i in e_values_density_namd_box_0_STEP_list]
    e_values_density_namd_box_0_TOTAL_POT_list = e_values_density_namd_box_0_df.loc[:, 'POTENTIAL'].tolist()
    e_values_density_namd_box_0_TOTAL_ELECT_list = e_values_density_namd_box_0_df.loc[:, 'ELECT'].tolist()
    e_values_density_namd_box_0_TOTAL_VDW_list = e_values_density_namd_box_0_df.loc[:, 'VDW'].tolist()
    e_values_density_namd_box_0_TOTAL_VDW_plus_ELECT_list = [float(e_values_density_namd_box_0_TOTAL_VDW_list[k_i]) +
                                                             float(e_values_density_namd_box_0_TOTAL_ELECT_list[k_i])
                                                             for k_i in range(0, len(e_values_density_namd_box_0_TOTAL_VDW_list))]
    e_values_density_namd_box_0_PRESSURE_list = e_values_density_namd_box_0_df.loc[:, 'PRESSURE'].tolist()
    e_values_density_namd_box_0_VOLUME_list = e_values_density_namd_box_0_df.loc[:, 'VOLUME'].tolist()
    e_values_density_namd_box_0_DENSITY_list = e_values_density_namd_box_0_df.loc[:, 'DENSITY'].tolist()

    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        e_values_density_namd_box_1_STEP_list = e_values_density_namd_box_1_df.loc[:, '#TS'].tolist()
        # add 0.1 to the NAMD modified timestep for easy sorting later
        e_values_density_namd_box_1_MOD_STEP_list = [str(float(i) + 0.2) for i in e_values_density_namd_box_1_STEP_list]
        e_values_density_namd_box_1_ENGINE_list = ["NAMD" for i in e_values_density_namd_box_1_STEP_list]
        e_values_density_namd_box_1_TOTAL_POT_list = e_values_density_namd_box_1_df.loc[:, 'POTENTIAL'].tolist()
        e_values_density_namd_box_1_TOTAL_ELECT_list = e_values_density_namd_box_1_df.loc[:, 'ELECT'].tolist()
        e_values_density_namd_box_1_TOTAL_VDW_list = e_values_density_namd_box_1_df.loc[:, 'VDW'].tolist()
        e_values_density_namd_box_1_TOTAL_VDW_plus_ELECT_list = [float(e_values_density_namd_box_1_TOTAL_VDW_list[k_i]) +
                                                                 float(e_values_density_namd_box_1_TOTAL_ELECT_list[k_i])
                                                                 for k_i in range(0, len(e_values_density_namd_box_1_TOTAL_VDW_list))]
        e_values_density_namd_box_1_PRESSURE_list = e_values_density_namd_box_1_df.loc[:, 'PRESSURE'].tolist()
        e_values_density_namd_box_1_PRESSURE_list = e_values_density_namd_box_1_df.loc[:, 'PRESSURE'].tolist()
        e_values_density_namd_box_1_VOLUME_list = e_values_density_namd_box_1_df.loc[:, 'VOLUME'].tolist()
        e_values_density_namd_box_1_DENSITY_list = e_values_density_namd_box_1_df.loc[:, 'DENSITY'].tolist()

    e_values_density_gomc_box_0_STEP_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, '#STEP'].tolist()
    # add 0.4 or 0.2 to the GOMC modified timestep for easy sorting later
    e_values_density_gomc_box_0_MOD_STEP_list = []
    for i in range(0, len(e_values_density_gomc_box_0_STEP_list)):
        if i % 2 == 1:
            e_values_density_gomc_box_0_MOD_STEP_iteration = str(float(e_values_density_gomc_box_0_STEP_list[i]) + 0.4 / 4)
        else:
            e_values_density_gomc_box_0_MOD_STEP_iteration = str(float(e_values_density_gomc_box_0_STEP_list[i]) + 0.4)
        e_values_density_gomc_box_0_MOD_STEP_list.append(e_values_density_gomc_box_0_MOD_STEP_iteration)
    e_values_density_gomc_box_0_ENGINE_list = ["GOMC" for i in e_values_density_gomc_box_0_STEP_list]
    e_values_density_gomc_box_0_TOTAL_POT_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOTAL'].tolist()
    e_values_density_gomc_box_0_TOTAL_ELECT_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOTAL_ELECT'].tolist()
    try:
        e_values_density_gomc_box_0_PRESSURE_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'PRESSURE'].tolist()
    except:
        e_values_density_gomc_box_0_PRESSURE_list = ['NA'
                                                     for k_i in
                                                     range(0, len(e_values_density_gomc_box_0_STEP_list))]

    if simulation_type in ["GCMC", 'NVT']:
        # use NAMD volume for GCMC and NVT since GOMC is not outputting it
        NAMD_Volume_for_NVT_or_GCMC_box_0 = e_values_density_namd_box_0_VOLUME_list[0]
        e_values_density_gomc_box_0_VOLUME_list = [NAMD_Volume_for_NVT_or_GCMC_box_0
                                                   for i in e_values_density_gomc_box_0_STEP_list]
    else:
        try:
            e_values_density_gomc_box_0_VOLUME_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'VOLUME'].tolist()
        except:
            e_values_density_gomc_box_0_VOLUME_list = ['NA'
                                                       for k_i in
                                                       range(0, len(e_values_density_gomc_box_0_TOTAL_POT_list))]

    e_values_density_gomc_box_0_DENSITY_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOT_DENSITY'].tolist()
    e_values_density_gomc_box_0_INTRA_NB_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'INTRA(NB)'].tolist()
    e_values_density_gomc_box_0_INTER_LJ_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'INTER(LJ)'].tolist()
    e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list = []
    for i in range(0, len(e_values_density_gomc_box_0_INTRA_NB_list)):
        e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list.append(float(e_values_density_gomc_box_0_INTRA_NB_list[i])
                                                                     + float(e_values_density_gomc_box_0_INTER_LJ_list[i])
                                                                     + float(e_values_density_gomc_box_0_TOTAL_ELECT_list[i])
                                                                     )

    if simulation_type in ["GEMC"]:
        e_values_density_gomc_box_1_STEP_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, '#STEP'].tolist()
        # add 0.4 or 0.2 to the GOMC modified timestep for easy sorting later
        e_values_density_gomc_box_1_MOD_STEP_list = []
        for i in range(0, len(e_values_density_gomc_box_1_STEP_list)):
            if i % 2 == 1:
                e_values_density_gomc_box_1_MOD_STEP_iteration = str(float(e_values_density_gomc_box_1_STEP_list[i])
                                                                     + 0.4/4)
            else:
                e_values_density_gomc_box_1_MOD_STEP_iteration = str(float(e_values_density_gomc_box_1_STEP_list[i])
                                                                     + 0.4)
            e_values_density_gomc_box_1_MOD_STEP_list.append(e_values_density_gomc_box_1_MOD_STEP_iteration)

        e_values_density_gomc_box_1_ENGINE_list = ["GOMC" for i in e_values_density_gomc_box_1_STEP_list]
        e_values_density_gomc_box_1_TOTAL_POT_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOTAL'].tolist()
        e_values_density_gomc_box_1_TOTAL_ELECT_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOTAL_ELECT'].tolist()
        e_values_density_gomc_box_1_PRESSURE_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'PRESSURE'].tolist()
        try:
            e_values_density_gomc_box_1_PRESSURE_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'PRESSURE'].tolist()
        except:
            e_values_density_gomc_box_1_PRESSURE_list = ['NA'
                                                         for k_i in
                                                         range(0, len(e_values_density_gomc_box_1_STEP_list))]

        if simulation_type in ["GCMC", 'NVT']:
            # use NAMD volume for GCMC and NVT since GOMC is not outputting it
            NAMD_Volume_for_NVT_or_GCMC_box_1 = e_values_density_namd_box_1_VOLUME_list[0]
            e_values_density_gomc_box_1_VOLUME_list = [NAMD_Volume_for_NVT_or_GCMC_box_1
                                                       for i in e_values_density_gomc_box_1_STEP_list]
        else:
            try:
                e_values_density_gomc_box_1_VOLUME_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'VOLUME'].tolist()
            except:
                e_values_density_gomc_box_1_VOLUME_list = ['NA'
                                                           for k_i in
                                                           range(0, len(e_values_density_gomc_box_1_TOTAL_POT_list))]

        e_values_density_gomc_box_1_DENSITY_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOT_DENSITY'].tolist()
        e_values_density_gomc_box_1_INTRA_NB_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'INTRA(NB)'].tolist()
        e_values_density_gomc_box_1_INTER_LJ_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'INTER(LJ)'].tolist()
        e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list = []
        for i in range(0, len(e_values_density_gomc_box_1_INTRA_NB_list)):
            e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list.append(float(e_values_density_gomc_box_1_INTRA_NB_list[i])
                                                                         + float(e_values_density_gomc_box_1_INTER_LJ_list[i])
                                                                         + float(e_values_density_gomc_box_1_TOTAL_ELECT_list[i])
                                                                         )

    # ****************************************
    # write the combined NAMD and GOMC data for box 0  (Start)
    # ****************************************

    # combine Engine data
    combined_MOD_STEP_box_0 = []
    # combine MOD_STEP data
    for i in range(0, len(e_values_density_namd_box_0_MOD_STEP_list)):
        combined_MOD_STEP_box_0.append(float(e_values_density_namd_box_0_MOD_STEP_list[i]))
    for i in range(0, len(e_values_density_gomc_box_0_MOD_STEP_list)):
        combined_MOD_STEP_box_0.append(float(e_values_density_gomc_box_0_MOD_STEP_list[i]))

    combined_ENGINE_box_0 = e_values_density_namd_box_0_ENGINE_list + e_values_density_gomc_box_0_ENGINE_list
    combined_STEP_box_0 = e_values_density_namd_box_0_STEP_list + e_values_density_gomc_box_0_STEP_list
    combined_TOTAL_POT_box_0 = e_values_density_namd_box_0_TOTAL_POT_list + e_values_density_gomc_box_0_TOTAL_POT_list
    combined_TOTAL_ELECT_box_0 = e_values_density_namd_box_0_TOTAL_ELECT_list + e_values_density_gomc_box_0_TOTAL_ELECT_list
    combined_TOTAL_VDW_plus_ELECT_box_0 = e_values_density_namd_box_0_TOTAL_VDW_plus_ELECT_list + e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list
    combined_PRESSURE_box_0 = e_values_density_namd_box_0_PRESSURE_list + e_values_density_gomc_box_0_PRESSURE_list
    combined_VOLUME_box_0 = e_values_density_namd_box_0_VOLUME_list + e_values_density_gomc_box_0_VOLUME_list
    combined_DENSITY_box_0 = e_values_density_namd_box_0_DENSITY_list + e_values_density_gomc_box_0_DENSITY_list

    combined_data_box_0_df = pd.DataFrame({
        "#ENGINE": combined_ENGINE_box_0,
        "MOD_STEP": combined_MOD_STEP_box_0,
        "STEP": combined_STEP_box_0,
        'TOTAL_POT': combined_TOTAL_POT_box_0,
        'TOTAL_ELECT': combined_TOTAL_ELECT_box_0,
        'TOTAL_VDW_plus_ELECT': combined_TOTAL_VDW_plus_ELECT_box_0,
        'PRESSURE': combined_PRESSURE_box_0,
        'VOLUME': combined_VOLUME_box_0,
        'DENSITY':  combined_DENSITY_box_0
    })
    combined_data_sorted_box_0_df = combined_data_box_0_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
    combined_data_sorted_box_0_df.drop("MOD_STEP", axis=1, inplace=True)
    combined_data_sorted_box_0_df.to_csv(combined_box_0_data_filename, sep="	", index=False)
    # ****************************************
    # write the combined NAMD and GOMC data for box 0  (Start)
    # ****************************************

    # ****************************************
    # write the combined NAMD and GOMC data for box 1  (Start)
    # ****************************************

    # combine Engine data
    if simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is False:
        combined_MOD_STEP_box_1 = []
        # combine MOD_STEP data
        for i in range(0, len(e_values_density_namd_box_1_MOD_STEP_list)):
            combined_MOD_STEP_box_1.append(float(e_values_density_namd_box_1_MOD_STEP_list[i]))
        for i in range(0, len(e_values_density_gomc_box_1_MOD_STEP_list)):
            combined_MOD_STEP_box_1.append(float(e_values_density_gomc_box_1_MOD_STEP_list[i]))

        combined_ENGINE_box_1 = e_values_density_namd_box_1_ENGINE_list + e_values_density_gomc_box_1_ENGINE_list
        combined_STEP_box_1 = e_values_density_namd_box_1_STEP_list + e_values_density_gomc_box_1_STEP_list
        combined_TOTAL_POT_box_1 = e_values_density_namd_box_1_TOTAL_POT_list + e_values_density_gomc_box_1_TOTAL_POT_list
        combined_TOTAL_ELECT_box_1 = e_values_density_namd_box_1_TOTAL_ELECT_list + e_values_density_gomc_box_1_TOTAL_ELECT_list
        combined_TOTAL_VDW_plus_ELECT_box_1 = e_values_density_namd_box_1_TOTAL_VDW_plus_ELECT_list + e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list
        combined_PRESSURE_box_1 = e_values_density_namd_box_1_PRESSURE_list + e_values_density_gomc_box_1_PRESSURE_list
        combined_VOLUME_box_1 = e_values_density_namd_box_1_VOLUME_list + e_values_density_gomc_box_1_VOLUME_list
        combined_DENSITY_box_1 = e_values_density_namd_box_1_DENSITY_list + e_values_density_gomc_box_1_DENSITY_list

        combined_data_box_1_df = pd.DataFrame({
            "#ENGINE": combined_ENGINE_box_1,
            "MOD_STEP": combined_MOD_STEP_box_1,
            "STEP": combined_STEP_box_1,
            'TOTAL_POT': combined_TOTAL_POT_box_1,
            'TOTAL_ELECT': combined_TOTAL_ELECT_box_1,
            'TOTAL_VDW_plus_ELECT': combined_TOTAL_VDW_plus_ELECT_box_1,
            'PRESSURE': combined_PRESSURE_box_1,
            'VOLUME': combined_VOLUME_box_1,
            'DENSITY':  combined_DENSITY_box_1
        })
        combined_data_sorted_box_1_df = combined_data_box_1_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
        combined_data_sorted_box_1_df.drop("MOD_STEP", axis=1, inplace=True)
        combined_data_sorted_box_1_df.to_csv(combined_box_1_data_filename, sep="	", index=False)

    elif simulation_type in ["GEMC"] and only_use_box_0_for_namd_for_gemc is True:
        combined_MOD_STEP_box_1 = []
        # combine MOD_STEP data
        for i in range(0, len(e_values_density_gomc_box_1_MOD_STEP_list)):
            combined_MOD_STEP_box_1.append(float(e_values_density_gomc_box_1_MOD_STEP_list[i]))

        combined_ENGINE_box_1 = e_values_density_gomc_box_1_ENGINE_list
        combined_STEP_box_1 = e_values_density_gomc_box_1_STEP_list
        combined_TOTAL_POT_box_1 = e_values_density_gomc_box_1_TOTAL_POT_list
        combined_TOTAL_ELECT_box_1 = e_values_density_gomc_box_1_TOTAL_ELECT_list
        combined_TOTAL_VDW_plus_ELECT_box_1 = e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list
        combined_PRESSURE_box_1 = e_values_density_gomc_box_1_PRESSURE_list
        combined_VOLUME_box_1 = e_values_density_gomc_box_1_VOLUME_list
        combined_DENSITY_box_1 = e_values_density_gomc_box_1_DENSITY_list

        combined_data_box_1_df = pd.DataFrame({
            "#ENGINE": combined_ENGINE_box_1,
            "MOD_STEP": combined_MOD_STEP_box_1,
            "STEP": combined_STEP_box_1,
            'TOTAL_POT': combined_TOTAL_POT_box_1,
            'TOTAL_ELECT': combined_TOTAL_ELECT_box_1,
            'TOTAL_VDW_plus_ELECT': combined_TOTAL_VDW_plus_ELECT_box_1,
            'PRESSURE': combined_PRESSURE_box_1,
            'DENSITY':  combined_DENSITY_box_1
        })

        combined_data_sorted_box_1_df = combined_data_box_1_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
        combined_data_sorted_box_1_df.drop("MOD_STEP", axis=1, inplace=True)
        combined_data_sorted_box_1_df.to_csv(combined_box_1_data_filename, sep="	", index=False)

    # ****************************************
    # write the combined NAMD and GOMC data for box 1  (end)
    # ****************************************

    # ****************************************
    # write the combined NAMD and GOMC data  (end)
    # ****************************************
    print("INFO: Finished all data combined for the NAMD-GOMC hybrid simulations and "
          "exported into muliple files and types")

    # ****************************************
    # ****************************************
    # GOMC-NAMD hybrid data extraction (end)
    # ****************************************
    # ****************************************

    # ****************************************
    # ****************************************
    # GOMC only data extraction (Start)
    # ****************************************
    # ****************************************
elif simulation_engine_options == 'GOMC-only':

    run_no = 1  # run number is always 1
    current_step = 0

    print("INFO: Started all data extraction for GOMC-only runs and exported into muliple files and types")

    read_gomc_box_0_log_file = open(gomc_or_namd_only_log_filename, 'r').readlines()
    # get box 0 data
    box_no_0 = int(0)

    e_titles_gomc_box_0_iteration, \
    e_titles_stat_titles_gomc_box_0_iteration_list, \
    e_titles_kcal_per_mol_stat_titles_gomc_box_0_iteration_list, \
    e_stat_values_gomc_box_0_iteration_list, \
    e_stat_values_gomc_box_0_list, \
    e_stat_values_gomc_kcal_per_mol_box_0_list = get_gomc_log_data(read_gomc_box_0_log_file,
                                                      gomc_box_0_data_file,
                                                      run_no,
                                                      box_no_0
                                                      )

    # note GOMC energy units in kcal/mol
    # generate energy and system file data for box 1
    print('simulation_type = ' +str(simulation_type))
    if simulation_type in ["GEMC"]:
        read_gomc_box_1_log_file = open(gomc_or_namd_only_log_filename, 'r').readlines()

        box_no_1 = int(1)

        e_titles_gomc_box_1_iteration, \
        e_titles_stat_titles_gomc_box_1_iteration_list, \
        e_titles_kcal_per_mol_stat_titles_gomc_box_1_iteration_list, \
        e_stat_values_gomc_box_1_iteration_list, \
        e_stat_values_gomc_box_1_list, \
        e_stat_values_gomc_kcal_per_mol_box_1_list = get_gomc_log_data(read_gomc_box_1_log_file,
                                                          gomc_box_1_data_file,
                                                          run_no,
                                                          box_no_1
                                                          )

    # *************************************************
    # *************************************************
    # RUN THE NAMD PORTION of the CODE (End)
    # *************************************************
    # *************************************************

    e_stat_gomc_box_0_df = pd.DataFrame(data=e_stat_values_gomc_box_0_list,
                                     columns=e_titles_stat_titles_gomc_box_0_iteration_list)
    e_stat_gomc_box_0_df.to_csv(gomc_box_0_energies_stat_filename, sep="	", index=False)

    e_stat_kcal_per_mol_gomc_box_0_df = pd.DataFrame(data=e_stat_values_gomc_kcal_per_mol_box_0_list,
                                     columns=e_titles_kcal_per_mol_stat_titles_gomc_box_0_iteration_list)
    e_stat_kcal_per_mol_gomc_box_0_df.to_csv(gomc_box_0_energies_stat_kcal_per_mol_filename, sep="	", index=False)

    if simulation_type in ["GEMC"]:
        e_stat_gomc_box_1_df = pd.DataFrame(data=e_stat_values_gomc_box_1_list,
                                            columns=e_titles_stat_titles_gomc_box_1_iteration_list)
        e_stat_gomc_box_1_df.to_csv(gomc_box_1_energies_stat_filename, sep="	", index=False)
        e_stat_kcal_per_mol_gomc_box_1_df = pd.DataFrame(data=e_stat_values_gomc_kcal_per_mol_box_1_list,
                                                         columns=e_titles_kcal_per_mol_stat_titles_gomc_box_1_iteration_list)
        e_stat_kcal_per_mol_gomc_box_1_df.to_csv(gomc_box_1_energies_stat_kcal_per_mol_filename, sep="	", index=False)

    # ****************************************
    # write the combined NAMD and GOMC data  (Start)
    # ****************************************

    e_values_density_gomc_box_0_STEP_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, '#STEP'].tolist()
    # add 0.4 or 0.2 to the GOMC modified timestep for easy sorting later
    e_values_density_gomc_box_0_MOD_STEP_list = []
    for i in range(0, len(e_values_density_gomc_box_0_STEP_list)):
        if i % 2 == 1:
            e_values_density_gomc_box_0_MOD_STEP_iteration = str(float(e_values_density_gomc_box_0_STEP_list[i]) + 0.4 / 4)
        else:
            e_values_density_gomc_box_0_MOD_STEP_iteration = str(float(e_values_density_gomc_box_0_STEP_list[i]) + 0.4)
        e_values_density_gomc_box_0_MOD_STEP_list.append(e_values_density_gomc_box_0_MOD_STEP_iteration)
    e_values_density_gomc_box_0_ENGINE_list = ["GOMC" for i in e_values_density_gomc_box_0_STEP_list]
    e_values_density_gomc_box_0_TOTAL_POT_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOTAL'].tolist()
    e_values_density_gomc_box_0_TOTAL_ELECT_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOTAL_ELECT'].tolist()
    e_values_density_gomc_box_0_PRESSURE_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'PRESSURE'].tolist()
    try:
        e_values_density_gomc_box_0_VOLUME_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'VOLUME'].tolist()
    except:
        e_values_density_gomc_box_0_VOLUME_list = ['NA'
                                                   for k_i in range(0, len(e_values_density_gomc_box_0_TOTAL_POT_list))]
    e_values_density_gomc_box_0_DENSITY_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'TOT_DENSITY'].tolist()

    e_values_density_gomc_box_0_INTRA_NB_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'INTRA(NB)'].tolist()
    e_values_density_gomc_box_0_INTER_LJ_list = e_stat_kcal_per_mol_gomc_box_0_df.loc[:, 'INTER(LJ)'].tolist()
    e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list = []
    for i in range(0, len(e_values_density_gomc_box_0_INTRA_NB_list)):
        e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list.append(float(e_values_density_gomc_box_0_INTRA_NB_list[i])
                                                                     + float(e_values_density_gomc_box_0_INTER_LJ_list[i])
                                                                     + float(e_values_density_gomc_box_0_TOTAL_ELECT_list[i]))

    if simulation_type in ["GEMC"]:
        e_values_density_gomc_box_1_STEP_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, '#STEP'].tolist()
        # add 0.4 or 0.2 to the GOMC modified timestep for easy sorting later
        e_values_density_gomc_box_1_MOD_STEP_list = []
        for i in range(0, len(e_values_density_gomc_box_1_STEP_list)):
            if i % 2 == 1:
                e_values_density_gomc_box_1_MOD_STEP_iteration = str(float(e_values_density_gomc_box_1_STEP_list[i])
                                                                     + 0.4/4)
            else:
                e_values_density_gomc_box_1_MOD_STEP_iteration = str(float(e_values_density_gomc_box_1_STEP_list[i])
                                                                     + 0.4)
            e_values_density_gomc_box_1_MOD_STEP_list.append(e_values_density_gomc_box_1_MOD_STEP_iteration)

        e_values_density_gomc_box_1_ENGINE_list = ["GOMC" for i in e_values_density_gomc_box_1_STEP_list]
        e_values_density_gomc_box_1_TOTAL_POT_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOTAL'].tolist()
        e_values_density_gomc_box_1_TOTAL_ELECT_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOTAL_ELECT'].tolist()
        e_values_density_gomc_box_1_PRESSURE_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'PRESSURE'].tolist()
        e_values_density_gomc_box_1_VOLUME_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'VOLUME'].tolist()
        try:
            e_values_density_gomc_box_1_VOLUME_list  = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'VOLUME'].tolist()
        except:
            e_values_density_gomc_box_1_VOLUME_list  = ['NA'
                                                       for k_i in
                                                       range(0, len(e_values_density_gomc_box_1_TOTAL_POT_list))]

        e_values_density_gomc_box_1_DENSITY_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'TOT_DENSITY'].tolist()
        e_values_density_gomc_box_1_INTRA_NB_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'INTRA(NB)'].tolist()
        e_values_density_gomc_box_1_INTER_LJ_list = e_stat_kcal_per_mol_gomc_box_1_df.loc[:, 'INTER(LJ)'].tolist()
        e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list = []
        for i in range(0, len(e_values_density_gomc_box_1_INTRA_NB_list)):
            e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list.append(float(e_values_density_gomc_box_1_INTRA_NB_list[i])
                                                              + float(e_values_density_gomc_box_1_INTER_LJ_list[i])
                                                              + float(e_values_density_gomc_box_0_TOTAL_ELECT_list[i]))

    # ****************************************
    # write the combined NAMD and GOMC data for box 0  (Start)
    # ****************************************
    # combine Engine data
    combined_MOD_STEP_box_0 = []
    # combine MOD_STEP data
    for i in range(0, len(e_values_density_gomc_box_0_MOD_STEP_list)):
        combined_MOD_STEP_box_0.append(float(e_values_density_gomc_box_0_MOD_STEP_list[i]))

    combined_ENGINE_box_0 = e_values_density_gomc_box_0_ENGINE_list
    combined_STEP_box_0 = e_values_density_gomc_box_0_STEP_list
    combined_TOTAL_POT_box_0 = e_values_density_gomc_box_0_TOTAL_POT_list
    combined_TOTAL_ELECT_box_0 = e_values_density_gomc_box_0_TOTAL_ELECT_list
    combined_TOTAL_VDW_plus_ELECT_box_0 = e_values_density_gomc_box_0_TOTAL_VDW_plus_ELECT_list
    combined_PRESSURE_box_0 = e_values_density_gomc_box_0_PRESSURE_list
    combined_VOLUME_box_0 = e_values_density_gomc_box_0_VOLUME_list
    combined_DENSITY_box_0 = e_values_density_gomc_box_0_DENSITY_list

    combined_data_box_0_df = pd.DataFrame({
        "ENGINE": combined_ENGINE_box_0,
        "MOD_STEP": combined_MOD_STEP_box_0,
        "#STEP": combined_STEP_box_0,
        'TOTAL_POT': combined_TOTAL_POT_box_0,
        'TOTAL_ELECT': combined_TOTAL_ELECT_box_0,
        'TOTAL_VDW_plus_ELECT': combined_TOTAL_VDW_plus_ELECT_box_0,
        'PRESSURE': combined_PRESSURE_box_0,
        'VOLUME': combined_VOLUME_box_0,
        'DENSITY': combined_DENSITY_box_0
    })
    combined_data_sorted_box_0_df = combined_data_box_0_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
    combined_data_sorted_box_0_df.drop("MOD_STEP", axis=1, inplace=True)
    combined_data_sorted_box_0_df.to_csv(combined_box_0_data_filename, sep="	", index=False)

    # ****************************************
    # write the combined NAMD and GOMC data for box 0  (Start)
    # ****************************************

    # ****************************************
    # write the combined NAMD and GOMC data for box 1  (Start)
    # ****************************************

    # combine Engine data
    if simulation_type in ["GEMC"]:
        combined_MOD_STEP_box_1 = []
        # combine MOD_STEP data
        for i in range(0, len(e_values_density_gomc_box_1_MOD_STEP_list)):
            combined_MOD_STEP_box_1.append(float(e_values_density_gomc_box_1_MOD_STEP_list[i]))

        combined_ENGINE_box_1 = e_values_density_gomc_box_1_ENGINE_list
        combined_STEP_box_1 = e_values_density_gomc_box_1_STEP_list
        combined_TOTAL_POT_box_1 = e_values_density_gomc_box_1_TOTAL_POT_list
        combined_TOTAL_ELECT_box_1 = e_values_density_gomc_box_1_TOTAL_ELECT_list
        combined_TOTAL_VDW_plus_ELECT_box_1 = e_values_density_gomc_box_1_TOTAL_VDW_plus_ELECT_list
        combined_PRESSURE_box_1 = e_values_density_gomc_box_1_PRESSURE_list
        combined_VOLUME_box_1 = e_values_density_gomc_box_1_VOLUME_list
        combined_DENSITY_box_1 = e_values_density_gomc_box_1_DENSITY_list

        combined_data_box_1_df = pd.DataFrame({
            "ENGINE": combined_ENGINE_box_1,
            "MOD_STEP": combined_MOD_STEP_box_1,
            "#STEP": combined_STEP_box_1,
            'TOTAL_POT': combined_TOTAL_POT_box_1,
            'TOTAL_ELECT': combined_TOTAL_ELECT_box_1,
            'TOTAL_VDW_plus_ELECT': combined_TOTAL_VDW_plus_ELECT_box_1,
            'PRESSURE': combined_PRESSURE_box_1,
            'VOLUME': combined_VOLUME_box_1,
            'DENSITY': combined_DENSITY_box_1
        })
        combined_data_sorted_box_1_df = combined_data_box_1_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
        combined_data_sorted_box_1_df.drop("MOD_STEP", axis=1, inplace=True)
        combined_data_sorted_box_1_df.to_csv(combined_box_1_data_filename, sep="	", index=False)

        # ****************************************
        # write the combined NAMD and GOMC data for box 1  (end)
        # ****************************************

        # ****************************************
        # write the combined NAMD and GOMC data  (end)
        # ****************************************
        print("INFO: Finished all data extraction for GOMC-only runs and exported into muliple files and types")

        # ****************************************
        # ****************************************
        # NAMD-onl data extraction (end)
        # ****************************************
        # ****************************************

elif simulation_engine_options == 'NAMD-only':

    run_no = 0  # run number is always 1
    current_step = 0

    print("INFO: Started all data extraction for NAMD-only runs and exported into multiple files and types")

    # *************************************
    # get NAMD- only energies
    # ***********************initial_Energies**************
    no_namd_box_0_directory = str(gomc_or_namd_only_log_filename)

    read_namd_box_0_log_file = open(gomc_or_namd_only_log_filename, 'r').readlines()

    for i, line in enumerate(read_namd_box_0_log_file):
        split_line = line.split()
        if line.startswith('TCL:') is True:
            if split_line[0] == 'TCL:' and len(split_line) >= 5:
                if split_line[1] == 'Minimizing' and split_line[2] == 'for' and split_line[4] == 'steps':
                    namd_minimizing_steps_box_0 = float(split_line[3])
                    current_step += (-1 * namd_minimizing_steps_box_0)

    e_titles_namd_box_0_iteration, \
    e_titles_namd_box_0_density_iteration, \
    e_values_namd_box_0_iteration, \
    e_values_namd_box_0_density_list, \
    e_property_values_namd_box_0_list = get_namd_log_data(read_namd_box_0_log_file,
                                                          namd_box_0_data_file,
                                                          run_no)

    e_values_density_namd_box_0_df = pd.DataFrame(data=e_values_namd_box_0_density_list,
                                                  columns=e_titles_namd_box_0_density_iteration)
    e_values_density_namd_box_0_df.to_csv(namd_box_0_data_density_filename, sep="	", index=False)

    # ****************************************
    # write the combined NAMD data  (Start)
    # ****************************************

    e_values_density_namd_box_0_STEP_list = e_values_density_namd_box_0_df.loc[:, '#TS'].tolist()
    # add 0.1 to the NAMD modified timestep for easy sorting later
    e_values_density_namd_box_0_MOD_STEP_list = [str(float(i) + 0.2) for i in e_values_density_namd_box_0_STEP_list]
    e_values_density_namd_box_0_ENGINE_list = ["NAMD" for i in e_values_density_namd_box_0_STEP_list]
    e_values_density_namd_box_0_TOTAL_POT_list = e_values_density_namd_box_0_df.loc[:, 'POTENTIAL'].tolist()
    e_values_density_namd_box_0_TOTAL_ELECT_list = e_values_density_namd_box_0_df.loc[:, 'ELECT'].tolist()
    e_values_density_namd_box_0_TOTAL_VDW_list = e_values_density_namd_box_0_df.loc[:, 'VDW'].tolist()
    e_values_density_namd_box_0_TOTAL_VDW_plus_ELECT_list = [float(e_values_density_namd_box_0_TOTAL_VDW_list[k_i]) +
                                                             float(e_values_density_namd_box_0_TOTAL_ELECT_list[k_i])
                                                             for k_i in range(0, len(e_values_density_namd_box_0_TOTAL_VDW_list))]
    e_values_density_namd_box_0_PRESSURE_list = e_values_density_namd_box_0_df.loc[:, 'PRESSURE'].tolist()
    e_values_density_namd_box_0_VOLUME_list = e_values_density_namd_box_0_df.loc[:, 'VOLUME'].tolist()
    e_values_density_namd_box_0_DENSITY_list = e_values_density_namd_box_0_df.loc[:, 'DENSITY'].tolist()

    # ****************************************
    # write the combined NAMD  data (end)
    # ****************************************

    # combine Engine data
    namd_MOD_STEP_box_0 = []
    # combine MOD_STEP data
    for i in range(0, len(e_values_density_namd_box_0_MOD_STEP_list)):
        namd_MOD_STEP_box_0.append(float(e_values_density_namd_box_0_MOD_STEP_list[i]))

    namd_ENGINE_box_0 = e_values_density_namd_box_0_ENGINE_list
    namd_STEP_box_0 = e_values_density_namd_box_0_STEP_list
    namd_TOTAL_POT_box_0 = e_values_density_namd_box_0_TOTAL_POT_list
    namd_TOTAL_ELECT_box_0 = e_values_density_namd_box_0_TOTAL_ELECT_list
    namd_TOTAL_VDW_plus_ELECT_box_0 = e_values_density_namd_box_0_TOTAL_VDW_plus_ELECT_list
    namd_PRESSURE_box_0 = e_values_density_namd_box_0_PRESSURE_list
    namd_VOLUME_box_0 = e_values_density_namd_box_0_VOLUME_list
    namd_DENSITY_box_0 = e_values_density_namd_box_0_DENSITY_list

    namd_data_box_0_df = pd.DataFrame({
        "#ENGINE": namd_ENGINE_box_0,
        "MOD_STEP": namd_MOD_STEP_box_0,
        "STEP": namd_STEP_box_0,
        'TOTAL_POT': namd_TOTAL_POT_box_0,
        'TOTAL_ELECT': namd_TOTAL_ELECT_box_0,
        'TOTAL_VDW_plus_ELECT': namd_TOTAL_VDW_plus_ELECT_box_0,
        'PRESSURE': namd_PRESSURE_box_0,
        'VOLUME': namd_VOLUME_box_0,
        'DENSITY': namd_DENSITY_box_0
    })
    namd_data_sorted_box_0_df = namd_data_box_0_df.sort_values(by=["MOD_STEP"], axis=0, ascending=True)
    namd_data_sorted_box_0_df.drop("MOD_STEP", axis=1, inplace=True)
    namd_data_sorted_box_0_df.to_csv(combined_box_0_data_filename, sep="	", index=False)


    # ****************************************
    # write the combined NAMD data  (end)
    # ****************************************
    print("INFO: Finished all data extraction for NAMD-only runs and exported into multiple files and types")

    # ****************************************
    # ****************************************
    # NAMD-only data extraction (end)
    # ****************************************
    # ****************************************

