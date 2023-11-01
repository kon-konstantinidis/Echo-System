import numpy as np
from matplotlib import pyplot as plt
import cv2
import onnxruntime
import pydicom
from pydicom.pixel_data_handlers.util import convert_color_space

def prep_dicom_video(video_rgb):    
    pixel_array_ybr = convert_color_space(video_rgb,"RGB","YBR_FULL")
    frames,height,width,channels = pixel_array_ybr.shape

    # This code section makes the image square by cropping the long dimension (at its center) to match the short one.
    bias = int(np.abs(width - height)/2)
    if bias !=0: # if the image is NOT SQUARE
        if height < width:
            pixel_array_ybr = pixel_array_ybr[:, :, bias:-bias, :]
            square_side = height
        else:
            pixel_array_ybr = pixel_array_ybr[:, bias:-bias, :, :]
            square_side = width
    else: # if the image is SQUARE already 
        square_side = height # (it could be width)
    
    # This code section crops 10% off all four sides and resizes to 112x112
    pixel_array_y = pixel_array_ybr[:,:,:,0] # Keep only the luminosity ('y') channel -> (nframes, height, width)
    pixel_array_y_cropped = pixel_array_y[:,int(square_side/10):(square_side - int(square_side/10)), int(square_side/10):(square_side - int(square_side/10))] # Crop 10% off all four sides (I believe this is to remove the ECG)
    pixel_array_y_cropped = np.transpose(pixel_array_y_cropped, (1,2,0)) # Change dims order to (height, width, nframes) as required by OpenCV below
    pixel_array_y_resized = cv2.resize(pixel_array_y_cropped, (112,112), interpolation = cv2.INTER_CUBIC) # Resize all frames to 112x112 as required by the EchoNet models

    pixel_array_y_resized_rgb = np.stack((pixel_array_y_resized, pixel_array_y_resized, pixel_array_y_resized), axis=0) # Turn the single-channel video to a 3-channel one (RGB with all channels equal), as required by the EchoNet models
    pixel_array_y_resized_rgb = np.transpose(pixel_array_y_resized_rgb, (3,1,2,0)) # From (channels, height, width, nframes) to (nframes, height, width, channels)
    return pixel_array_y_resized_rgb

def segment_lv(segmentation_model_path, video_array):
    # Normalize the video (pixel-wise) with the mean and std values provided by the EchoNet authors
    mean = [33.741943, 33.877575, 34.1646]
    std = [51.184673, 51.356464, 51.660316]
    video_array = (video_array - mean) / std # This is a standard step required by the model

    # Reshape the model input as required by the segmentation model
    video_array = (np.transpose(video_array, (0,3,1,2))).astype(np.float32) # Shape is (nframes, 3, 112, 112)

    # Perform the inference
    ort_session = onnxruntime.InferenceSession(segmentation_model_path)
    ort_input = {ort_session.get_inputs()[0].name: video_array}
    ort_output = ort_session.run(None, ort_input)[0][:,0,:,:]
    binary_mask = ort_output>0
    return binary_mask # Shape is (nframes, 112, 112)

def estimate_lvef(lvef_model_path, video_array):
    # Normalize the video (pixel-wise) with the mean and std values provided by the EchoNet authors
    mean = [33.741943, 33.877575, 34.1646]
    std = [51.184673, 51.356464, 51.660316]
    video_array = (video_array - mean) / std # This is a standard step required by the model

    # Reshape the model input as required by the segmentation model
    video_array = (np.expand_dims(np.transpose(video_array, (3,0,1,2)), axis = 0)).astype(np.float32) # Shape is (1, 3, nframes, 112, 112)
    # The following is a standard step required by the EchoNet LVEF model
    # The model expects an input of 32 frames.
    # The original clip is expected to be at 50 FPS. 
    # This 32-frame clip should be sampled from the original clip by skipping every other frame (1:2 temporal subsampling).
    # If the original clip was at 25 FPS, we would not skip frames. If it was at 100 FPS, we would do 1:4 temporal subsampling.
    video_array = video_array[:,:,0:64:2,:,:] # Sample a 32-frame subclip with 1:2 temporal subsampling from the beginning of the video.

    # Perform the inference
    ort_session = onnxruntime.InferenceSession(lvef_model_path)
    ort_input = {ort_session.get_inputs()[0].name: video_array}
    lvef = ort_session.run(None, ort_input)[0][0][0]
    
    return lvef

def mask_video_no_resize(mask,video):
    """
    Mask the resized to mask's dimensions video with the mask produced by segment_lv
    Returns the video in the mask's dimensions (112x112) with the mask applied on the border [1]
    and on the whole area [2].
    """
    border_masked_video = np.copy(video)
    masked_video = np.copy(video)

    for frame in range(0,mask.shape[0]):
        # For border masked video
        contours = cv2.findContours(mask[frame,:,:].astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0][0]
        for i in range(0,contours.shape[0]):
            x = contours[i,0,0]
            y = contours[i,0,1]
            border_masked_video[frame,y,x,0] = 0
            border_masked_video[frame,y,x,1] = 255
            border_masked_video[frame,y,x,2] = 0
        # For masked video
        for i in range(0,mask.shape[1]):
            for j in range(0,mask.shape[2]):
                if (mask[frame,i,j]):
                    masked_video[frame,i,j,0] = 255
                    masked_video[frame,i,j,1] = 0
                    masked_video[frame,i,j,2] = 0
    
    return (masked_video,border_masked_video)

def mask_video(mask,video_rgb):
    """
    Mask the original video with the mask produced by segment_lv
    Returns the video in its original dimensions with the mask applied on the border [1]
    and on the whole area [2].
    """
    print("Original Video shape:",video_rgb.shape)
    print("Mask shape:",mask.shape)

    # First, resize the mask to the video's shape
    nframes, height, width, channels = video_rgb.shape
    

    # Steps to make video (112,112)
    # Starting Video Dimensions: (nframes,height,width)
    # 1. Make the image square by cropping the long dimension (at its center) to match the short one.
    # Video Shape: (nframes,width,width) or (nframes,height,height)
    # 2. Crop 20% of the width and height
    # Video Shape: (nframes,0.8*width,0.8*width) or (nframes,0.8*height,0.8*height)
    # 3. cv2.resize to (112,112)
    # Final Video Shape: (nframes,112,112)
    # To resize the mash to the original video's height and width, traverse the steps backwards
    # So: 

    # 3. Resize (nframes,112,112) mask to (nframes,0.8*width,0.8*width) 
    # or (nframes,0.8*height,0.8*height) (whichever is smaller)
    # Example numbers in comments given for height=434 and width=636

    mask = np.transpose(mask, (1,2,0)) # Change dims order to (height, width, nframes) as required by OpenCV below
    if height < width:
        new_dim = int(0.8*height) + 1  # rounding error avoided
        smaller = height
    else:
        # rarely happens to be height>width
        new_dim = int(0.8*width) + 1 # rounding error avoided
        smaller = width
    mask = cv2.resize(mask.astype(np.uint8),(new_dim,new_dim),interpolation=cv2.INTER_CUBIC)
    mask = np.transpose(mask, (2,0,1)) # Change back to (nframes, height, width)

    # 2. Add 20% (10% from bottom-top/left-right to both height and width)
    # (nframes,348,348) -> (nframes,434,434)
    decropped_mask = np.zeros((nframes,smaller,smaller))
    print("Decropped Mask shape:",decropped_mask.shape)
    decropped_mask[:,int(smaller/10):(int(smaller/10) + mask.shape[1]), 
                    int(smaller/10):(int(smaller/10) + mask.shape[2])] = mask[:,:,:]
    mask = decropped_mask
    
    # 1. Make the image rectangular by adding to the long dimension (at its center)
    rect_mask = np.zeros((nframes,height,width))
    bias = int(np.abs(width - height)/2)
    if height < width:
        rect_mask[:,:,bias:-bias] = mask[:,:,:]
    else:
        rect_mask[:,bias:-bias,:] = mask[:,:,:]
    mask = rect_mask
    #return(mask)

    border_masked_video = np.copy(video_rgb)
    fully_masked_video = np.copy(video_rgb)
    for frame in range(0,mask.shape[0]):
        # For border masked video
        ans = cv2.findContours(mask[frame,:,:].astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        if(len(ans[0])>0):
            # Sometimes, the second indexing will throw an error, so skip that frame
            # Further investigation is required to determine how cv2.findContours behaves
            # Until then, this simple check deals with the issue (could maybe try a try-except block) 
            contours = ans[0][0]
            for i in range(0,contours.shape[0]):
                x = contours[i,0,0]
                y = contours[i,0,1]
                border_masked_video[frame,y,x,0] = 0
                border_masked_video[frame,y,x,1] = 255
                border_masked_video[frame,y,x,2] = 0
        else:
            print(ans[0])
    # For fully masked video
    fully_masked_video[:,:,:,2][np.where(mask)] = 255 # paint the lv chamber blue
    return (border_masked_video,fully_masked_video)

def lvef_estimation_pipeline(dicom_video_rgb):
    """
    Provided the dicom pixel array, estimate the LVEF and return that
    along with the video with the segmentation mask applied
    """
    segmentation_model_path = './Estimators/LVEF/echonet_segmentation.onnx'
    lvef_model_path = './Estimators/LVEF/echonet_pretrained.onnx'
    video_array = prep_dicom_video(dicom_video_rgb)
    segmentation_array = segment_lv(segmentation_model_path=segmentation_model_path, video_array=video_array)
    lvef = estimate_lvef(lvef_model_path=lvef_model_path, video_array=video_array)
    (border_masked_video,fully_masked_video) = mask_video(segmentation_array, dicom_video_rgb)

    # Return only the first 64 frames
    return (lvef,border_masked_video[0:64,:,:,:],fully_masked_video[0:64,:,:,:])


if ( __name__ == '__main__'):
    video_path = 'C:/Users/konko/Desktop/Diploma/DICOM Scans/AO131541/M3FDDD1S'
    segmentation_model_path = 'C:/Users/konko/Desktop/Diploma/Echo_Web_App/Estimators/LVEF/echonet_segmentation.onnx'
    lvef_model_path = 'C:/Users/konko/Desktop/Diploma/Echo_Web_App/Estimators/LVEF/echonet_pretrained.onnx'

    dataset = pydicom.dcmread(video_path, force=True)
    video_array = prep_dicom_video(dataset.pixel_array)
    segmentation_array = segment_lv(segmentation_model_path=segmentation_model_path, video_array=video_array)
    mask = mask_video(segmentation_array,dataset.pixel_array)
    lvef = estimate_lvef(lvef_model_path=lvef_model_path, video_array=video_array)
    #(masked_video,border_masked_video) = mask_video_no_resize(segmentation_array,video_array)
    #(masked_video,border_masked_video) = mask_video(segmentation_array, dataset.pixel_array)

    OG_video_rgb = convert_color_space(dataset.pixel_array,"YBR_FULL","RGB")
    #lvef,border_masked_video_ybr,fully_masked_video_ybr = lvef_estimation_pipeline(dataset.pixel_array)
    #mask = lvef_estimation_pipeline(dataset.pixel_array)
    print("LVEF estimation:",lvef)
    #fully_masked_video = convert_color_space(fully_masked_video_ybr,"YBR_FULL","RGB")
    
    # View the mask graphically
    import matplotlib.animation as animation
    img = OG_video_rgb # some array of images
    img2 = mask
    frames = [] # for storing the generated images
    fig = plt.figure()
    for i in range(0,img.shape[0]):
        frames.append(
            [
                plt.imshow(img[i],animated=True),
                plt.imshow(img2[i],animated=True,alpha=0.5)
            ]
        )

    ani = animation.ArtistAnimation(fig, frames, interval=100, blit=True,repeat_delay=1000)

    #ani.save('mask.mp4')
    print("Showing animation")
    plt.show()
    #"""