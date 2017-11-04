import pandas as pd # data analysis toolkit - create, read, update, delete datasets
import numpy as np #matrix math
from sklearn.model_selection import train_test_split #to split out training and testing data
#keras is a high level wrapper on top of tensorflow (machine learning library)
#The Sequential container is a linear stack of layers
from keras.models import Sequential
#popular optimization strategy that uses gradient descent
from keras.optimizers import Adam
#to save our model periodically as checkpoints for loading later
from keras.callbacks import ModelCheckpoint
#what types of layers do we want our model to have?
from keras.layers import Activation, BatchNormalization, Lambda, Conv2D, MaxPooling2D, Dropout, Dense, Flatten
#used to setup as categorical outputs
from keras.constraints import maxnorm
from keras.utils import np_utils
#helper class to define input shape and generate training images given image paths & steering angles
from utils import INPUT_SHAPE, batch_generator
#for command line arguments
import argparse
#for reading files
import os

#for debugging, allows for reproducible (deterministic) results
np.random.seed(0)


def load_data(args):
    """
    Load training data and split it into training and validation set
    """
    #reads CSV file into a single dataframe variable
    data_df = pd.read_csv(os.path.join(os.getcwd(), args.data_dir, \
        'driving_log.csv'), names=[\
        'center', 'c_detect', 'c_x', 'c_y', 'c_width', 'c_height', \
        'left', 'l_detect', 'l_x', 'l_y', 'l_width', 'l_height', \
        'right', 'r_detect', 'r_x', 'r_y', 'r_width', 'r_height'])

    #yay dataframes, we can select rows and columns by their names
    #we'll store the camera images as our input data
    x_center = data_df['center']
    x_left = data_df['left']
    x_right = data_df['right']
    x = pd.concat([x_center, x_left, x_right]).values

    #and our steering commands as our output data
    y_center = data_df['c_detect']
    y_left = data_df['l_detect']
    y_right = data_df['r_detect']
    y = pd.concat([y_center, y_left, y_right]).values.astype(int)

    #now we can split the data into a training (80), testing(20), and validation set
    #thanks scikit learn
    x_train, x_valid, y_train, y_valid = train_test_split(x, y, test_size=args.test_size, random_state=0)


    return x_train, x_valid, y_train, y_valid


def build_model(args):
    """
    NVIDIA model used
    Image normalization to avoid saturation and make gradients work better.
    Convolution: 5x5, filter: 24, strides: 2x2, activation: ELU
    Convolution: 5x5, filter: 36, strides: 2x2, activation: ELU
    Convolution: 5x5, filter: 48, strides: 2x2, activation: ELU
    Convolution: 3x3, filter: 64, strides: 1x1, activation: ELU
    Convolution: 3x3, filter: 64, strides: 1x1, activation: ELU
    Drop out (0.5)
    Fully connected: neurons: 100, activation: ELU
    Fully connected: neurons: 50, activation: ELU
    Fully connected: neurons: 10, activation: ELU
    Fully connected: neurons: 1 (output)

    # the convolution layers are meant to handle feature engineering
    the fully connected layer for predicting the steering angle.
    dropout avoids overfitting
    ELU(Exponential linear unit) function takes care of the Vanishing gradient problem.
    """
    # model = Sequential()
    # model.add(Lambda(lambda x: x/127.5-1.0, input_shape=INPUT_SHAPE))
    # model.add(Conv2D(24, 5, 5, activation='elu', subsample=(2, 2)))
    # model.add(Conv2D(36, 5, 5, activation='elu', subsample=(2, 2)))
    # model.add(Conv2D(48, 5, 5, activation='elu', subsample=(2, 2)))
    # model.add(Conv2D(64, 3, 3, activation='elu'))
    # model.add(Conv2D(64, 3, 3, activation='elu'))
    # model.add(Dropout(args.keep_prob))
    # model.add(Flatten())
    # model.add(Dense(100, activation='elu'))
    # model.add(Dense(50, activation='elu'))
    # model.add(Dense(10, activation='elu'))
    # model.add(Dense(1, activation='softmax'))
    # model.summary()

    # https://github.com/ltrottier/keras-object-recognition/blob/master/models.py
    model = Sequential()

    model.add(Conv2D(
        64, 3, 3, border_mode='same',
        input_shape=INPUT_SHAPE,
        init='he_normal'))
    model.add(BatchNormalization(
        mode=0,
        axis=1)) # or 3?
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(
        64, 3, 3, border_mode='same',
        init='he_normal'))
    model.add(BatchNormalization(
        mode=0,
        axis=1
    ))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))

    model.add(Conv2D(
        64, 3, 3, border_mode='same',
        init='he_normal'))
    model.add(BatchNormalization(
        mode=0,
        axis=1
    ))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))


    model.add(Flatten())
    model.add(Dense(512, bias=False))
    model.add(BatchNormalization(
        mode=0,
        axis=-1
    ))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(1))
    model.add(Activation('softmax'))

    #   File "C:\Users\zsmit\.conda\envs\pothole_detector\lib\site-packages\keras\backend\tensorflow_backend.py", line 2008, in binary_crossentropy
    #   CHANGE: return tf.nn.sigmoid_cross_entropy_with_logits(output, target)
    #   TO:  return tf.nn.sigmoid_cross_entropy_with_logits(logits=output, labels=target)

    return model


def train_model(model, args, x_train, x_valid, y_train, y_valid):
    """
    Train the model
    """
    #Saves the model after every epoch.
    #quantity to monitor, verbosity i.e logging mode (0 or 1),
    #if save_best_only is true the latest best model according to the quantity monitored will not be overwritten.
    #mode: one of {auto, min, max}. If save_best_only=True, the decision to overwrite the current save file is
    # made based on either the maximization or the minimization of the monitored quantity. For val_acc,
    #this should be max, for val_loss this should be min, etc. In auto mode, the direction is automatically
    # inferred from the name of the monitored quantity.
    checkpoint = ModelCheckpoint('model-{epoch:03d}.h5',
                                 monitor='val_loss',
                                 verbose=0,
                                 save_best_only=args.save_best_only,
                                 mode='auto')

    #calculate the difference between expected steering angle and actual steering angle
    #square the difference
    #add up all those differences for as many data points as we have
    #divide by the number of them
    #that value is our mean squared error! this is what we want to minimize via
    #gradient descent
    model.compile(loss='binary_crossentropy', optimizer=Adam(lr=args.learning_rate), metrics=['accuracy'])
    print(model.summary())

    #Fits the model on data generated batch-by-batch by a Python generator.

    #The generator is run in parallel to the model, for efficiency.
    #For instance, this allows you to do real-time data augmentation on images on CPU in
    #parallel to training your model on GPU.
    #so we reshape our data into their appropriate batches and train our model simulatenously
    t_data = batch_generator("", x_train, y_train, args.batch_size, True, args.is_unix)
    v_data = batch_generator("", x_valid, y_valid, args.batch_size, True, args.is_unix)
    model.fit_generator(t_data,
                        args.samples_per_epoch,
                        args.nb_epoch,
                        max_q_size=1,
                        validation_data=v_data,
                        nb_val_samples=len(x_valid),
                        callbacks=[checkpoint],
                        verbose=1)

#for command line args
def s2b(s):
    """
    Converts a string to boolean value
    """
    s = s.lower()
    return s == 'true' or s == 'yes' or s == 'y' or s == '1'


def main():
    """
    Load train/validation data set and train the model
    """
    parser = argparse.ArgumentParser(description='Behavioral Cloning Training Program')
    parser.add_argument('-d', help='data directory',        dest='data_dir',          type=str,   default='data')
    parser.add_argument('-t', help='test size fraction',    dest='test_size',         type=float, default=0.2)
    parser.add_argument('-k', help='drop out probability',  dest='keep_prob',         type=float, default=0.5)
    parser.add_argument('-n', help='number of epochs',      dest='nb_epoch',          type=int,   default=10)
    parser.add_argument('-s', help='samples per epoch',     dest='samples_per_epoch', type=int,   default=20000)
    parser.add_argument('-b', help='batch size',            dest='batch_size',        type=int,   default=40)
    parser.add_argument('-o', help='save best models only', dest='save_best_only',    type=s2b,   default='true')
    parser.add_argument('-l', help='learning rate',         dest='learning_rate',     type=float, default=1.0e-4)
    parser.add_argument('-u', help='unix file name',        dest='is_unix',           type=s2b,   default='false')
    args = parser.parse_args()

    #print parameters
    print('-' * 30)
    print('Parameters')
    print('-' * 30)
    for key, value in vars(args).items():
        print('{:<20} := {}'.format(key, value))
    print('-' * 30)

    #load data
    data = load_data(args)
    #print(data)
    #build model
    model = build_model(args)
    #train model on data, it saves as model.h5
    train_model(model, args, *data)


if __name__ == '__main__':
    main()
