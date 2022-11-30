import igraph as ig
import numpy as np
import scipy as sp
from scipy.special import gammaln

def irm_directed_weighted(X, T, a, b, A, random_seed = 42):
    N = len(X)
    z = np.ones([N,1])
    Z = []

    np.random.seed(random_seed)

    for t in range(T): # for T iterations
        print(t)
        for n in range(N): # for each node n
            #nn = index mask without currently sampled node n
            nn = [_ for _ in range(N)]  
            nn.remove(n) 

            X_ = X[np.ix_(nn,nn)]
            K = len(z[0])

            # Delete empty component if present
            if K > 1:
                idx = np.argwhere(np.sum(z[nn], 0) == 0)
                z = np.delete(z, idx, axis=1)
                K -= len(idx)

            m = np.sum(z[nn,:], 0)[np.newaxis]

            r = z[nn,:].T @ X[n, nn]
            R = np.tile(r, (K, 1))

            s = z[nn,:].T @ X[nn, n]
            S = np.tile(s[np.newaxis].T, (1, K))

            M = np.tile(m, (K, 1)) + np.diag(m.flatten())

            M1 = z[nn,:].T @ X_ @ z[nn,:]
            M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()

            link_matrix = np.concatenate([M1,M2],axis=1)
            current_node_links = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
            current_node_links[0:R.shape[0], 0:R.shape[1]] += R
            s_diag = np.diag(s.flatten())
            current_node_links[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
            S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
            if K > 1: 
                current_node_links[:,-S.shape[1]:] += S

            M__2 = M[~np.eye(M.shape[0],dtype=bool)].reshape(M.shape[0], -1)
            max_links_current_node = np.concatenate([M,M__2],axis=1)

            C1 = m.T@m - np.diag(m.flatten())
            C2 = C1.T[~np.eye(C1.T.shape[0],dtype=bool)].reshape(C1.T.shape[0], -1).copy()
            C = np.concatenate([C1, C2], axis=1) #no. of possible links


            F = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
            f_out = np.sum(gammaln(np.multiply(z[nn,:].T, X[n, nn]) + 1), axis = 1)
            F_out = np.tile(f_out, (K, 1))

            f_in = np.sum(gammaln(np.multiply(z[nn,:].T, X[nn, n]) + 1), axis = 1)
            f_in_diag = np.diag(f_in)
            F_in = np.tile(f_in[np.newaxis].T, (1, K))
            F_in = F_in.T[~np.eye(F_in.shape[0],dtype=bool)].reshape(F_in.shape[0], -1)

            F[0:F_out.shape[0], 0:F_out.shape[1]] += F_out
            F[0:F_out.shape[0], 0:F_out.shape[1]] += f_in_diag
            if K > 1: 
                F[:,-F_in.shape[1]:] += F_in
            if K == 1:
                F[:] += f_in


            likelihood = np.sum(gammaln(link_matrix + current_node_links + a) - gammaln(link_matrix + a) \
                        + (link_matrix + a)*np.log(C+b) - (link_matrix + current_node_links + a)*np.log(C + max_links_current_node + b) \
                        - F, 1)

            likelihood_n = np.sum(gammaln(np.hstack([r,s]) + a) - gammaln(a) \
                        + (b)*np.log(a) - (np.hstack([r,s]) + a)*np.log(np.hstack([m, m]) + b) \
                        - np.hstack([f_out, f_in]), 1)

            logLik = np.concatenate([likelihood, likelihood_n])

            logPrior = np.log(np.append(m, A))

            logPost = logPrior + logLik

            P = np.exp(logPost-max(logPost)) 

            # Assignment through random draw fron unif(0,1), taking first value from prob. vector
            draw = np.random.rand()
            i = np.argwhere(draw<np.cumsum(P)/sum(P))[0]

            # Assignment of current node to component i
            z[n,:] = 0
            if i == K: # If new component: add new column to partition matrix
                z = np.hstack((z, np.zeros((N,1)))) 
            z[n,i] = 1

        Z.append(z)
    return Z 


g = ig.Graph.Read_GML('celegansneural.gml')
X = np.array(g.get_adjacency(attribute = "value").data).astype(int)
X = X[:10,:10]

np.random.seed(42)
T = 500
a = 1
b = 1
A = 1

# Z = irm_directed(X, T, a, b, A)

N = len(X)
z = np.ones([N,1])
Z = []

#test X
X = np.array([[0, 1, 2, 3],
              [0, 0, 0, 5],
              [2, 0, 0, 6],
              [1, 4, 5, 0]])

N = len(X)

z = np.array([[1, 0],
              [1, 0],
              [0, 1],
              [0, 1]])
# z = np.ones([N,1])
# Z = []

n = 1
nn = [_ for _ in range(N)]  
nn.remove(n) 

X_ = X[np.ix_(nn,nn)]
K = len(z[0])

m = np.sum(z[nn,:], 0)[np.newaxis]

r = z[nn,:].T @ X[n, nn]
R = np.tile(r, (K, 1))

s = z[nn,:].T @ X[nn, n]
S = np.tile(s[np.newaxis].T, (1, K))

M = np.tile(m, (K, 1)) + np.diag(m.flatten())

M1 = z[nn,:].T @ X_ @ z[nn,:]
M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()

link_matrix = np.concatenate([M1,M2],axis=1)
current_node_links = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
current_node_links[0:R.shape[0], 0:R.shape[1]] += R
s_diag = np.diag(s.flatten())
current_node_links[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
if K > 1: 
    current_node_links[:,-S.shape[1]:] += S

M__2 = M[~np.eye(M.shape[0],dtype=bool)].reshape(M.shape[0], -1)
max_links_current_node = np.concatenate([M,M__2],axis=1)

C1 = m.T@m - np.diag(m.flatten())
C2 = C1.T[~np.eye(C1.T.shape[0],dtype=bool)].reshape(C1.T.shape[0], -1).copy()
C = np.concatenate([C1, C2], axis=1) #no. of possible links


F = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
f_out = np.sum(gammaln(np.multiply(z[nn,:].T, X[n, nn]) + 1), axis = 1)
F_out = np.tile(f_out, (K, 1))

f_in = np.sum(gammaln(np.multiply(z[nn,:].T, X[nn, n]) + 1), axis = 1)
f_in_diag = np.diag(f_in)
F_in = np.tile(f_in[np.newaxis].T, (1, K))
F_in = F_in.T[~np.eye(F_in.shape[0],dtype=bool)].reshape(F_in.shape[0], -1)

F[0:F_out.shape[0], 0:F_out.shape[1]] += F_out
F[0:F_out.shape[0], 0:F_out.shape[1]] += f_in_diag
if K > 1: 
    F[:,-F_in.shape[1]:] += F_in
if K == 1:
    F[:] += f_in


likelihood = np.sum(gammaln(link_matrix + current_node_links + a) - gammaln(link_matrix + a) \
            + (link_matrix + a)*np.log(C+b) - (link_matrix + current_node_links + a)*np.log(C + max_links_current_node + b) \
            - F, 1)

likelihood_n = np.sum(gammaln(np.hstack([r,s]) + a) - gammaln(a) \
            + (b)*np.log(a) - (np.hstack([r,s]) + a)*np.log(np.hstack([m, m]) + b) \
            - np.hstack([f_out, f_in]), 1)

logLik = np.concatenate([likelihood, likelihood_n])

logPrior = np.log(np.append(m, A))

logPost = logPrior + logLik

P = np.exp(logPost-max(logPost)) 

# Assignment through random draw fron unif(0,1), taking first value from prob. vector
draw = np.random.rand()
i = np.argwhere(draw<np.cumsum(P)/sum(P))[0]

# Assignment of current node to component i
z[n,:] = 0
if i == K: # If new component: add new column to partition matrix
    z = np.hstack((z, np.zeros((N,1)))) 
z[n,i] = 1


g = ig.Graph.Read_GML('celegansneural.gml')
X = np.array(g.get_adjacency(attribute = "value").data).astype(int)

T = 200   
N = len(X)
z = np.ones([N,1])
A = 1
Z = []     

for t in range(T): # for T iterations
    print(t)
    for n in range(N): # for each node n
        #nn = index mask without currently sampled node n
        nn = [_ for _ in range(N)]  
        nn.remove(n) 

        X_ = X[np.ix_(nn,nn)]
        K = len(z[0])

        # Delete empty component if present
        if K > 1:
            idx = np.argwhere(np.sum(z[nn], 0) == 0)
            z = np.delete(z, idx, axis=1)
            K -= len(idx)

        m = np.sum(z[nn,:], 0)[np.newaxis]

        r = z[nn,:].T @ X[n, nn]
        R = np.tile(r, (K, 1))

        s = z[nn,:].T @ X[nn, n]
        S = np.tile(s[np.newaxis].T, (1, K))

        M = np.tile(m, (K, 1)) + np.diag(m.flatten())

        M1 = z[nn,:].T @ X_ @ z[nn,:]
        M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()

        link_matrix = np.concatenate([M1,M2],axis=1)
        current_node_links = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
        current_node_links[0:R.shape[0], 0:R.shape[1]] += R
        s_diag = np.diag(s.flatten())
        current_node_links[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
        S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
        if K > 1: 
            current_node_links[:,-S.shape[1]:] += S

        M__2 = M[~np.eye(M.shape[0],dtype=bool)].reshape(M.shape[0], -1)
        max_links_current_node = np.concatenate([M,M__2],axis=1)

        C1 = m.T@m - np.diag(m.flatten())
        C2 = C1.T[~np.eye(C1.T.shape[0],dtype=bool)].reshape(C1.T.shape[0], -1).copy()
        C = np.concatenate([C1, C2], axis=1) #no. of possible links


        F = np.zeros((link_matrix.shape[0], link_matrix.shape[1]))
        f_out = np.sum(gammaln(np.multiply(z[nn,:].T, X[n, nn]) + 1), axis = 1)
        F_out = np.tile(f_out, (K, 1))

        f_in = np.sum(gammaln(np.multiply(z[nn,:].T, X[nn, n]) + 1), axis = 1)
        f_in_diag = np.diag(f_in)
        F_in = np.tile(f_in[np.newaxis].T, (1, K))
        F_in = F_in.T[~np.eye(F_in.shape[0],dtype=bool)].reshape(F_in.shape[0], -1)

        F[0:F_out.shape[0], 0:F_out.shape[1]] += F_out
        F[0:F_out.shape[0], 0:F_out.shape[1]] += f_in_diag
        if K > 1: 
            F[:,-F_in.shape[1]:] += F_in
        if K == 1:
            F[:] += f_in


        likelihood = np.sum(gammaln(link_matrix + current_node_links + a) - gammaln(link_matrix + a) \
                    + (link_matrix + a)*np.log(C+b) - (link_matrix + current_node_links + a)*np.log(C + max_links_current_node + b) \
                    - F, 1)

        likelihood_n = np.sum(gammaln(np.hstack([r,s]) + a) - gammaln(a) \
                    + (b)*np.log(a) - (np.hstack([r,s]) + a)*np.log(np.hstack([m, m]) + b) \
                    - np.hstack([f_out, f_in]), 1)

        logLik = np.concatenate([likelihood, likelihood_n])

        logPrior = np.log(np.append(m, A))

        logPost = logPrior + logLik

        P = np.exp(logPost-max(logPost)) 

        # Assignment through random draw fron unif(0,1), taking first value from prob. vector
        draw = np.random.rand()
        i = np.argwhere(draw<np.cumsum(P)/sum(P))[0]

        # Assignment of current node to component i
        z[n,:] = 0
        if i == K: # If new component: add new column to partition matrix
            z = np.hstack((z, np.zeros((N,1)))) 
        z[n,i] = 1

    Z.append(z.copy())