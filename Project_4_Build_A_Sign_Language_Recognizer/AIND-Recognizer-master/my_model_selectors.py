import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self, all_word_sequences: dict, all_word_Xlengths: dict, this_word: str,
                 n_constant=3,
                 min_n_components=2, max_n_components=10,
                 random_state=14, verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                    random_state=self.random_state, verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """ select the model with the lowest Bayesian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN
    Addition:
    p = num_states**2 + (2 * num_states * num_features) - 1
    """
    
    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)

        # TODO implement model selection based on BIC scores       
        best_score, best_model = float("inf"), None
        
        for num_hidden_states in range(self.min_n_components, self.max_n_components+1):
            try:
                model = GaussianHMM(n_components=num_hidden_states, n_iter=1000).fit(self.X, self.lengths)
                logL = model.score(self.X, self.lengths)
                num_features = len(self.X[0])
                p = num_hidden_states**2 + (2 * num_hidden_states * num_features) - 1
                logN = np.log(len(self.X))
                BIC = -2 * logL + p * logN
                #check if BIC is less
                if BIC < best_score:
                    best_score = BIC
                    best_model = model
            except:
                pass
                
        return best_model
        


class SelectorDIC(ModelSelector):
    ''' select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application to hmm topology optimization."
    Document Analysis and Recognition, 2003. Proceedings. Seventh International Conference on. IEEE, 2003.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.58.6208&rep=rep1&type=pdf
    https://pdfs.semanticscholar.org/ed3d/7c4a5f607201f3848d4c02dd9ba17c791fc2.pdf
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)

        # TODO implement model selection based on DIC scores
        best_score, best_model = float("-inf"), None
        
        for num_hidden_states in range(self.min_n_components, self.max_n_components+1):
            try:
                P_X_others = []
                model = GaussianHMM(n_components=num_hidden_states, n_iter=1000).fit(self.X, self.lengths)
                for word, (X_i, lengths_i) in self.hwords.items():
                    if word == self.this_word:
                        P_X_i = model.score(X_i, lengths_i)   #logL
                    else:
                        P_X_others.append(model.score(X_i, lengths_i))
                mean_P_X_others = np.mean(P_X_others)
                # DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
                DIC = P_X_i - mean_P_X_others
                
                #check if DIC is greater than best_score
                if DIC > best_score:
                    best_score = DIC
                    best_model = model
            except:
                pass
                
        return best_model


class SelectorCV(ModelSelector):
    ''' select best model based on average log Likelihood of cross-validation folds

    '''
    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        
        mean_score, best_score, best_model = None, float("-inf"), None
        
        n_splits = min(len(self.sequences), 3)
        if n_splits < 2:
            return None
        
        # implement model selection using CV
        for num_hidden_states in range(self.min_n_components, self.max_n_components+1):
            split_method = KFold(n_splits)
            logL = []
            for cv_train_idx, cv_test_idx in split_method.split(self.sequences):               
                X_train, lengths_train = combine_sequences(cv_train_idx, self.sequences)
                X_test, lengths_test = combine_sequences(cv_test_idx, self.sequences)
                try:
                    model = GaussianHMM(n_components=num_hidden_states, n_iter=1000).fit(X_train, lengths_train)
                    logL.append(model.score(X_test, lengths_test))                  
                except:
                    pass
                
            mean_score = np.mean(logL)
            if mean_score > best_score:
                best_score = mean_score
                best_model = model
                
        return best_model
                
