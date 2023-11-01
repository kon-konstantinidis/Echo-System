import matplotlib.pyplot as plt
import pydicom 
from os import listdir
import os
from pydicom.pixel_data_handlers.util import apply_color_lut,convert_color_space
import numpy as np

# Image printing/handling/tests

filename = '../DICOM Scans/AO131541/M3FDBO9C'

ds = pydicom.dcmread(filename)
#print("shape:",ds.PatientID)

# Play the scan
pixel_array_rgb = convert_color_space(ds.pixel_array, "YBR_FULL", "RGB")
import matplotlib.animation as animation
img = pixel_array_rgb # some array of images
frames = [] # for storing the generated images
fig = plt.figure()
for i in range(0,img.shape[0]):
    frames.append([plt.imshow(img[i],animated=True)])

ani = animation.ArtistAnimation(fig, frames, interval=100, blit=True, repeat_delay=1000)

#ani.save('scan.mp4')
print("Showing animation")
plt.show()
#"""

"""
allDicoms = [f for f in listdir('../DICOM Scans/AO131541/')]
frames = []
for f in allDicoms:
    ds = pydicom.dcmread('../DICOM Scans/AO131541/'+f)
    pixel_array_shape = ds.pixel_array.shape
    noOfFrames = pixel_array_shape[0] if(len(pixel_array_shape)==4) else 1
    frames.append(noOfFrames)
print(frames)
#"""
"""
def rgb2gray(rgb):
    # Converts rgp image to grayscale
    r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray

def rgb2rgba(rgb,A):
    # Transforms an RGB picture into an RGBA one (adds A channel)
    rows,cols,ch = rgb.shape
    rgba = A*np.ones(shape=(rows,cols,4))
    for i in range(0,rows):
        for j in range(0,cols):
            for k in range(0,4):
                if (k==3): continue
                rgba[i,j,k] = rgb[i,j,k]
    return rgba


rgb = convert_color_space(ds.pixel_array, "YBR_FULL", "RGB")
plt.imshow(rgb[0,:,:,:])
#plt.show()
"""
"""
rgbPic = rgb[40,:,:,:]
print("rgbPic.shape:",rgbPic.shape)
flat_rgbPic = rgbPic.flatten(order='F')


rgbaPic = rgb2rgba(rgbPic,255)
print("rgbaPic.shape:",rgbaPic.shape)
flat_rgbaPic = rgbaPic.flatten(order='C')


with open('imageFlatColorRGBA4.txt','x') as f:
    f.write(np.array2string(flat_rgbaPic,threshold=np.inf,suppress_small=True,separator=','))
"""

"""
# For grayscale image
gray = rgb2gray(rgb[0,:,:,:])

print("gray shape:" , gray.shape)
flat_gray = np.zeros(shape=(gray.shape[0]*gray.shape[1]))
print("flat_gray.shape: ",flat_gray.shape)

for i in range(0,gray.shape[0]):
    for j in range(0,gray.shape[1]):
        flat_gray[j*gray.shape[0]+i] = gray[i,j]

flat_gray = gray.flatten(order='F')
for i in range(0,len(flat_gray)):
    flat_gray[i] = int(flat_gray[i])

print(flat_gray.max())

with open('imageFlat.txt','x') as f:
    f.write(np.array2string(flat_gray,threshold=np.inf,suppress_small=True,separator=','))
"""
"""
for i in range(0,rgb.shape[0]):
    plt.imshow(rgb[i,:,:,:])
    plt.show()
"""

# Plot images back to back, video-like
""" 
video = ds.pixel_array[:,:,:,:] 
plt.figure(1)
for i in range(0,video.shape[0]):
    print('At frame: ',i)
    plt.pause(0.1)
    rgb = convert_color_space(video[i,:,:,:], "YBR_FULL", "RGB")
    plt.imshow(rgb)

fig = px.imshow(video,animation_frame=0)
fig.show()
"""