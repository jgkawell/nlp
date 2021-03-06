from collections import Counter
import numpy as np
import random

# initialize the data field variables
_train_data = []
_state_space = []
_observation_space = []
_initial_prob = []
_observation_prob = [[]]
_transition_prob = [[]]

# global string values for files and markers
_full_file_name = "berp-POS-training.txt"
_train_file_name = "train.txt"
_dev_file_name = "dev.txt"
_test_file_name = "test.txt"
_dev_results_file_name = "dev-results.txt"
_test_results_file_name = "test-results.txt"
_unknown_word_marker = "<UNK>"
_sentence_marker = "<s>"

# global int values for algorithm params
_dev_partition_ratio = 10
        
# preprocess the data to create a training and dev set
def preprocess():

    # read in the training data
    full_file = open(_full_file_name, "r")

    # create subset files for training and dev
    train_file = open(_train_file_name, "w")
    dev_file = open(_dev_file_name, "w")

    # pull out the sentences from the lines
    train_sentences = []
    temp_sentence = []
    for line in full_file:
        temp_sentence.append(line)
        if line == "\n":
            train_sentences.append(temp_sentence.copy())
            temp_sentence = []
        
    # get a random sampling of sentence indices
    sample = random.sample(range(len(train_sentences)), int(len(train_sentences) / _dev_partition_ratio))

    # pull out the sentences into train and dev sets
    dev_sentences = []
    count = 0
    for i in sample:
        i -= count
        dev_sentences.append(train_sentences.pop(i))
        count += 1

    # fill training file
    for sentence in train_sentences:
        for line in sentence:
            train_file.write(line)

    # fill dev file
    for sentence in dev_sentences:
        for line in sentence:
            dev_file.write(line)

# calculate all needed probs and counts for hmm/viterbi
def train():
    global _train_data
    global _initial_prob
    global _observation_prob
    global _transition_prob

    # get the list of sentences with words and pos for training
    _train_data = getSentences(_train_file_name)

    len_observation_space, len_state_space = buildSpaces()

    # iterate through training data and count the transitions for pos
    transition_count_matrix, observation_count_matrix = buildCountMatrices(len_state_space, len_observation_space)

    # find the observation likelihood for the pos given words
    _observation_prob = buildProbMatrix(len_state_space, len_observation_space, observation_count_matrix)

    # find the transition probability for pos given previous pos
    _transition_prob = buildProbMatrix(len_state_space, len_state_space, transition_count_matrix)

    # calculate the initial probabilities
    sentence_beginning_index = _state_space.index(_sentence_marker)
    for s in range(0, len(_state_space)):
        _initial_prob.append(_transition_prob[sentence_beginning_index][s])

# pulls out words and pos in sentences
def getSentences(file_name, dev=True):
     # read in training data
    lines = open(file_name, "r")
    
    num_sentences = 0    
    sentence_list = []
    sentence = []
    for line in lines:
        # increment the count for the total length of the training data
        num_sentences += 1
         #  pull out the individual columns of the data
        fields = line.rstrip("\n\r").split("\t")
        
        # if the data is not a blank line, add the data sentence
        # else, add sentence to list and clear for new sentence
        if len(fields) > 1:
            # if it is the dev file, we can pull out the pos (2) position for training
            # else, we only have two positions since there is no pos field
            if dev:
                entry = (fields[0], fields[1], fields[2])
            else:
                entry = (fields[0], fields[1])

            # add the entry to the sentence
            sentence.append(entry)
        else:
            # add sentence to list and clear
            sentence_list.append(sentence.copy())
            sentence.clear()

    return sentence_list

# scan through data and build the observation and state spaces
def buildSpaces():
    global _observation_space
    global _state_space
    
    # scan through data and find the spaces along with the single counts in the observation space
    _observation_space = []
    single_counts = []
    _state_space = []
    for sentence in _train_data:
        for entry in sentence:
            # pull out the word and pos
            word = entry[1]
            part = entry[2]

            # if word doesn't exist yet in observation space, add it
            # else, try to remove it from the single counts list
            if word not in _observation_space:
                _observation_space.append(word)
                single_counts.append(word)
            else:
                # try to remove word if it is in the single counts list
                try:
                    single_counts.remove(word)
                except:
                    pass

            # if pos doesn't exist yet in state space, add it
            if part not in _state_space:
                _state_space.append(part)

    # remove words with only a single count and replace them with <UNK>
    for word in single_counts:
        _observation_space.remove(word)

    # add unknown word marker <UNK>
    _observation_space.append(_unknown_word_marker)

    #  add sentence marker (<s>)
    _state_space.append(_sentence_marker)

    return (len(_observation_space), len(_state_space))

# build the count matrices needed to build the prob matrices
def buildCountMatrices(len_state_space, len_observation_space):

    # initialize as ones for laplace smoothing
    transition_count_matrix = np.ones((len_state_space, len_state_space))
    emission_count_matrix = np.ones((len_state_space, len_observation_space))
    
    # iterate through training data and count the transitions for pos and emissions for words
    for sentence in _train_data:
        prev_part = _sentence_marker
        for entry in sentence:
            cur_word = entry[1]
            cur_part = entry[2]

            # increment the count for the transition count
            transition_count_matrix[_state_space.index(cur_part)][_state_space.index(prev_part)] += 1

            # set the previous part
            prev_part = cur_part

            # increment the count for the emission count
            try:
               emission_count_matrix[_state_space.index(cur_part)][_observation_space.index(cur_word)] += 1
            except:
               emission_count_matrix[_state_space.index(cur_part)][_observation_space.index(_unknown_word_marker)] += 1

    return (transition_count_matrix, emission_count_matrix)

#  build the prob matrices (both transition and emission)
def buildProbMatrix(num_rows, num_cols, count_matrix):

    # scan through and find the sums of the counts on each row (needed for laplace smoothing)
    prob_matrix = np.zeros((num_rows, num_cols))
    row_sums = np.zeros(num_rows)
    for row in range(0, num_rows):
        for col in range(0, num_cols): 
            row_sums[row] += count_matrix[row][col]

    # find the transition probabilities for the pos
    for row in range(0, num_rows):
        for col in range(0, num_cols):
            # add num_rows to denominator for laplace smoothing
            prob_matrix[row][col] = count_matrix[row][col] / (row_sums[row] + num_rows)

    return prob_matrix

#  test using the basic "most frequent tag" technique
def test(run_file_name, results_file_name):

    # create results file
    results_file = open(results_file_name, "w")

    # retrieve data to run through model
    data = getSentences(run_file_name, dev=False)
            
    # go through data and run viterbi on each sentence, printing the results
    for sentence in data:
        observations = []
        for entry in sentence:
            word = entry[1]
            # try to get the index of the word, if not found, substitute the unknown word marker
            try:
                observations.append(_observation_space.index(word))
            except:
                observations.append(_observation_space.index(_unknown_word_marker))

        # run viterbi on each sentence
        best_path = viterbi(len(_state_space), _transition_prob, _observation_prob, _initial_prob, observations)

        # write results to the file
        count = 0
        for entry in sentence:
            # pull out the num, word, and predicted pos
            num = str(entry[0])
            word = str(entry[1])
            pos = _state_space[best_path[count]]

            # write line
            results_file.write(num + "\t" + word + "\t" + pos + "\n")

            # increment count
            count += 1

        # print line between sentences
        results_file.write("\n")

# implements the viterbi algorithm
def viterbi(num_states, transition, emission, prob, observations):

    # initialize constants for viterbi
    num_observations = len(observations)
    log_transition = np.log(transition)
    log_emission = np.log(emission)
    log_probability = np.log(prob)

    # initialize tracking matrices for viterbi
    path_prob = np.zeros((num_observations, num_states))
    back_pointer = np.zeros((num_observations, num_states))

    # initialize first column of the path prob matrix (first set of states)
    for s in range(0, num_states):
        path_prob[0][s] = log_probability[s] + log_emission[s][observations[0]]

    # scan through remaining observations and states finding the most probable and saving the backpointer
    for o in range(1, num_observations):
        for s in range(0, num_states):
            path_prob[o][s] = np.max(path_prob[o-1] + log_transition[s][:]) + log_emission[s][observations[o]]
            # don't need the emission value for back pointer
            back_pointer[o][s] = np.argmax(path_prob[o-1] + log_transition[s][:])

    # pull out the last saved backpointer
    best_pointer = np.argmax(path_prob[-1])

    # find the remaining backpointers from the last saved
    best_path = np.zeros(num_observations, dtype=np.int32)
    best_path[-1] = best_pointer
    for p in range(num_observations - 2, -1, -1):
        best_path[p] = back_pointer[p+1][best_path[p+1]]

    return best_path

# main to run program
if  __name__ == "__main__":

    # read and process data
    print("Processing data...")
    preprocess()

    # train on data
    print("Training on data...")
    train()

    # test on the dev set
    print("Running dev data...")
    test(_dev_file_name, _dev_results_file_name)

    # test on the test set
    print("Running test data...")
    test(_test_file_name, _test_results_file_name)

    # finished
    print("Finished.")