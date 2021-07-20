## py-MCMD: A Python Library for Performing  Hybrid Monte Carlo - Molecular Dynamics Simulations with GOMC and NAMD
--------

This Python code enables hybrid molecular dynamics/Monte Carlo (MD/MC) simulations using [NAMD](https://www.ks.uiuc.edu/Research/namd/) and the [GPU Optimized Monte Carlo (GOMC)](http://gomc.eng.wayne.edu) software.
The Python code allows users to switch back and forth between the NAMD and GOMC simulation engines, with one (1) iteration of each NAMD and GOMC consisting of a cycle.  The user programs the number of cycles and the number of NAMD and GOMC steps per cycle.  Combining the MD/MC simulations allows the best of both types of simulations while minimizing the downsides, and in some cases, enabling simulations that were previously not feasible. This code allows the modification of the NAMD and GOMC control files, maximizing user flexibility and functionality. 

Please see the [py-MCMD Read the Docs](https://py-mcmd.readthedocs.io/en/latest/) webpage for more information and instructions.


