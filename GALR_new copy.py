import tensorflow as tf
import numpy as np
import pandas as pd
import os
import scipy
import seaborn as sns
import matplotlib.pyplot as plt
import time
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


# Structure: loop through a big sample by taking minibatches, do this for a number of epochs . Do all of this for
# however many trials,randomising the learning rate parameters each time
number_of_trails = 56
number_of_epochs = 400
mini_batch_size = 10
sample_size = 2000
learn_steps = (number_of_epochs*sample_size) / mini_batch_size
hidden_layer_size_d = 6
hidden_layer_size_g = 5
optimize_algorithm = 'momentum0.6'  # one of 'adam', 'momentum0.6', 'momentum0.9', 'gd'


# Choose directory for data based on algorithm choice
algo_directory_dict = {'adam':'/Users/Billy/PycharmProjects/GALR/data/adam',
                       'momentum0.6':'/Users/Billy/PycharmProjects/GALR/data/momentum0.6',
                       'momentum0.9':'/Users/Billy/PycharmProjects/GALR/data/momentum0.9',
                       'gd':'/Users/Billy/PycharmProjects/GALR/data/gd'}

directory = algo_directory_dict[optimize_algorithm]


# define actual distribution
real_mean = 6
real_sd = 1


# discriminator and generator NNs
def discriminator(input, parameters):
    pre_0 = tf.to_float(input)
    activ_1 = tf.add(tf.matmul(pre_0, parameters[0]), parameters[1])
    pre_1 = tf.tanh(activ_1)
    activ_2 = tf.add(tf.matmul(pre_1, parameters[2]), parameters[3])
    pre_2 = tf.tanh(activ_2)
    activ_3 = tf.add(tf.matmul(pre_2, parameters[4]), parameters[5])
    output = tf.sigmoid(activ_3)
    return output


def generator(input, parameters):
    pre_0 = tf.to_float(input)
    activ_1 = tf.add(tf.matmul(pre_0, parameters[0]), parameters[1])
    pre_1 = tf.tanh(activ_1)
    output = tf.add(tf.matmul(pre_1, parameters[2]), parameters[3])
    return output


# Create weights and biases variables
weight_d_1 = tf.Variable(tf.random_uniform([1, hidden_layer_size_d], minval=0, maxval=1, dtype=tf.float32))
bias_d_1 = tf.Variable(tf.random_uniform([hidden_layer_size_d], minval=0, maxval=1, dtype=tf.float32))
weight_d_2 = tf.Variable(tf.random_uniform([hidden_layer_size_d, hidden_layer_size_d], minval=0, maxval=1, dtype=tf.float32))
bias_d_2 = tf.Variable(tf.random_uniform([hidden_layer_size_d], minval=0, maxval=1, dtype=tf.float32))
weight_d_3 = tf.Variable(tf.random_uniform([hidden_layer_size_d, 1], minval=0, maxval=1, dtype=tf.float32))
bias_d_3 = tf.Variable(tf.random_uniform([1], minval=0, maxval=1, dtype=tf.float32))

d_parameters = [weight_d_1,bias_d_1, weight_d_2, bias_d_2,weight_d_3, bias_d_3]


weight_g_1 = tf.Variable(tf.random_uniform([1, hidden_layer_size_g], minval=0, maxval=1, dtype=tf.float32))
bias_g_1 = tf.Variable(tf.random_uniform([hidden_layer_size_g], minval=0, maxval=1, dtype=tf.float32))
weight_g_2 = tf.Variable(tf.random_uniform([hidden_layer_size_g, 1], minval=0, maxval=1, dtype=tf.float32))
bias_g_2 = tf.Variable(tf.random_uniform([1], minval=0, maxval=1, dtype=tf.float32))

g_parameters = [weight_g_1,bias_g_1, weight_g_2, bias_g_2]


# losses
x = tf.placeholder(tf.float32, shape=(None, 1))
z = tf.placeholder(tf.float32, shape=(None, 1))

with tf.variable_scope("Discrim") as scope:
    D1 = discriminator(x, d_parameters)
    scope.reuse_variables()
    D2 = discriminator(generator(z, g_parameters), d_parameters)

loss_g = tf.reduce_mean(-tf.log(D2))
loss_d = tf.reduce_mean(-tf.log(D1) - tf.log(1 - D2))


# Game Adaptive Learning Rate
phi_g = tf.placeholder(tf.float32)
phi_d = tf.placeholder(tf.float32)
gamma = tf.placeholder(tf.float32)
adjuster = (1/2 * tf.log(phi_d/(2*phi_g +phi_d))) / tf.log(0.25)

V = tf.minimum(tf.reduce_mean(tf.log(D1)+tf.log(1-D2)),0)
V1 = tf.where(tf.is_nan(V), tf.zeros_like(V), V)

learning_rate_d = gamma-phi_d*tf.tanh(adjuster*V1)
learning_rate_g = gamma + phi_g*(1 + tf.tanh(adjuster*V1))

# Train step, we chose the algorithm based on the optimize_algorithm variable

algo_dict = {   'adam':['tf.train.AdamOptimizer(learning_rate_g).minimize(loss_g, var_list=g_parameters)',
                        'tf.train.AdamOptimizer(learning_rate_d).minimize(loss_d, var_list=d_parameters)'],
                'momentum0.6':[ 'tf.train.MomentumOptimizer(learning_rate_g,0.6).minimize(loss_g, var_list=g_parameters)',
                                'tf.train.MomentumOptimizer(learning_rate_d,0.6).minimize(loss_d, var_list=g_parameters)'],
                'momentum0.9':[ 'tf.train.MomentumOptimizer(learning_rate_g,0.9).minimize(loss_g, var_list=g_parameters)',
                                'tf.train.MomentumOptimizer(learning_rate_d,0.9).minimize(loss_d, var_list=g_parameters)'],
                'gd':[ 'tf.train.GradientDescentOptimizer(learning_rate_g).minimize(loss_g, var_list=g_parameters)',
                        'tf.train.GradientDescentOptimizer(learning_rate_d).minimize(loss_d, var_list=g_parameters)']
                }


train_g = eval(algo_dict[optimize_algorithm][0])
train_d = eval(algo_dict[optimize_algorithm][1])



# this just makes sure that we are not going to overwrite old data
f = open('recently_completed_trial.txt','r')
start_line = int(f.read())+1
f.close()

simuls = range(start_line,start_line+number_of_trails)

start_time = time.time()

for it in simuls:
    # sample data
    generator_input = np.random.uniform(0, 1, (sample_size, 1))
    real_dist = np.random.normal(real_mean, real_sd, (sample_size, 1))

    # sample parameters we sample 2 phis and also take phi = 0 and then 3 gammas and then train the GAN on each of
    # the 9 parameter pairs this gives:
    gamma_vec = np.random.uniform(0.00001,0.1,3)  # 0.00001,0.01,3
    phi_vec = np.random.uniform(0.00001, 0.2, 3) #0.00001, 0.02, 3, phi should be bigger as it is then made smaller by tanh
    phi_vec[0] = 0.00000001

    res_matrix = np.zeros((len(gamma_vec) * len(phi_vec), sample_size))
    gamma_out_vec, phi_out_vec = np.zeros((len(gamma_vec) * len(phi_vec))), np.zeros((len(gamma_vec) * len(phi_vec)))

    row =0
    for i, p in enumerate(phi_vec):
        for j, k in enumerate(gamma_vec):
            print 'Trial: {}/{}'.format(it,simuls[len(simuls)-1])
            print 'Step: {}/{}'.format(i*len(phi_vec)+j+1, len(phi_vec)*len(gamma_vec))
            print 'Phi: {0}'.format(p)
            print 'Gamma: {0}'.format(k)

            with tf.Session() as sess:
                tf.global_variables_initializer().run()
                for step in range(1, learn_steps):
                    start_index = ((step - 1) * mini_batch_size) % sample_size
                    end_index = (step * mini_batch_size) % sample_size

                    x_minibatch = real_dist[start_index:end_index,:]
                    z_minibatch = generator_input[start_index:end_index,:]

                    sess.run(train_d, feed_dict={x: x_minibatch, z: z_minibatch, phi_g: p,phi_d:p, gamma:k})
                    sess.run(train_g, feed_dict={x: x_minibatch, z: z_minibatch, phi_g: p,phi_d:p,gamma:k})

                generated = sess.run(generator(generator_input,g_parameters))
                res_matrix[row] = generated.reshape(sample_size)
                gamma_out_vec[row] = k
                phi_out_vec[row] = p
                row = row+1

                # decision_surface = sess.run(D1,feed_dict={x: decision_surface_input})
                # sns.distplot(generated, hist=False, rug=False)
                # sns.distplot(real_dist, hist=False, rug=False)
                # sns.distplot(decision_surface, hist=False, rug=False)
                # plt.show()


    res_dataframe = pd.DataFrame(data=res_matrix.astype(float))
    gamma_dataframe = pd.DataFrame(data=gamma_out_vec.astype(float))
    phi_dataframe = pd.DataFrame(data=phi_out_vec.astype(float))

    output_dataframe1 = pd.concat([gamma_dataframe.reset_index(drop=True), phi_dataframe], axis=1)
    output_dataframe2 = pd.concat([output_dataframe1.reset_index(drop=True), res_dataframe], axis=1)

    pd.DataFrame.to_csv(output_dataframe2, directory +'/output{0}.csv'.format(it), sep=',', header=False, float_format='%.7f', index=False)

    f = open('recently_completed_trial.txt', 'w')
    f.write(str(it))
    f.close()

print 'Total time taken: {0} seconds'.format(time.time()- start_time)



os.system('afplay /System/Library/Sounds/Sosumi.aiff')
