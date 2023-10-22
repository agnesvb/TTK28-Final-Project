
import numpy as np
import matplotlib.pyplot as plt

#Inputs
data_folder = 'data/'
models_folder = 'models/'
hidden_units = 300
ss = 0.001
epochs = 5
batch_size = 100
lam = 0.0001
load = False
save = not load

# Load data MNIST-dataset
trainX = np.loadtxt(data_folder + 'train_data.csv', delimiter=',', skiprows=1)[:,1:]
trainY = np.loadtxt(data_folder + 'train_labels.csv', delimiter=',', skiprows=1)[:,1:]
testX = np.loadtxt(data_folder + 'test_data.csv', delimiter=',', skiprows=1)[:,1:]
testY = np.loadtxt(data_folder + 'test_labels.csv', delimiter=',', skiprows=1)[:,1:]

# Set seed
np.random.seed(0)

# Randomize training set and pick validation set
ind = np.random.choice(trainX.shape[0],size=trainX.shape[0],replace=False)
valX = trainX[ind[0:10000],:]
valY = trainY[ind[0:10000]]
trainX = trainX[10000:,:]
trainY = trainY[10000:]

#Standardize
mean = trainX.mean()
std = trainX.std()
trainX = (trainX-mean)/std
valX = (valX-mean)/std
testX = (testX - mean)/std

# %%
#Batchs
num_batches = int( np.floor( trainY.size/batch_size ) )
BX = [trainX[(i*batch_size):((i+1)*batch_size)] for i in range(num_batches)]
BY = [trainY[(i*batch_size):((i+1)*batch_size)] for i in range(num_batches)]

# %%
# Visualize
for i in range(16):
    plt.subplot(4,4,i+1)
    plt.imshow(np.reshape(trainX[i],[28,28]), cmap='gray')
    plt.title(str(int(trainY[i,0])))
    plt.axis('off')
    
plt.show()
# %%
#Network class
class net(object):
    def __init__(self,L=300):
        #Constants
        self.dim_in = 784
        self.dim_out = 10
        
        #Initialize weights
        self.W1 = np.random.randn(L,self.dim_in)
        self.W2 = np.random.randn(self.dim_out,L)
        self.b1 = np.zeros([L,1])
        self.b2 = np.zeros([self.dim_out,1])
        
        #Initialize random stuff
        self.total_loss = []
        self.total_accuracy = []
        self.loss_val = []
        self.acc_val = []
        self.loss_train = []
        self.acc_train = []
        
    def sigmoid(self, x):
        temp = x*0
        ind = x >= 0 
        temp[ind] = 1/(1+np.exp(-x[ind]))
        ind = x < 0
        temp[ind ] = np.exp(x[ind])/(1+np.exp(x[ind]))
        return temp
    
    def softmax(self,x):
        x = np.exp(x-np.max(x))
        return x/x.sum()
    
    def softmax_der(self,x):
        #This is used for the derivative
        B = x.shape[1]
        temp = np.zeros([self.dim_out,B]) # x is shape 10 x B
        for i in range(B):
            temp[:,i] = self.softmax(x[:,i])
        
        #Make the return matrix
        ret = np.zeros([B,self.dim_out,self.dim_out])
        I = np.identity(self.dim_out)
        for i in range(self.dim_out):
            for ii in range(self.dim_out):
                ret[:,i,ii] = temp[i,:]*(I[i,ii] - temp[ii,:])
        
        return ret
    
    def forward(self,x):
        #Reshape
        x = x.transpose()
        self.x_0 = x + 0 #The initial x

        #Hidden layer
        x = np.matmul(self.W1,x) + self.b1
        self.x_1 = x + 0 #x after the fully connected layer
        x = self.sigmoid(x)
        self.x_sigmoid = x + 0 #x after the sigmoid
        
        #Output layers
        x = np.matmul(self.W2,x) + self.b2
        self.x_2 = x + 0 #x afte second fully connected layer
        for i in range(x.shape[1]):
            x[:,i] = self.softmax(x[:,i])
        
        return x.squeeze()
    
    def loss(self, y, y_hat):
        #For numeric stability
        tol = 1e-64
        y_hat[y_hat <= tol] = tol
        
        self.y_hat = y_hat + 0
        self.y_hat_pred = np.argmax(y_hat,0)
        self.y = y
        self.loss_val = 0
        for i in range(y.size):
            self.loss_val -= np.log(y_hat[y[i],i])
        self.loss_val /= y.size
            
        return self.loss_val
    
    def zero_grad(self):
        self.W1_grad = self.W1*0
        self.b1_grad = self.b1*0
        self.W2_grad = self.W2*0
        self.b2_grad = self.b2*0
        return 
    
    def step(self,step_size):
        self.W1 = self.W1 - ss*self.W1_grad
        self.b1 = self.b1 - ss*self.b1_grad
        self.W2 = self.W2 - ss*self.W2_grad
        self.b2 = self.b2 - ss*self.b2_grad
        return

    def backward(self, lam):
        #Batch size
        B = self.y.size
        
        #Calculate the jacobian of the loss
        J_L = np.zeros([B,self.dim_out])
        for i in range(B):
            J_L[i,self.y[i]] = -(1)/(self.y_hat[self.y[i],i])

        #Softmax
        J_SM = self.softmax_der(self.x_2)

        ## b2 grad 
        grad_temp1 = np.zeros([B,self.dim_out])
        for i in range(B):
            grad_temp1[i,:] = np.matmul(J_L[i,:],J_SM[i,:])
        self.b2_grad = grad_temp1.sum(0).reshape(-1,1)
        
        #W2 jacobian
        T = self.W2.shape[0]
        N = self.W2.shape[1]
        temp = np.zeros([B,N*T])
        for i in range(T):
            ind1 = i*(N)
            ind2 = ind1 + N
            temp[:,ind1:ind2] = grad_temp1[:,i].reshape(B,1) * self.x_sigmoid.transpose()
        self.W2_grad = temp.sum(0).reshape(self.W2.shape) + 0
                        
        #Temporary gradient that will be used later
        grad_temp2 = np.matmul(grad_temp1,self.W2)
        
        #Sigmoid jacobian
        temp = self.sigmoid(self.x_1).squeeze()
        J_sig = np.zeros([B,self.W1.shape[0],self.W1.shape[0]])
        for i in range(self.W1.shape[0]):
            J_sig[i,:,:] = np.diag(temp[:,i]*(1-temp[:,i]))
            
        # b1 grad
        grad_temp3 = np.zeros([B,J_sig.shape[2]])
        for i in range(B):
            grad_temp3[i,:] = np.matmul(grad_temp2[i,:].reshape(1,-1),J_sig[i,:,:])
        self.b1_grad = grad_temp3.sum(0).reshape(-1,1)

        #W1 jacobian
        T = self.W1.shape[0]
        N = self.W1.shape[1]
        temp = np.zeros([B,N*T])
        for i in range(T):
            ind1 = i*(N)
            ind2 = ind1 + N
            temp[:,ind1:ind2] = grad_temp3[:,i].reshape(B,1) * self.x_0.transpose()
        self.W1_grad = temp.sum(0).reshape(self.W1.shape) + 0
    
        #Add regularization
        self.W1_grad += lam*self.W1
        self.W2_grad += lam*self.W2
    
        #Clip if gradient exploded
        tol = 1000
        self.W1_grad[self.W1_grad > tol] = tol
        self.W1_grad[self.W1_grad < -tol] = -tol
        self.b1_grad[self.b1_grad > tol] = tol
        self.b1_grad[self.b1_grad < -tol] = -tol
        self.W2_grad[self.W2_grad > tol] = tol
        self.W2_grad[self.W2_grad < -tol] = -tol
        self.b2_grad[self.b2_grad > tol] = tol
        self.b2_grad[self.b2_grad < -tol] = -tol
    
        return
    
    def save(self, filename):
        np.savez(filename, self.W1, self.b1, self.W2, self.b2, self.total_loss, self.total_accuracy, self.loss_val, self.acc_val, self.loss_train, self.acc_train)
        return
    
    def load(self, filename):
        temp = np.load(filename)
        self.W1 = temp['arr_0']
        self.b1 = temp['arr_1']
        self.W2 = temp['arr_2']
        self.b2 = temp['arr_3']
        
        self.total_loss = temp['arr_4']
        self.total_accuracy = temp['arr_5']
        self.loss_val = temp['arr_6']
        self.acc_val = temp['arr_7']
        self.loss_train = temp['arr_8']
        self.acc_train = temp['arr_9']
        return
# %%
#Make the network
model = net(300)
# %%
if load == True:
    print("load was ture")
    model.load(models_folder + 'model1.npz')
else:
    print("load was false")
    #Initialize stats arrays
    loss = np.zeros([epochs,len(BX)])
    acc = np.zeros([epochs,len(BX)])
    loss_val = np.zeros([epochs,1])
    acc_val = np.zeros([epochs,1])
    loss_train = np.zeros([epochs,1])
    acc_train = np.zeros([epochs,1])
    
    #Loop through data
    for epoch in range(epochs):
        for batch in range(len(BX)):
            #Make back
            X = BX[batch]
            Y = BY[batch]
            
            #Zero out the gradient
            model.zero_grad()
            
            #Forward
            out = model.forward(X)

            #calculate loss and accuracy
            loss[epoch,batch] = model.loss(Y.astype(int)[:,0],out)
            acc[epoch,batch] = np.mean(model.y_hat_pred == model.y)

            #Backward
            model.backward(0)

            #Update weights
            model.step(ss)
            
        #Calcualte the validation loss and stuff
        model.zero_grad()
        out = model.forward(valX)
        loss_val[epoch] = model.loss(valY.astype(int)[:,0],out)
        acc_val[epoch] = np.mean(model.y_hat_pred == model.y)

        #Calcualte over the whole training set
        model.zero_grad()
        out = model.forward(trainX)
        loss_train[epoch] = model.loss(trainY.astype(int)[:,0],out)
        acc_train[epoch] = np.mean(model.y_hat_pred == model.y)
        print('Epoch ' + str(epoch+1) + '... loss = ' + str(loss_train[epoch,0]) + '... acc = ' + str(acc_train[epoch,0]))
        
    #Save stats
    model.total_loss = loss + 0
    model.total_accuracy = acc + 0
    model.loss_val = loss_val + 0
    model.acc_val = acc_val + 0
    model.loss_train = loss_train + 0
    model.acc_train = acc_train + 0
    
    #Save network
    if save == True:
        model.save(models_folder + 'model1.npz')

# %% [markdown]
# ### Plots for part 1

# %%
plt.plot(loss_val)
plt.plot(loss_train)
plt.legend(['validation','training'])
plt.title('Unregularized loss')
plt.xlabel('epoch')
plt.ylabel('loss')
plt.show()

# %%
plt.plot(acc_val)
plt.plot(acc_train)
plt.legend(['validation','training'])
plt.title('Unregularized accuracy')
plt.xlabel('epoch')
plt.ylabel('accuracy')
plt.show()

# %% [markdown]
# ## Part 2

# %%
#Make the network
model = net(300)

# %%
if load == True:
    model.load(models_folder + 'model2.npz')

else:
    #Initialize stats arrays
    loss = np.zeros([epochs,len(BX)])
    acc = np.zeros([epochs,len(BX)])
    loss_val = np.zeros([epochs,1])
    acc_val = np.zeros([epochs,1])
    loss_train = np.zeros([epochs,1])
    acc_train = np.zeros([epochs,1])
    
    #Loop through data
    for epoch in range(epochs):
        for batch in range(len(BX)):
            #Make back
            X = BX[batch]
            Y = BY[batch]
            
            #Zero out the gradient
            model.zero_grad()
            
            #Forward
            out = model.forward(X)

            #calculate loss and accuracy
            loss[epoch,batch] = model.loss(Y.astype(int)[:,0],out)
            acc[epoch,batch] = np.mean(model.y_hat_pred == model.y)

            #Backward
            model.backward(lam)

            #Update weights
            model.step(ss)
            
        #Calcualte the validation loss and stuff
        model.zero_grad()
        out = model.forward(valX)
        loss_val[epoch] = model.loss(valY.astype(int)[:,0],out)
        acc_val[epoch] = np.mean(model.y_hat_pred == model.y)

        #Calcualte over the whole training set
        model.zero_grad()
        out = model.forward(trainX)
        loss_train[epoch] = model.loss(trainY.astype(int)[:,0],out)
        acc_train[epoch] = np.mean(model.y_hat_pred == model.y)
        print('Epoch ' + str(epoch+1) + '... loss = ' + str(loss_train[epoch,0]) + '... acc = ' + str(acc_train[epoch,0]))

    #Save stats
    model.total_loss = loss + 0
    model.total_accuracy = acc + 0
    model.loss_val = loss_val + 0
    model.acc_val = acc_val + 0
    model.loss_train = loss_train + 0
    model.acc_train = acc_train + 0
    
    #Save network
    if save == True:
        model.save(models_folder + 'model2.npz')

# %%
plt.plot(loss_val)
plt.plot(loss_train)
plt.legend(['validation','training'])
plt.title('Regularized loss')
plt.xlabel('epoch')
plt.ylabel('loss')
plt.show()

# %%
plt.plot(acc_val)
plt.plot(acc_train)
plt.legend(['validation','training'])
plt.title('Regularized accuracy')
plt.xlabel('epoch')
plt.ylabel('accuracy')
plt.show()

# %% [markdown]
# ## Part 3

# %%
#Regularized model
out = model.forward(testX)
loss_reg = model.loss(testY.astype(int)[:,0],out)
acc_reg = np.mean(model.y_hat_pred == model.y)

# %%
#Unregularized model
model.load(models_folder + 'model1.npz')
out = model.forward(testX)
loss_unreg = model.loss(testY.astype(int)[:,0],out)
acc_unreg = np.mean(model.y_hat_pred == model.y)

# %%
#Show results
print('The accuracy of the unregularized model is ' + str(round(100*acc_unreg,1)) + '%')
print('The accuracy of the regularized model is ' + str(round(100*acc_reg,1)) + '%')

# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%



