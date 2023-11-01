import cv2
import numpy as np
import onnxruntime
import scipy
from scipy.signal import savgol_filter
from scipy.interpolate import splprep, splev

import astropy.units as u

from matplotlib import pyplot as plt
from fil_finder import FilFinder2D

import heartpy as hp

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

def detect_single_cardiac_cycle(endo_areas_sequence, framerate, debug=False):
    '''
    The function receives a sequence of values representing areas of the LV endocardium at each frame of an ECHO scan.
    The sequence is expected to be AT LEAST 3 CARDIAC CYCLES long.

    In our LVGLS pipeline, we use a CNN to generate binary segmentation of the LV at each frame of the ECHO scan.
    The LV area at each frame is then estimated as the pixel-wise sum of the binary segmentation mask.

    The function smooths the input sequence using the DCT to estimate the mean and maximum half cardiac cycle length in the sequence,
    , and detects peaks that are distanced by at least the maximum half cycle length. The peaks mark end-diastole moments. 

    To detect a single cardiac cycle, we select the first detected peak that is distanced from frame 0 by at least the mean half cycle length.
    This way we may ignore a peak that is near the beginning of the sequence, but we make sure that the selected peak will be an end-diastole moment.
    
    '''

    endo_areas_sequence = np.asarray(
        endo_areas_sequence)  # (not sure if needed) convert to np array in case it isn't one already

    '''
    # NOTE: Below, the DCT has been replaced by lowpass filtering with heartpy. We leave it here just for reference.

    endo_areas_dct = scipy.fft.dct(endo_areas_sequence)
    dct_threshold = sorted(abs(endo_areas_dct))[
        round(len(endo_areas_dct) * 0.97)]  # define the threshold at the 97th percentile of dct magnitudes (chosen empirically)
    endo_areas_dct[
        abs(endo_areas_dct) < dct_threshold] = 0  # zero all components below threshold (keep the DCT terms with magnitude less than the biggest 5%)
    endo_areas_dct[0] = 0  # remove DC component, mean is zero
    endo_areas_filtered = scipy.fft.idct(endo_areas_dct)  # invert DCT, get filtered signal
    '''

    endo_areas_filtered = hp.filter_signal(endo_areas_sequence, cutoff = 3, sample_rate = framerate, order = 3, filtertype='lowpass')
    endo_areas_filtered_mean = np.mean(endo_areas_filtered)
    endo_areas_filtered = endo_areas_filtered - endo_areas_filtered_mean

    zero_crossings = np.where(np.diff(np.sign(endo_areas_filtered)))[0]  # this detects sign changes (so zero crossings) of the filtered signal
    half_cycle_lengths1 = (zero_crossings - np.roll(zero_crossings, 1)) #   # the number of frames from each zero crossing to the next
    half_cycle_lengths = [item for item in half_cycle_lengths1 if item >= 0]
    max_half_cycle_length = max(half_cycle_lengths) # This will be used as the minimum acceptable distance between peaks detected by scipy later
    mean_half_cycle_length = np.mean(half_cycle_lengths) # This will be used as the minimum number of frames before a peak can be considered as end-diastole (to filter peaks early in the sequence that might not be actual peaks)

    endo_areas_mean = np.mean(endo_areas_sequence)

    end_diastole_frames, _ = scipy.signal.find_peaks(endo_areas_sequence, height=endo_areas_mean,
                                                     distance=max_half_cycle_length)
    
    for i in range(len(end_diastole_frames)): # Iterate through all end_diastole_frames 
        if end_diastole_frames[i] >= mean_half_cycle_length: break # stop iterating as soon as an entry >= mean_half_cycle_length is found
    cycle_begin = end_diastole_frames[i]
    # We now have set the first end-diastole frame as the beginning of the cardiac cycle. 
    # We check if another end-diastole has been detected after that. 
    if i+1 <= len(end_diastole_frames): cycle_end = end_diastole_frames[i+1] # If yes, we end the cycle there
    else: cycle_end = len(endo_areas_sequence) - 1 # If not, we end the cycle at the end of the scan.

    cardiac_cycle_frames = [cycle_begin, cycle_end]

    if debug:
        plt.figure()
        plt.plot(endo_areas_sequence)
        plt.plot(cardiac_cycle_frames, endo_areas_sequence[cardiac_cycle_frames], 'o')
        plt.plot(max_half_cycle_length, endo_areas_mean, '*')
        plt.plot(mean_half_cycle_length, endo_areas_mean, 'x')
        plt.plot(endo_areas_filtered + endo_areas_mean)
        plt.axhline(endo_areas_filtered_mean)

    return cardiac_cycle_frames

def get_lv_border_from_segmentation(binary_mask):

    b = binary_mask.astype(np.uint8)

    i = np.squeeze(cv2.findContours(b, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[0][0])
    image = np.zeros((112, 112))
    image[i[:, 0], i[:, 1]] = 1
    image = image.astype('uint8')
    image = np.transpose(image)

    kernel = np.array(([-1, -1],
                       [1, 1],
                       [-1, -1]), dtype="int")

    # ---------------FOR THE BOTTOM CURVES----------#
    # kernel1 = np.array((
    #     [-1, -1, 1],
    #     [-1, 1, -1],
    #     [1, -1, -1]), dtype="int")
    #
    # kernel2 = np.array((
    #     [1, -1, -1],
    #     [-1, 1, -1],
    #     [-1, -1, 1]), dtype="int")

    # hitormiss1 = cv2.morphologyEx(image, cv2.MORPH_HITMISS, kernel1)
    # not_hitormiss1 = cv2.bitwise_not(hitormiss1)
    # not_hitormiss1[0:55, :] = 1
    # final1 = cv2.bitwise_and(image, not_hitormiss1)

    # hitormiss2 = cv2.morphologyEx(final1, cv2.MORPH_HITMISS, kernel2)
    # not_hitormiss2 = cv2.bitwise_not(hitormiss2)
    # not_hitormiss2[55:112, :] = 1
    # final2 = cv2.bitwise_and(final1, not_hitormiss2)

    # ----------FOR THE BOTTOM LINES-----------#

    hitormiss = cv2.morphologyEx(image, cv2.MORPH_HITMISS, kernel)
    not_hitormiss = cv2.bitwise_not(hitormiss)
    not_hitormiss[0:55, :] = 1
    final = cv2.bitwise_and(image, not_hitormiss)

    fil = FilFinder2D(final, distance=250 * u.pc, mask=final)
    fil.preprocess_image(flatten_percent=85)
    fil.create_mask(border_masking=True, verbose=False,
                    use_existing_mask=True)
    fil.medskel(verbose=False)
    fil.analyze_skeletons(branch_thresh=40 * u.pix, skel_thresh=40 * u.pix, prune_criteria='length')

    sth = np.array(fil.skeleton)

    return sth 

def findPathBwTwoPoints(k, start, end):

    # All 8 directions
    delta = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]

    bfs = list()

    bfs.append(tuple(start))

    i = 0

    # Look all 8 directions for a good path
    while len(bfs) > 0:
        if bfs[i] == tuple(end):
            break
        x, y = bfs[i]
        for dy, dx in delta:
            yy, xx = y + dy, x + dx
            if k[xx][yy] == 1.0:
                bfs.append((xx, yy))
                k[x][y] = 0
                i = i + 1
    return np.asarray(bfs)

def get_path_from_lv_border(lv_borderList):

    lv_border_PathList = list()

    i = 0

    for lv_border in lv_borderList:
        img_conv = cv2.filter2D((lv_border).astype(np.uint8), -1, np.ones((3, 3)))  #
        img_conv = img_conv * (lv_border)
        img_tips = img_conv == 2
        tips = np.array(np.nonzero(img_tips)).T

        start, end = tips[1, :], tips[0, :]

        lv_border_PathList.append(findPathBwTwoPoints(lv_border, start, end))

    return lv_border_PathList

def tracking_update(lv_border_PathList, vectorFieldList):
    lv_border = lv_border_PathList[0]

    new_lv_border_path_list = list()
    new_lv_border_path_list.append(lv_border)

    for vectorFieldTest in vectorFieldList:
        # IF FLOW IS IN (DIRECTION, WIDTH, HEIGHT) SHAPE DO THIS
        if vectorFieldTest.shape[0] == 2:
            vectorFieldTest = np.transpose(vectorFieldTest, (1, 2, 0))
        # vectorFieldTest = np.transpose(vectorFieldTest, (1, 2, 0))
        pixelDisplacement = []
        for points in lv_border:
            x = round(points[0])
            y = round(points[1])
            pixelDisplacement.append(vectorFieldTest[x, y, :])

            # IF FLOW IS IN (DIRECTION, WIDTH, HEIGHT) SHAPE DO THIS
            # pixelDisplacement.append(vectorFieldTest[:, x, y])
        pixelDisplacement = np.array(pixelDisplacement)
        x_dis = pixelDisplacement[:, 1]
        y_dis = pixelDisplacement[:, 0]
        dis = np.transpose(np.stack((x_dis, y_dis)))
        lv_border = lv_border + dis
        new_lv_border_path_list.append(lv_border)

    return new_lv_border_path_list

def measure_strain(lv_border_PathList, ed_frame = 0):
    lv_borderLengthList = []

    for array in lv_border_PathList:
        # Fit a smooth spline to the lv_border path and subsample it, and measure the arc length in the subsampled path.
        # This helps alleviate the slight zigzag pattern that may occur between points as tracking progresses and neighboring points move in slightly different directions.
        # This zigzag pattern introduces error because it leads to false estimation of the lv_border length (a zigzag path is longer than a straight path).
        tck, u = splprep(array.T, u=None, s=0.0, per=0)
        u_new = np.linspace(u.min(), u.max(), 10)
        new_coords = np.transpose(np.array(splev(u_new, tck, der=0)))

        lv_borderLengthList.append(cv2.arcLength(curve=new_coords.astype(int), closed=False))

    strain_sequence = []
    for length in lv_borderLengthList:
        strain_sequence.append((length - lv_borderLengthList[ed_frame]) / lv_borderLengthList[ed_frame])

    return strain_sequence
