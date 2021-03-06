# nnode

Neural network code for solving ordinary differential equations.

Reference: Lagaris et al, IEEE Transactions on Neural Networks 8(5),
p. 987 (1998).

## Experiments

### 1-D Diffusion

The main functions for 1-D diffusion are a.py, b.py.

The best results were found using the BFGS method in scipy.optimize.

In the following, `nx=11` and `nt=11`.

* (diff1d_0_BFGS.ipynb)[/notebooks/diff1d_0_BFGS.ipynb] tests the solution using an initial condition of $$\psi=0$$ and boundary conditions of $$\psi(0,t)=\psi(1,t)=0$$.
* (diff1d_0_BFGS.ipynb)[/notebooks/diff1d_1_BFGS.ipynb] differs from the previous experiment by ...

# Description of Libraries


Help for all programs is available using the -h command-line option.

The program nnode1.py is used to solve 1st-order ODE IVP. This program
can process ode00.py, lagaris01.py, and lagaris02.py.

The program nnode2bvp.py is used to solve 2nd-order ODE BVP. This
program can process lagaris03bvp.py.

The program nnode2ivp.py is used to solve 2nd-order ODE IVP. This
program can process lagaris03ivp.py.

The files lagaris01.py, lagaris02.py define the code needed for
problems 1 and 2 in the Lagaris et al paper. The files lagaris03bvp.py
and lagaris03ivp.py define the BVP and IVP versions of Problem 3 in
Lagaris et al. The file ode00.py is a simple 1st order ODE problem for
testing nnode1.py.

The file sigma.py provides code for the sigmoid transfer function and
its derivatives. The corresponding .nb and .ipynb files are Jupyter
and Mathematica notebooks for examination of the sigmoid function, and
to ensure the Python code gives the same results as Mathematica.

The file nnode1.ipynb, nnode2bvp.ipynb, and nnode3ivp.ipynb are
detailed walkthroughs of nnode1.py, nnode2bvp.py, and nnode2ivp.py,
respectively, explaining the algorithms and program options using
several examples.

The remaining iPython (*.ipynb) and Mathematica (*.nb) files are
notebooks used for ensuring the Python and Mathematica code gives the
same results.

# Contact

Eric Winter
ewinter@stsci.edu
2017-11-02
