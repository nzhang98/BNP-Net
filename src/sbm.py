import numpy as np

from scipy.special import betaln
from scipy.special import gammaln

class smb():
    """
    Main Class for BNP SBM modeling
    """
    
    def __init__(self, setup,
                prior_r = None, prior_c = None,
                a = 1, b = 1, set_seed = False
                ):

        self.directed = setup['directed']
        self.binary = setup['binary']
        self.unicluster = setup['unicluster']

        self.A = 1 #temporary prior DP
        self.prior_r = prior_r
        self.prior_c = prior_c


        self.a = a
        self.b = b

        if isinstance(set_seed, int):
            np.random.seed(set_seed)

    def fit(self, X, T):
        self.X = X

        self.X_bin = self.X.copy()
        self.X_bin[X_bin>0] = 1

        self.T = T
        self.N = len(self.X)

        if self.unicluster:
            self.gibbs_unicluster(self.directed, self.binary)
        else:
            self.gibbs_bicluster(self.directed, self.binary)

    def gibbs_unicluster(self, directed, binary):
        #self.z = initialization
        self.z = np.ones([self.N, 1]) #Init as single cluster
        self.Z = [] #Empty list init

        self.idx_list = [x for x in range(self.N)]
        for _ in range(self.T):
            for n in range(self.N):
                nn = list(self.idx_list)
                nn.remove(n) #nn = index mask without currently sampled node n

                X_ = self.X[np.ix_(nn,nn)] #adjacency matrix without currently sampled node

                K = len(self.z[0])  # K = n. of components

                # Delete empty component if present
                if K > 1:
                    idx = np.argwhere(np.sum(self.z[nn], 0) == 0)
                    self.z = np.delete(self.z, idx, axis=1)
                    K -= len(idx)

                loglikelihood = self.evalLikelihood(nn, K, self.directed, self.binary):

                logPrior = np.log(np.append(m, self.A)) #TODO: Priors

                logPosterior = logPrior + logLikelihood

                # Convert from log probabilities, normalized to max
                p = np.exp(logPosterior-max(logPosterior)) 

                # Assignment through random draw fron unif(0,1), taking first value from prob. vector
                draw = np.random.rand()
                i = np.argwhere(draw<np.cumsum(p)/sum(p))[0]

                # Assignment of current node to component i
                self.z[n,:] = 0
                if i == K: # If new component: add new column to partition matrix
                    self.z = np.hstack([self.z, np.zeros(self.N,1)]) 
                self.z[n,i] = 1

                # self.gibbs_sweep(n, directed, binary)

            self.Z.append(self.z.copy())

    def gibbs_bicluster(self, directed, binary):
        self.zr = np.ones([self.N, 1])
        self.zc = np.ones([self.N, 1])
        self.Z = []
        self.Zr = []
        self.Zc = []

        self.idx_list = [x for x in range(self.N)]
        
        for _ in range(self.T):
            for n in range(self.N):
                self.gibbs_sweep_bicluster(n, "rows", directed, binary)
            for n in range(self.N):
                self.gibbs_sweep_bicluster(n, "columns", directed, binary)

            self.Z.append([self.zr.copy(), self.zc.copy()])
            self.Zr.append(self.zr.copy())
            self.Zc.append(self.zc.copy())

        
    def gibbs_sweep_bicluster(self, n, direction, directed, binary):
        nn = list(self.idx_list)
        nn.remove(n)

        X_ = self.X.copy().astype(int) 

        if direction == "rows":
            X_[n,:] = 0 #adj matrix without currently sampled node rows

            Kr = len(self.zr[0])

            if Kr > 1:
                idx = np.argwhere(np.sum(self.zr[nn], 0) == 0)
                self.zr = np.delete(self.zr, idx, axis=1)
                Kr -= len(idx)

            # m = n. of nodes in each component 
            mr = np.sum(self.zr[nn,:], 0)[np.newaxis] #newaxis allows m to become 2d array (for transposing)
            mc = np.sum(self.zc[nn,:], 0)[np.newaxis]
            Mc = np.tile(mc, (Kr, 1))
            LM = self.zr.T @ X_ @ self.zc

            X_rev = (np.where((X_==0)|(X_==1), X_^1, X_) - np.eye(X_.shape[0])).copy() #reverse matrix for non_links
            X_rev[n,:] = 0
            NLM = self.zr.T @ X_rev @ self.zc #n. of non-links between biclusters without current node

            r = self.zc[nn,:].T @ self.X[n, nn]
            R = np.tile(r, (Kr, 1))

            logLikelihood_old = np.sum(betaln(LM + R + self.a, NLM + Mc - R + self.b) \
                                 - betaln(LM + self.a, NLM + self.b)
                                       , 1)
            logLikelihood_new = np.sum(betaln(r + self.a, mc - r + self.b) \
                                     - betaln(self.a, self.b)
                                       , 1)

            logLikelihood = np.concatenate([logLikelihood_old, logLikelihood_new])

            logPrior = np.log(np.append(mr, self.A))

            logPosterior = logPrior + logLikelihood

            p = np.exp(logPosterior-max(logPosterior)) 

            # Assignment through random draw fron unif(0,1), taking first value from prob. vector
            draw = np.random.rand()
            i = np.argwhere(draw<np.cumsum(p)/sum(p))[0]

            self.zr[n,:] = 0
            if i == Kr: # If new component: add new column to partition matrix
                self.zr = np.hstack([self.zr, np.zeros(self.N, 1)]) 
            self.zr[n,i] = 1

        elif direction == "columns":
            X_[:,n] = 0 #adj matrix without currently sampled node columns

            Kc = len(self.zc[0])

            if Kc > 1:
                idx = np.argwhere(np.sum(self.zc[nn], 0) == 0)
                self.zc = np.delete(self.zc, idx, axis=1)
                Kc -= len(idx)

            # m = n. of nodes in each component 
            mr = np.sum(self.zr[nn,:], 0)[np.newaxis] #newaxis allows m to become 2d array (for transposing)
            mc = np.sum(self.zc[nn,:], 0)[np.newaxis]
            Mr = np.tile(mr.T, (1, Kc))

            LM = self.zr.T @ X_ @ self.zc

            X_rev = (np.where((X_==0)|(X_==1), X_^1, X_) - np.eye(X_.shape[0])).copy() #reverse matrix for non_links
            X_rev[:,n] = 0
            NLM = self.zr.T @ X_rev @ self.zc #n. of non-links between biclusters without current node

            s = self.zr[nn,:].T @ self.X[nn, n]
            S = np.tile(s[np.newaxis].T, (1, Kc))

            logLikelihood_new = np.sum(betaln(LM + S + self.a, NLM + Mr - S + self.b) \
                                     - betaln(LM + self.a, NLM + self.b)
                                       , 1)

            logLikelihood_old = np.sum(betaln(s + self.a, mr - s + self.b) \
                                     - betaln(self.a, self.b)
                                       , 1)

            logLikelihood = np.concatenate([logLikelihood_new, logLikelihood_old])
            logPrior = np.log(np.append(mc, self.A))

            logPosterior = logPrior + logLikelihood

            p = np.exp(logPosterior-max(logPosterior)) 

            # Assignment through random draw fron unif(0,1), taking first value from prob. vector
            draw = np.random.rand()
            i = np.argwhere(draw<np.cumsum(p)/sum(p))[0]

            self.zc[n,:] = 0
            if i == Kc: # If new component: add new column to partition matrix
                self.zc = np.hstack([self.zc, np.zeros(self.N,1)]) 
            self.zc[n,i] = 1
    
    def evalLikelihood(nn, K, directed, binary):
        X_ = self.X[np.ix_(nn,nn)] #adjacency matrix without currently sampled node

        if directed:
            if binary: #directed binary
                # m = n. of nodes in each component 
                m = np.sum(self.z[nn,:], 0)[np.newaxis] #newaxis allows m to become 2d array (for transposing)
                
                M1 = self.z[nn,:].T @ X_ @ self.z[nn,:] #n. of links between components without current node

                # r = n. of links from current node to components
                r = self.z[nn,:].T @ self.X[n, nn]
                R = np.tile(r, (K, 1))

                # s = n. of links from components to current node
                s = self.z[nn,:].T @ self.X[nn, n]
                S = np.tile(s[np.newaxis].T, (1, K))

                M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()
                LM = np.concatenate([M1,M2],axis=1) #Link Matrix

                LM_n = np.zeros((LM.shape[0], LM.shape[1])) #LM of current node n
                LM_n[0:R.shape[0], 0:R.shape[1]] += R
                s_diag = np.diag(s.flatten())
                LM_n[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
                S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
                if K > 1: 
                    LM_n[:,-S.shape[1]:] += S

                M0 = m.T@m - np.diag(m.flatten()) - M1 #n. of non-links between components without current node
                M0_2 = M0.T[~np.eye(M0.T.shape[0],dtype=bool)].reshape(M0.T.shape[0], -1)
                NLM = np.concatenate([M0, M0_2], axis=1) #Non-Link Matrix

                PLM = np.tile(m, (K, 1)) + np.diag(m.flatten()) #Potential links matrix from other clusts
                PLM_2 = PLM[~np.eye(PLM.shape[0],dtype=bool)].reshape(PLM.shape[0], -1)
                P_n = np.concatenate([PLM,PLM_2],axis=1) #Potential links for current node n

                logLikelihood_old = np.sum(betaln(LM + LM_n + self.a, NLM + P_n - LM_n + self.b) \
                                     - betaln(LM + self.a, NLM + self.b)
                                       , 1) #log prob of assigning to existing clusters

                logLikelihood_new = np.sum(betaln(np.hstack([r,s]) + self.a, np.hstack([m-r,m-s]) + self.b) \
                                         - betaln(self.a, self.b)
                                           , 1) #log prob of assigning to new clusters

                logLikelihood = np.concatenate([logLikelihood_old, logLikelihood_new])
                
            else: #directed weighted
                m = np.sum(self.z[nn,:], 0)[np.newaxis]

                r = self.z[nn,:].T @ self.X[n, nn]
                R = np.tile(r, (K, 1))

                s = self.z[nn,:].T @ self.X[nn, n]
                S = np.tile(s[np.newaxis].T, (1, K))

                M = np.tile(m, (K, 1)) + np.diag(m.flatten())

                M1 = self.z[nn,:].T @ X_ @ self.z[nn,:]
                M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()

                LM = np.concatenate([M1,M2],axis=1) #Link Matrix
                LM_n = np.zeros((LM.shape[0], LM.shape[1])) #Link Matrix of current node n
                LM_n[0:R.shape[0], 0:R.shape[1]] += R
                s_diag = np.diag(s.flatten())
                LM_n[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
                S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
                if K > 1: 
                    LM_n[:,-S.shape[1]:] += S

                M__2 = M[~np.eye(M.shape[0],dtype=bool)].reshape(M.shape[0], -1)
                max_links_current_node = np.concatenate([M,M__2],axis=1)

                
                # Section for C
                X_bin_ = self.X_bin[np.ix_(nn,nn)]

                r_bin = self.z[nn,:].T @ self.X_bin[n, nn]
                R_bin = np.tile(r_bin, (K, 1))

                s_bin = self.z[nn,:].T @ self.X_bin[nn, n]
                S_bin = np.tile(s_bin[np.newaxis].T, (1, K))

                C1 = self.z[nn,:].T @ X_bin_ @ self.z[nn,:]
                C2 = C1.T[~np.eye(C1.T.shape[0],dtype=bool)].reshape(C1.T.shape[0], -1).copy()
                C = np.concatenate([C1, C2], axis=1) #no. of possible links

                LM_n_bin = np.zeros((LM.shape[0], LM.shape[1]))
                LM_n_bin[0:R_bin.shape[0], 0:R_bin.shape[1]] += R_bin
                s_diag_bin = np.diag(s_bin.flatten())
                LM_n_bin[0:s_diag_bin.shape[0], 0:s_diag_bin.shape[1]] += s_diag_bin
                S_bin = S_bin.T[~np.eye(S_bin.shape[0],dtype=bool)].reshape(S_bin.shape[0], -1)
                if K > 1: 
                    LM_n_bin[:,-S_bin.shape[1]:] += S_bin
                #End section for C

                F = np.zeros((LM.shape[0], LM.shape[1]))
                f_out = np.sum(gammaln(np.multiply(self.z[nn,:].T, self.X[n, nn]) + 1), axis = 1)
                F_out = np.tile(f_out, (K, 1))

                f_in = np.sum(gammaln(np.multiply(self.z[nn,:].T, self.X[nn, n]) + 1), axis = 1)
                f_in_diag = np.diag(f_in)
                F_in = np.tile(f_in[np.newaxis].T, (1, K))
                F_in = F_in.T[~np.eye(F_in.shape[0],dtype=bool)].reshape(F_in.shape[0], -1)

                F[0:F_out.shape[0], 0:F_out.shape[1]] += F_out
                F[0:F_out.shape[0], 0:F_out.shape[1]] += f_in_diag
                if K > 1: 
                    F[:,-F_in.shape[1]:] += F_in
                if K == 1:
                    F[:] += f_in


                logLikelihood_old = np.sum(gammaln(LM + LM_n + self.a) - gammaln(LM + self.a) \
                            + (LM + self.a)*np.log(C + self.b) - (LM + LM_n + self.a)*np.log(C + LM_n_bin + self.b) \
                            - F, 1)

                logLikelihood_new = np.sum(gammaln(np.hstack([r,s]) + self.a) - gammaln(self.a) \
                            + (self.b)*np.log(self.a) - (np.hstack([r,s]) + self.a)*np.log(np.hstack([r_bin,s_bin]) + self.b) \
                            - np.hstack([f_out, f_in]))[np.newaxis]

                logLikelihood = np.concatenate([likelihood, likelihood_n])                
        else:
            if binary: #undirected binary
                # m = n. of nodes in each component 
                m = np.sum(self.z[nn], 0)[np.newaxis]
                P = np.tile(m, (K, 1)) #Potential links

                M1 = self.z[nn].T @ X_ @ self.z[nn] - np.diag(np.sum(X_@self.z[nn]*self.z[nn], 0) / 2) #n. of links between components without current node

                M0 = m.T@m - np.diag((m*(m+1) / 2).flatten()) - M1 #n. of non-links between components without current node

                r = self.z[nn].T @ self.X[nn, n] #n. of links from current node to components
                R = np.tile(r, (K, 1))

                logLikelihood_old = np.sum(betaln(M1 + R + self.a, M0 + P - R + self.b) \
                                         - betaln(M1 + self.a, M0 + self.b)
                                           , 1)

                logLikelihood_new = np.sum(betaln(r + self.a, m - r + self.b) \
                                         - betaln(self.a, self.b)
                                           , 1)

                logLikelihood = np.concatenate([logLikelihood_old, logLikelihood_new])

            else: #undirected weighted
                pass

        return logLikelihood

    # def gibbs_sweep(self, n, directed, binary):
    #     nn = list(self.idx_list)
    #     nn.remove(n) #nn = index mask without currently sampled node n

    #     X_ = self.X[np.ix_(nn,nn)] #adjacency matrix without currently sampled node

    #     K = len(self.z[0])  # K = n. of components

    #     # Delete empty component if present
    #     if K > 1:
    #         idx = np.argwhere(np.sum(self.z[nn], 0) == 0)
    #         self.z = np.delete(self.z, idx, axis=1)
    #         K -= len(idx)

    #     if directed:
    #         if binary: #directed binary
    #             # m = n. of nodes in each component 
    #             m = np.sum(self.z[nn,:], 0)[np.newaxis] #newaxis allows m to become 2d array (for transposing)
                
    #             M1 = self.z[nn,:].T @ X_ @ self.z[nn,:] #n. of links between components without current node

    #             # r = n. of links from current node to components
    #             r = self.z[nn,:].T @ self.X[n, nn]
    #             R = np.tile(r, (K, 1))

    #             # s = n. of links from components to current node
    #             s = self.z[nn,:].T @ self.X[nn, n]
    #             S = np.tile(s[np.newaxis].T, (1, K))

    #             M2 = M1.T[~np.eye(M1.T.shape[0],dtype=bool)].reshape(M1.T.shape[0], -1).copy()
    #             LM = np.concatenate([M1,M2],axis=1) #Link Matrix

    #             LM_n = np.zeros((LM.shape[0], LM.shape[1])) #LM of current node n
    #             LM_n[0:R.shape[0], 0:R.shape[1]] += R
    #             s_diag = np.diag(s.flatten())
    #             LM_n[0:s_diag.shape[0], 0:s_diag.shape[1]] += s_diag
    #             S = S.T[~np.eye(S.shape[0],dtype=bool)].reshape(S.shape[0], -1)
    #             if K > 1: 
    #                 LM_n[:,-S.shape[1]:] += S

    #             M0 = m.T@m - np.diag(m.flatten()) - M1 #n. of non-links between components without current node
    #             M0_2 = M0.T[~np.eye(M0.T.shape[0],dtype=bool)].reshape(M0.T.shape[0], -1)
    #             NLM = np.concatenate([M0, M0_2], axis=1) #Non-Link Matrix

    #             PLM = np.tile(m, (K, 1)) + np.diag(m.flatten()) #Potential links matrix from other clusts
    #             PLM_2 = PLM[~np.eye(PLM.shape[0],dtype=bool)].reshape(PLM.shape[0], -1)
    #             P_n = np.concatenate([PLM,PLM_2],axis=1) #Potential links for current node n

    #             logLikelihood_old = np.sum(betaln(LM + LM_n + self.a, NLM + P_n - LM_n + self.b) \
    #                                  - betaln(LM + self.a, NLM + self.b)
    #                                    , 1) #log prob of assigning to existing clusters

    #             logLikelihood_new = np.sum(betaln(np.hstack([r,s]) + self.a, np.hstack([m-r,m-s]) + self.b) \
    #                                      - betaln(self.a, self.b)
    #                                        , 1) #log prob of assigning to new clusters

    #             logLikelihood = np.concatenate([logLikelihood_old, logLikelihood_new])
                
    #         else: #directed weighted

    #             pass
    #     else:
    #         if binary: #undirected binary
    #             # m = n. of nodes in each component 
    #             m = np.sum(self.z[nn], 0)[np.newaxis]
    #             P = np.tile(m, (K, 1)) #Potential links

    #             M1 = self.z[nn].T @ X_ @ self.z[nn] - np.diag(np.sum(X_@self.z[nn]*self.z[nn], 0) / 2) #n. of links between components without current node

    #             M0 = m.T@m - np.diag((m*(m+1) / 2).flatten()) - M1 #n. of non-links between components without current node

    #             r = self.z[nn].T @ self.X[nn, n] #n. of links from current node to components
    #             R = np.tile(r, (K, 1))

    #             logLikelihood_old = np.sum(betaln(M1 + R + self.a, M0 + P - R + self.b) \
    #                                      - betaln(M1 + self.a, M0 + self.b)
    #                                        , 1)

    #             logLikelihood_new = np.sum(betaln(r + self.a, m - r + self.b) \
    #                                      - betaln(self.a, self.b)
    #                                        , 1)

    #             logLikelihood = np.concatenate([logLikelihood_old, logLikelihood_new])

    #         else: #undirected weighted
    #             pass

        
    #     logPrior = np.log(np.append(m, self.A)) #TODO: Priors

    #     logPosterior = logPrior + logLikelihood

    #     # Convert from log probabilities, normalized to max
    #     p = np.exp(logPosterior-max(logPosterior)) 

    #     # Assignment through random draw fron unif(0,1), taking first value from prob. vector
    #     draw = np.random.rand()
    #     i = np.argwhere(draw<np.cumsum(p)/sum(p))[0]

    #     # Assignment of current node to component i
    #     self.z[n,:] = 0
    #     if i == K: # If new component: add new column to partition matrix
    #         self.z = np.hstack([self.z, np.zeros(self.N,1)]) 
    #     self.z[n,i] = 1


