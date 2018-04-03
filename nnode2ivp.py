#!/usr/bin/env python

# Use a neural network to solve a 2nd-order ODE IVP, with Neumann BC,
# i.e. the value of the solution and its derivative are specified at
# x=0, in solution region [0,1]. Note that any 2nd-order IVP can be
# mapped to a corresponding IVP with initial values at 0, so this is
# the only solution form needed.

#********************************************************************************

# Import external modules, using standard shorthand.

import argparse
import importlib
from math import sqrt
import numpy as np

from sigma import sigma, dsigma_dz, d2sigma_dz2, d3sigma_dz3, d4sigma_dz4

#********************************************************************************

# Default values for program parameters
default_debug = False
default_eta = 0.01
default_maxepochs = 1000
default_nhid = 10
default_ntrain = 10
default_ode = 'lagaris03ivp'
default_seed = 0
default_verbose = False

# Default ranges for weights and biases
v_min = -1
v_max = 1
u_min = -1
u_max = 1
w_min = -1
w_max = 1

#********************************************************************************

# Define the trial solution for a 2nd-order ODE IVP.
def ytrial(A, Ap, x, N):
    return (
        A + x * Ap + N * x**2
    )

# Define the 1st trial derivative.
def dytrial_dx(A, Ap, x, N, dN_dx):
    return (
        Ap + N * 2 * x + dN_dx * x**2
    )

# Define the 2nd trial derivative.
def d2ytrial_dx2(A, Ap, x, N, dN_dx, d2N_dx2):
    return (
        N * 2 + dN_dx * 2 * x + dN_dx * 2 * x + d2N_dx2 * x**2
    )

#********************************************************************************

# Function to solve a 2nd-order ODE IVP using a single-hidden-layer
# feedforward neural network.
def nnode2ivp(x,                             # x-values for training points
              F,                             # Original 2nd-order ODE
              dF_dy,                         # 1st derivative of F wrt y
              d2F_dy2,                       # 2nd derivative of F wrt y
              A,                             # Boundary value at x=0
              Ap,                            # 1st derivative at x=0
              maxepochs = default_maxepochs, # Training epochs to use
              eta = default_eta,             # Normalized learning rate
              nhid = default_nhid,           # Nodes in hidden layer
              debug = default_debug, verbose = default_verbose):

    if debug: print('x =', x)
    if debug: print('F =', F)
    if debug: print('dF_dy =', dF_dy)
    if debug: print('d2F_dy2 =', d2F_dy2)
    if debug: print('A =', A)
    if debug: print('Ap =', Ap)
    if debug: print('maxepochs =', maxepochs)
    if debug: print('eta =', eta)
    if debug: print('nhid =', nhid)
    if debug: print('debug =', debug)
    if debug: print('verbose =', verbose)

    # Sanity-check arguments.
    assert len(x) > 0
    assert F
    assert dF_dy
    assert d2F_dy2
    assert A != None
    assert Ap != None
    assert maxepochs > 0
    assert eta > 0
    assert nhid > 0

    #----------------------------------------------------------------------------

    # Determine the number of training points.
    ntrain = len(x)
    if debug: print('ntrain =', ntrain)

    #----------------------------------------------------------------------------

    # Create the network.

    # Create an array to hold the weights connecting the input node to the
    # hidden nodes. The weights are initialized with a uniform random
    # distribution.
    w = np.random.uniform(w_min, w_max, nhid)
    if debug: print('w =', w)

    # Create an array to hold the weights connecting the hidden nodes
    # to the output node. The weights are initialized with a uniform
    # random distribution.
    v = np.random.uniform(v_min, v_max, nhid)
    if debug: print('v =', v)

    # Create an array to hold the biases for the hidden nodes. The
    # biases are initialized with a uniform random distribution.
    u = np.random.uniform(u_min, u_max, nhid)
    if debug: print('u =', u)

    #----------------------------------------------------------------------------

    # Run the network.
    for epoch in range(maxepochs):

        if debug: print('Starting epoch %d.' % epoch)

        # General note:
        # i is an index into the training point array
        # j is an index for the nodes in the hidden layer

        # Compute the input to each hidden node using the weights and
        # biases, then compute the sigmoid activation function (and
        # its first 4 derivatives) for this input.
        z = np.zeros((ntrain, nhid))
        s = np.zeros((ntrain, nhid))
        s1 = np.zeros((ntrain, nhid))
        s2 = np.zeros((ntrain, nhid))
        s3 = np.zeros((ntrain, nhid))
        s4 = np.zeros((ntrain, nhid))
        for i in range(ntrain):
            for j in range(nhid):
                z[i][j] = w[j] * x[i] + u[j]
                s[i][j] = sigma(z[i][j])
                s1[i][j] = dsigma_dz(z[i][j])
                s2[i][j] = d2sigma_dz2(z[i][j])
                s3[i][j] = d3sigma_dz3(z[i][j])
                s4[i][j] = d4sigma_dz4(z[i][j])
        if debug: print('z =', z)
        if debug: print('s =', s)
        if debug: print('s1 =', s1)
        if debug: print('s2 =', s2)
        if debug: print('s3 =', s3)
        if debug: print('s4 =', s4)
        N = np.zeros(ntrain)
        dN_dx = np.zeros(ntrain)
        d2N_dx2 = np.zeros(ntrain)
        dN_dv = np.zeros((ntrain, nhid))
        dN_du = np.zeros((ntrain, nhid))
        dN_dw = np.zeros((ntrain, nhid))
        d2N_dv2 = np.zeros((ntrain, nhid))
        d2N_du2 = np.zeros((ntrain, nhid))
        d2N_dw2 = np.zeros((ntrain, nhid))
        d2N_dvdx = np.zeros((ntrain, nhid))
        d2N_dudx = np.zeros((ntrain, nhid))
        d2N_dwdx = np.zeros((ntrain, nhid))
        d3N_dv2dx = np.zeros((ntrain, nhid))
        d3N_du2dx = np.zeros((ntrain, nhid))
        d3N_dw2dx = np.zeros((ntrain, nhid))
        d3N_dvdx2 = np.zeros((ntrain, nhid))
        d3N_dudx2 = np.zeros((ntrain, nhid))
        d3N_dwdx2 = np.zeros((ntrain, nhid))
        d4N_dv2dx2 = np.zeros((ntrain, nhid))
        d4N_du2dx2 = np.zeros((ntrain, nhid))
        d4N_dw2dx2 = np.zeros((ntrain, nhid))
        for i in range(ntrain):
            for j in range(nhid):
                N[i] += v[j] * s[i][j]
                dN_dx[i] += v[j] * s1[i][j] * w[j]
                d2N_dx2[i] += v[j] * s2[i][j] * w[j]**2
                dN_dv[i][j] = s[i][j]
                dN_du[i][j] = v[j] * s1[i][j]
                dN_dw[i][j] = v[j] * s1[i][j] * x[i]
                d2N_dv2[i][j] = 0
                d2N_du2[i][j] = v[j] * s2[i][j]
                d2N_dw2[i][j] = v[j] * s2[i][j] * x[i]**2
                d2N_dvdx[i][j] = s1[i][j] * w[j]
                d2N_dudx[i][j] = v[j] * s2[i][j] * w[j]
                d2N_dwdx[i][j] = v[j] * (s1[i][j] + s2[i][j] * w[j] * x[i])
                d3N_dv2dx[i][j] = 0
                d3N_du2dx[i][j] = v[j] * s3[i][j] * w[j]
                d3N_dw2dx[i][j] = (
                    v[j] * (
                        s2[i][j] * x[i] +
                        (s2[i][j] + s3[i][j] * w[j] * x[i]) * x[i]
                    )
                )
                d3N_dvdx2[i][j] = s2[i][j] * w[j]**2
                d3N_dudx2[i][j] = v[j] * s3[i][j] * w[j]**2
                d3N_dwdx2[i][j] = (
                    v[j] * (2 * s2[i][j] * w[j] + s3[i][j] * w[j]**2 * x[i])
                )
                d4N_dv2dx2[i][j] = 0
                d4N_du2dx2[i][j] = v[j] * s4[i][j] * w[j]**2
                d4N_dw2dx2[i][j] = (
                    v[j] * (
                        2 * s2[i][j] + 2 * s3[i][j] * x[i] * w[j] +
                        (s3[i][j] * 2 * w[j] + s4[i][j] * w[j]**2 * x[i]) * x[i]
                    )
                )
        if debug: print('N =', N)
        if debug: print('dN_dx =', dN_dx)
        if debug: print('d2N_dx2 =', d2N_dx2)
        if debug: print('dN_dv =', dN_dv)
        if debug: print('dN_du =', dN_du)
        if debug: print('dN_dw =', dN_dw)
        if debug: print('d2N_dv2 =', d2N_dv2)
        if debug: print('d2N_du2 =', d2N_du2)
        if debug: print('d2N_dw2 =', d2N_dw2)
        if debug: print('d2N_dvdx =', d2N_dvdx)
        if debug: print('d2N_dudx =', d2N_dudx)
        if debug: print('d2N_dwdx =', d2N_dwdx)
        if debug: print('d3N_dv2dx =', d3N_dv2dx)
        if debug: print('d3N_du2dx =', d3N_du2dx)
        if debug: print('d3N_dw2dx =', d3N_dw2dx)
        if debug: print('d3N_dvdx2 =', d3N_dvdx2)
        if debug: print('d3N_dudx2 =', d3N_dudx2)
        if debug: print('d3N_dwdx2 =', d3N_dwdx2)
        if debug: print('d4N_dv2dx2 =', d4N_dv2dx2)
        if debug: print('d4N_du2dx2 =', d4N_du2dx2)
        if debug: print('d4N_dw2dx2 =', d4N_dw2dx2)

        #------------------------------------------------------------------------

        # Compute the value of the trial solution and its derivatives
        # for each training point.
        yt = np.zeros(ntrain)
        dyt_dx = np.zeros(ntrain)
        d2yt_dx2 = np.zeros(ntrain)
        dyt_dv = np.zeros((ntrain, nhid))
        dyt_du = np.zeros((ntrain, nhid))
        dyt_dw = np.zeros((ntrain, nhid))
        d2yt_dv2 = np.zeros((ntrain, nhid))
        d2yt_du2 = np.zeros((ntrain, nhid))
        d2yt_dw2 = np.zeros((ntrain, nhid))
        d2yt_dvdx = np.zeros((ntrain, nhid))
        d2yt_dudx = np.zeros((ntrain, nhid))
        d2yt_dwdx = np.zeros((ntrain, nhid))
        d3yt_dv2dx = np.zeros((ntrain, nhid))
        d3yt_du2dx = np.zeros((ntrain, nhid))
        d3yt_dw2dx = np.zeros((ntrain, nhid))
        d3yt_dvdx2 = np.zeros((ntrain, nhid))
        d3yt_dudx2 = np.zeros((ntrain, nhid))
        d3yt_dwdx2 = np.zeros((ntrain, nhid))
        d4yt_dv2dx2 = np.zeros((ntrain, nhid))
        d4yt_du2dx2 = np.zeros((ntrain, nhid))
        d4yt_dw2dx2 = np.zeros((ntrain, nhid))
        for i in range(ntrain):
            yt[i] = ytrial(A, Ap, x[i], N[i])
            dyt_dx[i] = dytrial_dx(A, Ap, x[i], N[i], dN_dx[i])
            d2yt_dx2[i] = d2ytrial_dx2(A, Ap, x[i], N[i], dN_dx[i], d2N_dx2[i])
            for j in range(nhid):
                dyt_dv[i][j] = dN_dv[i][j] * x[i]**2
                dyt_du[i][j] = dN_du[i][j] * x[i]**2
                dyt_dw[i][j] = dN_dw[i][j] * x[i]**2
                d2yt_dv2[i][j] = d2N_dv2[i][j] * x[i]**2
                d2yt_du2[i][j] = d2N_du2[i][j] * x[i]**2
                d2yt_dw2[i][j] = d2N_dw2[i][j] * x[i]**2
                d2yt_dvdx[i][j] = (
                    dN_dv[i][j] * 2 * x[i] + d2N_dvdx[i][j] * x[i]**2
                )
                d2yt_dudx[i][j] = (
                    dN_du[i][j] * 2 * x[i] + d2N_dudx[i][j] * x[i]**2
                )
                d2yt_dwdx[i][j] = (
                    dN_dw[i][j] * 2 * x[i] + d2N_dwdx[i][j] * x[i]**2
                )
                d3yt_dv2dx[i][j] = (
                    d2N_dv2[i][j] * 2 * x[i] + d3N_dv2dx[i][j] * x[i]**2
                )
                d3yt_du2dx[i][j] = (
                    d2N_du2[i][j] * 2 * x[i] + d3N_du2dx[i][j] * x[i]**2
                )
                d3yt_dw2dx[i][j] = (
                    d2N_dw2[i][j] * 2 * x[i] + d3N_dw2dx[i][j] * x[i]**2
                )
                d3yt_dvdx2[i][j] = (
                    dN_dv[i][j] * 2 + 4 * d2N_dvdx[i][j] * x[i]
                    + d3N_dvdx2[i][j] * x[i]**2
                )
                d3yt_dudx2[i][j] = (
                    dN_du[i][j] * 2 + 4 * d2N_dudx[i][j] * x[i]
                    + d3N_dudx2[i][j] * x[i]**2
                )
                d3yt_dwdx2[i][j] = (
                    dN_dw[i][j] * 2 + 4 * d2N_dwdx[i][j] * x[i]
                    + d3N_dwdx2[i][j] * x[i]**2
                )
                d4yt_dv2dx2[i][j] = (
                    d2N_dv2[i][j] * 2 + 4 * d3N_dv2dx[i][j] * x[i]
                    + d4N_dv2dx2[i][j] * x[i]**2
                )
                d4yt_du2dx2[i][j] = (
                    d2N_du2[i][j] * 2 + 4 * d3N_du2dx[i][j] * x[i]
                    + d4N_du2dx2[i][j] * x[i]**2
                )
                d4yt_dw2dx2[i][j] = (
                    d2N_dw2[i][j] * 2 + 4 * d3N_dw2dx[i][j] * x[i]
                    + d4N_dw2dx2[i][j] * x[i]**2
                )
        if debug: print('yt =', yt)
        if debug: print('dyt_dx =', dyt_dx)
        if debug: print('d2yt_dx2 =', d2yt_dx2)
        if debug: print('dyt_dv =', dyt_dv)
        if debug: print('dyt_du =', dyt_du)
        if debug: print('dyt_dw =', dyt_dw)
        if debug: print('d2yt_dv2 =', d2yt_dv2)
        if debug: print('d2yt_du2 =', d2yt_du2)
        if debug: print('d2yt_dw2 =', d2yt_dw2)
        if debug: print('d2yt_dvdx =', d2yt_dvdx)
        if debug: print('d2yt_dudx =', d2yt_dudx)
        if debug: print('d2yt_dwdx =', d2yt_dwdx)
        if debug: print('d3yt_dv2dx =', d3yt_dv2dx)
        if debug: print('d3yt_du2dx =', d3yt_du2dx)
        if debug: print('d3yt_dw2dx =', d3yt_dw2dx)
        if debug: print('d3yt_dvdx2 =', d3yt_dvdx2)
        if debug: print('d3yt_dudx2 =', d3yt_dudx2)
        if debug: print('d3yt_dwdx2 =', d3yt_dwdx2)
        if debug: print('d4yt_dv2dx2 =', d4yt_dv2dx2)
        if debug: print('d4yt_du2dx2 =', d4yt_du2dx2)
        if debug: print('d4yt_dw2dx2 =', d4yt_dw2dx2)

        # Compute the value of the original 2nd derivative function
        # for each training point, and its derivatives.
        f = np.zeros(ntrain)
        df_dyt = np.zeros(ntrain)
        d2f_dyt2 = np.zeros(ntrain)
        df_dv = np.zeros((ntrain, nhid))
        df_du = np.zeros((ntrain, nhid))
        df_dw = np.zeros((ntrain, nhid))
        d2f_dv2 = np.zeros((ntrain, nhid))
        d2f_du2 = np.zeros((ntrain, nhid))
        d2f_dw2 = np.zeros((ntrain, nhid))
        for i in range(ntrain):
            f[i] = F(x[i], yt[i], dyt_dx[i])
            df_dyt[i] = dF_dy(x[i], yt[i], dyt_dx[i])
            d2f_dyt2[i] = d2F_dy2(x[i], yt[i], dyt_dx[i])
            for j in range(nhid):
                df_dv[i][j] = df_dyt[i] * dyt_dv[i][j]
                df_du[i][j] = df_dyt[i] * dyt_du[i][j]
                df_dw[i][j] = df_dyt[i] * dyt_dw[i][j]
                d2f_dv2[i][j] = (
                    df_dyt[i] * d2yt_dv2[i][j] + d2f_dyt2[i] * dyt_dv[i][j]**2
                )
                d2f_du2[i][j] = (
                    df_dyt[i] * d2yt_du2[i][j] + d2f_dyt2[i] * dyt_du[i][j]**2
                )
                d2f_dw2[i][j] = (
                    df_dyt[i] * d2yt_dw2[i][j] + d2f_dyt2[i] * dyt_dw[i][j]**2
                )
        if debug: print('f =', f)
        if debug: print('df_dyt =', df_dyt)
        if debug: print('d2f_dyt2 =', d2f_dyt2)
        if debug: print('df_dv =', df_dv)
        if debug: print('df_du =', df_du)
        if debug: print('df_dw =', df_dw)
        if debug: print('d2f_dv2 =', d2f_dv2)
        if debug: print('d2f_du2 =', d2f_du2)
        if debug: print('d2f_dw2 =', d2f_dw2)

        # Compute the error function for this pass.
        E = 0
        for i in range(ntrain):
            E += (d2yt_dx2[i] - f[i])**2
        if debug: print('E =', E)

        # Compute the partial derivatives of the error with respect to
        # the network parameters.
        dE_dv = np.zeros(nhid)
        dE_du = np.zeros(nhid)
        dE_dw = np.zeros(nhid)
        d2E_dv2 = np.zeros(nhid)
        d2E_du2 = np.zeros(nhid)
        d2E_dw2 = np.zeros(nhid)
        for j in range(nhid):
            for i in range(ntrain):
                dE_dv[j] += (
                    2 * (d2yt_dx2[i] - f[i]) * (d3yt_dvdx2[i][j] - df_dv[i][j])
                )
                dE_du[j] += (
                    2 * (d2yt_dx2[i] - f[i]) * (d3yt_dudx2[i][j] - df_du[i][j])
                )
                dE_dw[j] += (
                    2 * (d2yt_dx2[i] - f[i]) * (d3yt_dwdx2[i][j] - df_dw[i][j])
                )
                d2E_dv2[j] += 2 * (
                    (d2yt_dx2[i] - f[i]) * (d4yt_dv2dx2[i][j] - d2f_dv2[i][j])
                    + (d3yt_dvdx2[i][j] - df_dv[i][j])**2
                )
                d2E_du2[j] += 2 * (
                    (d2yt_dx2[i] - f[i]) * (d4yt_du2dx2[i][j] - d2f_du2[i][j])
                    + (d3yt_dudx2[i][j] - df_du[i][j])**2
                )
                d2E_dw2[j] += 2 * (
                    (d2yt_dx2[i] - f[i]) * (d4yt_dw2dx2[i][j] - d2f_dw2[i][j])
                    + (d3yt_dwdx2[i][j] - df_dw[i][j])**2
                )
        if debug: print('dE_dv =', dE_dv)
        if debug: print('dE_du =', dE_du)
        if debug: print('dE_dw =', dE_dw)
        if debug: print('d2E_dv2 =', d2E_dv2)
        if debug: print('d2E_du2 =', d2E_du2)
        if debug: print('d2E_dw2 =', d2E_dw2)

        #------------------------------------------------------------------------

        # Update the weights and biases.
    
        # Compute the new values of the network parameters.
        v_new = np.zeros(nhid)
        u_new = np.zeros(nhid)
        w_new = np.zeros(nhid)
        for j in range(nhid):
            v_new[j] = v[j] - eta * dE_dv[j] / d2E_dv2[j]
            u_new[j] = u[j] - eta * dE_du[j] / d2E_du2[j]
            w_new[j] = w[j] - eta * dE_dw[j] / d2E_dw2[j]
        if debug: print('v_new =', v_new)
        if debug: print('u_new =', u_new)
        if debug: print('w_new =', w_new)

        if verbose: print(epoch, E)

        # Save the new weights and biases.
        v = v_new
        u = u_new
        w = w_new

    # Return the final solution.
    return (yt, dyt_dx, d2yt_dx2)

#--------------------------------------------------------------------------------

# Begin main program.

if __name__ == '__main__':

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description =
        'Solve a 2nd-order ODE IVP with Neumann BC with a neural net',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
        epilog = 'Experiment with the settings to find what works.'
    )
    print('parser =', parser)

    # Add command-line options.
    parser.add_argument('--debug', '-d',
                        action = 'store_true',
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
                        help = 'Number of evenly-spaced training points to use')
    parser.add_argument('--ode', type = str,
                        default = default_ode,
                        help = 'Name of module containing ODE to solve')
    parser.add_argument('--seed', type = int,
                        default = default_seed,
                        help = 'Random number generator seed')
    parser.add_argument('--verbose', '-v',
                        action = 'store_true',
                        help = 'Produce verbose output')
    parser.add_argument('--version',
                        action = 'version',
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
    ode = args.ode
    seed = args.seed
    verbose = args.verbose

    if debug: print('debug =', debug)
    if debug: print('eta =', eta)
    if debug: print('maxepochs =', maxepochs)
    if debug: print('nhid =', nhid)
    if debug: print('ntrain =', ntrain)
    if debug: print('ode =', ode)
    if debug: print('seed =', seed)

    # Perform basic sanity checks on the command-line options.
    assert eta > 0
    assert maxepochs > 0
    assert nhid > 0
    assert ntrain > 0
    assert ode
    assert seed >= 0

    #----------------------------------------------------------------------------

    # Initialize the random number generator to ensure repeatable results.
    if verbose: print('Seeding random number generator with value %d.' % seed)
    np.random.seed(seed)

    # Import the specified ODE module.
    odemod = importlib.import_module(ode)
    assert odemod.ya
    assert odemod.dya_dx
    assert odemod.d2ya_dx2
    assert odemod.F
    assert odemod.dF_dy
    assert odemod.d2F_dy2
    assert odemod.ymin != None
    assert odemod.dy_dx_min != None

    # Create the array of evenly-spaced training points.
    if verbose: print('Computing training points in domain[0,1].')
    dx = 1 / (ntrain - 1)
    if debug: print('dx =', dx)
    xt = [i * dx for i in range(ntrain)]
    if debug: print('xt =', xt)

    #----------------------------------------------------------------------------

    # Compute the 2nd-order ODE solution using the neural network.
    (yt, dyt_dx, d2yt_dx2) = nnode2ivp(xt, # x-values for training points
                                       odemod.F, # Original 2nd-order ODE
                                       odemod.dF_dy, # 1st deriv. of F wrt y
                                       odemod.d2F_dy2, # 2nd deriv. of F wrt y
                                       odemod.ymin, # Boundary value at x=0
                                       odemod.dy_dx_min, # 1st derivative at x=1
                                       maxepochs = maxepochs, # Training epochs
                                       eta = eta, # Normalized learning rate
                                       nhid = nhid, # Nodes in hidden layer
                                       debug = debug, verbose = verbose)

    #----------------------------------------------------------------------------

    # Compute the analytical solution at the training points.
    ya = np.zeros(ntrain)
    for i in range(ntrain):
        ya[i] = odemod.ya(xt[i])
    if debug: print('ya =', ya)

    # Compute the 1st analytical derivative at the training points.
    dya_dx = np.zeros(ntrain)
    for i in range(ntrain):
        dya_dx[i] = odemod.dya_dx(xt[i])
    if debug: print('dya_dx =', dya_dx)

    # Compute the 2nd analytical derivative at the training points.
    d2ya_dx2 = np.zeros(ntrain)
    for i in range(ntrain):
        d2ya_dx2[i] = odemod.d2ya_dx2(xt[i])
    if debug: print('d2ya_dx2 =', d2ya_dx2)

    # Compute the RMS error of the trial solution.
    y_err = yt - ya
    if debug: print('y_err =', y_err)
    rmse_y = sqrt(sum((yt - ya)**2) / ntrain)
    if debug: print('rmse_y =', rmse_y)

    # Compute the RMS error of the 1st trial derivative.
    dy_dx_err = dyt_dx - dya_dx
    if debug: print('dy_dx_err =', dy_dx_err)
    rmse_dy_dx = sqrt(sum((dyt_dx - dya_dx)**2) / ntrain)
    if debug: print('rmse_dy_dx =', rmse_dy_dx)

    # Compute the RMS error of the 2nd trial derivative.
    d2y_dx2_err = d2yt_dx2 - d2ya_dx2
    if debug: print('d2y_dx2_err =', d2y_dx2_err)
    rmse_d2y_dx2 = sqrt(sum((d2yt_dx2 - d2ya_dx2)**2) / ntrain)
    if debug: print('rmse_d2y_dx2 =', rmse_d2y_dx2)

    # Print the report.
    print('    xt       yt       ya      dyt_dx    dya_dx   d2yt_dx2  d2ya_dx2')
    for i in range(ntrain):
        print('%f %f %f %f %f %f %f' %
              (xt[i], yt[i], ya[i], dyt_dx[i], dya_dx[i],
               d2ya_dx2[i], d2yt_dx2[i])
        )
    print('RMSE     %f          %f           %f' %
          (rmse_y, rmse_dy_dx, rmse_d2y_dx2)
    )