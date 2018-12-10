# UQpy is distributed under the MIT license.
#
# Copyright (C) 2018  -- Michael D. Shields
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""This module contains functionality for all the surrogate methods supported in UQpy."""

import numpy as np
import scipy.stats as stats
from UQpy.Distributions import *
from scipy.spatial.distance import pdist, cdist, squareform


########################################################################################################################
########################################################################################################################
#                                         Stochastic Reduced Order Model  (SROM)                                       #
########################################################################################################################
########################################################################################################################

class SROM:

    """

        Description:

            Stochastic Reduced Order Model(SROM) provide a low-dimensional, discrete approximation of a given random
            quantity.
            SROM generates a discrete approximation of continuous random variables. The probabilities/weights are
            considered to be the parameters for the SROM and they can be obtained by minimizing the error between the
            marginal distributions, first and second order moments about origin and correlation between random variables
            References:
            M. Grigoriu, "Reduced order models for random functions. Application to stochastic problems",
                Applied Mathematical Modelling, Volume 33, Issue 1, Pages 161-175, 2009.
        Input:
            :param samples: An array/list of samples corresponding to each random variables

            :param cdf_target: A list of Cumulative distribution functions of random variables
            :type cdf_target: list str or list function

            :param cdf_target_params: Parameters of distribution
            :type cdf_target_params: list

            :param moments: A list containing first and second order moment about origin of all random variables

            :param weights_errors: Weights associated with error in distribution, moments and correlation.
                                   Default: weights_errors = [1, 0.2, 0]
            :type weights_errors: list

            :param properties: A list of booleans representing properties, which are required to match in reduce
                               order model. This class focus on reducing errors in distribution, first order moment
                               about origin, second order moment about origin and correlation of samples.
                               Default: properties = [True, True, True, False]
                               Example: properties = [True, True, False, False] will minimize errors in distribution and
                               errors in first order moment about origin in reduce order model.
            :type properties: list

            :param weights_distribution: An list or array containing weights associated with different samples.
                                         Options:
                                            If weights_distribution is None, then default value is assigned.
                                            If size of weights_distribution is 1xd, then it is assigned as dot product
                                                of weights_distribution and default value.
                                            Otherwise size of weights_distribution should be equal to Nxd.
                                         Default: weights_distribution = Nxd dimensional array with all elements equal
                                         to 1.

            :param weights_moments: An array of dimension 2xd, where 'd' is number of random variables. It contain
                                    weights associated with moments.
                                    Options:
                                        If weights_moments is None, then default value is assigned.
                                        If size of weights_moments is 1xd, then it is assigned as dot product
                                            of weights_moments and default value.
                                        Otherwise size of weights_distribution should be equal to 2xd.
                                    Default: weights_moments = Square of reciprocal of elements of moments.
            :type weights_moments: ndarray or list (float)

            :param weights_correlation: An array of dimension dxd, where 'd' is number of random variables. It contain
                                        weights associated with correlation of random variables.
                                        Default: weights_correlation = dxd dimensional array with all elements equal to
                                        1.

            :param correlation: Correlation matrix between random variables.

        Output:
            :return: SROM.samples: Last column contains the probabilities/weights defining discrete approximation of
                                   continuous random variables.
            :rtype: SROM.samples: ndarray

    """
    # Authors: Mohit Chauhan
    # Updated: 6/7/18 by Dimitris G. Giovanis

    def __init__(self, samples=None, cdf_target=None, moments=None, weights_errors=None,
                 weights_distribution=None, weights_moments=None, weights_correlation=None,
                 properties=None, cdf_target_params=None, correlation=None):

        if type(weights_distribution) is list:
            self.weights_distribution = np.array(weights_distribution)
        else:
            self.weights_distribution = weights_distribution

        if type(weights_moments) is list:
            self.weights_moments = np.array(weights_moments)
        else:
            self.weights_moments = weights_moments

        if type(correlation) is list:
            self.correlation = np.array(correlation)
        else:
            self.correlation = correlation

        if type(moments) is list:
            self.moments = np.array(moments)
        else:
            self.moments = moments
        if type(samples) is list:
            self.samples = np.array(samples)
            self.nsamples = self.samples.shape[0]
            self.dimension = self.samples.shape[1]
        else:
            self.dimension = samples.shape[1]
            self.samples = samples
            self.nsamples = samples.shape[0]

        if type(weights_correlation) is list:
            self.weights_correlation = np.array(weights_correlation)
        else:
            self.weights_correlation = weights_correlation

        self.weights_errors = weights_errors
        self.cdf_target = cdf_target
        self.properties = properties
        self.cdf_target_params = cdf_target_params
        self.init_srom()
        self.sample_weights = self.run_srom()

    def run_srom(self):
        print('UQpy: Performing SROM...')
        from scipy import optimize

        def f(p0, samples, wd, wm, wc, mar, n, d, m, alpha, para, prop, correlation):
            e1 = 0.
            e2 = 0.
            e22 = 0.
            e3 = 0.
            com = np.append(samples, np.transpose(np.matrix(p0)), 1)
            for j in range(d):
                srt = com[np.argsort(com[:, j].flatten())]
                s = srt[0, :, j]
                a = srt[0, :, d]
                a0 = np.cumsum(a)
                marginal = mar[j]

                if prop[0] is True:
                    for i in range(n):
                        e1 += wd[i, j] * (a0[0, i] - marginal(s[0, i], para[j])) ** 2

                if prop[1] is True:
                    e2 += wm[0, j] * (np.sum(np.array(p0) * samples[:, j]) - m[0, j]) ** 2

                if prop[2] is True:
                    e22 += wm[1, j] * (
                            np.sum(np.array(p0) * (samples[:, j] * samples[:, j])) - m[1, j]) ** 2

                if prop[3] is True:
                    for k in range(d):
                        if k > j:
                            r = correlation[j, k] * np.sqrt((m[1, j] - m[0, j] ** 2) * (m[1, k] - m[0, k] ** 2)) + \
                                m[0, j] * m[0, k]
                            e3 += wc[k, j] * (
                                    np.sum(np.array(p_) * (
                                                np.array(samples[:, j]) * np.array(samples[:, k]))) - r) ** 2

            return alpha[0] * e1 + alpha[1] * (e2 + e22) + alpha[2] * e3

        def constraint(x):
            return np.sum(x) - 1

        def constraint2(y):
            n = np.size(y)
            return np.ones(n) - y

        def constraint3(z):
            n = np.size(z)
            return z - np.zeros(n)

        cons = ({'type': 'eq', 'fun': constraint}, {'type': 'ineq', 'fun': constraint2},
                {'type': 'ineq', 'fun': constraint3})

        p_ = optimize.minimize(f, np.zeros(self.nsamples),
                               args=(self.samples, self.weights_distribution, self.weights_moments,
                                     self.weights_correlation, self.cdf_target, self.nsamples, self.dimension,
                                     self.moments, self.weights_errors, self.cdf_target_params, self.properties,
                                     self.correlation),
                               constraints=cons, method='SLSQP')

        print('Done!')
        return p_.x

    def init_srom(self):

        if self.cdf_target is None:
            raise NotImplementedError("Exit code: Distribution not defined.")

        # Check samples
        if self.samples is None:
            raise NotImplementedError('Samples not provided for SROM')

        # Check properties to match
        if self.properties is None:
            self.properties = [True, True, True, False]

        # Check moments and correlation
        if self.properties[1] is True or self.properties[2] is True or self.properties[3] is True:
            if self.moments is None:
                raise NotImplementedError("'moments' are required")
        # Both moments are required, if correlation property is required to be match
        if self.properties[3] is True:
            if self.moments.shape != (2, self.dimension):
                raise NotImplementedError("1. Size of 'moments' is not correct")
            if self.correlation is None:
                self.correlation = np.identity(self.dimension)
        # moments.shape[0] should be 1 or 2
        if self.moments.shape != (1, self.dimension) and self.moments.shape != (2, self.dimension):
            raise NotImplementedError("2. Size of 'moments' is not correct")
        # If both the moments are to be included in objective function, then moments.shape[0] should be 2
        if self.properties[1] is True and self.properties[2] is True:
            if self.moments.shape != (2, self.dimension):
                raise NotImplementedError("3. Size of 'moments' is not correct")
        # If only second order moment is to be included in objective function and moments.shape[0] is 1. Then
        # self.moments is converted shape = (2, self.dimension) where is second row contain second order moments.
        if self.properties[1] is False and self.properties[2] is True:
            if self.moments.shape == (1, self.dimension):
                temp = np.ones(shape=(1, self.dimension))
                self.moments = np.concatenate((temp, self.moments))

        # Check weights corresponding to errors
        if self.weights_errors is None:
            self.weights_errors = [1, 0.2, 0]
        self.weights_errors = np.array(self.weights_errors).astype(np.float64)

        # Check weights corresponding to distribution
        if self.weights_distribution is None:
            self.weights_distribution = np.ones(shape=(self.samples.shape[0], self.dimension))

        self.weights_distribution = np.array(self.weights_distribution)
        if self.weights_distribution.shape == (1, self.dimension):
            self.weights_distribution = self.weights_distribution * np.ones(shape=(self.samples.shape[0],
                                                                                   self.dimension))
        elif self.weights_distribution.shape != (self.samples.shape[0], self.dimension):
            raise NotImplementedError("Size of 'weights for distribution' is not correct")

        # Check weights corresponding to moments and it's default list
        if self.weights_moments is None:
            self.weights_moments = np.reciprocal(np.square(self.moments))

        self.weights_moments = np.array(self.weights_moments)
        if self.weights_moments.shape == (1, self.dimension):
            self.weights_moments = self.weights_moments * np.ones(shape=(2, self.dimension))
        elif self.weights_moments.shape != (2, self.dimension):
            raise NotImplementedError("Size of 'weights for moments' is not correct")

        # Check weights corresponding to correlation and it's default list
        if self.weights_correlation is None:
            self.weights_correlation = np.ones(shape=(self.dimension, self.dimension))

        self.weights_correlation = np.array(self.weights_correlation)
        if self.weights_correlation.shape != (self.dimension, self.dimension):
            raise NotImplementedError("Size of 'weights for correlation' is not correct")

        # Check cdf_target
        if len(self.cdf_target) == 1:
            self.cdf_target = self.cdf_target * self.dimension
            self.cdf_target_params = [self.cdf_target_params] * self.dimension
        elif len(self.cdf_target) != self.dimension:
            raise NotImplementedError("Size of cdf_type should be 1 or equal to dimension")

        # Assign cdf_target function for each dimension
        for i in range(len(self.cdf_target)):
            if type(self.cdf_target[i]).__name__ == 'function':
                self.cdf_target[i] = self.cdf_target[i]
            elif type(self.cdf_target[i]).__name__ == 'str':
                self.cdf_target[i] = Distribution(self.cdf_target[i]).cdf
            else:
                raise NotImplementedError("Distribution type should be either 'function' or 'list'")

########################################################################################################################
########################################################################################################################
#                                         Kriging Interpolation  (Krig)                                       #
########################################################################################################################
########################################################################################################################


class Krig:
    """

            Description:

                Kriging surrogate creates an approximate model to predict the function value at unknown locations.

                References:
                S.N. Lophaven , Hans Bruun Nielsen , J. Søndergaard, "DACE -- A MATLAB Kriging Toolbox",
                    Informatics and Mathematical Modelling, Version 2.0, 2002.
            Input:
                :param samples: An array of samples corresponding to each random variables

                :param values: An array of function evaluated at sample points
                :type values: ndarray

                :param reg_model: Regression model contains the basis function, which defines the trend of the model.
                                  Options: Constant, Linear, Quadratic.
                :type reg_model: string or function

                :param corr_model: Correlation model contains the correlation function, which uses sample distance
                                   to define similarity between samples.
                                   Options: Exponential, Gaussian, Linear, Spherical, Cubic, Spline.
                :type corr_model: string or function

                :param corr_model_params: Initial values corresponding to hyperparameters/scale parameters.
                :type corr_model_params: ndarray

            Output:
                :return: Krig.interpolate: This function predicts the function value and uncertainty associated with
                                           it at unknown samples.
                :rtype: Krig.interpolate: function

                :return: Krig.jacobian: This function predicts the gradient of function and uncertainty associated with
                                        it at unknown samples.
                :rtype: Krig.jacobian: function

        """

    # Authors: Mohit Chauhan, Matthew Lombardo
    # Last modified: 12/03/2018 by Mohit S. Chauhan

    def __init__(self, samples=None, values=None, reg_model=None, corr_model=None, corr_model_params=None, bounds=None,
                 n_opt=1, op='Yes'):

        self.samples = samples
        self.values = values
        self.reg_model = reg_model
        self.corr_model = corr_model
        self.corr_model_params = corr_model_params
        self.bounds = bounds
        self.n_opt = n_opt
        self.init_krig()
        self.op = op
        self.beta, self.gamma, self.sig, self.F_dash, self.C_inv, self.G = self.run_krig()
        print(np.allclose(values, self.interpolate(samples), 1e-10))

    def run_krig(self):
        print('UQpy: Performing Krig...')
        s_ = self.samples
        y_ = self.values
        # Number of samples and dimensions of samples and values
        m_, n_ = s_.shape
        q = int(np.size(y_)/m_)

        f_, jf_ = self.reg_model(s_)

        # Update the initial values of hyperparameters to ensure that covariance matrix is positive definite
        r_ = self.corr_model(x=s_, s=s_, params=self.corr_model_params)
        while np.linalg.det(r_) < 10**(-12):
            self.corr_model_params = 1.5*self.corr_model_params
            r_ = self.corr_model(x=s_, s=s_, params=self.corr_model_params)

        from scipy import optimize

        def log_likelihood(p0, s, m, n, f, y):
            r__, dr_ = self.corr_model(x=s, s=s, params=p0, flag=1)
            try:
                cc = np.linalg.cholesky(r__)
            except np.linalg.LinAlgError:
                return np.inf, np.zeros(n)

            if np.prod(np.diagonal(cc)) == 0:
                return np.inf, np.zeros(n)

            c_in = np.linalg.inv(cc)
            r_in = np.matmul(c_in.T, c_in)

            f_das = np.matmul(c_in, f)
            y_das = np.matmul(c_in, y)
            q_ll, g_ll = np.linalg.qr(f_das)
            bt = np.linalg.solve(g_ll, np.matmul(np.transpose(q_ll), y_das))

            tmp = y_das - np.matmul(f_das, bt)
            alpha = np.matmul(r_in, tmp)
            t4 = np.matmul(tmp.T, alpha)
            # print(np.prod(np.diagonal(cc)))
            # print(np.sum(t4)/m)

            ll = (np.log(np.prod(np.diagonal(cc))) + m*np.log(np.sum(t4)/m) + m * np.log(2 * np.pi)) / 2
            # ll = (np.log(np.prod(np.diagonal(cc))) + t4) / 2

            grad = np.zeros(n)
            for i in range(n):
                # grad[i] = 0.5 * np.matrix.trace(np.matmul((np.matmul(alpha, alpha.T) - r_in), dr_[:, :, i]))
                # TODO: Find efficient ways to estimate gradient
                t1 = np.matrix.trace(np.matmul(r_in, dr_[:, :, i]))
                r_bar = np.matmul(r_in, np.matmul(dr_[:, :, i], r_in))
                f__ = np.linalg.cholesky(np.matmul(f.T, np.matmul(r_in, f)))
                f_in = np.linalg.inv(f__)
                fr_bar = np.matmul(f_in.T, f_in)
                fr = np.matmul(f, np.matmul(fr_bar, f.T))
                t2 = 2*np.matmul(tmp.T, np.matmul(r_in, np.matmul(fr, np.matmul(r_in, np.matmul((np.matmul(fr, r_in) -
                                                                                                 np.eye(m)), y_das)))))
                t3 = np.matmul(tmp.T, np.matmul(r_in, tmp))
                t4 = np.matmul(tmp.T, np.matmul(r_bar, tmp))
                grad[i] = 0.5*(t1 - (m/t3) * (t2 - t4))

            return ll, grad

        p_ = optimize.fmin_l_bfgs_b(log_likelihood, self.corr_model_params, args=(s_, m_, n_, f_, y_),
                                    bounds=self.bounds)
        self.corr_model_params = p_[0]
        # if self.op == 'Yes':
        #     sp = self.corr_model_params
        #     p = np.zeros([self.n_opt, n_])
        #     pf = np.zeros([self.n_opt, 1])
        #     for i in range(self.n_opt):
        #         # print('i=', i)
        #         p_ = optimize.fmin_l_bfgs_b(log_likelihood, sp, args=(s_, m_, n_, f_, y_), bounds=self.bounds)
        #         p[i, :] = p_[0]
        #         pf[i, 0] = p_[1]
        #         sp = stats.reciprocal.rvs([j[0] for j in self.bounds], [j[1] for j in self.bounds], 1)
        #     t = np.argmin(pf)
        #     # print(pf, p)
        #     self.corr_model_params = p[t, :]
        #     # print(t, p[t, :])
        #     if t == 0:
        #         print('yes')

        r_ = self.corr_model(x=s_, s=s_, params=self.corr_model_params)
        print(r_)
        c = np.linalg.cholesky(r_)                   # Eq: 3.8, DACE
        c_inv = np.linalg.inv(c)
        f_dash = np.matmul(c_inv, f_)
        y_dash = np.matmul(c_inv, y_)
        q_, g_ = np.linalg.qr(f_dash)                 # Eq: 3.11, DACE

        # Check if F is a full rank matrix
        if np.linalg.matrix_rank(g_) != min(np.size(f_, 0), np.size(f_, 1)):
            raise NotImplementedError("Chosen regression functions are not sufficiently linearly independent")

        # Design parameters
        beta = np.linalg.solve(g_, np.matmul(np.transpose(q_), y_dash))
        gamma = np.matmul(np.matmul(np.transpose(c_inv), c_inv), (y_ - np.matmul(f_, beta)))

        # Computing the process variance (Eq: 3.13, DACE)
        sigma = np.zeros(q)
        for l in range(q):
            sigma[l] = (1 / m_) * (np.linalg.norm(y_dash[:, l] - np.matmul(f_dash, beta[:, l])) ** 2)

        print('Done!')
        return beta, gamma, sigma, f_dash, c_inv, g_

    def interpolate(self, x, dy=False):
        fx, jf = self.reg_model(x)
        rx = self.corr_model(x=x, s=self.samples, params=self.corr_model_params)
        y = np.einsum('ij,jk->ik', fx, self.beta) + np.einsum('ij,jk->ik', rx.T, self.gamma)
        if dy:
            r_dash = np.einsum('ij,jk->ik', self.C_inv, rx)
            u = np.einsum('ij,jk->ik', self.F_dash.T, r_dash)-fx.T
            norm1 = np.sum(r_dash**2, 0)**0.5
            norm2 = np.sum(np.linalg.solve(self.G, u)**2, 0)**0.5
            mse = (self.sig ** 2) * (1 + norm2**2 - norm1**2)
            return y, mse.reshape(y.shape)
        else:
            return y

    def jacobian(self, x):
        fx, jf = self.reg_model(x)
        rx, drdx = self.corr_model(x=x, s=self.samples, params=self.corr_model_params, flag=2)
        y_grad = np.einsum('ijk,jm->ik', jf, self.beta) + np.einsum('ijk,jm->ki', drdx.T, self.gamma)
        # TODO: Add uncertainty in gradient

        return y_grad

    # Defining Regression model (Linear)
    def regress(self, model=None):
        def r(s):
            s = np.atleast_2d(s)
            if model == 'Constant':
                fx = np.ones([np.size(s, 0), 1])
                jf = np.zeros([np.size(s, 0), 1])
            if model == 'Linear':
                fx = np.concatenate((np.ones([np.size(s, 0), 1]), s), 1)
                jf = np.concatenate((np.zeros([np.size(s, 1), 1]), np.eye(np.size(s, 1))), 1)
                return fx, jf
            if model == 'Quadratic':
                fx = np.zeros([np.size(s, 0), int((np.size(s, 1) + 1) * (np.size(s, 1) + 2) / 2)])
                jf = np.zeros(
                    [np.size(s, 1), int((np.size(s, 1) + 1) * (np.size(s, 1) + 2) / 2), np.size(s, 0)])
                for i in range(np.size(s, 0)):
                    temp = np.hstack((1, s[i, :]))
                    for j in range(np.size(s, 1)):
                        temp = np.hstack((temp, s[i, j] * s[i, j::]))
                    fx[i, :] = temp
                    # definie H matrix
                    for j in range(np.size(s, 1)):
                        tmp_ = s[i, j] * np.eye(np.size(s, 1))
                        t1 = np.zeros([np.size(s, 1), np.size(s, 1)])
                        t1[j, :] = s[i, :]
                        tmp = tmp_ + t1
                        if j == 0:
                            h_ = tmp[:, j::]
                        else:
                            h_ = np.hstack((h_, tmp[:, j::]))
                    jf[:, :, i] = np.hstack((np.zeros([np.size(s, 1), 1]), np.eye(np.size(s, 1)), h_))
                return fx, jf.T

        return r

    # Defining Correlation model (Gaussian Process)
    def corr(self, model):
        def c(x, s, params, flag=0):
            rx, drdt, drdx = 0, 0, 0
            x = np.atleast_2d(x)
            if model == 'Exponential':
                dis = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1)) - np.tile(s, (
                np.size(x, 0), 1, 1))
                rx = np.exp(np.sum(-params * abs(dis), axis=2)).T
                drdt = -abs(dis) * np.tile(rx, (np.size(x, 1), 1, 1)).T
                drdx = -params * np.sign(dis) * np.tile(rx, (np.size(x, 1), 1, 1)).T
            elif model == 'Gaussian':
                dis = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1)) - np.tile(s, (
                np.size(x, 0), 1, 1))
                rx = np.exp(np.sum(-params * (dis ** 2), axis=2)).T
                drdt = -(dis ** 2) * np.tile(rx, (np.size(x, 1), 1, 1)).T
                drdx = -2 * params * abs(dis) * np.tile(rx, (np.size(x, 1), 1, 1)).T
            elif model == 'Linear':
                # Create stack matrix, where each block is x_i with all s
                stack = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1)) - np.tile(s, (np.size(x, 0),
                                                                                                          1, 1))
                # Taking stack and turning each d value into 1-theta*dij
                after_parameters = 1 - params * abs(stack)
                # Define matrix of zeros to compare against (not necessary to be defined separately,
                # but the line is bulky if this isn't defined first, and it is used more than once)
                comp_zero = np.zeros((np.size(x, 0), np.size(s, 0), np.size(s, 1)))
                # Compute matrix of max{0,1-theta*d}
                max_matrix = np.maximum(after_parameters, comp_zero)
                rx = np.prod(max_matrix, 2).T
                # Create matrix that has 1s where max_matrix is nonzero
                # -Essentially, this acts as a way to store the indices of where the values are nonzero
                ones_and_zeros = max_matrix.astype(bool).astype(int)
                # Set initial derivatives as if all were positive
                first_dtheta = -abs(stack)
                first_dx = np.negative(params) * np.sign(stack)
                # Multiply derivs by ones_and_zeros...this will set the values where the
                # derivative should be zero to zero, and keep all other values the same
                drdt = np.multiply(first_dtheta, ones_and_zeros)
                drdx = np.multiply(first_dx, ones_and_zeros)
                # Loop over parameters, shifting max_matrix and multiplying over derivative
                # matrix with each iteration
                for i in range(len(params) - 1):
                    drdt = drdt * np.roll(max_matrix, i + 1, axis=2)
                    drdx = drdx * np.roll(max_matrix, i + 1, axis=2)
                # Multiplying matrices by ones_and_zeros multiplication sets 0 values equal to
                # -0.0, so this comparison sets all -0.0 to 0.0 (Python should treat these the
                # same, but it looks better with 0.0)
                drdt[drdt == -0.0] = 0
                drdx[drdx == -0.0] = 0
            elif model == 'Spherical':
                # Create stack matrix, where each block is x_i with all s
                stack = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1)) - np.tile(s, (np.size(x, 0),
                                                                                                          1, 1))
                # Taking stack and creating array of all thetaj*dij
                after_parameters = params * abs(stack)
                # Create matrix of all ones to compare
                comp_ones = np.ones((np.size(x, 0), np.size(s, 0), np.size(s, 1)))
                # zeta_matrix has all values min{1,theta*dij}
                zeta_matrix = np.minimum(after_parameters, comp_ones)
                # Copy zeta_matrix to another matrix that will used to find where derivative should be zero
                indices = zeta_matrix
                # If value of min{1,theta*dij} is 1, the derivative should be 0.
                # So, replace all values of 1 with 0, then perform the .astype(bool).astype(int)
                # operation like in the linear example, so you end up with an array of 1's where
                # the derivative should be caluclated and 0 where it should be zero
                indices[indices == 1] = 0
                # Create matrix of all |dij| (where non zero) to be used in calculation of dR/dtheta
                dtheta_derivs = indices.astype(bool).astype(int) * abs(stack)
                # Same as above, but for matrix of all thetaj where non-zero
                dx_derivs = indices.astype(bool).astype(int) * params
                # Initial matrices containing derivates for all values in array. Note since
                # dtheta_s and dx_s already accounted for where derivative should be zero, all
                # that must be done is multiplying the |dij| or thetaj matrix on top of a
                # matrix of derivates w.r.t zeta (in this case, dzeta = -1.5+1.5zeta**2)
                drdt = (-1.5 + 1.5 * zeta_matrix ** 2) * dtheta_derivs
                drdx = (-1.5 + 1.5 * zeta_matrix ** 2) * dx_derivs
                # Also, create matrix for values of equation, 1 - 1.5zeta + 0.5zeta**3, for loop
                zeta_function = 1 - 1.5 * zeta_matrix + 0.5 * zeta_matrix ** 3
                rx = np.prod(zeta_function, 2).T
                # Same as previous example, loop over zeta matrix by shifting index
                for i in range(len(params) - 1):
                    drdt = drdt * np.roll(zeta_function, i + 1, axis=2)
                    drdx = drdx * np.roll(zeta_function, i + 1, axis=2)
                # Replace -0.0 with 0.0
                drdt[drdt == -0.0] = 0.0
                drdx[drdx == -0.0] = 0.0
            elif model == 'Cubic':
                # Create stack matrix, where each block is x_i with all s
                stack = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1)) - np.tile(s, (np.size(x, 0),
                                                                                                          1, 1))
                # Taking stack and creating array of all thetaj*dij
                after_parameters = params * abs(stack)
                # Create matrix of all ones to compare
                comp_ones = np.ones((np.size(x, 0), np.size(s, 0), np.size(s, 1)))
                # zeta_matrix has all values min{1,theta*dij}
                zeta_matrix = np.minimum(after_parameters, comp_ones)
                # Copy zeta_matrix to another matrix that will used to find where derivative should be zero
                indices = zeta_matrix
                # If value of min{1,theta*dij} is 1, the derivative should be 0.
                # So, replace all values of 1 with 0, then perform the .astype(bool).astype(int)
                # operation like in the linear example, so you end up with an array of 1's where
                # the derivative should be caluclated and 0 where it should be zero
                indices[indices == 1] = 0
                # Create matrix of all |dij| (where non zero) to be used in calculation of dR/dtheta
                dtheta_derivs = indices.astype(bool).astype(int) * abs(stack)
                # Same as above, but for matrix of all thetaj where non-zero
                dx_derivs = indices.astype(bool).astype(int) * params
                # Initial matrices containing derivates for all values in array. Note since
                # dtheta_s and dx_s already accounted for where derivative should be zero, all
                # that must be done is multiplying the |dij| or thetaj matrix on top of a
                # matrix of derivates w.r.t zeta (in this case, dzeta = -6zeta+6zeta**2)
                drdt = (-6 * zeta_matrix + 6 * zeta_matrix**2) * dtheta_derivs
                drdx = (-6 * zeta_matrix + 6 * zeta_matrix**2) * dx_derivs
                # Also, create matrix for values of equation, 1 - 1.5zeta + 0.5zeta**3, for loop
                zeta_function = 1 - 3 * zeta_matrix**2 + 2 * zeta_matrix**3
                rx = np.prod(zeta_function, 2).T
                # Same as previous example, loop over zeta matrix by shifting index
                for i in range(len(params) - 1):
                    drdt = drdt * np.roll(zeta_function, i + 1, axis=2)
                    drdx = drdx * np.roll(zeta_function, i + 1, axis=2)
                # Replace -0.0 with 0.0
                drdt[drdt == -0.0] = 0.0
                drdx[drdx == -0.0] = 0.0
            if flag == 0:
                return rx
            elif flag == 1:
                return rx, drdt
            else:
                return rx, drdx
        return c

    def init_krig(self):
        if self.reg_model is None:
            raise NotImplementedError("Exit code: Correlation model is not defined.")

        if self.corr_model is None:
            raise NotImplementedError("Exit code: Correlation model is not defined.")

        if self.corr_model_params is None:
            self.corr_model_params = np.ones(np.size(self.samples, 1))

        if self.bounds is None:
            self.bounds = [[0.001, 10**7]]*self.samples.shape[1]

        if type(self.reg_model).__name__ == 'function':
            self.reg_model = self.reg_model
        elif self.reg_model in ['Linear', 'Quadratic']:
            self.reg_model = self.regress(model=self.reg_model)
        else:
            raise NotImplementedError("Exit code: Doesn't recognize the Regression model.")

        if type(self.corr_model).__name__ == 'function':
            self.corr_model = self.corr_model
        elif self.corr_model in ['Other', 'Exponential', 'Gaussian', 'Linear', 'Spherical', 'Cubic', 'Spline']:
            self.corr_model = self.corr(model=self.corr_model)
        else:
            raise NotImplementedError("Exit code: Doesn't recognize the Correlation model.")



            # x = np.atleast_2d(x)
            # rx1 = np.ones([np.size(s, 0), np.size(x, 0)])
            # drdt = np.zeros([np.size(s, 0), np.size(x, 0), np.size(s, 1)])
            # drdx = np.zeros([np.size(s, 0), np.size(x, 0), np.size(s, 1)])

            # if model == 'Other':
            #     for j in range(np.size(x, 0)):
            #         for i in range(np.size(s, 0)):
            #             rx[i, j] = rx[i, j] * np.exp(-np.sqrt(np.sum(params * (s[i, :] - x[j, :]) ** 2)))
            #     return rx
# elif model == 'Linear':
            #     tmp_x = np.tile(np.swapaxes(np.atleast_3d(x), 1, 2), (1, np.size(s, 0), 1))
            #     tmp_s = np.tile(s, (np.size(x, 0), 1, 1))
            #     dis = tmp_x - tmp_s
            #     # define array of zeros for max() comparison
            #     a = np.zeros((np.size(x, 0), np.size(s, 0), np.size(s, 1)))
            #     rx = np.prod(np.maximum(a, (1 - params * abs(dis))), axis=2).T
            #     tmp_ = np.tile(tmp_x, (1, 1, np.size(x, 1)))
            #     tmp_[:, :, 0::(np.size(x, 1) + 1)] = tmp_s
            #     t = tmp_ - np.tile(tmp_s, (1, 1, np.size(x, 1)))
            #     # print(rx, rx_)
            #     # print(np.array_equal(rx, rx_))
            #     ######
            #     drdt = -(np.tile(abs(dis), (np.size(x, 1), 1, 1)) / tmp) * np.tile(rx, (np.size(x, 1), 1, 1)).T
            #     # drdxg = -(2 * abs(dis) * params * np.sign(dis)) * np.tile(rx, (np.size(x, 1), 1, 1)).T
            #
            #     for j in range(np.size(x, 0)):
            #         for i in range(np.size(s, 0)):
            #             for k in range(np.size(s, 1)):
            #                 rx1[i, j] = rx1[i, j] * max(0, 1 - params[k] * abs(s[i, k] - x[j, k]))
            #
            #     print(np.array_equal(rx, rx1))

            # elif model == 'Spherical':
            #     for j in range(np.size(x, 0)):
            #         for i in range(np.size(s, 0)):
            #             for k in range(np.size(s, 1)):
            #                 zeta = min(1, params[k] * abs(s[i, k] - x[j, k]))
            #                 rx[i, j] = rx[i, j] * (1 - 1.5 * zeta + 0.5 * zeta ** 3)
            #     return rx
            # elif model == 'Cubic':
            #     for j in range(np.size(x, 0)):
            #         for i in range(np.size(s, 0)):
            #             for k in range(np.size(s, 1)):
            #                 zeta = min(1, params[k] * abs(s[i, k] - x[j, k]))
            #                 rx[i, j] = rx[i, j] * (1 - 3 * zeta ** 2 + 2 * zeta ** 3)
            #     return rx
            # elif model == 'Spline':
            #     for j in range(np.size(x, 0)):
            #         for i in range(np.size(s, 0)):
            #             for k in range(np.size(s, 1)):
            #                 zeta = params[k] * abs(s[i, k] - x[j, k])
            #                 if zeta <= 0.2:
            #                     rx[i, j] = rx[i, j] * (1 - 15 * zeta ** 2 + 30 * zeta ** 3)
            #                 elif zeta <= 1:
            #                     rx[i, j] = rx[i, j] * (1.25 * (1 - zeta) ** 3)
            #                 else:
            #                     rx[i, j] = rx[i, j] * 0
            #     return rx


# grad1 = np.zeros(n)
#
#             def func(p0, S, q, m, n, F, Y):
#                 R, dR = self.corr_model(x=S, s=S, params=p0, flag=1)
#                 try:
#                     C = np.linalg.cholesky(R)
#                 except np.linalg.LinAlgError:
#                     return np.inf
#
#                 C_inv = np.linalg.inv(C)
#                 R_inv = np.matmul(C_inv.T, C_inv)
#
#                 F_dash = np.matmul(C_inv, F)
#                 Y_dash = np.matmul(C_inv, Y)
#                 Q, G = np.linalg.qr(F_dash)
#                 beta = np.linalg.solve(G, np.matmul(np.transpose(Q), Y_dash))
#
#                 tmp = Y_dash - np.matmul(F_dash, beta)
#                 alpha = np.matmul(R_inv, tmp)
#                 t4 = np.matmul(tmp.T, alpha)
#
#                 # L = (np.log(np.prod(np.diagonal(C))) + m * np.log(t4 / m) + m * np.log(2 * np.pi)) / 2
#                 L = (np.log(np.prod(np.diagonal(C))) + t4) / 2
#                 return L
#
#             h = 0.005
#             for dir in range(n):
#                 temp = np.zeros(n)
#                 temp[dir] = 1
#                 low = p0 - h / 2 * temp
#                 hi = p0 + h / 2 * temp
#                 f_hi = func(hi, S, q, m, n, F, Y)
#                 f_low = func(low, S, q, m, n, F, Y)
#                 if f_hi == np.inf or f_low == np.inf:
#                     grad1[dir] = 0
#                 else:
#                     grad1[dir] = (f_hi-f_low)/h
#
#             # print(grad, grad1)
#             # print(np.array_equal(grad, grad1))


            # y = np.matmul(fx, self.beta) + np.matmul(rx.T, self.gamma)

            # mse = np.zeros(np.size(y))
            # for i in range(np.size(rx, 1)):
            #     r_dash = np.matmul(self.C_inv, rx[:, i])
            #     u = np.matmul(self.F_dash.T, r_dash) - fx.T[:, i]
            #     mse[i] = (self.sig ** 2) * (
            #             1 + np.linalg.norm(np.linalg.solve(self.G, u)) ** 2 - np.linalg.norm(r_dash) ** 2)
            # print(mse, mse1)

            # y_grad = np.sum(Jf.T * self.beta[None, :], 1).T + np.sum(drdx.T * self.gamma[:, 0], 1).T
            # if np.size(x, 0) == 1:
            #     print('here')
            #     y_grad = np.sum(Jf * self.beta[:, 0], 1) + np.sum(drdx.T * self.gamma[:, 0], 1)
            # else:

    # if q == 1:
    #     print('hi')
    #     sigma[l] = (1/m)*(np.linalg.norm(Y_dash - np.matmul(F_dash, beta))**2)
    # else:
    #     sigma[l] = (1 / m) * (np.linalg.norm(Y_dash[:, l] - np.matmul(F_dash, beta[:, l])) ** 2)
    # print(sigma, sigma1)


