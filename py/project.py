# PROJECT - CV
# Ignacio Garrido Botella & Abel Rodriguez Romero
import cv2
import random
import numpy as np
import matplotlib.pyplot as plt
from lxml import etree
import os
from skimage import io
from skimage.transform import resize
import keras
from keras.datasets import mnist
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Conv2D, MaxPooling2D, UpSampling2D, Flatten, Reshape
from keras import regularizers
from keras.models import load_model


#For making the NN work:
os.environ['KMP_DUPLICATE_LIB_OK']='True'
#Problem: https://medium.com/@valeryyakovlev/python-keras-hangs-on-fit-method-spyder-anaconda-8d555eeeb47e

#Source: https://blog.keras.io/building-autoencoders-in-keras.html

# parameters that you should set before running this script
filter = ['aeroplane', 'car', 'chair', 'dog', 'bird']       # select class, this default should yield 1489 training and 1470 validation images
voc_root_folder = "/Users/ignacio/Documents/Universidad/Master/Segundo/SegundoSemestre/Computer vision/Project/Data/VOCdevkit/"  # please replace with the location on your laptop where you unpacked the tarball
image_size = 128    # image size that you will use for your network (input images will be resampled to this size), lower if you have troubles on your laptop (hint: use io.imshow to inspect the quality of the resampled images before feeding it into your network!)


# step1 - build list of filtered filenames
annotation_folder = os.path.join(voc_root_folder, "VOC2009/Annotations/")
annotation_files = os.listdir(annotation_folder) #List all the files from the subfolder "Annotations"
filtered_filenames = []
for a_f in annotation_files:
    tree = etree.parse(os.path.join(annotation_folder, a_f)) #To get all the xml
    if np.any([tag.text == filt for tag in tree.iterfind(".//name") for filt in filter]):
        filtered_filenames.append(a_f[:-4]) #It stores the file name that contains one of the words of the keyword list "filter"

# step2 - build (x,y) for TRAIN/VAL (classification)
classes_folder = os.path.join(voc_root_folder, "VOC2009/ImageSets/Main/") #List all the files from the subfolder "ImageSets/Main/"
classes_files = os.listdir(classes_folder)
train_files = [os.path.join(classes_folder, c_f) for filt in filter for c_f in classes_files if filt in c_f and '_train.txt' in c_f] #List all the train files
val_files = [os.path.join(classes_folder, c_f) for filt in filter for c_f in classes_files if filt in c_f and '_val.txt' in c_f] #List all the test files


def build_classification_dataset(list_of_files):
    """ build training or validation set

    :param list_of_files: list of filenames to build trainset with
    :return: tuple with x np.ndarray of shape (n_images, image_size, image_size, 3) and  y np.ndarray of shape (n_images, n_classes)
    """
    temp = []
    train_labels = []
    for f_cf in list_of_files:
        with open(f_cf) as file: #It opens the files with all the names of the files with the pictures
            lines = file.read().splitlines()
            temp.append([line.split()[0] for line in lines if int(line.split()[-1]) == 1])
            label_id = [f_ind for f_ind, filt in enumerate(filter) if filt in f_cf][0]
            train_labels.append(len(temp[-1]) * [label_id])
    train_filter = [item for l in temp for item in l]

    image_folder = os.path.join(voc_root_folder, "VOC2009/JPEGImages/")
    image_filenames = [os.path.join(image_folder, file) for f in train_filter for file in os.listdir(image_folder) if
                       f in file]
    x = np.array([resize(io.imread(img_f), (image_size, image_size, 3)) for img_f in image_filenames]).astype(
        'float32')
    # changed y to an array of shape (num_examples, num_classes) with 0 if class is not present and 1 if class is present
    y_temp = []
    for tf in train_filter:
        y_temp.append([1 if tf in l else 0 for l in temp])
    y = np.array(y_temp)

    return x, y #y_temp


x_train, y_train = build_classification_dataset(train_files)
print('%i training images from %i classes' %(x_train.shape[0], y_train.shape[1]))
x_val, y_val = build_classification_dataset(val_files)
print('%i validation images from %i classes' %(x_val.shape[0],  y_train.shape[1]))

# from here, you can start building your model
# you will only need x_train and x_val for the autoencoder
# you should extend the above script for the segmentation task (you will need a slightly different function for building the label images)

#Randomly permutate the train/val sets:
p_train = np.random.permutation(len(x_train))
p_val = np.random.permutation(len(x_val))
x_train=x_train[p_train]
y_train=y_train[p_train]
x_val=x_val[p_val]
y_val=y_val[p_val]
#Smaller sets for fast training
x_train_small=x_train[p_train[1:100]]
y_train_small=y_train[p_train[1:100]]
x_val_small=x_val[p_val[1:100]]
y_val_small=y_val[p_val[1:100]]

#%%

##############
#Autoencoder:#
##############

#Source: https://ramhiser.com/post/2018-05-14-autoencoders-with-keras/
random.seed(42)

autoencoder = Sequential()

# Encoder Layers
autoencoder.add(Conv2D(16, (3, 3), activation='relu', padding='same', input_shape=(image_size, image_size, 3))) # 16 kernels of size 3x3 - The output is of size 16*size_image*size_image.
autoencoder.add(MaxPooling2D((2, 2), padding='same'))  #Reduction in size x2.
autoencoder.add(Conv2D(32, (3, 3), activation='relu', padding='same'))
autoencoder.add(Conv2D(32, (5, 5), activation='relu', padding='same'))
autoencoder.add(MaxPooling2D((2, 2), padding='same'))
autoencoder.add(Conv2D(64, (3, 3),  strides = (2,2),activation='relu', padding='same'))
autoencoder.add(MaxPooling2D((2, 2), padding='same'))
autoencoder.add(Conv2D(4, (3, 3), activation='relu', padding='same'))

# Flatten encoding for visualization
autoencoder.add(Flatten())
autoencoder.add(Reshape((8, 8, 4)))

# Decoder Layers
autoencoder.add(Conv2D(4, (3, 3), activation='relu', padding='same'))
autoencoder.add(UpSampling2D((2, 2)))
autoencoder.add(Conv2D(64, (3, 3), activation='relu', padding='same'))
autoencoder.add(UpSampling2D((2, 2)))
autoencoder.add(Conv2D(32, (5, 5), activation='relu', padding='same'))
autoencoder.add(Conv2D(32, (3, 3), activation='relu', padding='same'))
autoencoder.add(UpSampling2D((2, 2)))
autoencoder.add(Conv2D(16, (3, 3), activation='relu', padding='same')) # 16 kernels of size 3x3 - The output is of size 16*size_image*size_image.
autoencoder.add(UpSampling2D((2, 2)))
autoencoder.add(Conv2D(3, (3, 3), activation='sigmoid', padding='same'))

autoencoder.summary()

#%%
#We build the model of the encoder
encoder = Model(inputs=autoencoder.input, outputs=autoencoder.get_layer('flatten_1').output)

#autoencoder.compile(optimizer='sgd', loss='mean_squared_error')
#autoencoder.compile(optimizer='adam', loss='binary_crossentropy')
autoencoder.compile(loss='mean_squared_error', optimizer = 'RMSprop')

#%% Trainning
autoencoder.fit(x_train, x_train, epochs=25, batch_size=64, validation_data=(x_val, x_val))

#Bigger batch size -> Bigger generalization

#%%

img_x = x_val[0:100]
img = autoencoder.predict(img_x)

n_image = 92
f = plt.figure()
f.add_subplot(1,2, 1)
plt.imshow(img_x[n_image])
plt.title("Original")
f.add_subplot(1,2, 2)
plt.imshow(img[n_image])
plt.title("Decoded")
plt.show(block=True)


#%% Save the model

#model_name = 'model_5conv_256compression.h5'
#path = voc_root_folder[:-16]+"/Models/"+model_name
#autoencoder.save(path) 
#path = voc_root_folder[:-16]+"/computer-vision-kul-project/Models/"+model_name
#autoencoder.save(path) 

#To load the model:
#autoencoder = load_model(path)



