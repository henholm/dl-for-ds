"""In this assignment you will train and test a one layer network with multiple
outputs to classify images from the CIFAR-10 dataset. You will train the network
using mini-batch gradient descent applied to a cost function that computes the
cross-entropy loss of the classifier applied to the labelled training data and
an L2 regularization term on the weight matrix."""


import os
import csv
import pickle
import matplotlib.pyplot as plt
import numpy as np


__author__ = "Henrik Holm"


def load_batch(filepath):
	""" Copied from the dataset website """
	with open(filepath, 'rb') as fo:
		dict = pickle.load(fo, encoding='bytes')
	return dict


def split_batch(batch, num_of_labels):
	""" Split the input batch into its labels and its data
	X: image pixel data, size d x n, entries between 0 and 1. n is number of
	   images (10000) and d dimensionality of each image (3072 = 32 * 32 * 3).
	Y: K x n (with K = # of labels = 10) and contains the one-hot
	   representation of the label for each image (0 to 9).
	y: vector of length n containing label for each image, 0 to 9. """

	X = (batch[b'data'] / 255).T # Normalize by dividing over 255.
	y = np.asarray(batch[b'labels'])
	Y = (np.eye(num_of_labels)[y]).T

	return X, Y, y


def load_dataset(folder, filename, num_of_labels):
	""" Load a batch and split it before returning it as a dictionary
	folder: folder where data is located.
	filename: name of file.
	num_of_labels: number of labels in data. """
	dataset_dict = load_batch(folder + filename)
	X, Y, y = split_batch(dataset_dict, num_of_labels=num_of_labels)
	dataset = {'X': X, 'Y': Y, 'y': y}

	return dataset


def normalize_dataset(data, verbose=False):
	""" Pre-process data by normalizing """
	# "Both mean_X and std_X have size d x 1".
	mean_X = np.mean(data, axis=1)
	std_X = np.std(data, axis=1)

	data = data - np.array([mean_X]).T
	data = data / np.array([std_X]).T

	if verbose:
		print()
		print(f'Mean after normalizing:\t{np.mean(data)}')
		print(f'Std after normalizing:\t{np.std(data)}')

	return data


def unpickle(filename):
	""" Unpickle a file """
	with open(filename, 'rb') as f:
		file_dict = pickle.load(f, encoding='bytes')

	return file_dict


def montage(W, title, labels):
	""" Display the image for each label in W """
	_, ax = plt.subplots(2, 5)
	for i in range(2):
		for j in range(5):
			im  = W[((i * 5) + j), :].reshape(32,32,3, order='F')
			sim = (im-np.min(im[:]))/(np.max(im[:])-np.min(im[:]))
			sim = sim.transpose(1,0,2)
			ax[i][j].imshow(sim, interpolation='nearest')
			ax[i][j].set_title(str(labels[((5 * i) + j)]), fontsize=10)
			ax[i][j].axis('off')

	plt.savefig(f'plots/weights_{title}.png', bbox_inches="tight")
	plt.show()

	return


def plot_lines(line_A, line_B, label_A, label_B, xlabel, ylabel, title, show=False):
   """ Plots performance curves """
   assert(line_A.shape == line_B.shape)

   _, ax = plt.subplots(figsize=(10, 8))
   ax.plot(range(len(line_A)), line_A, label=label_A)
   ax.plot(range(len(line_B)), line_B, label=label_B)
   ax.legend()

   ax.set(xlabel=xlabel, ylabel=ylabel)
   ax.grid()

   plt.savefig(f'plots/{title}.png', bbox_inches="tight")

   if show:
	   plt.show()

   return plt


def plot_three_subplots(costs, losses, accuracies, title, show=False):
	fig, (ax_costs, ax_losses, ax_accuracies) = plt.subplots(1, 3, figsize=(16, 6))
	fig.suptitle(title)

	xlabel = 'epoch'
	label_A = 'training'
	label_B = 'validation'

	# ax_costs.plot(costs[0], costs[1])
	ax_costs.plot(range(len(costs[0])), costs[0], label=label_A + ' cost')
	ax_costs.plot(range(len(costs[1])), costs[1], label=label_B + ' cost')
	ax_costs.legend()
	ax_costs.set(xlabel=xlabel, ylabel='cost')
	ax_costs.grid()

	# ax_losses.plot(losses[0], losses[1])
	ax_losses.plot(range(len(losses[0])), losses[0], label=label_A + ' loss')
	ax_losses.plot(range(len(losses[1])), losses[1], label=label_B + ' loss')
	ax_losses.legend()
	ax_losses.set(xlabel=xlabel, ylabel='loss')
	ax_losses.grid()

	# ax_accuracies.plot(accuracies[0], accuracies[1])
	ax_accuracies.plot(range(len(accuracies[0])), accuracies[0], label=label_A + ' accuracy')
	ax_accuracies.plot(range(len(accuracies[1])), accuracies[1], label=label_B + ' accuracy')
	ax_accuracies.legend()
	ax_accuracies.set(xlabel=xlabel, ylabel='accuracy')
	ax_accuracies.grid()

	plt.savefig(f'plots/{title}.png', bbox_inches="tight")

	if show:
		plt.show()

	return


class KLayerNetwork():
	""" K-layer network classifier based on mini-batch gradient descent """

	def __init__(self, labels, data, layers, alpha=0.9, batch_norm=False, verbose=0):
		""" W: weight matrix of size K x d
			b: bias matrix of size K x 1 """
		self.activation_functions = {'softmax': self.__softmax, 'relu': self.__relu}
		self.labels = labels

		self.data = data
		self.d = self.data['train_set']['X'].shape[0]

		self.alpha = alpha

		self.batch_norm = batch_norm
		if self.batch_norm:
			self.params = ['W', 'b', 'gamma', 'beta']
		else:
			self.params = ['W', 'b']

		self.verbose = verbose

		self.layers = self.__create_layers(layers)

		self.__he_initialization()

	@staticmethod
	def __shuffle_in_unison(a, b):
		assert a.shape[1] == b.shape[1]
		p = np.random.permutation(a.shape[1])
		return a[:, p], b[:, p]

	def __create_layers(self, input_layers):
		output_layers = list()

		first_layer = {'shape': (input_layers[0][0], self.d), 'activation': input_layers[0][1]}
		output_layers.append(first_layer)

		for i, layer in enumerate(input_layers[1:]):
			shape = (layer[0], output_layers[i]['shape'][0])
			activation = layer[1]
			next_layer = {'shape': shape, 'activation': activation}
			output_layers.append(next_layer)

		if self.verbose:
			print()
			print(f'Layers and activation functions of our {len(input_layers)}-Layer Network:')
			for i, layer in enumerate(output_layers):
				print(f'- layer{i+1} \t\t shape: {layer["shape"]} \t activation: {layer["activation"]}')

		return output_layers

	def __he_initialization(self):
		""" Adds weight matrix, bias matrix and other parameters to each layer"""
		for layer in self.layers:
			shape = layer['shape']

			# Initialize as Gaussian random values with 0 mean and 1/sqrt(d) stdev.
			layer['W'] = np.random.normal(0, 1 / np.sqrt(shape[1]), size=shape)
			# layer['W'] = np.random.normal(0, 2 / np.sqrt(shape[1]), size=shape)
			# layer['W'] = np.random.normal(0, 1e-4, size=shape)

			# "Set biases equal to zero"
			layer['b'] = np.zeros((shape[0], 1)) # ?

			layer['gamma'] = np.ones((shape[0], 1))

			layer['beta'] = np.zeros((shape[0], 1))

			layer['mu_av'] = np.zeros((shape[0], 1))

			layer['var_av'] = np.zeros((shape[0], 1))

			activation = layer['activation']
			activation_function = self.activation_functions[activation]
			layer['activation_function'] = activation_function

		return

	def __softmax(self, s):
		""" Standard definition of the softmax function """
		# return np.exp(s) / np.sum(np.exp(s), axis=0)
		return np.exp(s - np.max(s, axis=0)) / np.exp(s - np.max(s, axis=0)).sum(axis=0)

	def __relu(self, s):
		""" Standard definition of the softmax function """
		return np.maximum(s, 0)

	def __evaluate_classifier(self, X, is_testing=False, is_training=False):
		s = np.copy(X)
		N = X.shape[1]

		# Default values
		s_list, mu_list, var_list, s_hat_list = None, None, None, None

		if self.batch_norm:
			# Use np.finfo(input_float_type).eps to get the machine epsilon of
			# the input float type.
			eps = np.finfo(np.float64).eps
			# Implement equations 12 - 19 and store intermediary vectors.
			H_list, s_list, mu_list, var_list, s_hat_list = list(), list(), list(), list(), list()
			for i, layer in enumerate(self.layers):
				W, b, gamma = layer['W'], layer['b'], layer['gamma']
				beta, mu_av, var_av = layer['beta'], layer['mu_av'], layer['var_av']
				activation_function = layer['activation_function']
				H_list.append(s)
				s = np.dot(W, s) + b
				if i < len(self.layers) - 1:
					s_list.append(s)
					if is_testing:
						s = (s - mu_av) / np.sqrt(var_av + eps)
					else:
						mu = np.mean(s, axis=1, keepdims=True)
						# Page 7 in Assignment3.pdf. Compensate with (N - 1) / N
						var = np.var(s, axis=1, keepdims=True) * np.float64((N - 1) / N)

						if is_training:
							layer['mu_av'] = self.alpha * mu_av + (1 - self.alpha) * mu
							layer['var_av'] = self.alpha * var_av + (1 - self.alpha) * var

						s = (s - mu) / np.sqrt(var + eps)

						var_list.append(var)
						mu_list.append(mu)

					s_hat_list.append(s)
					s = activation_function(np.multiply(gamma, s) + beta)
				else:
					P = activation_function(s)

		else:
			H_list = list()
			for layer in self.layers:
				W, b = layer['W'], layer['b']
				activation = layer['activation']
				activation_function  = layer['activation_function']
				if activation == 'relu':
					s = activation_function(np.dot(W, s) + b)
					H_list.append(s)
				else:
					P = activation_function(np.dot(W, s) + b)

		return H_list, P, s_list, mu_list, var_list, s_hat_list

	def __compute_loss_and_cost(self, X, Y, our_lambda, is_testing=False):
		""" Compute cost using the cross-entropy loss.
			- each column of X corresponds to an image and X has size d x N.
			- Y corresponds to the one-hot ground truth label matrix.
			- our_lambda is the regularization term ("lambda" is reserved).
			Returns the cost, which is a scalar. """
		N = X.shape[1]

		_, p, _, _, _, _ = self.__evaluate_classifier(X, is_testing)

		# If label is encoded as one-hot repr., then cross entropy is -log(yTp).
		loss = np.float64(1 / N) * (-np.sum(Y * np.log(p)))

		weights_squared = np.float64(0.0)
		for layer in self.layers:
			weights_squared += np.sum(np.square(layer['W']))

		cost = loss + np.float64(our_lambda) * weights_squared

		return loss, cost

	def __compute_accuracy(self, X, y, is_testing=False):
		""" Compute classification accuracy
			- each column of X corresponds to an image and X has size d x N.
			- y is a vector pf ground truth labels of length N
			Returns the accuracy. which is a scalar. """
		N = X.shape[1]
		highest_P = np.argmax(self.__evaluate_classifier(X, is_testing)[1], axis=0)
		count = highest_P.T[highest_P == np.asarray(y)].shape[0]

		return count / N

	def __update_params(self, gradients, eta):
		for i, layer in enumerate(self.layers):
			for param in self.params:
				layer[param] -= eta * gradients[param][i]
		return

	def __batch_norm_back_pass(self, G_batch, S_batch, mu_batch, var_batch):
		# Equations 31 to 37 in Assignment3.pdf.
		eps = np.finfo(np.float64).eps
		N = G_batch.shape[1]

		sigma1 = np.power(var_batch + eps, -0.5)
		sigma2 = np.power(var_batch + eps, -1.5)

		G1 = np.multiply(G_batch, sigma1)
		G2 = np.multiply(G_batch, sigma2)

		D = S_batch - mu_batch
		c = np.sum(np.multiply(G2, D), axis=1, keepdims=True)
		G_batch = G1 - np.float64(1 / N) * np.sum(G1, axis=1, keepdims=True) - \
		np.float64(1 / N) * np.multiply(D, c)

		return G_batch

	def compute_gradients(self, X_batch, Y_batch, our_lambda):
		N = X_batch.shape[1]
		gradients = dict()
		for param in self.params:
			gradients[param] = [np.zeros(layer[param].shape) for layer in self.layers]

		if self.batch_norm:
			# 1) evalutate the network (the forward pass)
			H_batch, P_batch, S_batch, mu_batch, var_batch, S_hat_batch = \
			self.__evaluate_classifier(X_batch, is_training=True)

			# 2) compute the gradients (the backward pass). Page 4 in Assignment4.pdf
			G_batch = -(Y_batch - P_batch)

			gradients['W'][-1] = np.float64(1 / N) * np.dot(G_batch, H_batch[-1].T) \
			+ 2 * our_lambda * self.layers[-1]['W']

			gradients['b'][-1] = np.reshape(np.float64(1 / N) * \
			np.dot(G_batch, np.ones(N)), gradients['b'][-1].shape)

			G_batch = np.dot(self.layers[-1]['W'].T, G_batch)
			H_batch[-1] = np.maximum(H_batch[-1], 0)
			G_batch = np.multiply(G_batch, H_batch[-1] > 0)

			# Backwards as per page 4 in Assignment3.pdf ("for l=k-1, k-2, ..., 1").
			for l in range(len(self.layers) - 2, -1, -1):
				gradients['gamma'][l] = np.reshape(np.float64(1 / N) * \
				np.dot(np.multiply(G_batch, S_hat_batch[l]), np.ones(N)), gradients['gamma'][l].shape)

				gradients['beta'][l] = np.reshape(np.float64(1 / N) * \
				np.dot(G_batch, np.ones(N)), gradients['beta'][l].shape)

				G_batch = np.multiply(G_batch, self.layers[l]['gamma'])
				G_batch = self.__batch_norm_back_pass(G_batch, S_batch[l],
													  mu_batch[l], var_batch[l])

				gradients['W'][l] = np.float64(1 / N) * np.dot(G_batch, H_batch[l].T) \
				+ 2 * our_lambda * self.layers[l]['W']

				gradients['b'][l] = np.reshape(np.float64(1 / N) * \
				np.dot(G_batch, np.ones(N)), gradients['b'][l].shape)

				# If l > 0, propagate G_batch to the next layer.
				if l > 0:
					G_batch = np.dot(self.layers[l]['W'].T, G_batch)
					H_batch[l] = np.maximum(H_batch[l], 0)
					G_batch = np.multiply(G_batch, H_batch[l] > 0)
		else:
			# 1) evalutate the network (the forward pass)
			# H_batch, P_batch = self.__evaluate_classifier(X_batch)
			H_batch, P_batch, _, _, _, _ = \
			self.__evaluate_classifier(X_batch, is_training=True)

			# 2) compute the gradients (the backward pass). Page 49 in Lecture4.pdf
			G_batch = -(Y_batch - P_batch)

			# Backwards as per page 36 in Lecture4.pdf ("for l=k, k-1, ..., 2").
			for l in range(len(self.layers) - 1, 0, -1):
				gradients['W'][l] = (1 / N) * np.dot(G_batch, H_batch[l-1].T) + \
				(2 * our_lambda * self.layers[l]['W'])

				gradients['b'][l] = np.reshape((1 / N) * \
				np.dot(G_batch, np.ones(N)), (self.layers[l]['b'].shape[0], 1))

				G_batch = np.dot(self.layers[l]['W'].T, G_batch)
				H_batch[l-1] = np.maximum(H_batch[l-1], 0)

				# Indicator function on H_batch to yield only values larger than 0.
				# COMMENT OUT IF TESTING GRADIENTS
				G_batch = np.multiply(G_batch, H_batch[l-1] > 0)

			# And now for the first layer, which was left out of the loop.
			gradients['W'][0] = (1 / N) * np.dot(G_batch, X_batch.T) + \
			(our_lambda * self.layers[0]['W'])
			gradients['b'][0] = np.reshape((1 / N) * \
			np.dot(G_batch, np.ones(N)), self.layers[0]['b'].shape)

		return gradients

	def compute_gradients_num(self, X_batch, Y_batch, our_lambda=np.float64(0), h=1e-7):
		""" Compute gradients of the weight and bias numerically.
			- X_batch is a d x N matrix.
			- Y_batch is a K x N one-hot-encoding vector.
			- our_lambda is the regularization term ("lambda" is reserved).
			- h is the marginal offset.
			Returns the gradients of the weight and bias. """

		gradients = dict()
		for param in self.params:
			gradients[param] = list()

		for i, layer in enumerate(self.layers):
			for param in self.params:
				gradients[param].append(np.zeros(layer[param].shape))
				for j in np.ndindex(layer[param].shape):
					old_values = np.copy(layer[param][j])

					layer[param][j] = old_values + h
					_, cost1 = self.__compute_loss_and_cost(X_batch, Y_batch, our_lambda)

					layer[param][j] = old_values - h
					_, cost2 = self.__compute_loss_and_cost(X_batch, Y_batch, our_lambda)

					layer[param][j] = old_values
					gradients[param][i][j] = (cost1 - cost2) / (2 * h)

		# for i, layer in enumerate(self.layers):
		# 	for param in self.params:
		# 		gradients[param].append(np.zeros(layer[param].shape))
		# 		param_try = np.copy(layer[param])
		# 		for j in np.ndindex(layer[param].shape):
		# 			layer[param] = param_try[:]
		# 			layer[param][j] -= h
		# 			_, cost1 = self.__compute_loss_and_cost(X_batch, Y_batch, our_lambda)
		# 			layer[param][j] += (2 * h)
		# 			_, cost2 = self.__compute_loss_and_cost(X_batch, Y_batch, our_lambda)
		# 			gradients[param][i][j] = (cost2 - cost1) / (2 * h)

		return gradients

	def check_gradient_similarity(self, grads_ana, grads_num):
		# np.allclose(a, b, rtol=1e-05, atol=1e-08, equal_nan=False)[source]
		atols = [1e-08, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]
		# rtols = [1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1]

		for atol in atols:
			results = list()
			print()
			print(f'--------------------------- Atol {atol} --------------------------')
			for i in range(len(self.layers)):
				print()
				# print(f'\nLayer {i}')
				for param in self.params:
					if self.verbose:
						print(f'grads_ana[{param}][{i}]')
						print(grads_ana[param][i][:10, :10])
						print(f'Actual shape is: {grads_ana[param][i].shape}')
						print()
						print(f'grads_num[{param}][{i}]')
						print(grads_num[param][i][:10, :10])
						print(f'Actual shape is: {grads_num[param][i].shape}')
					all_close = np.allclose(grads_ana[param][i], grads_num[param][i], atol=atol)
					results.append(all_close)

					numerator = abs(grads_ana[param][i].flat[:] - grads_num[param][i].flat[:])
					denominator = np.asarray([max(abs(a), abs(b)) + 1e-10 for a, b in zip(grads_ana[param][i].flat[:], grads_num[param][i].flat[:])])
					max_relative_error = max(numerator / denominator)

					print(f'{param}[{i}]    \tAll close: {all_close} \tRelative error: {max_relative_error}')

			# Break prematurely if all are close.
			if all(result for result in results):
				break

		return

	def mini_batch_gradient_descent(self, X, Y, our_lambda=0, batch_size=100, eta_min=1e-5, eta_max=1e-1, n_s=500, n_epochs=20, shuffle=True):
		""" Learn the model by performing mini-batch gradient descent
			our_lambda 	- regularization term
			batch_size 	- number of examples per mini-batch
			eta_min		- minimum learning rate
			eta_max		- maximum learning rate
			n_s			- step size
			n_epochs 	- number of runs through the whole training set """

		accuracies = dict()
		accuracies['train'] = np.zeros(n_epochs)
		accuracies['val'] = np.zeros(n_epochs)
		accuracies['test'] = np.zeros(n_epochs)

		list_settings = list()

		losses, costs = dict(), dict()
		losses['train'], costs['train'] = np.zeros(n_epochs), np.zeros(n_epochs)
		losses['val'], costs['val'] = np.zeros(n_epochs), np.zeros(n_epochs)

		# Get the number of batches needed given the input batch size.
		n_batch = int(np.floor(X.shape[1] / batch_size))
		eta = eta_min
		t = 0
		for n in range(n_epochs):
			if shuffle:
				# Randomly shuffle our samples before each epoch.
				X, Y = self.__shuffle_in_unison(X, Y)
			for i in range(n_batch):
				i_start = (i) * batch_size
				i_end = (i + 1) * batch_size

				X_batch = X[:, i_start:i_end]
				Y_batch = Y[:, i_start:i_end]

				gradients = self.compute_gradients(X_batch, Y_batch, our_lambda)

				self.__update_params(gradients, eta)

				# Equations (14) and (15).
				if t <= n_s:
					eta = eta_min + ((t / n_s) * (eta_max - eta_min))
				elif t <= (2 * n_s):
					eta = eta_max - (((t - n_s) / n_s) * (eta_max - eta_min))
				t = (t + 1) % (2 * n_s)

				# if t == (n_s + 1) or t == (2 * n_s - 1):
				# if t == (2 * n_s - 1):
					# tr_acc = self.__compute_accuracy(self.data['train_set']['X'],
					# 								 self.data['train_set']['y'])
					# v_acc = self.__compute_accuracy(self.data['val_set']['X'],
					# 								self.data['val_set']['y'])
					# te_acc = self.__compute_accuracy(self.data['test_set']['X'],
					# 								 self.data['test_set']['y'])
					#
					# settings = {'t': t, 'our_lambda': our_lambda, 'eta': eta,
					# 			'eta_min': eta_min, 'eta_max': eta_max,
					# 			'n_batch': n_batch, 'n_s': n_s, 'n_epochs': n_epochs,
					# 			'tr-acc': tr_acc, 'v-acc': v_acc, 'te-acc': te_acc}
					#
					# list_settings.append(settings)

			losses['train'][n], costs['train'][n] = \
			self.__compute_loss_and_cost(X, Y, our_lambda)

			losses['val'][n], costs['val'][n] = \
			self.__compute_loss_and_cost(self.data['val_set']['X'],
										 self.data['val_set']['Y'],
										 our_lambda)

			accuracies['train'][n] = self.__compute_accuracy(self.data['train_set']['X'],
															 self.data['train_set']['y'])
			accuracies['val'][n] = self.__compute_accuracy(self.data['val_set']['X'],
														   self.data['val_set']['y'])
			accuracies['test'][n] = self.__compute_accuracy(self.data['test_set']['X'],
															self.data['test_set']['y'],
															is_testing=True)

			if self.verbose:
				print()
				print(f'Loss training:\t\t{round(losses["train"][n], 4)}\t| Loss validation:\t{round(losses["val"][n], 4)}')
				print(f'Cost training:\t\t{round(costs["train"][n], 4)}\t| Cost validation:\t{round(costs["val"][n], 4)}')
				print(f'Accuracy training:\t{round(accuracies["train"][n], 4)}\t| Accuracy validation:\t{round(accuracies["val"][n], 4)}\t| Accuracy testing:\t{round(accuracies["test"][n], 4)}')
				# print(f'Accuracy testing:\t{accuracies["test"][n]}')

			# print(f'Current learning rate: {eta}')

		settings = {'t': t, 'our_lambda': our_lambda, 'eta': eta,
					'eta_min': eta_min, 'eta_max': eta_max, 'n_batch': n_batch,
					'n_s': n_s, 'n_epochs': n_epochs,
					'tr-acc': accuracies["train"][-1],
					'v-acc': accuracies["val"][-1],
					'te-acc': accuracies["test"][-1]}
		list_settings.append(settings)


		return accuracies, costs, losses, list_settings


def main():
	seed = 12345
	np.random.seed(seed)

	# Specifies whether to use "all" available data for training (5000 for val).
	all = True

	sanity_check = False

	# Exercise 1: Implement Gradient Computations for K-Layer Network
	# Checking gradients
	exercise_1_2_layer = False
	exercise_1_3_layer = False
	exercise_1_4_layer = False

	# Exercise 2: Train using K-Layer Network
	# Training
	exercise_2_2_layer = False
	exercise_2_3_layer = False
	exercise_2_9_layer = False

	# Exercise 3: Implement Batch Normalization
	# Checking gradients
	exercise_3_check_2_layer = False
	exercise_3_check_3_layer = False

	# Training
	exercise_3_train_3_layer = False
	exercise_3_train_3_layer_best_lambda = False
	exercise_3_train_9_layer_best_lambda = False
	exercise_3_train_3_layer_sensitivity = True

	# Lambda search
	exercise_3_search_3_layer = False

	if exercise_2_3_layer or exercise_2_9_layer or exercise_3_train_3_layer:
		all = True

	print()
	print("------------------------ Loading dataset ------------------------")
	datasets_folder = "Datasets/cifar-10-batches-py/"
	labels = unpickle(datasets_folder + "batches.meta")[b'label_names']

	if all:
		num_val = 5000

		# Use all available data for training. Reduce validation to num_val.
		train_set_1 = load_dataset(datasets_folder, "data_batch_1", num_of_labels=len(labels))
		train_set_2 = load_dataset(datasets_folder, "data_batch_2", num_of_labels=len(labels))
		train_set_3 = load_dataset(datasets_folder, "data_batch_3", num_of_labels=len(labels))
		train_set_4 = load_dataset(datasets_folder, "data_batch_4", num_of_labels=len(labels))
		train_set_5 = load_dataset(datasets_folder, "data_batch_5", num_of_labels=len(labels))

		train_set = dict()
		train_set['X'] = np.concatenate((train_set_1['X'], train_set_2['X'], train_set_3['X'], train_set_4['X'], train_set_5['X']), axis=1)
		train_set['Y'] = np.concatenate((train_set_1['Y'], train_set_2['Y'], train_set_3['Y'], train_set_4['Y'], train_set_5['Y']), axis=1)
		train_set['y'] = np.concatenate((train_set_1['y'], train_set_2['y'], train_set_3['y'], train_set_4['y'], train_set_5['y']))

		# Use last num_val for validation ...
		val_set = dict()
		val_set['X'] = train_set['X'][:, -num_val:]
		val_set['Y'] = train_set['Y'][:, -num_val:]
		val_set['y'] = train_set['y'][-num_val:]

		# ... and subsequently remove them from the training data.
		train_set['X'] = train_set['X'][:, :-num_val]
		train_set['Y'] = train_set['Y'][:, :-num_val]
		train_set['y'] = train_set['y'][:-num_val]

		test_set = load_dataset(datasets_folder, "test_batch", num_of_labels=len(labels))

		datasets = {'train_set': train_set, 'val_set': val_set, 'test_set': test_set}
	else:
		train_set = load_dataset(datasets_folder, "data_batch_1", num_of_labels=len(labels))
		val_set = load_dataset(datasets_folder, "data_batch_2", num_of_labels=len(labels))
		test_set = load_dataset(datasets_folder, "test_batch", num_of_labels=len(labels))

		datasets = {'train_set': train_set, 'val_set': val_set, 'test_set': test_set}

	print()
	print("---------------------- Normalizing dataset ----------------------")
	for dataset in datasets.values():
		dataset['X'] = normalize_dataset(dataset['X'], verbose=1)

	print()
	print("-------------------- Instantiating classifier -------------------")

	print()
	print("---------------------- Learning classifier ----------------------")
	# Has been deprecated. Was used to check if model could overfit. It could.
	if sanity_check:
		print()
		print("------------------------ Sanity check ------------------------")
		# See if we can overfit, i.e. achieve a very small loss on the training
		# data by training on the following 100 examples.
		num_pixels = 3072
		num_images = 100
		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		# our_lambda = 0.01
		our_lambda = 0.005
		n_epochs = 60
		batch_size = 10
		eta_min = 1e-5
		eta_max = 1e-1
		n_s = 800

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		title = f'lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='sanity_' + title, show=True)

	if exercise_1_2_layer:
		print()
		print("---------------- Running gradient tests: 2-layer ----------------")
		num_pixels = 10
		num_images = 2

		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		X_batch = train_set['X']
		Y_batch = train_set['Y']

		layers = [(50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

		our_lambda = 0.0
		h = 1e-7

		analytical_gradients = clf.compute_gradients(X_batch, Y_batch, our_lambda)
		numerical_gradients = clf.compute_gradients_num(X_batch, Y_batch, our_lambda, h)

		clf.check_gradient_similarity(analytical_gradients, numerical_gradients)

	if exercise_1_3_layer:
		print()
		print("---------------- Running gradient tests: 3-layer ----------------")
		num_pixels = 10
		num_images = 2

		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		X_batch = train_set['X']
		Y_batch = train_set['Y']

		layers = [(50, 'relu'), (40, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

		our_lambda = 0.0
		h = 1e-7

		analytical_gradients = clf.compute_gradients(X_batch, Y_batch, our_lambda)
		numerical_gradients = clf.compute_gradients_num(X_batch, Y_batch, our_lambda, h)

		clf.check_gradient_similarity(analytical_gradients, numerical_gradients)

	if exercise_1_4_layer:
		print()
		print("---------------- Running gradient tests: 4-layer ----------------")
		num_pixels = 10
		num_images = 2

		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		X_batch = train_set['X']
		Y_batch = train_set['Y']

		layers = [(50, 'relu'), (40, 'relu'), (20, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

		our_lambda = 0.0
		h = 1e-7

		analytical_gradients = clf.compute_gradients(X_batch, Y_batch, our_lambda)
		numerical_gradients = clf.compute_gradients_num(X_batch, Y_batch, our_lambda, h)

		clf.check_gradient_similarity(analytical_gradients, numerical_gradients)

	if exercise_2_2_layer:
		print()
		print("---------------------- Exercise 2: 2-layer ----------------------")
		layers = [(50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.01
		n_epochs = 48
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		n_s = 800

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		title = f'lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex2l2_' + title, show=True)

	if exercise_2_3_layer:
		print()
		print("---------------------- Exercise 2: 3-layer ----------------------")
		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.005
		n_epochs = 20
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		title = f'lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex2l3_' + title, show=True)

	if exercise_2_9_layer:
		print()
		print("---------------------- Exercise 2: 9-layer ----------------------")
		layers = [(50, 'relu'), (30, 'relu'), (20, 'relu'), (20, 'relu'),
				  (10, 'relu'), (10, 'relu'), (10, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.005
		n_epochs = 20
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		title = f'lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex2l9_' + title, show=True)

	if exercise_3_check_2_layer:
		print()
		print("------------------- Exercise 3: 2-layer test --------------------")
		num_pixels = 10
		num_images = 2

		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		X_batch = train_set['X']
		Y_batch = train_set['Y']

		layers = [(50, 'relu'), (10, 'softmax')]

		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

		our_lambda = 0.0
		h = 1e-7

		analytical_gradients = clf.compute_gradients(X_batch, Y_batch, our_lambda)
		numerical_gradients = clf.compute_gradients_num(X_batch, Y_batch, our_lambda, h)

		clf.check_gradient_similarity(analytical_gradients, numerical_gradients)

	if exercise_3_check_3_layer:
		print()
		print("------------------- Exercise 3: 3-layer test --------------------")
		num_pixels = 10
		num_images = 2

		train_set['X'] = train_set['X'][:num_pixels, :num_images]
		train_set['Y'] = train_set['Y'][:num_pixels, :num_images]

		X_batch = train_set['X']
		Y_batch = train_set['Y']

		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]

		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

		our_lambda = 0.0
		h = 1e-7

		analytical_gradients = clf.compute_gradients(X_batch, Y_batch, our_lambda)
		numerical_gradients = clf.compute_gradients_num(X_batch, Y_batch, our_lambda, h)

		clf.check_gradient_similarity(analytical_gradients, numerical_gradients)

	if exercise_3_train_3_layer:
		print()
		print("---------------------- Exercise 3: 3-layer ----------------------")
		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.005
		n_epochs = 20
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		if batch_norm:
			bn = 'T'
		else:
			bn = 'F'

		title = f'bn{bn}_lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_alpha{alpha}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex3l3_' + title, show=True)

	if exercise_3_search_3_layer:
		print()
		print("------------------- Exercise 3: Lambda Search -------------------")
		coarse = False
		results_file = 'results/results_best.csv'
		# If file not exists, create it with its headers.
		if not os.path.exists(results_file):
			headers = ['top_5_vacc', 'tracc', 'vacc', 'teacc', 'lambda', 'alpha',
					   'eta_min', 'eta_max', 'n_epochs', 'batch_size', 'n_s',
					   'N', 'layers', 'seed']
			with open(results_file, 'w+') as f:
				writer = csv.writer(f, dialect='excel', delimiter=';')
				writer.writerow(headers)

		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = True

		our_lambda = 0.005
		n_epochs = 20
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		if coarse:
			# Coarse lambda search.
			lambda_min = 1e-5
			lambda_max = 1e-1
			lambdas = np.linspace(lambda_min, lambda_max, 8)
		else:
			# Fine lambda search.
			lambda_min = 1e-5
			lambda_max = 0.0285785714285714 # Pasted in from coarse results.
			lambdas = np.linspace(lambda_min, lambda_max, 8)

		for our_lambda in lambdas:
			our_lambda = round(our_lambda, 4)

			clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=0)

			accuracies, costs, losses, _ = \
			clf.mini_batch_gradient_descent(datasets['train_set']['X'],
											datasets['train_set']['Y'],
											our_lambda=our_lambda,
											batch_size=batch_size,
											eta_min=eta_min,
											eta_max=eta_max,
											n_s=n_s,
											n_epochs=n_epochs)

			tracc = round(accuracies["train"][-1], 4)
			vacc = round(accuracies["val"][-1], 4)
			teacc = round(accuracies["test"][-1], 4)

			top_5_mean = np.sum(sorted(accuracies['val'][:], reverse=True)[:5]) / 5
			top_5_mean = round(top_5_mean, 4)

			print()
			print(f'Lambda {our_lambda}')
			print(f'Final training data accuracy:\t\t{tracc}')
			print(f'Final validation data accuracy:\t\t{vacc}')
			print(f'Final test data accuracy:\t\t{teacc}')
			print(f'Final top 5 mean:\t\t\t{top_5_mean}')

			if batch_norm:
				bn = 'T'
			else:
				bn = 'F'

			N = datasets['train_set']['X'].shape[1]
			title = f'bn{bn}_layers{len(layers)}_N{N}_lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_alpha{alpha}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

			plot_three_subplots(costs=(costs['train'], costs['val']),
								losses=(losses['train'], losses['val']),
								accuracies=(accuracies['train'], accuracies['val']),
								title='ex3search_' + title, show=False)

			headers = ['top_5_vacc', 'tracc', 'vacc', 'teacc', 'lambda', 'alpha',
					   'eta_min', 'eta_max', 'n_epochs', 'batch_size', 'n_s',
					   'N', 'layers', 'seed']

			results = [top_5_mean, tracc, vacc, teacc, our_lambda, alpha,
					   eta_min, eta_max, n_epochs, batch_size, n_s,
					   N, len(layers), seed]
			with open(results_file, 'a') as f:
				writer = csv.writer(f, dialect='excel', delimiter=';')
				writer.writerow(results)

	if exercise_3_train_3_layer_best_lambda:
		print()
		print("--------------- Exercise 3: 3-layer best lambda ---------------")
		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.0041
		n_epochs = 30 # Three cycles
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		if batch_norm:
			bn = 'T'
		else:
			bn = 'F'

		title = f'bn{bn}_lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_alpha{alpha}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex3l3_' + title, show=True)

	if exercise_3_train_9_layer_best_lambda:
		print()
		print("--------------- Exercise 3: 3-layer best lambda ---------------")
		layers = [(50, 'relu'), (30, 'relu'), (20, 'relu'), (20, 'relu'),
				  (10, 'relu'), (10, 'relu'), (10, 'relu'), (10, 'relu'),
				  (10, 'softmax')]
		alpha = 0.9
		batch_norm = True

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.0041
		n_epochs = 30 # Three cycles
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		if batch_norm:
			bn = 'T'
		else:
			bn = 'F'

		title = f'bn{bn}_lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_alpha{alpha}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='ex3l9_' + title, show=True)

	if exercise_3_train_3_layer_sensitivity:
		print()
		print("--------------- Exercise 3: 3-layer best lambda ---------------")
		layers = [(50, 'relu'), (50, 'relu'), (10, 'softmax')]
		alpha = 0.9
		batch_norm = False

		clf = KLayerNetwork(labels, datasets, layers, alpha, batch_norm, verbose=1)

		our_lambda = 0.005
		n_epochs = 20 # Two cycles of training.
		batch_size = 100
		eta_min = 1e-5
		eta_max = 1e-1
		# n_s = 800
		n_s = 5 * datasets['train_set']['X'].shape[1] / 100

		accuracies, costs, losses, _ = \
		clf.mini_batch_gradient_descent(datasets['train_set']['X'],
										datasets['train_set']['Y'],
										our_lambda=our_lambda,
										batch_size=batch_size,
										eta_min=eta_min,
										eta_max=eta_max,
										n_s=n_s,
										n_epochs=n_epochs)

		tracc = round(accuracies["train"][-1], 4)
		vacc = round(accuracies["val"][-1], 4)
		teacc = round(accuracies["test"][-1], 4)

		print()
		print(f'Final training data accuracy:\t\t{tracc}')
		print(f'Final validation data accuracy:\t\t{vacc}')
		print(f'Final test data accuracy:\t\t{teacc}')

		if batch_norm:
			bn = 'T'
		else:
			bn = 'F'

		title = f'bn{bn}_lambda{our_lambda}_batch_size{batch_size}_n-epochs{n_epochs}_n-s{n_s}_alpha{alpha}_eta-min{eta_min}_eta-max{eta_max}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'

		plot_three_subplots(costs=(costs['train'], costs['val']),
							losses=(losses['train'], losses['val']),
							accuracies=(accuracies['train'], accuracies['val']),
							title='sigma1e-4_' + title, show=True)

	print()

	return


if __name__ == '__main__':
	main()
