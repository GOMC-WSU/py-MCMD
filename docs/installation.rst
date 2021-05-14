Installation and Other Required Files
============

The hybrid NAMD_GOMC Python code can be downloaded or cloned from the `NAMD_GOMC GitHub repository <https://github.com/bc118/NAMD_GOMC>`_.  This hybrid NAMD_GOMC Python code does not require any setup, but does require the proper files as input, which are listed below:

* PSF

* PDB

* Force field (.inp or .par) files

* NAMD binary files for the CPU and GPU version, depending on which one you plan on using.  **NOTE: NAMD provides two (2) different downloads, one (1) for the CPU version and one (1) for the GPU version.**

* GOMC binary files for all the ensembles (built automatically when building GOMC) and for the CPU and GPU version, depending on which one you plan on using.


This Python code is compatible only with `NAMD version 2.13-2.14 <https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD>`_ and `GOMC-development branch <https://github.com/GOMC-WSU/GOMC/tree/development>`_.  The NAMD and GOMC software needs to be installed before using this hybrid python code. Please refer to the NAMD and GOMC software instructions for installing them and building the binary file.  These binary files can be moved to a different directory, as this directory is specified in the hybrid simulation input.

* In NAMD, the binary file is typically located in the *NAMD_version_OS-CPUorGPU/* directory, named *namd2*. **NOTE: the user will need to specify the NAMD binary file directory and name in this python code variables.**

* For GOMC, the binary files are typically located *GOMC_version_No/bin* directory. The CPU versions of the binary files are named GOMC_CPU_GCMC, GOMC_CPU_GEMC, GOMC_CPU_NPT, and GOMC_CPU_NVT.  
The GPU versions of the files are name GOMC_GPU_GCMC, GOMC_GPU_GEMC, GOMC_GPU_NPT, and GOMC_GPU_NVT.  **NOTE: the user just needs to specify the GOMC binary directory since this Python code will select the proper binary file.**
