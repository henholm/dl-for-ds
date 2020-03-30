"""In this assignment you will train and test a one layer network with multiple
outputs to classify images from the CIFAR-10 dataset. You will train the network
using mini-batch gradient descent applied to a cost function that computes the
cross-entropy loss of the classifier applied to the labelled training data and
an L2 regularization term on the weight matrix."""


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


def preprocess_dataset(training_data):
	""" Pre-process data by normalizing """
	# "Both mean_X and std_X have size d x 1".
	mean_X = np.mean(training_data, axis=1)
	std_X = np.std(training_data, axis=1)

	training_data = training_data - np.array([mean_X]).T
	training_data = training_data / np.array([std_X]).T

	return training_data


def unpickle(filename):
	""" Unpickle a file """
	with open(filename, 'rb') as f:
		file_dict = pickle.load(f, encoding='bytes')

	return file_dict


def montage(W, title, labels):
	""" Display the image for each label in W """
	fig, ax = plt.subplots(2, 5)
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


def plot_lines(line_A, line_B, label_A, label_B, xlabel, ylabel, title):
   """ Plots performance curves """
   assert(line_A.shape == line_B.shape)

   N = len(line_A)

   fig, ax = plt.subplots(figsize=(10, 8))
   ax.plot(range(N), line_A, label=label_A)
   ax.plot(range(N), line_B, label=label_B)
   ax.legend()

   plt.xticks(range(N))

   ax.set(xlabel=xlabel, ylabel=ylabel)
   ax.grid()

   plt.savefig(f'plots/{title}.png', bbox_inches="tight")
   plt.show()

   return


class SingleLayerNetwork():
	""" Single-layer network classifier based on mini-batch gradient descent """

	def __init__(self, labels, data, decay_factor=1, xavier=False, SVM_loss=False):
		""" W: weight matrix of size K x d
			b: bias matrix of size K x 1 """
		self.labels = labels
		K = len(self.labels)

		self.decay_factor = decay_factor

		self.data = data
		d = self.data['train_set']['X'].shape[0]

		self.SVM_loss = SVM_loss

		# Bonus E) implement xavier initialization for weights.
		if xavier:
			# https://towardsdatascience.com/weight-initialization-in-neural-networks-a-journey-from-the-basics-to-kaiming-954fb9b47c79
			# self.W = np.random.normal(0, np.sqrt(2 / (d + K)), (K, d))
			# As per lecture 4.
			self.W = np.random.normal(0, 1 / np.sqrt(d), (K, d))
		else:
			# Initialize as Gaussian random values with 0 mean and 0.01 stdev.
			self.W = np.random.normal(0, 0.01, (K, d))

		self.b = np.random.normal(0, 0.01, (K, 1))

	def evaluate_classifier(self, X):
		""" Implement SoftMax using equations 1 and 2.
			Each column of X corresponds to an image and it has size d x n. """
		s = np.dot(self.W, X) + self.b
		# p has size K x n, where n is n of the input X.
		p = self.soft_max(s)
		return p

	def soft_max(self, s):
		""" Standard definition of the softmax function """
		return np.exp(s) / np.sum(np.exp(s), axis=0)

	def compute_cost(self, X, Y, our_lambda):
		""" Compute cost using the cross-entropy loss.
			- each column of X corresponds to an image and X has size d x N.
			- Y corresponds to the one-hot ground truth label matrix.
			- our_lambda is the regularization term ("lambda" is reserved).
			Returns the cost, which is a scalar. """
		N = X.shape[1]
		p = self.evaluate_classifier(X)
		# If label is encoded as one-hot repr., then cross entropy is -log(yTp).
		cost = ((1 / N) * -np.sum(Y * np.log(p))) + (our_lambda * np.sum(self.W**2))
		return cost

	def compute_accuracy(self, X, y):
		""" Compute classification accuracy
			- each column of X corresponds to an image and X has size d x N.
			- y is a vector pf ground truth labels of length N
			Returns the accuracy. which is a scalar. """
		N = X.shape[1]
		highest_P = np.argmax(self.evaluate_classifier(X), axis=0)
		count = highest_P.T[highest_P == np.asarray(y)].shape[0]

		return count / N

	def compute_gradients_entropy_loss(self, X_batch, Y_batch, our_lambda):
		N = X_batch.shape[1]
		C = Y_batch.shape[0]
		P_batch = self.evaluate_classifier(X_batch)

		# As per the last slide of lecture 3.
		G_batch = - (Y_batch - P_batch)
		grad_W = (1 / N) * (G_batch @ X_batch.T) + (2 * our_lambda * self.W)

		# No regularization term necessary.
		grad_b = np.reshape((1 / N) * (G_batch @ np.ones(N)), (C, 1))

		return grad_W, grad_b

	def compute_gradients_SVM_loss(self, X_batch, Y_batch, our_lambda):
		"""
		Data of dimension D, C classes, and minibatches of N examples.

		Inputs:
		- W: A numpy array of shape (D, C) containing weights.				(K, d)
		- X: A numpy array of shape (N, D) containing a minibatch of data.	(d, N)
		- y: A numpy array of shape (N,) containing training labels; y[i] = c means
		that X[i] has label c, where 0 <= c < C.
		- our_lambda: (float) regularization strength

		Returns a tuple of:
		- loss as single float
		- gradient with respect to weights W; an array of same shape as W
		"""
		# Inspiration drawn from the following link:
		# https://mlxai.github.io/2017/01/06/vectorized-implementation-of-svm-loss-and-gradient-update.html

		N = X_batch.shape[1]

		# s = self.evaluate_classifier(X_batch)
		# sc = s.T[np.arange(s.shape[1]), np.argmax(Y_batch, axis=0)].T
		# print(s.shape)
		# print(sc.shape)
		#
		# margins = np.maximum(0, s - np.asarray(sc) + 1)
		# print(margins.shape)
		# margins.T[np.arange(N), np.argmax(Y_batch, axis=0)] = 0
		# print(margins.shape)
		#
		# mcsvm_loss = Y_batch.shape[0] * np.mean(np.sum(margins, axis=1))
		#
		# cost = 1/N * mcsvm_loss + 0.5 * our_lambda * np.sum(self.W**2)
		#
		# binaries = margins
		# binaries[margins > 0] = 1
		# binaries_row_sum = np.sum(binaries, axis=0)
		#
		# print()
		# print(np.arange(N).shape)
		# print(binaries.T[np.arange(N), np.argmax(Y_batch, axis=0)].shape)
		# print(binaries_row_sum.T.shape)
		#
		# binaries.T[np.arange(N), np.argmax(Y_batch, axis=0)] = -binaries_row_sum.T
		# print(binaries.shape)
		# print(binaries.T.shape)
		#
		# print(X_batch.T.shape)
		# print(self.W.shape)
		# grad_W = np.dot(binaries, X_batch.T) / N + our_lambda * self.W
		# print(grad_W.shape)
		#
		# grad_b = np.reshape(np.sum(binaries, axis=1) / binaries.shape[1], self.b.shape)


		loss = 0.0
		grad_W = np.zeros(self.W.shape) # initialize the gradient as zero

		# scores = X_batch.dot(self.W)
		# yi_scores = scores[np.arange(scores.shape[0]),y] # http://stackoverflow.com/a/23435843/459241
		scores = self.evaluate_classifier(X_batch)
		print(scores.shape)
		yi_scores = scores.T[np.arange(scores.shape[1]), np.argmax(Y_batch, axis=0)].T
		print(yi_scores.shape)

		# margins = np.maximum(0, scores - np.matrix(yi_scores).T + 1)
		margins = np.maximum(0, scores - np.asarray(yi_scores) + 1)
		print(margins.shape)
		# margins = np.maximum(0, scores - np.matrix(yi_scores) + 1)
		# margins = np.maximum(0, scores - yi_scores + 1)
		# margins[np.arange(N),Y_batch] = 0
		margins.T[np.arange(N), np.argmax(Y_batch, axis=0)] = 0
		print(margins.shape)

		loss = np.mean(np.sum(margins, axis=1))
		loss += 0.5 * our_lambda * np.sum(self.W * self.W)
		cost = (1 / N) * loss

		binary = margins
		binary[margins > 0] = 1
		# row_sum = np.sum(binary, axis=1)
		row_sum = np.sum(binary, axis=0)
		# binary[np.arange(N), Y_batch] = -row_sum.T
		print(np.arange(N).shape)
		print(binary.T[np.arange(N), np.argmax(Y_batch, axis=0)].shape)
		print(row_sum.T.shape)
		binary.T[np.arange(N), np.argmax(Y_batch, axis=0)] = -row_sum.T

		print(binary.shape)
		print(binary.T.shape)

		print(X_batch.T.shape)
		print(self.W.shape)

		grad_W = np.dot(binary, X_batch.T) / N + our_lambda * self.W
		# grad_W = (np.dot(X_batch.T, binary) / N) + (our_lambda * self.W)
		print(grad_W.shape)

		grad_b = np.reshape(np.sum(binary, axis=1) / binary.shape[1], self.b.shape)

		quit()

		return grad_W, grad_b

	def compute_gradients(self, X_batch, Y_batch, our_lambda):
		""" Compute gradients of the weight and bias.
			- X_batch is a D x N matrix
			- Y_batch is a C x N one-hot-encoding vector
			- our_lambda is the regularization term ("lambda" is reserved).
			Returns the gradients of the weight and bias. """
		if self.SVM_loss:
			grad_W, grad_b = self.compute_gradients_SVM_loss(X_batch, Y_batch, our_lambda)
			# grad_W = np.zeros((C, X_batch.shape[0]))
			# grad_b = np.zeros((C, 1))
			# for i in range(N):
			# 	x = X_batch[:, i]
			# 	y_int = np.where(Y_batch[:, [i]].T[0] == 1)[0][0]
			# 	s = np.dot(self.W, X_batch[:, [i]]) + self.b
			# 	for j in range(C):
			# 		if j != y_int:
			# 			if max(0, s[j] - s[y_int] + 1) != 0:
			# 				grad_W[j] += x
			# 				grad_W[y_int] -= x
			# 				grad_b[j, 0] += 1
			# 				grad_b[y_int, 0] -= 1
			# grad_W /= N
			# grad_W += (our_lambda * self.W)
			# grad_b /= N
		else:
			grad_W, grad_b = self.compute_gradients_entropy_loss(X_batch, Y_batch, our_lambda)

		return grad_W, grad_b


	def mini_batch_gradient_descent(self, X, Y, our_lambda=0, n_batch=100,
									eta=0.001, n_epochs=20, save_costs=False):
		""" Learn the model by performing mini-batch gradient descent
			n_batch is the number of batches
			eta is the learning rate
			n_epochs is number of training epochs """

		accuracies = dict()

		if save_costs:
			costs = dict()
			costs['train'] = np.zeros(n_epochs)
			costs['val'] = np.zeros(n_epochs)
		else:
			costs = None

		for n in range(n_epochs):
			for j in range(n_batch):
				N = int(X.shape[1] / n_batch)
				j_start = (j) * N
				j_end = (j+1) * N

				X_batch = X[:, j_start:j_end]
				Y_batch = Y[:, j_start:j_end]

				grad_W, grad_b = self.compute_gradients(X_batch, Y_batch, our_lambda)
				self.W -= eta * grad_W
				self.b -= eta * grad_b

			if save_costs:
				costs['train'][n] = self.compute_cost(X, Y, our_lambda)
				costs['val'][n] = self.compute_cost(self.data['val_set']['X'],
													self.data['val_set']['Y'],
													our_lambda)

			# Bonus B) implement a decay of the learning rate.
			eta *= self.decay_factor
			print(f'Current learning rate: {eta}')

		accuracies['train'] = self.compute_accuracy(self.data['train_set']['X'],
													self.data['train_set']['y'])
		accuracies['val'] = self.compute_accuracy(self.data['val_set']['X'],
												  self.data['val_set']['y'])
		accuracies['test'] = self.compute_accuracy(self.data['test_set']['X'],
												   self.data['test_set']['y'])


		return accuracies, costs


def main():
	seed = 12345
	np.random.seed(seed)
	our_lambda = 0.0
	n_epochs = 40
	n_batch = 100
	eta = 0.1
	decay_factor = 0.90
	xavier = True
	SVM_loss = True

	if xavier:
		xavier_str = 'T'
	else:
		xavier_str = 'F'

	if SVM_loss:
		SVM_str = 'T'
	else:
		SVM_str = 'F'

	print()
	print("------------------------ Loading dataset ------------------------")
	datasets_folder = "Datasets/cifar-10-batches-py/"

	labels = unpickle(datasets_folder + "batches.meta")[b'label_names']

	# Bonus A) use all available data for training. Reduce validation to 1000.
	train_set_1 = load_dataset(datasets_folder, "data_batch_1", num_of_labels=len(labels))
	train_set_2 = load_dataset(datasets_folder, "data_batch_2", num_of_labels=len(labels))
	train_set_3 = load_dataset(datasets_folder, "data_batch_3", num_of_labels=len(labels))
	train_set_4 = load_dataset(datasets_folder, "data_batch_4", num_of_labels=len(labels))
	train_set_5 = load_dataset(datasets_folder, "data_batch_5", num_of_labels=len(labels))

	train_set = dict()
	train_set['X'] = np.concatenate((train_set_1['X'], train_set_2['X'], train_set_3['X'], train_set_4['X'], train_set_5['X']), axis=1)
	train_set['Y'] = np.concatenate((train_set_1['Y'], train_set_2['Y'], train_set_3['Y'], train_set_4['Y'], train_set_5['Y']), axis=1)
	train_set['y'] = np.concatenate((train_set_1['y'], train_set_2['y'], train_set_3['y'], train_set_4['y'], train_set_5['y']))

	train_set['X'] = train_set['X'][:, :-1000]
	train_set['Y'] = train_set['Y'][:, :-1000]
	train_set['y'] = train_set['y'][:-1000]

	val_set = load_dataset(datasets_folder, "data_batch_5", num_of_labels=len(labels))
	val_set['X'] = val_set['X'][:, :1000]
	val_set['Y'] = val_set['Y'][:, :1000]
	val_set['y'] = val_set['y'][:1000]

	test_set = load_dataset(datasets_folder, "test_batch", num_of_labels=len(labels))

	datasets = {'train_set': train_set, 'test_set': test_set, 'val_set': val_set}
	print()
	print("----------------------- Preparing dataset -----------------------")
	for dataset_name, dataset in datasets.items():
		dataset['X'] = preprocess_dataset(dataset['X'])

	print()
	print("---------------------- Learning classifier ----------------------")
	clf = SingleLayerNetwork(labels, datasets, decay_factor=decay_factor,
							 xavier=xavier, SVM_loss=SVM_loss)

	accuracies, costs = clf.mini_batch_gradient_descent(datasets['train_set']['X'],
														datasets['train_set']['Y'],
														our_lambda=our_lambda,
														n_batch=n_batch,
														eta=eta,
														n_epochs=n_epochs,
														save_costs=True)

	print()
	print(f'Training data accuracy:\t\t{accuracies["train"]}')
	print(f'Validation data accuracy:\t{accuracies["val"]}')
	print(f'Test data accuracy:\t\t{accuracies["test"]}')

	tracc = accuracies["train"]
	vacc = accuracies["val"]
	teacc = accuracies["test"]
	title = f'lambda{our_lambda}_n-batch{n_batch}_eta{eta}_n-epochs{n_epochs}_df-{decay_factor}_xavier-{xavier_str}_svm-{SVM_str}_tr-acc{tracc}_v-acc{vacc}_te-acc{teacc}_seed{seed}'
	plot_lines(line_A=costs['train'], line_B=costs['val'],
			   label_A='training loss', label_B='validation loss',
			   xlabel='epoch', ylabel='loss', title=title)

	labels = ['airplane', 'automobile', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck']
	montage(clf.W, title, labels)

	print()

	return


if __name__ == '__main__':
	main()
