import numpy as np
import pickle


def softmax(x):
	""" Standard definition of the softmax function """
	return np.exp(x) / np.sum(np.exp(x), axis=0)


def load_batch(filename):
	""" Copied from the dataset website """
	with open(filename, 'rb') as fo:
		dict = pickle.load(fo, encoding='bytes')
	return dict


def split_batch(batch):
	""" Split the input batch into its labels and its data """
	X = (batch[b'data'] / 255).T
	y = batch[b'labels']
	Y = (np.eye(10)[y]).T
	# X = (dataDict[b"data"] / 255).T
	# y = dataDict[b"labels"]
	# Y = (np.eye(10)[y]).T

	return X, Y, y


def unpickle(filename):
    """Unpickle a file"""
    with open(filename, 'rb') as f:
        file_dict = pickle.load(f, encoding='bytes')

    return file_dict


def compute_grads_num(X, Y, P, W, b, lamda, h):
	""" Converted from matlab code """
	no 	= 	W.shape[0]
	d 	= 	X.shape[0]

	grad_W = np.zeros(W.shape);
	grad_b = np.zeros((no, 1));

	c = compute_cost(X, Y, W, b, lamda);

	for i in range(len(b)):
		b_try = np.array(b)
		b_try[i] += h
		c2 = compute_cost(X, Y, W, b_try, lamda)
		grad_b[i] = (c2-c) / h

	for i in range(W.shape[0]):
		for j in range(W.shape[1]):
			W_try = np.array(W)
			W_try[i,j] += h
			c2 = compute_cost(X, Y, W_try, b, lamda)
			grad_W[i,j] = (c2-c) / h

	return [grad_W, grad_b]


def compute_grads_num_slow(X, Y, P, W, b, lamda, h):
	""" Converted from matlab code """
	no 	= 	W.shape[0]
	d 	= 	X.shape[0]

	grad_W = np.zeros(W.shape);
	grad_b = np.zeros((no, 1));

	for i in range(len(b)):
		b_try = np.array(b)
		b_try[i] -= h
		c1 = compute_cost(X, Y, W, b_try, lamda)

		b_try = np.array(b)
		b_try[i] += h
		c2 = compute_cost(X, Y, W, b_try, lamda)

		grad_b[i] = (c2-c1) / (2*h)

	for i in range(W.shape[0]):
		for j in range(W.shape[1]):
			W_try = np.array(W)
			W_try[i,j] -= h
			c1 = compute_cost(X, Y, W_try, b, lamda)

			W_try = np.array(W)
			W_try[i,j] += h
			c2 = compute_cost(X, Y, W_try, b, lamda)

			grad_W[i,j] = (c2-c1) / (2*h)

	return [grad_W, grad_b]


def montage(W):
	""" Display the image for each label in W """
	import matplotlib.pyplot as plt
	fig, ax = plt.subplots(2,5)
	for i in range(2):
		for j in range(5):
			im  = W[i+j,:].reshape(32,32,3, order='F')
			sim = (im-np.min(im[:]))/(np.max(im[:])-np.min(im[:]))
			sim = sim.transpose(1,0,2)
			ax[i][j].imshow(sim, interpolation='nearest')
			ax[i][j].set_title("y="+str(5*i+j))
			ax[i][j].axis('off')
	plt.show()


def save_as_mat(data, name="model"):
	""" Used to transfer a python model to matlab """
	import scipy.io as sio
	sio.savemat(name+'.mat',{name:b})
