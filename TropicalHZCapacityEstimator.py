# HZCapacityEstimator class

import numpy as np
from scipy import optimize
from math  import sqrt, fabs, exp, log

# implements a version of the algeorithm in HZCapacityEstimator

# the function H is a strictly convex, quadratic growth approximation 
# of the piecewise linear function whose sublevel set is a triangle with 
# area = HZcapacity = 4.5

class TropicalHZCapacityEstimator:
    
    def __init__(self, m, t=4.):
        # temporarily demand that n=1
        self.n = 1
        if m >=3:
            self.m = m
        else: self.m=3
        
        # define the matrix J, used frequently in the algorithm.
        Z = np.zeros((self.n,self.n))
        I = np.identity(self.n)
        self.J = np.block([[Z,I],[-I,Z]])

        self.t = t

        return

    def H(self,x):  
        # Assume x is a vector in R^2
        # function H is a tropical estimate of the piecewise linear function that defines a triangle of area 4.5
        return (log( exp(self.t*(x[0]+x[1])) + exp(-self.t*x[0]) + exp(-self.t*x[1]) )/self.t)**2

    def dH(self,x):
        # Assume x is a vector in R^2
        dH = np.zeros(x.shape)
        a = (2/self.t)*log( exp(self.t*(x[0]+x[1])) + exp(-self.t*x[0]) + exp(-self.t*x[1]) )
        a = a/( exp(self.t*(x[0]+x[1])) + exp(-self.t*x[0]) + exp(-self.t*x[1]) )
        dH[0] = a*(exp(self.t*(x[0]+x[1])) - exp(-self.t*x[0]))
        dH[1] = a*(exp(self.t*(x[0]+x[1])) - exp(-self.t*x[1]))

        # define the jacobian

        return dH - self.y, jac 

    def dG(self,y):
        # Assume x is a vector in R^2
        # Estimates dH inverse = dG using scipy.optimize
        self.y = y
        sol = optimize.root(self.dH, [.1,.1], method='hybr',jac=True)


        return sol.x

    def G(self,y):
        # Assume y is a vector in R^2n
        # G(y) is the Legendre transform of H(x)
        x = self.dG(y)   
        return np.sum(y*x) - self.H(x)

    def proj(self,x):
        #   Orthogonal projection to the subspace H
        #   described in section 2.3 of the paper, equation (2.17)
        #   Assume x is a 2n x m matrix

        s = np.sum(x,axis = 1,keepdims=True)

        return x - s/self.m

    def F(self,x):
        #   Assume x is a 2n x m matrix

        A = -np.dot(self.J,x)
        S = 0.
        for i in range(0,self.m):
            S += self.G(A[:,i])

        return S/self.m

    def dF(self,x):
        #   Assume x is a 2n x m matrix

        A = -np.dot(self.J,x)

        for i in range(0,self.m):
            A[:,i] = np.dot(self.J, self.dG(A[:,i])) 

        return A/self.m 

    def A2n(self,x):
        # Compute the product A2n x 
        # (see paper sec. 2.1 equation (2.5))

        A = -np.dot(self.J,x)
        b = np.zeros(x.shape)

        for k in range (0,self.m):
            for j in range (k+1,self.m):
                b[:,k] += A[:,j]

        return b
    
    def f(self,x):
        # Compute f(x) 
        # (see paper sec. 2.1 equation (2.5))
        f = np.sum(x*self.A2n(x))/(self.m**2.) - 1.
        return f

    def df(self,x):
        # Compute the product (A2n + A2n^T)x /m^2
        # (see G-J sec. 2.1 equation (2.11))

        return (self.A2n(x) - np.flip(self.A2n(np.flip(x,axis=1)),axis=1))/(self.m**2.)
    
    def randomStartingPoint(self,epsilon):
        # Starting point for gradient descent needs to be in the constraint submanifold
        # where f(x) = 0 and np.sum(x,axis = 1,keepdims=True) = 0

        c = 0.
        while c < epsilon:
            x = 0.5-np.random.rand(2*self.n,self.m)
            x = self.proj(x)
            c = self.f(x)+1.
        
        if c > 0.:
            return x/sqrt(c)
        else:
            # reversing the order of columns in x changes the sign of f(x)+1
            return np.flip(x,axis = -1)/sqrt(-c)

    def estimate(self, iterations = 100, epsilon = 10.**(-12), VOCAL = True):
        # Estimates the Hofer-Zehnder capacity of the convex body using 
        # projected gradients to solve the convex constrained optimization 
        # problem (see the thesis of GJ for details).
       
        k = 0
        
        # create random x_0 in the space M_m
        np.random.seed(0)
        x = self.randomStartingPoint(epsilon)
        
        while k < iterations:

            k = k + 1
            if VOCAL:
                print("At k =", k, ", F(x) =", self.F(x),", f(x) =", self.f(x))

            # Part 1

            a     = self.df(x)                                        # calculate a_k
            y     = -self.dF(x)                                       # calculate y_k
            a_H   = self.proj(a)                                      # calculate a_kH
            y_hat = self.proj(y) - a_H*np.sum(a_H*y)/np.sum(a_H*a_H)  # calculate y_k hat

            # Part 2

            if np.sum(y_hat*y_hat) < epsilon:
                if VOCAL:
                    print("Early stop at iteration ", k)
                    print("The estimated Hofer-Zehnder capacity of the unit ball is ", 2*self.F(x))
                return 2*self.F(x)

            # Part 3

            else:
                L_max   = self.m * sqrt( 3./fabs( np.sum( y_hat* self.A2n(y_hat) ) ))/2.
                h_kLmax = np.sum(-y_hat * self.dF(x + L_max*y_hat))
                h_k0    = np.sum(y_hat*y_hat)

                if h_kLmax >= 0:
                    L_0 = L_max

                else:
                    L_0 = L_max * h_k0/(h_k0-h_kLmax)

                carryOn = True
                
                while carryOn:

                    c_L0  = self.f(L_0 * y_hat) + 2.
                    x_L0  = x + L_0 * y_hat
                    x_ML0 = x_L0/sqrt(c_L0)

                    del_1 = self.F(x) - self.F(x_L0)
                    del_2 = self.F(x) - self.F(x_ML0)

                    if 4.*del_2 <= del_1:
                        L_0 = L_0/2.
                    else:
                        carryOn  = False
                        x        = x_ML0

        if VOCAL:
            print("The estimated Hofer-Zehnder capacity of the unit ball is ", 2*self.F(x))
            # self.plot(x)
        return 2*self.F(x)

    def plot(self,x):
    
        return


