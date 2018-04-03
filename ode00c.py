# Sample 1st-order ODE IVP

from math import sqrt, sin, cos

# A reasonable solution can be found using the following settings:
# 

# The equation is defined on the domain [0,1], with the boundary
# conditions defined at x=0.

# Define the original differential equation, assumed to be in the form
# G(x,y,dy/dx) = dy/dx - sqrt(1 - y**2) = 0, y(0) = 0
# Solution is y(x) = sin(x)
def Gf(x, y, dy_dx):
    print(x, y, dy_dx)
    return dy_dx - sqrt(1 - y**2)

# Initial condition
ic = 0

# Derivatives of ODE

def dG_dyf(x, y, dy_dx):
    return y / sqrt(1 - y**2)

def dG_dydxf(x, y, dy_dx):
    return 1

# Define the analytical solution.
def yaf(x):
    return sin(x)

# Define the 1st analytical derivative.
def dya_dxf(x):
    return cos(x)