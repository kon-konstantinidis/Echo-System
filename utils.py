# Import General Packages
import numpy as np
import time
import cv2
import base64
import datetime
import io
import json
import pydicom
import os
from flask import request
from pydicom.pixel_data_handlers.util import convert_color_space
from dash.exceptions import PreventUpdate
import matplotlib
matplotlib.use('Agg')  # non-GUI backend to avoid annoying warning message
import matplotlib.pylab as plt




### Utility Functions ###
# General utility functions

def resize_video(video, factor):
    """
    Resizes the video of format (nframes,height,width,3) to (nframes,height/factor,width/factor,3)
    """
    #print("resize_video called to resize ",video.shape," to (",video.shape[1]/factor,",",video.shape[2]/factor,")",sep="")
    nframes = video.shape[0]
    new_height = int(video.shape[1]/factor)
    new_width = int(video.shape[2]/factor)
    channels = video.shape[3]

    video_resized = np.zeros((nframes, new_height, new_width, channels))
    for frame in range(0, nframes):
        #print("At frame",frame,"of",nframes)
        image = video[frame, :, :, :]
        image_resized = cv2.resize(image, (new_width, new_height),  # fx=factor,fy=factor,
                                   interpolation=cv2.INTER_CUBIC)
        video_resized[frame, :, :, :] = image_resized
    return video_resized

def extract_type_index(str_dict):
    """
    Extracts the type and the index properties of the stringified 
    dictionary that is dash.callback_context.triggered[0]['prop_id']
    when pattern matching is used
    """
    #print("extract_type_index called with str_dict:",str_dict)
    # The stringified dictionary is in the format {"index":"index_value","type":"type_value"}.property
    # Find the id's type
    type_value_start = str_dict.index('"type":"') + len('"type":"')
    type_value_end = str_dict.find('"}')
    type_value = str_dict[type_value_start:type_value_end]
    #print("Type of trigger:",type_value)

    # Find the id's index
    index_value_start = str_dict.index('"index":"') + len('"index":"')
    index_value_end = str_dict.find('",')
    index_value = str_dict[index_value_start:index_value_end]
    #print("Index of trigger:",index_value)
    return (type_value,index_value)

def create_study_summary(patient_general_info, patient_background_info, patient_other_notes):
    """
    Given the patient's general info, background info, and other notes, this function
    creates the study's summary dict
    """
    summary = {}

    # Add study duration
    username = request.authorization['username']
    log_dict_path = './Sessions/' + username + '/log'
    with open(log_dict_path, 'r') as fp:
            log_dict = json.load(fp)
    
    summary['Study Info'] = {
        "Study Start":log_dict['user actions']["0"]['timestamp'],
        "Study End":log_dict['user actions'][str(len(log_dict['user actions'])-1)]['timestamp']
    }
    # Add patient info
    summary['patient'] = {
        'General Information':patient_general_info,
        'Background Information':patient_background_info,
        'Other Notes':patient_other_notes
    }

    # Add the performed estimations
    # Get the estimations dictionary file
    estimations_dict_path = './Sessions/' + username + '/estimations'
    if (not os.path.exists(estimations_dict_path)):
        # This is the first estimation saved, create the estimations dictionary
        estimations_dict = {}
    else:
        with open(estimations_dict_path, 'r', encoding='utf8') as fp:
            estimations_dict = json.load(fp)
    if (len(estimations_dict)==0):
        estimations_dict = "No estimations performed."
    summary['Estimations performed'] = estimations_dict

    return summary

def prep_video_for_playback(pixel_array_rgb,resize_factor):
    """
    Converts pixel_array_rgb to a list of flattened 1-D arrays 
    after resizing the video and adding an opacity channel

    Returns the imagePixelsList
    """
    
    def rgb2rgba(rgb, A):
        # Transforms an RGB picture into an RGBA one (adds opacity channel)
        rows, cols, ch = rgb.shape
        rgba = A*np.ones(shape=(rows, cols, 4))
        for i in range(0, rows):
            for j in range(0, cols):
                for k in range(0, 4):
                    if (k == 3):
                        continue
                    rgba[i, j, k] = rgb[i, j, k]
        return rgba

    processing_start = time.time()
    rgb_resized = resize_video(pixel_array_rgb, resize_factor)
    # print("rgb_resized:",rgb_resized.shape)

    # rgb/rgb_short all are (nframes,height,width,channels)
    video = rgb_resized
    image_pixels_list = [0]*video.shape[0]
    for i in range(0, video.shape[0]):
        rgbPic = video[i, :, :, :]
        rgbaPic = rgb2rgba(rgbPic, 255)
        flat_rgbaPic = rgbaPic.flatten(order='C')
        image_pixels_list[i] = flat_rgbaPic
    processing_end = time.time()
    processing_time = processing_end-processing_start
    print("Video processing time: ", processing_time)
    return(image_pixels_list)


######### File Handlers #######
# Bellow are all function that deal with reading, storing, deleting or updating data from the filespace

def handle_upload(list_of_contents, list_of_filenames):
    """
    Handles the user's uploaded files
    Returns the new thumbnails (as a 3-element tuple to be later converted into a thumbnail), a list of the uploaded files that were not accepted because they were already
    uploaded and a list of the uploaded files that were not accepted because they belong to a different patient
    than the one currently being studied
    """

    # Since the callback's output is already in the layout, prevent_initial_call=True will not prevent the callback from being executed
    # when its input is added to the layout (the dcc.Upload element of the upload window). Thus, there is a need for a check
    if list_of_contents is None:
        raise PreventUpdate

    username = request.authorization['username']
    # Check whether this is the beggining of the study and the log should be initialized
    log_dict_filepath = './Sessions/' + username + '/log'
    init_log = False
    if (not os.path.exists(log_dict_filepath)):
        init_log = True
    
    already_uploaded_files = []
    diff_patient_files = []
    thumbnail_tuples = []
    for content, filename in zip(list_of_contents, list_of_filenames):
        #print('handle_upload has file: ', filename)

        # Check if the file has been uploaded before by the current active user
        if (is_already_uploaded(filename)):
            print("File",filename,"has been already uploaded before")
            already_uploaded_files.append(filename)
            continue
        
        content_type, content_string = content.split(',')

        # Decode file bytes and read as DICOM file
        decoded_contents = base64.b64decode(content_string)
        ds = pydicom.dcmread(io.BytesIO(decoded_contents))

        # Check if the uploaded file belongs to the currently active patient (can only study one patient at a time)
        if (is_patient_different(ds)):
            print("File",filename,"belongs to a different patient than the one currently studied")
            diff_patient_files.append(filename)
            continue

        # File is accepted
        if(init_log):
            write_to_log('current patient ID',ds.PatientID)
            print("Log Initialized")
            init_log = False
        write_to_log('user actions',filename+" uploaded")
        # Add scans thumbnail in the scans section
        thumbnail_text = filename
        # In case AcquisitionDateTime is not provided, catch the resulting error from trying to access it
        try:
            thumbnail_text = thumbnail_text + ": " + ds.AcquisitionDateTime[6:8] + "/" + ds.AcquisitionDateTime[4:6] + "/" + \
                ds.AcquisitionDateTime[0:4] + " " + ds.AcquisitionDateTime[8:10] + ":" + \
                ds.AcquisitionDateTime[10:12] + ":" + \
                ds.AcquisitionDateTime[12:14]
        except:
            thumbnail_text = thumbnail_text + ": AcquisitionDateTime Not Found"
        # In case the pixel_array is a single image (not a video) or something else of not acceptable shape, catch that here
        if (len(ds.pixel_array.shape) == 4):
            # pixel_array is a video
            thumbnail_input = ds.pixel_array[0, :, :, :]
        elif (len(ds.pixel_array.shape) == 3):
            # pixel_array is a single image
            thumbnail_input = ds.pixel_array[:, :, :]
        else:
            # pixel_array is ?
            print("Error, pixel_array shape not accepted/recognized.")
            thumbnail_input = 250*np.ones((420, 650, 3))
        
        # Open the file_indexes dictionary and get the last index for this scan
        index_dict_path = './Sessions/' + username + '/file_indexes'
        if (not os.path.exists(index_dict_path)):
            # This is the first uploaded scan, create the indexes dictionary
            index_dict = {}
        else:
            with open(index_dict_path, 'r') as fp:
                index_dict = json.load(fp)
                
        index_dict_list = list(index_dict) # converts the dict's keys to a list
        if (len(index_dict_list) == 0):
            last_index = -1
        else:
            last_index = int(index_dict_list[-1])

        rgb_image_pixels = convert_color_space(thumbnail_input, "YBR_FULL", "RGB")
        first_frame_fig = plt.imshow(rgb_image_pixels)
        first_frame_fig.axes.get_xaxis().set_visible(False)
        first_frame_fig.axes.get_yaxis().set_visible(False)
        image_bytes = io.BytesIO()
        plt.savefig(image_bytes, format='png', bbox_inches='tight', pad_inches=0)
        plt.close()
        img_encoding = base64.b64encode(image_bytes.getvalue()).decode()
        img_b64 = "data:image/png;base64," + img_encoding
        thumbnail_tuples.append((img_b64, last_index+1, thumbnail_text))

        # Also save the file to this user's directory (server-side)
        save_ds(ds, filename, last_index+1)

    return (thumbnail_tuples,already_uploaded_files,diff_patient_files)

def fetch_fields(filename, get_pixel_array=False, get_datetime=False, get_framerate=False):
    """
    Returns specific fields from the dicom file specified as filename, in the order specified in the arguments
    
    :param get_pixel_array (Boolean) Return the pixel_array?
    :param get_datetime (Boolean) Return the acquisition datetime?
    :param get_framerate (Boolean) Return the recommended display framerate?
    """
    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms/'+filename
    ds = pydicom.dcmread(filepath)
    dateTime = ds.AcquisitionDateTime[6:8] + "/" + ds.AcquisitionDateTime[4:6] + "/" + \
                ds.AcquisitionDateTime[0:4] + " " + ds.AcquisitionDateTime[8:10] + ":" + \
                ds.AcquisitionDateTime[10:12] + ":" + \
                ds.AcquisitionDateTime[12:14]
    framerate = ds.RecommendedDisplayFrameRate
    
    return_values = []
    if (get_pixel_array):
        return_values.append(convert_color_space(ds.pixel_array,"YBR_FULL", "RGB"))
    if(get_datetime):
        dateTime = ds.AcquisitionDateTime[6:8] + "/" + ds.AcquisitionDateTime[4:6] + "/" + \
                ds.AcquisitionDateTime[0:4] + " " + ds.AcquisitionDateTime[8:10] + ":" + \
                ds.AcquisitionDateTime[10:12] + ":" + \
                ds.AcquisitionDateTime[12:14]
        return_values.append(dateTime)
    if(get_framerate):
        return_values.append(framerate)

    return return_values

def is_already_uploaded(uploaded_filename):
    """
    Checks whether the input filename is already in the current user's Dicoms directory
    Returns True if it is, False otherwise

    toDo: Might need to implement the check with something other than the filename
    """
   
    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms'
    for fname in os.listdir(filepath):
        if (fname == uploaded_filename):
            return True
    return False

def is_patient_different(ds):
    """
    Check's if the patient's ID and name in the provided ds file match
    the patient's ID and name whose DICOMs are already uploaded
    Returns True if the patient is different, False if its the same patient
    
    NOTE: If this is the first uploaded file in the user's empty directory,
    the function returns True.
    """
    log_dict = {}
    username = request.authorization['username']
    log_dict_filepath = './Sessions/' + username + '/log'
    if (os.path.exists(log_dict_filepath)):
        with open(log_dict_filepath, 'r') as fp:
            log_dict = json.load(fp)
    
    try:
        if (log_dict['current patient ID'] != ds.PatientID):
            return True
    except:
        # If the above check threw an error, it is because the current patient ID field does not exist
        # Hence, there is no current patient, so accept this one
        return False

def save_ds(ds_file, filename, file_index):
    """
    Stores the upload dicom scan in the current user's DICOMs filepath
    and updates the index-mapping dictionary
    """

    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms/' + filename
    ds_file.save_as(filepath)

    # Also update the index-mapping dictionary to 
    # what index this filename corresponds to
    index_dict_path = './Sessions/' + username + '/file_indexes'
    if (not os.path.exists(index_dict_path)):
        # This is the first uploaded scan, create the indexes dictionary
        index_dict = {}
    else:
        with open(index_dict_path, 'r') as fp:
            index_dict = json.load(fp)

    # Add the current index:filename entry         
    index_dict[str(file_index)] = filename
    #print(index_dict)

    # Save the indexes dictionary
    with open(index_dict_path, 'w') as fp:
        json.dump(index_dict, fp, indent=4, sort_keys=True)
    
def load_session():
    """
    Load the current user's directory (uploaded files, etc)
    """
    # toDo: Should  it load more than just load dicom scans? -- LATER

    # Check whether there are scans to be loaded
    username = request.authorization['username']
    index_dict_path = './Sessions/' + username + '/file_indexes'
    if (not os.path.exists(index_dict_path)):
        return []


    # Go to the file_indexes dict and get the order in which the files should be loaded
    with open(index_dict_path, 'r') as fp:
            index_dict = json.load(fp)

    # Load the scans and create the thumbnails
    thumbnail_tuples = []
    for scan_index in index_dict:
        filename = index_dict[scan_index]
        filepath = './Sessions/' + username + '/Dicoms/' + filename
        thumbnail_text = filename

        ds = pydicom.dcmread(filepath)
        try:
            thumbnail_text = thumbnail_text + ": " + ds.AcquisitionDateTime[6:8] + "/" + ds.AcquisitionDateTime[4:6] + "/" + \
                ds.AcquisitionDateTime[0:4] + " " + ds.AcquisitionDateTime[8:10] + ":" + \
                ds.AcquisitionDateTime[10:12] + ":" + \
                ds.AcquisitionDateTime[12:14]
        except:
            thumbnail_text = thumbnail_text + ": AcquisitionDateTime Not Found"
        # In case the pixel_array is a singly image (not a video) or something else of not acceptable shape, catch that here
        if (len(ds.pixel_array.shape) == 4):
            # pixel_array is a video
            thumbnail_input = ds.pixel_array[0, :, :, :]
        elif (len(ds.pixel_array.shape) == 3):
            # pixel_array is a single image
            thumbnail_input = ds.pixel_array[:, :, :]
        else:
            # pixel_array is ?
            print("Error, pixel_array shape not accepted/recognized.")
            thumbnail_input = 250*np.ones((420, 650, 3))

        rgb_image_pixels = convert_color_space(thumbnail_input, "YBR_FULL", "RGB")
        first_frame_fig = plt.imshow(rgb_image_pixels)
        first_frame_fig.axes.get_xaxis().set_visible(False)
        first_frame_fig.axes.get_yaxis().set_visible(False)
        image_bytes = io.BytesIO()
        plt.savefig(image_bytes, format='png', bbox_inches='tight', pad_inches=0)
        plt.close()
        img_encoding = base64.b64encode(image_bytes.getvalue()).decode()
        img_b64 = "data:image/png;base64," + img_encoding
        thumbnail_tuples.append((img_b64, scan_index, thumbnail_text))

    return thumbnail_tuples

def clear_all_dicom_files():
    """
    Deletes all of the uploaded dicom files of the current user.\n
    Also empties the indexes dictionary.
    """
    # May be needed to be called with the username
    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms/'
    for fname in os.listdir(filepath):
        os.remove(os.path.join(filepath, fname))

    # Also clear the file_indexes dictionary
    index_dict_path = './Sessions/' + username + '/file_indexes'
    if (os.path.exists(index_dict_path)):
        os.remove(index_dict_path)

def delete_uploaded_dicom(index):
    """
    Given the index of clicked thumbnail, this function deletes from 
    the user's DICOMs directory the corresponding DICOM file
    """
    ## Delete the entry from the file_indexes dictionary
    username = request.authorization['username']
    index_dict_path = './Sessions/' + username + '/file_indexes'
    with open(index_dict_path, 'r') as fp:
        index_dict = json.load(fp)
    
    # Delete the corresponding entry
    filename = index_dict.pop(index)
    write_to_log('user actions',filename+" deleted")

    # Re-store the mutated dictionary
    with open(index_dict_path, 'w') as fp:
        json.dump(index_dict, fp, indent=4, sort_keys=True)

    ## Also delete the actual DICOM file
    dicom_filepath = './Sessions/' + username + '/Dicoms/' + filename
    os.remove(dicom_filepath)

def write_to_log(category,text):
    """
    Writes the action performed (must be a string) in the current user's log.
    Adds the system time the action was performed.
    """
    log_dict = {}
    username = request.authorization['username']
    log_dict_filepath = './Sessions/' + username + '/log'
    if (os.path.exists(log_dict_filepath)):
        with open(log_dict_filepath, 'r') as fp:
            log_dict = json.load(fp)

    if (category == "user actions"):
        new_log_key = len(log_dict['user actions'])
        entry = {
            "action": text,
            "timestamp": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        log_dict['user actions'][str(new_log_key)] = entry
    elif (category == "current patient ID"):
        # This key-value pair should only be called to be set when the study first starts
        # In any other cases, changing the current patient ID is erroneous
        if(len(log_dict) > 0):
            print("LOG ERROR: Attempting to set patient ID on an ongoing study!")
        else:
            log_dict['current patient ID'] = text
            log_dict['user actions'] = {}
    else:
        print("Invalid log category entry")
    
    # Update the log dictionary
    with open(log_dict_filepath, 'w') as fp:
        json.dump(log_dict, fp, indent=4)

def delete_log():
    """
    Deletes the log file(to be used as part of "End Of Study")
    """
    username = request.authorization['username']
    log_dict_filepath = './Sessions/' + username + '/log'
    if (os.path.exists(log_dict_filepath)):
        os.remove(log_dict_filepath)

def get_filename_from_index(scan_index):
    """
    Provided the scan index, return the corresponding filename from
    the file_indexes dictionary
    """
    username = request.authorization['username']
    index_dict_path = './Sessions/' + username + '/file_indexes'
    with open(index_dict_path, 'r') as fp:
        index_dict = json.load(fp)
    return index_dict[str(scan_index)]

def save_estimation(estimation_type, filename, estimation_value, exec_time, notes):
    """
    Saves the estimation of type estimation_type performed on file filename along
    with whatever additional notes (as a string) the user inserted in the user's
    estimation's directory
    """
    # Create new entry
    new_entry = {
        "File Used":filename,
        "Estimation Type":estimation_type,
        "Estimation Value":estimation_value,
        "Estimation Time":exec_time,
        "Notes":notes
    }
    # Get the estimations dictionary file
    username = request.authorization['username']
    estimations_dict_path = './Sessions/' + username + '/estimations'
    if (not os.path.exists(estimations_dict_path)):
        # This is the first estimation saved, create the estimations dictionary
        estimations_dict = {}
    else:
        with open(estimations_dict_path, 'r', encoding='utf8') as fp:
            estimations_dict = json.load(fp)
    
    # Assign new entry to the estimations dictionary
    new_estimation_key = len(estimations_dict)
    estimations_dict[str(new_estimation_key)] = new_entry
    
    # Update the estimations dictionary
    with open(estimations_dict_path, 'w', encoding='utf8') as fp:
        json.dump(estimations_dict, fp, indent=4, ensure_ascii=False)
    
def delete_estimations():
    """
    Deletes the estimations file (as part of the end_of_study - reset workspace use case)
    """
    username = request.authorization['username']
    estimations_dict_filepath = './Sessions/' + username + '/estimations'
    if (os.path.exists(estimations_dict_filepath)):
        os.remove(estimations_dict_filepath)

def get_estimations_dict():
    """
    Get the estimations dictionary file
    """
    username = request.authorization['username']
    estimations_dict_path = './Sessions/' + username + '/estimations'
    if (not os.path.exists(estimations_dict_path)):
        # This is the first estimation saved, create the estimations dictionary
        estimations_dict = {}
    else:
        with open(estimations_dict_path, 'r', encoding='utf8') as fp:
            estimations_dict = json.load(fp)
    return estimations_dict

def is_session_active():
    """
    Checks whether there is a currently active user session via the existance (or not) of the session's log
    """
    username = request.authorization['username']
    log_dict_filepath = './Sessions/' + username + '/log'
    if os.path.exists(log_dict_filepath):
        return True
    return False

def is_docker():
    """
    Checks whether the app is running inside a container.
    Credit to: https://stackoverflow.com/questions/43878953/how-does-one-detect-if-one-is-running-within-a-docker-container-within-python/48710609#48710609
    """
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )