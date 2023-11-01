import cv2, pydicom
import numpy as np
from skimage.morphology import skeletonize
from pydicom.pixel_data_handlers.util import convert_color_space

from Estimators.LVGLS.lvgls_pipeline_functions import segment_lv, detect_single_cardiac_cycle, get_lv_border_from_segmentation, get_path_from_lv_border, tracking_update, measure_strain

def estimate_lv_strain_from_DICOM_file(dicom_path):
    '''
    This function expects a path to a DICOM file containing an ECHO scan.
    It has only been tested with DICOM files from a GE Healthcare device with the Vivid S5 scanner.
    The function loads the dicom file and:
        - Converts it to YBR
        - Sends a centered square crop of the luminosity (Y) channel to estimate_lv_strain_from_square_gray_frames_array()
        - Returns the strain sequence and an RGB segment of the ECHO scan for visualization of the lv border tracking
    '''

    # Load the video array from DICOM, convert to YBR and obtain Y channel
    dicom_contents = pydicom.dcmread(dicom_path, force=True)
    framerate = dicom_contents.CineRate
    pixel_array_ybr = convert_color_space(dicom_contents.pixel_array, dicom_contents.PhotometricInterpretation, 'YBR_FULL')
    nframes,height,width,channels = pixel_array_ybr.shape
    
    # Make the image square by cropping the long dimension (at its center) to match the short one
    bias = int(np.abs(width - height)/2)
    if bias != 0:
        if height < width:
            image_type = 'Wide'
            pixel_array_ybr = pixel_array_ybr[:, :, bias:-bias, :]
        else:
            image_type = 'Tall'
            pixel_array_ybr = pixel_array_ybr[:, bias:-bias, :, :]
    else: image_type = 'Square'
    
    # Send the luminosity ('Y') channel to the LVGLS estimation pipeline
    strain_sequence, cardiac_cycle_framespan, tracked_lv_border_paths = estimate_lv_strain_from_square_gray_frames_array(pixel_array_ybr[:,:,:,0], framerate)

    # Visualize results
    pixel_array_rgb = convert_color_space(dicom_contents.pixel_array, dicom_contents.PhotometricInterpretation, 'RGB')[cardiac_cycle_framespan[0]:cardiac_cycle_framespan[1]]
    for f in range(len(pixel_array_rgb)):
        for p in range(len(tracked_lv_border_paths[f])):
            coords = np.flip(np.round(tracked_lv_border_paths[f][p]).astype('int'))
            if image_type =='Wide': coords[0] += bias
            elif image_type == 'Tall': coords[1] += bias
            cv2.circle(pixel_array_rgb[f], coords, color=(225,225,0), radius = 3, thickness = -1)

    return strain_sequence, pixel_array_rgb

def estimate_lv_strain_from_RGB_frames_array(echo_scan_rgb, framerate):
    '''
    This funection expects a three-channel (RGB) ECHO scan in an array of shape (nframes, height, width, 3), along with its framerate.
    The entire ultrasound scan sector (i.e., the triangle-shape that contains the ultrasound image) should be visible and centered within the frame.
    The function receives the scan and:
        - Converts it to YBR
        - Sends a centered square crop of the luminosity (Y) channel to estimate_lv_strain_from_square_gray_frames_array()
        - Returns the strain sequence and an RGB segment of the ECHO scan for visualization of the lv border tracking
    '''
    
    pixel_array_ybr = convert_color_space(echo_scan_rgb, 'RGB', 'YBR_FULL')
    nframes,height,width,channels = pixel_array_ybr.shape
    
    # Make the image square by cropping the long dimension (at its center) to match the short one
    bias = int(np.abs(width - height)/2)
    if bias != 0:
        if height < width:
            image_type = 'Wide'
            pixel_array_ybr = pixel_array_ybr[:, :, bias:-bias, :]
        else:
            image_type = 'Tall'
            pixel_array_ybr = pixel_array_ybr[:, bias:-bias, :, :]
    else: image_type = 'Square'
    
    # Send the luminosity ('Y') channel to the LVGLS estimation pipeline
    strain_sequence, cardiac_cycle_framespan, tracked_lv_border_paths = estimate_lv_strain_from_square_gray_frames_array(pixel_array_ybr[:,:,:,0], framerate)

    pixel_array_rgb = echo_scan_rgb[cardiac_cycle_framespan[0]:cardiac_cycle_framespan[1]]
    for f in range(len(pixel_array_rgb)):
        for p in range(len(tracked_lv_border_paths[f])):
            coords = np.flip(np.round(tracked_lv_border_paths[f][p]).astype('int'))
            if image_type =='Wide': coords[0] += bias
            elif image_type == 'Tall': coords[1] += bias
            cv2.circle(pixel_array_rgb[f], coords, color=(225,225,0), radius = 3, thickness = -1)

    return strain_sequence, pixel_array_rgb

def estimate_lv_strain_from_square_gray_frames_array(square_echo_scan_y, framerate):
    '''
    The function expects a single-channel (luminosity, or Y-channel only), square ECHO scan in an array of shape (nframes, square_side, square_side), along with its framerate.
    The entire ultrasound scan sector (i.e., the triangle-shape that contains the ultrasound image) should be visible and centered within the square.
    
    The function processes the ECHO scan to:
        - segment the left ventricle (LV)
        - detect a singe cardiac cycle
        - find a path of points along the lv border
        - track the path's points across the cardiac cycle with the Farneback method for optical flow estimation
        - measure the tracked path's length across the cardiac cycle to derive the LV strain sequence

    The function returns the:
        - strain sequence, 
        - framespan (startframe, endframe) of the detected cardiac cycle,
        - the sequence of tracked lv border paths 
    '''

    # Make sure the scan is square and crop 10% off all sides to remove the ECG plot; resize to the preferred image size for tracking
    assert(square_echo_scan_y.shape[1] == square_echo_scan_y.shape[2])

    original_square_side = square_echo_scan_y.shape[1]
    crop_amount = int(original_square_side/10) # 10% was empirically chosen
    square_echo_scan_y_cropped = square_echo_scan_y[:,crop_amount:(original_square_side - crop_amount), crop_amount:(original_square_side - crop_amount)]

    preferred_image_size_for_tracking = (568, 568) # This was chosen based on the dataset of ~30 patients from the Ippokratio Hospital; the optical flow parameters were tuned to this size
    # Some robustness w.r.t. image size has been observed experimentally.
    
    scale_factor = square_echo_scan_y_cropped.shape[1] / preferred_image_size_for_tracking[0] # This will be used to later scale the tracked points coordinates back to the original image size
    # It's not the exact size that matters, but that we are close enough; in any case, resizing to this size is the best we can do to ensure the conditions match 
    if square_echo_scan_y_cropped.shape[1] != preferred_image_size_for_tracking[0]:
        square_echo_scan_y_cropped = np.transpose(square_echo_scan_y_cropped, (1,2,0)) # Change dims order to (height, width, nframes) as required by OpenCV below
        square_echo_scan_y_cropped = cv2.resize(square_echo_scan_y_cropped, preferred_image_size_for_tracking, interpolation=cv2.INTER_LINEAR)
        square_echo_scan_y_cropped = np.transpose(square_echo_scan_y_cropped, (2,0,1))



    # Prepare and feed the scan to the LV segmentation CNN to get the LV mask sequence
    square_echo_scan_y_cropped_transposed = np.transpose(square_echo_scan_y_cropped, (1,2,0)) # Change dims order to (height, width, nframes) as required by OpenCV below
    square_echo_scan_y_cropped_resized = cv2.resize(square_echo_scan_y_cropped_transposed, (112,112), interpolation = cv2.INTER_CUBIC) # Resize all frames to 112x112 as required by the EchoNet models

    square_echo_scan_y_cropped_resized_rgb = np.stack((square_echo_scan_y_cropped_resized, square_echo_scan_y_cropped_resized, square_echo_scan_y_cropped_resized), axis=0) # Turn the single-channel video to a 3-channel one (RGB with all channels equal), as required by the EchoNet models
    square_echo_scan_y_cropped_resized_rgb = np.transpose(square_echo_scan_y_cropped_resized_rgb, (3,1,2,0)) # From (channels, height, width, nframes) to (nframes, height, width, channels)

    lv_mask_sequence = segment_lv('Estimators/LVGLS/echonet_segmentation.onnx', square_echo_scan_y_cropped_resized_rgb)


    
    # Detect and isolate a single cardiac cycle using the LV mask sequence
    lv_areas_sequence = np.sum(lv_mask_sequence, axis=(1,2)) # approximate the LV area at every frame by summing the mask's pixels
    cardiac_cycle_framespan = detect_single_cardiac_cycle(lv_areas_sequence, framerate=framerate, debug=True)
    square_echo_scan_y_cropped = square_echo_scan_y_cropped[cardiac_cycle_framespan[0]:cardiac_cycle_framespan[1]]



    # Process the LV mask at frame 0 to get the LV endocardium border
    initial_lv_mask = lv_mask_sequence[cardiac_cycle_framespan[0]]
    # Smoothen the mask in order to avoid jagged edges and sharp turns which can cause problems in get_path_from_lv_border() later on
    smooth_initial_lv_mask = cv2.medianBlur(initial_lv_mask.astype('uint8'), 13) # 13 is the size of the filter; chosen empirically so that it doesn't distort the overall shape but smooths the edges
    # Get the the outside border of the endocardium, without its bottom part 
    # NOTE: the function below should be renamed to reflect what it actually does
    initial_lv_border = get_lv_border_from_segmentation(smooth_initial_lv_mask)



    '''
    # NOTE: It was experimentally seen that the below segment does not help at all; instead, it worsens the results.
    # We will leave it here commented out in case someone wants to experiment with it
    # Zoom the initial lv border by a small factor so that it actually falls INSIDE the myocardium region; 
    M = cv2.moments((smooth_initial_lv_mask).astype('uint8'))
    cX = int(M["m10"] / M["m00"])
    cY = int(M["m01"] / M["m00"])
    zoom_matrix = cv2.getRotationMatrix2D((cX, cY), angle=0, scale=1.10) # Empirically chosen
    initial_lv_border = cv2.warpAffine(1.0 * initial_lv_border, zoom_matrix, initial_lv_border.shape[1::-1], flags=cv2.INTER_LINEAR)
    initial_lv_border = 1 * (initial_lv_border > 0) # from boolean to number
    '''



    # Resize the initial lv_border to match the (resized) echo scan dimensions
    resized_initial_lv_border = cv2.resize(1.0 * initial_lv_border, preferred_image_size_for_tracking, interpolation=cv2.INTER_LINEAR)
    # Smoothen the resized lv_border in order to avoid jagged edges and sharp turns which can cause problems in get_path_from_lv_border() later on
    smooth_resized_initial_lv_border = cv2.medianBlur((1.0*(resized_initial_lv_border>0)).astype('uint8'), 13) # 13 is the size of the filter; again, chosen empirically so that it doesn't distort the overall shape but smooths the edges
    smooth_resized_initial_lv_border = 1.0 * ( skeletonize(smooth_resized_initial_lv_border, method='lee') > 0 )



    # Sample a set of equidistant points along the lv_border
    smooth_resized_initial_lv_border_path = get_path_from_lv_border([smooth_resized_initial_lv_border.astype('uint8')])[0]
    num_tracked_points = 30 # number of points to track (empirically chosen)
    sampling_step = len(smooth_resized_initial_lv_border_path) // num_tracked_points
    offset = (len(smooth_resized_initial_lv_border_path) % num_tracked_points) // 2 # Offset is the modulus divided by two; to discard points evenly from the start and end of the path
    start = offset
    end = len(smooth_resized_initial_lv_border_path) - offset
    resampled_smooth_resized_initial_lv_border_path = smooth_resized_initial_lv_border_path[start:end:sampling_step]
    

    
    # Remove the first and last points. These lie at the base of the myocardium and are sometimes caught by the valve opening motion, which introduces significant error.
    # NOTE: This is a MAJOR point for future improvement. 
    # It would be better to detect when this happens (e.g., by detecting abnormal patterns in the trajectory of points), and filter out only those cases.
    resampled_smooth_resized_initial_lv_border_path = resampled_smooth_resized_initial_lv_border_path[1:-1]   



    # Calculate the optical flow between consecutive frames of the echo scan using the Farneback method
    # The parameters of the method were chosen empirically in a trial-and-error fashion and by manual visualization of the results on the dataset of ~30 patients from the Ippokratio Hospital
    optical_flows = []
    for i in range(len(square_echo_scan_y_cropped) - 1):
        frame1 = square_echo_scan_y_cropped[i]
        frame2 = square_echo_scan_y_cropped[i+1]
        optical_flows.append(cv2.calcOpticalFlowFarneback(prev=frame1, next=frame2, flow=None, pyr_scale=0.5, levels=3, winsize=41, iterations=5, poly_n=5, poly_sigma=1.1, flags=0))


    # Perform tracking of the lv_border paths (of points) using the calculated optical flows
    tracked_lv_border_paths = tracking_update([resampled_smooth_resized_initial_lv_border_path], optical_flows)
    # Measure strain using the tracked lv_border paths
    strain_sequence = measure_strain(tracked_lv_border_paths)
    # Rescale and pad the tracked lv_border path points (essentially undo the 10% crop and resizing that were performed initially)
    rescaled_padded_tracked_lv_border_paths = [(scale_factor * tcp + crop_amount).astype(int) for tcp in tracked_lv_border_paths]

    return strain_sequence, cardiac_cycle_framespan, rescaled_padded_tracked_lv_border_paths

# Exported pipeline function
def lvgls_estimation_pipeline(dicom_video_rgb,framerate):
    """
    Provided the dicom pixel array, estimate the LVGLS percentage and return that
    along with the video with the segmentation mask applied
    """
    gls_timeseries, masked_cut_video = estimate_lv_strain_from_RGB_frames_array(dicom_video_rgb,framerate)
    return np.nanmin(gls_timeseries)*100,masked_cut_video
