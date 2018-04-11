#!/usr/bin/env python

# Use a neural network to solve a 2-variable, 2nd-order PDE BVP with
# Dirichlet BC. Note that any 2-variable 2nd-order PDE BVP can be
# mapped to a corresponding BVP with boundaries at 0 and 1, so this is
# the only solution form needed.

# The general form of such equations is, for Y = Y(x,y):

# G(x[], Y, delY[], del2Y[]) = 0

# Notation notes:

# * Notation is developed to mirror my derivations and notes.

# * The symbol psi has been replaced by 'Y' to simplify variable names.

# * No space between differential operators and the variables they act on.

# * Names that end in 'f' are usually functions, or containers of functions.

# * Underscores separate the numerator and denominator in a name
# which represents a derivative or fraction.

# * Names beginning with 'del' are gradients of another function.

# * delYt[i,j] is the derivative of the trial solution Yt[i] wrt
# x[i][j]. Similarly for del2Yt[i,j].

#********************************************************************************

# Import external modules, using standard shorthand.

import argparse
from importlib import import_module
from math import sqrt
import numpy as np
from sigma import sigma, dsigma_dz, d2sigma_dz2, d3sigma_dz3

#********************************************************************************

# Default values for program parameters
default_debug = False
default_eta = 0.01
default_maxepochs = 1000
default_nhid = 10
default_ntrain = 10
default_pde = 'pde02bvp'
default_seed = 0
default_verbose = False

# Default ranges for weights and biases
w_min = -1
w_max = 1
u_min = -1
u_max = 1
v_min = -1
v_max = 1

#********************************************************************************

# The range of the trial solution is assumed to be [0, 1].
# N.B. ASSUMES ONLY 2 DIMENSIONS!

# Define the coefficient functions for the trial solution, and their derivatives.
def Af(xy, bcf):
    (x, y) = xy
    ((f0f, g0f), (f1f, g1f)) = bcf
    A = (
        (1 - x)*f0f(y) + x*f1f(y)
        + (1 - y)*(g0f(x) - (1 - x)*g0f(0) - x*g0f(1))
        + y*(g1f(x) - (1 - x)*g1f(0) - x*g1f(1))
    )
    return A

def dA_dxf(xy, bcf, bcdf):
    (x, y) = xy
    ((f0f, g0f), (f1f, g1f)) = bcf
    ((df0_dyf, dg0_dxf), (df1_dyf, dg1_dxf)) = bcdf
    dA_dx = (
        -f0f(y) + f1f(y) + (1 - y)*(dg0_dxf(x) + g0f(0) - g0f(1))
        + y*(dg1_dxf(x) + g1f(0) - g1f(1))
        )
    return dA_dx

def dA_dyf(xy, bcf, bcdf):
    (x, y) = xy
    ((f0f, g0f), (f1f, g1f)) = bcf
    ((df0_dyf, dg0_dxf), (df1_dyf, dg1_dxf)) = bcdf
    dA_dy = (
        (1 - x)*df0_dyf(y) + x*df1_dyf(y)
        - (g0f(x) - (1 - x)*g0f(0) - x*g0f(1))
        + (g1f(x) - (1 - x)*g1f(0) + x*g1f(1))
    )
    return dA_dy

delAf = (dA_dxf, dA_dyf)

def d2A_dx2f(xy, bcf, bcdf, bcd2f):
    (x, y) = xy
    ((f0f, g0f), (f1f, g1f)) = bcf
    ((df0_dyf, dg0_dxf), (df1_dyf, dg1_dxf)) = bcdf
    ((d2f0_dy2f, d2g0_dx2f), (d2f1_dy2f, d2g1_dx2f)) = bcd2f
    d2A_dx2 = (1 - y)*d2g0_dx2f(x) + y*d2g1_dx2f(x)
    return d2A_dx2

def d2A_dy2f(xy, bcf, bcdf, bcd2f):
    (x, y) = xy
    ((f0f, g0f), (f1f, g1f)) = bcf
    ((df0_dyf, dg0_dxf), (df1_dyf, dg1_dxf)) = bcdf
    ((d2f0_dy2f, d2g0_dx2f), (d2f1_dy2f, d2g1_dx2f)) = bcd2f
    d2A_dy2 = (1 - x)*d2f0_dy2f(y) + x*d2f1_dy2f(y)
    return d2A_dy2

del2Af = (d2A_dx2f, d2A_dy2f)

def Pf(xy):
    (x, y) = xy
    P = x*(1 - x)*y*(1 - y)
    return P

def dP_dxf(xy):
    (x, y) = xy
    dP_dx = (1 - 2*x)*y*(1 - y)
    return dP_dx

def dP_dyf(xy):
    (x, y) = xy
    dP_dy = x*(1 - x)*(1 - 2*y)
    return dP_dy

delPf = (dP_dxf, dP_dyf)

def d2P_dx2f(xy):
    (x, y) = xy
    d2P_dx2 = -2*y*(1 - y)
    return d2P_dx2

def d2P_dy2f(xy):
    (x, y) = xy
    d2P_dy2 = -2*x*(1 - x)
    return d2P_dy2

del2Pf = (d2P_dx2f, d2P_dy2f)

# Define the trial solution and its derivatives.
def Ytf(xy, N, bcf):
    A = Af(xy, bcf)
    P = Pf(xy)
    Yt = A + P*N
    return Yt

#********************************************************************************

# Function to solve a 2-variable, 2nd-order PDE BVP with Dirichlet BC,
# using a single-hidden-layer feedforward neural network with 2 input
# nodes and a single output node.

def nnpde2bvp(
        Gf,                            # 2-variable, 2nd-order PDE BVP
        dG_dYf,                        # Partial of G wrt Y
        dG_ddelYf,                     # Partials of G wrt delY
        dG_ddel2Yf,                    # Partials of G wrt del2Y
        bcf,                           # BC functions
        bcdf,                          # BC function derivatives
        bcd2f,                         # BC function 2nd derivatives
        x,                             # Training points as pairs
        nhid = default_nhid,           # Node count in hidden layer
        maxepochs = default_maxepochs, # Max training epochs
        eta = default_eta,             # Learning rate
        debug = default_debug,
        verbose = default_verbose
):
    if debug: print('Gf =', Gf)
    if debug: print('dG_dYf =', dG_dYf)
    if debug: print('dG_ddelYf =', dG_ddelYf)
    if debug: print('dG_ddel2Yf =', dG_ddel2Yf)
    if debug: print('bcf =', bcf)
    if debug: print('bcdf =', bcdf)
    if debug: print('bcd2f =', bcd2f)
    if debug: print('x =', x)
    if debug: print('nhid =', nhid)
    if debug: print('maxepochs =', maxepochs)
    if debug: print('eta =', eta)
    if debug: print('debug =', debug)
    if debug: print('verbose =', verbose)

    # Sanity-check arguments.
    assert Gf
    assert dG_dYf
    assert len(dG_ddelYf) == 2
    assert len(dG_ddel2Yf) == 2
    assert len(bcf) == 2
    assert len(bcdf) == 2
    assert len(bcd2f) == 2
    assert len(x) > 0
    assert nhid > 0
    assert maxepochs > 0
    assert eta > 0

    #----------------------------------------------------------------------------

    # Determine the number of training points.
    n = len(x)
    if debug: print('n =', n)

    # Change notation for convenience.
    m = len(bcf)
    if debug: print('m =', m)  # Will always be 2 in this code.
    H = nhid
    if debug: print('H =', H)

    #----------------------------------------------------------------------------

    # Create the network.

    # Create an array to hold the weights connecting the 2 input nodes
    # to the hidden nodes. The weights are initialized with a uniform
    # random distribution.
    w = np.random.uniform(w_min, w_max, (2, H))
    if debug: print('w =', w)

    # Create an array to hold the biases for the hidden nodes. The
    # biases are initialized with a uniform random distribution.
    u = np.random.uniform(u_min, u_max, H)
    if debug: print('u =', u)

    # Create an array to hold the weights connecting the hidden nodes
    # to the output node. The weights are initialized with a uniform
    # random distribution.
    v = np.random.uniform(v_min, v_max, H)
    if debug: print('v =', v)

    #----------------------------------------------------------------------------

    # Run the network.
    for epoch in range(maxepochs):
        if debug: print('Starting epoch %d.' % epoch)

        # Compute the net input, the sigmoid function and its derivatives,
        # for each hidden node.
        z = np.zeros((n, H))
        s = np.zeros((n, H))
        s1 = np.zeros((n, H))
        s2 = np.zeros((n, H))
        s3 = np.zeros((n, H))
        for i in range(n):
            for k in range(H):
                z[i,k] = u[k]
                for j in range(m):
                    z[i,k] += w[j,k]*x[i,j]
                s[i,k] = sigma(z[i,k])
                s1[i,k] = dsigma_dz(z[i,k])
                s2[i,k] = d2sigma_dz2(z[i,k])
                s3[i,k] = d3sigma_dz3(z[i,k])
        if debug: print('z =', z)
        if debug: print('s =', s)
        if debug: print('s1 =', s1)
        if debug: print('s2 =', s2)
        if debug: print('s3 =', s3)

        # Compute the network output and its derivatives, for each
        # training point.
        N = np.zeros(n)
        dN_dx = np.zeros((n, m))
        dN_dv = np.zeros((n, H))
        dN_du = np.zeros((n, H))
        dN_dw = np.zeros((n, m, H))
        d2N_dvdx = np.zeros((n, m, H))
        d2N_dudx = np.zeros((n, m, H))
        d2N_dwdx = np.zeros((n, m, H))
        d2N_dx2 = np.zeros((n, m))
        d3N_dvdx2 = np.zeros((n, m, H))
        d3N_dudx2 = np.zeros((n, m, H))
        d3N_dwdx2 = np.zeros((n, m, H))
        for i in range(n):
            for k in range(H):
                N[i] += v[k]*s[i,k]
                dN_dv[i,k] = s[i,k]
                dN_du[i,k] = v[k]*s1[i,k]
                for j in range(m):
                    dN_dx[i,j] += v[k]*s1[i,k]*w[j,k]
                    dN_dw[i,j,k] = v[k]*s1[i,k]*x[i,j]
                    d2N_dvdx[i,j,k] = s1[i,k]*w[j,k]
                    d2N_dudx[i,j,k] = v[k]*s2[i,k]*w[j,k]
                    d2N_dwdx[i,j,k] = v[k]*(s1[i,k] + s2[i,k]*w[j,k]*x[i,j])
                    d2N_dx2[i,j] += v[k]*s2[i,k]*w[j,k]**2
                    d3N_dvdx2[i,j,k] = s2[i,k]*w[j,k]**2
                    d3N_dudx2[i,j,k] = v[k]*s3[i,k]*w[j,k]**2
                    d3N_dwdx2[i,j,k] = (
                        v[k]*(2*s2[i,k]*w[j,k] + s3[i,k]*w[j,k]**2*x[i,j])
                    )
        if debug: print('N =', N)
        if debug: print('dN_dx =', dN_dx)
        if debug: print('dN_dv =', dN_dv)
        if debug: print('dN_du =', dN_du)
        if debug: print('dN_dw =', dN_dw)
        if debug: print('d2N_dvdx =', d2N_dvdx)
        if debug: print('d2N_dudx =', d2N_dudx)
        if debug: print('d2N_dwdx =', d2N_dwdx)
        if debug: print('d2N_dx2 =', d2N_dx2)
        if debug: print('d3N_dvdx2 =', d3N_dvdx2)
        if debug: print('d3N_dudx2 =', d3N_dudx2)
        if debug: print('d3N_dwdx2 =', d3N_dwdx2)

        #------------------------------------------------------------------------

        # Compute the value of the trial solution and its derivatives,
        # for each training point.
        dA_dx = np.zeros((n, m))
        d2A_dx2 = np.zeros((n, m))
        P = np.zeros(n)
        dP_dx = np.zeros((n, m))
        d2P_dx2 = np.zeros((n, m))
        Yt = np.zeros(n)
        dYt_dx = np.zeros((n, m))
        dYt_dv = np.zeros((n, H))
        dYt_du = np.zeros((n, H))
        dYt_dw = np.zeros((n, m, H))
        d2Yt_dvdx = np.zeros((n, m, H))
        d2Yt_dudx = np.zeros((n, m, H))
        d2Yt_dwdx = np.zeros((n, m, H))
        d2Yt_dx2 = np.zeros((n, m))
        d3Yt_dvdx2 = np.zeros((n, m, H))
        d3Yt_dudx2 = np.zeros((n, m, H))
        d3Yt_dwdx2 = np.zeros((n, m, H))
        for i in range(n):
            P[i] = Pf(x[i])
            Yt[i] = Ytf(x[i], N[i], bcf)
            for j in range(m):
                dA_dx[i,j] = delAf[j](x[i], bcf, bcdf)
                d2A_dx2[i,j] = del2Af[j](x[i], bcf, bcdf, bcd2f)
                dP_dx[i,j] = delPf[j](x[i])
                d2P_dx2[i,j] = del2Pf[j](x[i])
                dYt_dx[i,j] = dA_dx[i,j] + P[i]*dN_dx[i,j] + dP_dx[i,j]*N[i]
                d2Yt_dx2[i,j] = (
                    d2A_dx2[i,j] + P[i]*d2N_dx2[i,j]
                    +  2*dP_dx[i,j]*dN_dx[i,j] + d2P_dx2[i,j]*N[i]
                )
            for k in range(H):
                dYt_dv[i,k] = P[i]*dN_dv[i,k]
                dYt_du[i,k] = P[i]*dN_du[i,k]
                for j in range(m):
                    dYt_dw[i,j,k] = P[i]*dN_dw[i,j,k]
                    d2Yt_dvdx[i,j,k] = (
                        P[i]*d2N_dvdx[i,j,k] + dP_dx[i,j]*dN_dv[i,k]
                    )
                    d2Yt_dudx[i,j,k] = (
                        P[i]*d2N_dudx[i,j,k] + dP_dx[i,j]*dN_du[i,k]
                    )
                    d2Yt_dwdx[i,j,k] = (
                        P[i]*d2N_dwdx[i,j,k] + dP_dx[i,j]*dN_dw[i,j,k]
                    )
                    d3Yt_dvdx2[i,j,k] = (
                        P[i]*d3N_dvdx2[i,j,k] + 2*dP_dx[i,j]*d2N_dvdx[i,j,k]
                        + d2P_dx2[i,j]*dN_dv[i,k]
                    )
                    d3Yt_dudx2[i,j,k] = (
                        P[i]*d3N_dudx2[i,j,k] + 2*dP_dx[i,j]*d2N_dudx[i,j,k]
                        + d2P_dx2[i,j]*dN_du[i,k]
                    )
                    d3Yt_dwdx2[i,j,k] = (
                        P[i]*d3N_dwdx2[i,j,k] + 2*dP_dx[i,j]*d2N_dwdx[i,j,k]
                        + d2P_dx2[i,j]*dN_dw[i,j,k]
                    )
        if debug: print('dA_dx =', dA_dx)
        if debug: print('d2A_dx2 =', d2A_dx2)
        if debug: print('P =', P)
        if debug: print('dP_dx =', dP_dx)
        if debug: print('d2P_dx2 =', d2P_dx2)
        if debug: print('Yt =', Yt)
        if debug: print('dYt_dx =', dYt_dx)
        if debug: print('dYt_dv =', dYt_dv)
        if debug: print('dYt_du =', dYt_du)
        if debug: print('dYt_dw =', dYt_dw)
        if debug: print('d2Yt_dvdx =', d2Yt_dvdx)
        if debug: print('d2Yt_dudx =', d2Yt_dudx)
        if debug: print('d2Yt_dwdx =', d2Yt_dwdx)
        if debug: print('d2Yt_dx2 =', d2Yt_dx2)
        if debug: print('d3Yt_dvdx2 =', d3Yt_dvdx2)
        if debug: print('d3Yt_dudx2 =', d3Yt_dudx2)
        if debug: print('d3Yt_dwdx2 =', d3Yt_dwdx2)

        # Compute the value of the original differential equation
        # for each training point, and its derivatives.
        G = np.zeros(n)
        dG_dYt = np.zeros(n)
        dG_ddelYt = np.zeros((n, m))
        dG_ddel2Yt = np.zeros((n, m))
        dG_dv = np.zeros((n, H))
        dG_du = np.zeros((n, H))
        dG_dw = np.zeros((n, m, H))
        for i in range(n):
            G[i] = Gf(x[i], Yt[i], dYt_dx[i], d2Yt_dx2[i])
            dG_dYt[i] = dG_dYf(x[i], Yt[i], dYt_dx[i], d2Yt_dx2[i])
            for j in range(m):
                dG_ddelYt[i,j] = dG_ddelYf[j](x[i], Yt[i],
                                              dYt_dx[i], d2Yt_dx2[i])
                dG_ddel2Yt[i,j] = dG_ddel2Yf[j](x[i], Yt[i],
                                                dYt_dx[i], d2Yt_dx2[i])
            for k in range(H):
                dG_dv[i,k] = dG_dYt[i]*dYt_dv[i,k]
                dG_du[i,k] = dG_dYt[i]*dYt_du[i,k]
                for j in range(m):
                    dG_dv[i,k] += dG_ddelYt[i,j]*d2Yt_dvdx[i,j,k]
                    + dG_ddel2Yt[i,j]*d3Yt_dvdx2[i,j,k]
                    dG_du[i,k] += dG_ddelYt[i,j]*d2Yt_dudx[i,j,k]
                    + dG_ddel2Yt[i,j]*d3Yt_dudx2[i,j,k]
                    dG_dw[i,j,k] = (
                        dG_dYt[i]*dYt_dw[i,j,k]
                        + dG_ddelYt[i,j]*d2Yt_dwdx[i,j,k]
                        + dG_ddel2Yt[i,j]*d3Yt_dwdx2[i,j,k]
                    )
        if debug: print('G =', G)
        if debug: print('dG_dYt =', dG_dYt)
        if debug: print('dG_ddelYt =', dG_ddelYt)
        if debug: print('dG_ddel2Yt =', dG_ddel2Yt)
        if debug: print('dG_dv =', dG_dv)
        if debug: print('dG_du =', dG_du)
        if debug: print('dG_dw =', dG_dw)

        # Compute the error function for this pass.
        E = 0
        for i in range(n):
            E += G[i]**2
        if debug: print('E =', E)

        # Compute the partial derivatives of the error with respect to the
        # network parameters.
        dE_dv = np.zeros(H)
        dE_du = np.zeros(H)
        dE_dw = np.zeros((m, H))
        for k in range(H):
            for i in range(n):
                dE_dv[k] += 2*G[i]*dG_dv[i,k]
                dE_du[k] += 2*G[i]*dG_du[i,k]
            for j in range(m):
                for i in range(n):
                    dE_dw[j,k] += 2*G[i]*dG_dw[i,j,k]
        if debug: print('dE_dv =', dE_dv)
        if debug: print('dE_du =', dE_du)
        if debug: print('dE_dw =', dE_dw)

        #------------------------------------------------------------------------

        # Update the weights and biases.
    
        # Compute the new values of the network parameters.
        v_new = np.zeros(H)
        u_new = np.zeros(H)
        w_new = np.zeros((m, H))
        for k in range(H):
            v_new[k] = v[k] - eta*dE_dv[k]
            u_new[k] = u[k] - eta*dE_du[k]
            for j in range(m):
                w_new[j,k] = w[j,k] - eta*dE_dw[j,k]
        if debug: print('v_new =', v_new)
        if debug: print('u_new =', u_new)
        if debug: print('w_new =', w_new)

        if verbose: print(epoch, sqrt(E/n))

        # Save the new weights and biases.
        v = v_new
        u = u_new
        w = w_new

    # Return the final solution.
    return (Yt, dYt_dx, d2Yt_dx2)

#--------------------------------------------------------------------------------

# Begin main program.

if __name__ == '__main__':

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description = 'Solve a 2-variable, 2nd-order PDE BVP with a neural net',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
        epilog = 'Experiment with the settings to find what works.'
    )
    # print('parser =', parser)

    # Add command-line options.
    parser.add_argument('--debug', '-d',
                        action = 'store_true',
                        default = default_debug,
                        help = 'Produce debugging output')
    parser.add_argument('--eta', type = float,
                        default = default_eta,
                        help = 'Learning rate for parameter adjustment')
    parser.add_argument('--maxepochs', type = int,
                        default = default_maxepochs,
                        help = 'Maximum number of training epochs')
    parser.add_argument('--nhid', type = int,
                        default = default_nhid,
                        help = 'Number of hidden-layer nodes to use')
    parser.add_argument('--ntrain', type = int,
                        default = default_ntrain,
                        help = 'Number of evenly-spaced training points to use along each dimension')
    parser.add_argument('--pde', type = str,
                        default = default_pde,
                        help = 'Name of module containing PDE to solve')
    parser.add_argument('--seed', type = int,
                        default = default_seed,
                        help = 'Random number generator seed')
    parser.add_argument('--verbose', '-v',
                        action = 'store_true',
                        default = default_verbose,
                        help = 'Produce verbose output')
    parser.add_argument('--version', action = 'version',
                        version = '%(prog)s 0.0')

    # Fetch and process the arguments from the command line.
    args = parser.parse_args()
    if args.debug: print('args =', args)

    # Extract the processed options.
    debug = args.debug
    eta = args.eta
    maxepochs = args.maxepochs
    nhid = args.nhid
    ntrain = args.ntrain
    pde = args.pde
    seed = args.seed
    verbose = args.verbose
    if debug: print('debug =', debug)
    if debug: print('eta =', eta)
    if debug: print('maxepochs =', maxepochs)
    if debug: print('nhid =', nhid)
    if debug: print('ntrain =', ntrain)
    if debug: print('pde =', pde)
    if debug: print('seed =', seed)
    if debug: print('verbose =', verbose)

    # Perform basic sanity checks on the command-line options.
    assert eta > 0
    assert maxepochs > 0
    assert nhid > 0
    assert ntrain > 0
    assert pde
    assert seed >= 0

    #----------------------------------------------------------------------------

    # Initialize the random number generator to ensure repeatable results.
    if verbose: print('Seeding random number generator with value %d.' % seed)
    np.random.seed(seed)

    # Import the specified PDE module.
    if verbose:
        print('Importing PDE module %s.' % pde)
    pdemod = import_module(pde)
    assert pdemod.Gf
    assert len(pdemod.bcf) > 0
    assert len(pdemod.bcdf) == len(pdemod.bcf)
    assert len(pdemod.bcd2f) == len(pdemod.bcf)
    assert pdemod.dG_dYf
    assert pdemod.dG_ddelYf
    assert pdemod.dG_ddel2Yf
    assert pdemod.Yaf
    assert len(pdemod.delYaf) == len(pdemod.bcf)
    assert len(pdemod.del2Yaf) == len(pdemod.bcf)

    # Create the array of evenly-spaced training points. Use the same
    # values of the training points for each dimension.
    if verbose: print('Computing training points in [0,1] along 2 dimensions.')
    dxy = 1/(ntrain - 1)
    if debug: print('dxy =', dxy)
    xt = [i*dxy for i in range(ntrain)]
    if debug: print('xt =', xt)
    yt = xt
    if debug: print('yt =', yt)

    # Determine the number of training points.
    nxt = len(xt)
    if debug: print('nxt =', nxt)
    nyt = len(yt)
    if debug: print('nyt =', nyt)
    ntrain = nxt*nyt
    if debug: print('ntrain =', ntrain)

    # Create the list of training points.
    # ((x0,y0),(x1,y0),(x2,y0),...
    #  (x0,y1),(x1,y1),(x2,y1),...
    x = np.zeros((ntrain, 2))
    for j in range(nyt):
        for i in range(nxt):
            k = j*nxt + i
            x[k,0] = xt[i]
            x[k,1] = yt[j]
    if debug: print('x =', x)

    #----------------------------------------------------------------------------

    # Compute the PDE solution using the neural network.
    (Yt, delYt, del2Yt) = nnpde2bvp(
        pdemod.Gf,             # 2-variable, 1st-order PDE IVP to solve
        pdemod.dG_dYf,         # Partial of G wrt psi
        pdemod.dG_ddelYf,      # Partials of G wrt del psi
        pdemod.dG_ddel2Yf,     # Partials of G wrt del2 psi
        pdemod.bcf,            # BC functions
        pdemod.bcdf,           # BC function derivatives
        pdemod.bcd2f,          # BC function 2nd derivatives
        x,                     # Training points as pairs
        nhid = nhid,           # Node count in hidden layer
        maxepochs = maxepochs, # Max training epochs
        eta = eta,             # Learning rate
        debug = debug,
        verbose = verbose
    )

    #----------------------------------------------------------------------------

    # Compute the analytical solution at the training points.
    Ya = np.zeros(len(x))
    for i in range(len(x)):
        Ya[i] = pdemod.Yaf(x[i])
    if debug: print('Ya =', Ya)

    # Compute the analytical derivatives at the training points.
    delYa = np.zeros((len(x), len(x[1])))
    for i in range(len(x)):
        for j in range(len(x[0])):
            delYa[i,j] = pdemod.delYaf[j](x[i])
    if debug: print('delYa =', delYa)

    # Compute the analytical 2nd derivatives at the training points.
    del2Ya = np.zeros((len(x), len(x[1])))
    for i in range(len(x)):
        for j in range(len(x[0])):
            del2Ya[i,j] = pdemod.del2Yaf[j](x[i])
    if debug: print('del2Ya =', del2Ya)

    # Compute the RMSE of the trial solution.
    Yerr = Yt - Ya
    if debug: print('Yerr =', Yerr)
    rmseY = sqrt(sum(Yerr**2)/len(x))
    if debug: print('rmseY =', rmseY)

    # Compute the RMSE of the trial derivative.
    delYerr = delYt - delYa
    if debug: print('delYerr =', delYerr)
    rmsedelY = np.zeros(len(x[0]))
    e2sum = np.zeros(len(x[0]))
    for j in range(len(x[0])):
        for i in range(len(x)):
            e2sum[j] += delYerr[i,j]**2
        rmsedelY[j] = sqrt(e2sum[j]/len(x))
    if debug: print('rmsedelY =', rmsedelY)

    # Compute the RMSE of the 2nd trial derivative.
    del2Yerr = del2Yt - del2Ya
    if debug: print('del2Yerr =', del2Yerr)
    rmsedel2Y = np.zeros(len(x[0]))
    e2sum = np.zeros(len(x[0]))
    for j in range(len(x[0])):
        for i in range(len(x)):
            e2sum[j] += del2Yerr[i,j]**2
        rmsedel2Y[j] = sqrt(e2sum[j]/len(x))
    if debug: print('rmsedel2Y =', rmsedel2Y)

    # Print the report.
    print('    x        y       Ya       Yt     dYa_dx   dYt_dx   dYa_dy   dYt_dy  d2Ya_dx2 d2Yt_dx2 d2Ya_dy2 d2Yt_dy2')
    for i in range(len(Ya)):
        print('%.6f %.6f|%.6f %.6f|%.6f %.6f|%.6f %.6f|%.6f %.6f|%.6f %.6f' %
              (x[i,0], x[i,1],
               Ya[i], Yt[i],
               delYa[i,0], delYt[i,0], delYa[i,1], delYt[i,1],
               del2Ya[i,0], del2Yt[i,0], del2Ya[i,1], del2Yt[i,1]
              )
    )
    print('RMSE                       %f          %f          %f          %f          %f' %
          (rmseY, rmsedelY[0], rmsedelY[1], rmsedel2Y[0], rmsedel2Y[1]))