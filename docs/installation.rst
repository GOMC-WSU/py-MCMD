Installation and Other Required Files
============

The hybrid NAMD_GOMC Python code can be downloaded or cloned from the `NAMD_GOMC GitHub repository <https://github.com/bc118/NAMD_GOMC>`_.  This hybrid NAMD_GOMC Python code does not require any setup, but does require the proper files as input, which are listed below:

* **PSF** and **PDB** files.  *NOTE:  One (1) PSF and PDB file are required for the NPT and NVT ensembles, while two (2) PSF and PDB files are required for the GCMC and GEMC ensembles.*

* **Force field (.inp or .par) files**

* **NAMD binary files** for the CPU and GPU version, depending on which one you plan on using.  *NOTE: NAMD provides two (2) different downloads, one (1) for the CPU version and one (1) for the GPU version.*

* **GOMC binary files**  are automatically built for all the ensembles when compiling GOMC.  The CPU version of GOMC is always built, while the GPU version of GOMC is only compiled if the proper CUDA version is installed and accessible during the building process.


This Python code is currently compatible only with `NAMD version 2.14 <https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD>`_ and `GOMC-development branch <https://github.com/GOMC-WSU/GOMC/tree/development>`_.  The NAMD and GOMC software needs to be installed before using this hybrid python code. Please refer to the NAMD and GOMC software instructions for installing them and building the binary files.  Please also see the `GOMC Manual <https://gomc.eng.wayne.edu/documentation/>`_ and the `NAMD Users Guide <https://www.ks.uiuc.edu/Research/namd/2.14/ug/>`_. These binary files can be moved to a different directory, as this directory is specified in the hybrid simulation input.


* In NAMD, the binary file is typically located in the *NAMD_version_OS-CPUorGPU/* directory, named *namd2*. 
	*NOTE: the user will need to specify the NAMD binary file directory and file name in this python code variables.*

* For GOMC, the binary files are typically located *GOMC_version_No/bin* directory. The CPU versions of the binary files are named GOMC_CPU_GCMC, GOMC_CPU_GEMC, GOMC_CPU_NPT, and GOMC_CPU_NVT.  The GPU versions of the files are named GOMC_GPU_GCMC, GOMC_GPU_GEMC, GOMC_GPU_NPT, and GOMC_GPU_NVT.  
	*NOTE: the user just needs to specify the GOMC binary directory since this Python code will select the proper binary file.*


**NOTE: This code was only tested on Linux operating systems.  It was not tested using the Windows, Mac, or other operating systems, so it may not function properly on these operating systems.**  


**NOTE: A bug exists when running the NAMD simulations in GPU mode with the hybrid GEMC ensemble.  It is currently unclear if this is an issue with NAMD, CUDA, or a precision error since the NAMD simulations run perfectly in CPU mode.  A temporary workaround when using the hybrid GEMC ensemble is to run GOMC in GPU mode and NAMD in CPU mode.**  

**NOTE: ONLY run NAMD in the NVT ensemble, as running NAMD in the NPT ensemble will cause errors in the box positioning since NAMD and GOMC have different box centering algorithms when centering the box during box size changes.**  

**NOTE:**  GOMC does not currently use improper or Urey—Bradley potentials, so if the hybrid simulations contain impropers or Urey—Bradleys, the NAMD simulation energies will be different.  In a protein simulation, it should be OK not to use impropers or Urey-Bradleys in GOMC and utilize them in NAMD since the protein will not move in the GOMC simulation due to its size.  Each simulation will need to be individually evaluated to determine if not having the impropers or Urey-Bradleys in GOMC is irrelevant or significant to the simulation results.**
