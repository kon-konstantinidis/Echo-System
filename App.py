# Import General Packages
import json
import os
import dash
import dash_auth
import pydicom
from dash import ALL, Dash, Input, Output, State
from dash.exceptions import PreventUpdate
from flask import request
import time

# Importing Development Modules
from Estimators.LVEF.lvef import lvef_estimation_pipeline
from Estimators.LVGLS.estimate_lvgls import lvgls_estimation_pipeline
from layout_servers import *
from utils import *
import cvp

# Keep this out of source code repository - save in a file or a database
valid_username_password_pairs = {
    'kon': '123',
    'kon2': '123'
}

# Create the Sessions directories for the above users
if (not os.path.exists('./Sessions')):
    os.mkdir('./Sessions')
for user in valid_username_password_pairs.keys():
    user_dir = './Sessions/' + user
    if (not os.path.exists(user_dir)):
        os.mkdir(user_dir)
        os.mkdir(user_dir+'/Dicoms')

external_stylesheet = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__,title="ECHO App")
app.layout = serve_homepage_layout
app.config.suppress_callback_exceptions = False

auth = dash_auth.BasicAuth(
    app,
    valid_username_password_pairs
)


@app.callback(
    Output('patient_window_first_name','value'),
    Output('patient_window_last_name','value'),
    Output('patient_window_dob','value'),
    Output('patient_window_gender','value'),
    Output('patient_background_info','value'),
    Output('patient_info_other_notes','value'),
    Input('scan_thumbnails','children'),
    Input({'type':'end_of_study_window','index':ALL},'n_clicks'),
    State("patient_background_info","value"),
    State("patient_info_other_notes","value"),
    prevent_initial_call = True
)
def patient_info_master(scan_thumbnails_children, reset_workspace_button_nclicks, p_background_info, p_other_notes):
    """
    When a dicom file is loaded, this callback is executed and updates the general information of the patient,
    if this is the first dicom file uploaded (marking the beggining of a study). 
    On the other hand, when the last dicom file is deleted along with the study log (study has ended),
    this callback resets the information of the patient.
    """
    print("-> patient_info_master fired")

    # Stringified Dictionary
    str_dict = dash.callback_context.triggered[0]['prop_id']
    print("-->",str_dict)
    
    if (str_dict == "scan_thumbnails.children"):
        # Get the current user's directory
        username = request.authorization['username']
        log_filepath = './Sessions/' + username + '/log'
        dicoms_filepath = './Sessions/' + username + '/Dicoms/'
        p_name = ""
        p_last_name = ""
        p_dob = ""
        p_gender= ""
        # If we are in the middle of an ongoing study and there are dicom files uploaded,
        # load and display the desired patient info
        dicoms_dir = os.listdir(dicoms_filepath)
        if (os.path.exists(log_filepath) and len(dicoms_dir)>0 ):
            # If there is at least one dicom, load the first one and grab the info
            fname = dicoms_dir[0]
            ds = pydicom.dcmread(dicoms_filepath+fname)
            p_name,p_last_name = str(ds.PatientName).split("^")
            p_dob = str(ds.PatientBirthDate) # str(YYYYMMDD)
            p_dob = p_dob[-2:] + '/' + p_dob[-4:-2] + '/' + p_dob[0:4]
            p_gender = str(ds.PatientSex)
            if (p_gender=="M"):
                p_gender="Male"
            elif (p_gender=="F"):
                p_gender="Female"
            elif (p_gender=="O"):
                # Are we really doing this?
                p_gender="Other" 
        elif(os.path.exists(log_filepath) and len(dicoms_dir)==0):
            # There is an ongoing study, there just aren't any dicom files right now
            raise PreventUpdate
        # The initiallized and now returned strings are either empty (e.g. "") or
        # they have the desired values
        return (p_name,p_last_name,p_dob,p_gender,p_background_info,p_other_notes)

    # Else, the reset_workspace_button must have been pressed, confirm it and erase all fields
    type_value, index_value = extract_type_index(str_dict)
    if (type_value == 'end_of_study_window' and index_value == 'reset_workspace_button'):
        print("---> Resetting patient info",flush=True)
        return("","","","","","")
    if (type_value == 'end_of_study_window' and not index_value == 'reset_workspace_button'):
        # We only care about the reset_workspace_button of the end_of_study_window, ignore the rest
        print("---> Prevent Update",flush=True)
        raise PreventUpdate

    # Callback trigger not recognized
    print("---> patient_info_master fired but trigger not recognined:\n",dash.callback_context.triggered,flush=True)
    raise PreventUpdate


@app.callback(
    Output('patient_info_window', 'style'),
    Input({'type':'patient_info_window_button','index':ALL}, 'n_clicks'),
    State('patient_info_window', 'style'),
    prevent_initial_call=True
)
def patient_info_window_master(button_nclicks, patient_info_window_style):
    """
    Manages patient info window, namely making it visible and invisible 
    """
    print("-> patient_info_window_master fired")
    print('-->',dash.callback_context.triggered)

    # Stringified Dictionary
    str_dict = dash.callback_context.triggered[0]['prop_id']
    type_value, index_value = extract_type_index(str_dict)
    #print("type:",type_value,"  index:",index_value)
    
    if (type_value == "patient_info_window_button" and index_value == "display_window_button"):
        print("---> Displaying patient info",flush=True)
        patient_info_window_style['display'] = 'block'
        return patient_info_window_style

    if (type_value == "patient_info_window_button" and index_value == "X_button"):
        print("---> Hiding patient info",flush=True)
        patient_info_window_style['display'] = 'none'
        return patient_info_window_style
    
    # Callback trigger not recognized
    print("---> patient_info_window_master fired but trigger not recognined:\n",dash.callback_context.triggered,flush=True)
    raise PreventUpdate


@app.callback(
    Output('settings_window', 'style'),
    Input({'type':'settings_window_button','index':ALL}, 'n_clicks'),
    State('settings_window', 'style'),
    prevent_initial_call=True
)
def settings_window_master(button_nclicks, settings_window_style):
    print("-> settings_window_master fired")
    print('-->',dash.callback_context.triggered)

    # Stringified Dictionary
    str_dict = dash.callback_context.triggered[0]['prop_id']
    type_value, index_value = extract_type_index(str_dict)
    #print("type:",type_value,"  index:",index_value)
    
    if (type_value == "settings_window_button" and index_value == "display_window_button"):
        print('---> Displaying settings window',flush=True)
        settings_window_style['display'] = 'block'
        return settings_window_style
    
    if (type_value == "settings_window_button" and index_value == "X_button"):
        print('---> Hiding settings window',flush=True)
        settings_window_style['display'] = 'none'
        return settings_window_style

    # Callback trigger not recognized
    print("---> settings_window_master fired but trigger not recognined:\n",dash.callback_context.triggered,flush=True)
    raise PreventUpdate


@app.callback(
    # Output to the scan thumbnails section to update them after uploads/deletions
    Output('scan_thumbnails', 'children'),
    # Output to the hidden uploaded file warning div to possibly display warnings messages to the user
    Output('uploaded_file_warning_div','children'),
    Output('uploaded_file_warning_div','style'),
    Input({'type': 'clear_all_scans_button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'scan_remove_button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'uploaded_file_warning_div', 'index': ALL},'n_clicks'),
    Input({'type': 'file_upload', 'index': ALL}, 'contents'),
    # Listen to this button as well so scans are cleared when the study ends
    Input({'type':'end_of_study_window','index':ALL},'n_clicks'),
    State({'type': 'file_upload', 'index': ALL}, 'filename'),
    State('scan_thumbnails', 'children')
)
def uploaded_scans_master(n_clicks_clear_scans, n_clicks_remove_scan_button, warning_div2_X_button_nclicks, list_of_contents, end_of_study_window_button_n_clicks, list_of_filenames, scan_thumbnails_children):
    """
    This callback handles the elements on the upload window, once it is served in the hidden_div.
    At initial call (the app's page is loaded), the callback loads the user's previous session.
    After that, it handles the user's uploads.
    This callback also controls the output of the uploaded_file_warning_div, which is a hidden div used to
    output messages to the user regarding the files being uploaded.
    """
    print('-> uploaded_scans_master callback fired') #with dash.callback_context.triggered:',dash.callback_context.triggered)
    #print('-->',dash.callback_context.triggered)
    # stringified dict
    str_dict = dash.callback_context.triggered[0]['prop_id']
    print("-->",str_dict)

    if (str_dict == '.' and len(scan_thumbnails_children) == 0):
        print("---> Loading Sessions",flush=True)
        return (load_session_thumbnails(),[],{'display':'none'})
    
    if (str_dict == '.' and len(scan_thumbnails_children) > 0 and not is_session_active()):
        # Triggered after the reset_workspace button's actions, so we again return [] to empty the scans
        # The rest of the workspace is already dealt with
        print("--> After Reset Workspace button")
        return([],[],{'display':'none'})
    

    # If the upload_window was just closed, this callback will fire with a prop_id = '.' (why it's a dot is unknown)
    # So, it turns out that the dot trigger is Dash's way to represent an empty callback trigger
    if (str_dict == '.'):
        #print(dash.callback_context.)
        print("---> PreventUpdate, dot trigger",flush=True)
        raise PreventUpdate

    # So now, the callback was called either because a scan remove button was pressed, a file was uploaded or the clear scans button was pressed
    type_value, index_value = extract_type_index(str_dict)
    """
    if (not type_value == "file_upload"):
        # File uploads triggered context is the file itself, not a good idea to print that
        print('with:',dash.callback_context.triggered)
    """
    #print(type_value,index_value)

    # A file was uploaded
    if(type_value == 'file_upload'):
        print("---> Handling uploaded files:",list_of_filenames,flush=True)
        thumbnail_tuples, already_uploaded_files, diff_patient_files = handle_upload(list_of_contents[0], list_of_filenames[0])
        
        # Create the thumbnails from the thumbnail tuples info (img_b64,scan_index,thumbnail_text) and append the to the list
        for thumbnail_input, scan_index, thumbnail_text in thumbnail_tuples:
            scan_thumbnails_children.append(serve_scan_thumbnail(thumbnail_input, scan_index, thumbnail_text))
        
        if (len(already_uploaded_files) == 0 and len(diff_patient_files)==0):
            # No files were uploaded that require a warning
            return (scan_thumbnails_children,[],{'display':'none'})
        else:
            # A warning must be issued about some of the uploaded files
            (warning_window_children, warning_window_style) = serve_invalid_files_warning_window(already_uploaded_files,diff_patient_files)
            return (scan_thumbnails_children,warning_window_children,warning_window_style)
    
    # Else, a scan_remove button was pressed
    if (type_value == 'scan_remove_button'):
        # Find the value of index (in order to know which button was clicked)
        print("---> Removing scan with index:", index_value,flush=True)
        delete_uploaded_dicom(index_value)

        # Search for the corresponding thumbnail div
        scan_thumbnails_children_list_index = -1
        for i in range(0,len(scan_thumbnails_children)):
            if (scan_thumbnails_children[i]['props']['children'][2]['props']['id']['index'] == index_value):
                scan_thumbnails_children_list_index = i
        
        # Remove the deleted file's thumbnail
        scan_thumbnails_children.remove(scan_thumbnails_children[scan_thumbnails_children_list_index])
        
        return (scan_thumbnails_children,[],{'display':'none'})

    # Else, the clear all scans button was pressed
    if (type_value == 'clear_all_scans_button'):
        if(len(scan_thumbnails_children)==0):
            print("---> No scans to clear, PreventUpdate",flush=True)
            raise PreventUpdate
        print("---> Clearing all scans",flush=True)
        write_to_log('user actions',"clear_all_scans_button was pressed")
        clear_all_dicom_files()
        return ([],[],{'display':'none'})

    if (type_value == "uploaded_file_warning_div" and index_value == "X_button"):
        # A warning was displayed earlier in the hiddev_div2, now close it with no change to the scan thumbnails
        print("---> Hiding warning message div",flush=True)
        return (scan_thumbnails_children,[],{'display':'none'})
    
    if(type_value == "end_of_study_window" and not index_value == "reset_workspace_button"):
        # Currently, this callback will also fire when any of the end_of_study_window components are interacted
        # We only care about the reset_workspace_button here, so ignore the rest, they are handled elsewhere
        print("---> End Of Study button other than reset workspace, PreventUpdate",flush=True)
        raise PreventUpdate

    if(type_value == "end_of_study_window" and index_value == "reset_workspace_button"):
        # Erase all data for this study (log files, dicoms, estimations), essentialy starting over fresh
        print("---> Resetting Workspace",flush=True)
        clear_all_dicom_files()
        delete_log()
        delete_estimations()
        return ([],[],{'display':'none'})
    
    # If for some reason we've reached here, the callback trigger type was not identified
    print('---> uploaded_scans_master callback trigger of type:',type_value,' and index:',index_value, 'not identified, nothing to be done',flush=True)
    raise PreventUpdate


@app.callback(
    # To notify the user that the estimation is saved and disable that button
    Output({"type":"estimation_result_window","index":"save_button"},'children'),
    Output({"type":"estimation_result_window","index":"save_button"},'style'),
    Output({"type":"estimation_result_window","index":"save_button"},'disabled'),
    # To make the reject button spell "Close" instead of "Reject" after saving the estimation
    Output({"type":"hidden_div_button","index":"X_button"},'children'),
    Input({"type":"estimation_result_window","index":"save_button"},"n_clicks"),
    State({"type":"estimation_result_window","index":"save_button"},"style"),
    # Following are the states needed to access the estimation
    State({"type":"estimation_result_window","index":"estimation_cvp"},"dicomName"),
    State({"type":"estimation_result_window","index":"estimaton_value"},"children"),
    State({"type":"estimation_result_window","index":"extra_info_div_execution_time"},"children"),
    State({"type":"estimation_result_window","index":"notes"},"value"),
    # In case adding a pattern-matching id to the lvef_cvp causes errors,
    # we can get the dicomName by accessing the parent div's children:
    #State({"type":"estimation_result_window","index":"body"},'children'),
    # and navigating to it like so:
    # #dicomName = window_children[1]['props']['children']['props']['dicomName']
    # However, this navigation breaks when changing the order in the parent div's children
    prevent_initial_call=True
)
def estimation_result_master(n_clicks, button_style, dicomFilename, estimation_value, exec_time, notes):
    print("-> estimation_result_master fired")
    print("-->",dash.callback_context.triggered)
    #str_dict = dash.callback_context.triggered[0]['prop_id']
    #type_value, index_value = extract_type_index(str_dict)
    #if (index_value == "save_lvef_button"):
    if (n_clicks is None):
        print("---> Save workspace button was not pressed, PreventUpdate",flush=True)
        raise PreventUpdate
    # Save the estimation
    print("---> Saving the estimation",flush=True)
    estimation_type,estimation_value = estimation_value.split(": ")
    save_estimation(estimation_type,dicomFilename,estimation_value,exec_time,notes)
    button_style["backgroundColor"] = 'green'
    return ("Saved!",button_style,True,'Close')


@app.callback(
    Output({'type':'end_of_study_window','index':"download_study_summary"},'data'),
    Input({'type':'end_of_study_window','index':'download_study_summary_button'},'n_clicks'),
    State('patient_window_first_name','value'),
    State('patient_window_last_name','value'),
    State('patient_window_dob','value'),
    State('patient_window_gender','value'),
    State('patient_background_info','value'),
    State('patient_info_other_notes','value'),
    prevent_initial_call = True
)
def download_study_summary(n_clicks, p_name, p_last_name, p_dob, p_gender, p_back_info, p_notes):
    print('-> download_study_summary fired')
    print('--> ',dash.callback_context.triggered)

    # Should only be called when there is an ongoing study
    username = request.authorization['username']
    log_dict_filepath = './Sessions/' + username + '/log'
    if (not os.path.exists(log_dict_filepath)):
        # No ongoing study, the user is messing around
        print("---> Study summary is empty",flush=True)
        return dict(content="Study summmary is empty, you must initiate a study first.", filename="Study Summary.txt")
    
    # Out of the states, create the patient's general info dict
    general_info = {
        "First Name":p_name,
        "Last Name":p_last_name,
        "Date Of Birth":p_dob,
        "Gender":p_gender
    }
    study_summary = create_study_summary(general_info,p_back_info,p_notes)
    print("--->Returning study summary",flush=True)
    return dict(content=json.dumps(study_summary,ensure_ascii=False,indent=4), filename="Study Summary.txt")


@app.callback(
    Output('hidden_div', 'children'),
    Output('hidden_div', 'style'),
    Input({'type': 'hidden_div_button', 'index': ALL}, 'n_clicks'),
    Input({'type':'end_of_study_window','index':ALL}, 'n_clicks'),
    State('scan_thumbnails', 'children'),
    State({'type':'settings_window_component','index':'resize_percentage_slider'},'value'),
    State({'type':'settings_window_component','index':'mask_display'},'value'),
    prevent_initial_call=True
)
def hidden_div_master(hidden_div_button_nclicks,end_of_study_window_button_nclicks, scan_thumbnails_children, resize_percentage_slider_value, mask_display_value):
    """
    Complex callback that controls all button that want to output to the app's hidden div
    Some of the inputs are not initially rendered (e.g. the X button on the upload window)
    To solve this, pattern matching is once again used (see serve_scan_playback() callback)
    """
    print("-> hidden_div_master fired")
    print("-->",dash.callback_context.triggered)

    # This is a stringified dictionary
    str_dict = dash.callback_context.triggered[0]['prop_id']
    type_value, index_value = extract_type_index(str_dict)
    #print("hidden_div_master called by ", index_value, " with n_clicks ", n_clicks)

    # Here, depending on the button clicked, are the children that will be on hidden_div
    new_window_children = []
    new_window_style = {}  # style preset to the underlying hidden div

    if (type_value == 'hidden_div_button' and index_value == 'upload_button'):
        # The upload ECHO Scan button is clicked, so serve the upload layout to the user
        print("---> Serving Upload Window",flush=True)
        new_window_children, new_window_style = serve_upload_window()
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and index_value == 'X_button'):
        # The X button on the upload/scan selection layout has been clicked, so erase the children of the div and make it hidden again
        print("---> Hiding Hidden Div Window",flush=True)
        new_window_children = []
        new_window_style = {'zIndex': '-1'}
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and index_value == 'LVEF_button'):
        # The LVEF estimation button was pressed, so serve the corresponding window
        print("---> Serving LVEF Selection Window",flush=True)
        (new_window_children, new_window_style) = serve_LVEF_selection_window(scan_thumbnails_children)
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and 'LVEF_scan_select_button/' in index_value):
        # A scan was selected for the LVEG estimation
        # Get it's scan index
        print("---> Performing LVEF Estimation and Serving Results Window",flush=True)
        scan_index = int(index_value[(index_value.find('/')+1):])
        """
        # Serve the window without performing the estimation (during development)
        (new_window_children, new_window_style) = serve_LVEF_results(59.9,cvp.cornerstoneVP(
            id={"type":"estimation_result_window","index":"lvef_cvp"},dicomName="name"))
        return (new_window_children, new_window_style)
        """
        # Get the current DICOM filename the scan_index belongs to
        filename = get_filename_from_index(scan_index)
        #print("Scan", filename, "was selected for LVEF estimation with index:",scan_index)
        write_to_log('user actions',filename+" was selected for LVEF estimation")

        # Fetch the video and perform the LVEF estimation
        video_rgb,dateTime,framerate = fetch_fields(filename,get_pixel_array=True,get_datetime=True,get_framerate=True)
        start_time = time.time()
        # Wrap the estimation pipeline with a try-except, so as to display an error message to the user should the estimation fail 
        try:
            lvef_estimation, border_masked_video,fully_masked_video = lvef_estimation_pipeline(video_rgb)
        except Exception as e:
            print(str(e))
            return serve_estimation_error_window(str(e))
        end_time = time.time()
        exec_time = str(round(end_time-start_time,3)) + 's'

        if (mask_display_value == "Border Mask"):
            masked_video = border_masked_video
        if (mask_display_value == "Full Mask"):
            masked_video = fully_masked_video

        # Display the results
        resize_factor = 1/(resize_percentage_slider_value/100)
        videoHeight = int(masked_video.shape[1]/resize_factor)
        videoWidth = int(masked_video.shape[2]/resize_factor)
        image_pixels_list = prep_video_for_playback(masked_video,resize_factor)

        masked_video_cvp =  cvp.cornerstoneVP(
            id={"type":"estimation_result_window","index":"estimation_cvp"},
            imagePixelsList=image_pixels_list,
            dicomName=filename,
            dicomDateTime=dateTime,
            imageHeight=videoHeight,
            imageWidth=videoWidth,
            framerate=framerate
        )
        (new_window_children, new_window_style) = serve_LVEF_results_window(lvef_estimation,masked_video_cvp,exec_time)
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and index_value == 'LVGLS_button'):
        # The LVGLS estimation button was pressed, so serve the corresponding window
        print("---> Serving LVGLS Selection Window",flush=True)
        (new_window_children, new_window_style) = serve_LVGLS_selection(scan_thumbnails_children)
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and 'LVGLS_scan_select_button/' in index_value):
        print("---> Performing LVGLS Estimation and Serving Results Window",flush=True)
        # A scan was selected for the LVEG estimation, get it's scan index
        scan_index = int(index_value[(index_value.find('/')+1):])
        # Get the current DICOM filename the scan_index belongs to
        filename = get_filename_from_index(scan_index)
        #print("Scan", filename, "was selected for LVGLS estimation with index:",scan_index)
        write_to_log('user actions',filename+" was selected for LVGLS estimation")

        # Fetch the video and perform the LVGLS estimation
        video_rgb,dateTime,framerate = fetch_fields(filename,get_pixel_array=True,get_datetime=True,get_framerate=True)
        # Additionally measure estimation execution time
        start_time = time.time()
        # Wrap the estimation pipeline with a try-except, so as to display an error message to the user should the estimation fail
        try:
            lvgls_estimation, masked_cut_video = lvgls_estimation_pipeline(video_rgb,framerate)
        except Exception as e:
            print(str(e))
            return serve_estimation_error_window(str(e))
        end_time = time.time()
        exec_time = str(round(end_time-start_time,3)) + 's'

        # Display the results
        resize_factor = 1/(resize_percentage_slider_value/100)
        videoHeight = int(masked_cut_video.shape[1]/resize_factor)
        videoWidth = int(masked_cut_video.shape[2]/resize_factor)
        image_pixels_list = prep_video_for_playback(masked_cut_video,resize_factor)

        masked_video_cvp =  cvp.cornerstoneVP(
            id={"type":"estimation_result_window","index":"estimation_cvp"},
            imagePixelsList=image_pixels_list,
            dicomName=filename,
            dicomDateTime=dateTime,
            imageHeight=videoHeight,
            imageWidth=videoWidth,
            framerate=framerate
        )
        (new_window_children, new_window_style) = serve_LVGLS_results_window(lvgls_estimation,masked_video_cvp,exec_time)
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and index_value == 'view_estimations'):
        # Display the performed estimations to the user
        print("---> Serving Estimations Overview Window",flush=True)
        (new_window_children, new_window_style) = serve_estimations_overview_window()
        return (new_window_children, new_window_style)

    if (type_value == 'hidden_div_button' and index_value == "end_of_study"):
        print("---> Serving End Of Study Window",flush=True)
        # Display the study overview window to the user
        (new_window_children, new_window_style) = serve_study_overview_window()
        return (new_window_children, new_window_style)
    
    if (type_value == 'end_of_study_window' and index_value == 'reset_workspace_button'):
        # Close the end of study window
        print("---> Hiding Hidden Div Window",flush=True)
        new_window_children = []
        new_window_style = {'zIndex': '-1'}
        return (new_window_children, new_window_style)
    
    # If for some reason we've reached here, the callback trigger type was not identified
    print('uploaded_scans_master callback trigger:\n',dash.callback_context.triggered,'\nnot identified, PreventUpdate',flush=True)
    raise PreventUpdate


@app.callback(
    Output('cvp', 'dicomDateTime'),
    Output('cvp', 'dicomName'),
    Output('cvp', 'framerate'),
    Output('cvp', 'imageHeight'),
    Output('cvp', 'imagePixelsList'),
    Output('cvp', 'imageWidth'),
    Input({'type': 'scan_playbutton', 'index': ALL}, 'n_clicks'),
    State({'type':'settings_window_component','index':'resize_percentage_slider'},'value'),
    prevent_initial_call=True
)
def serve_scan_playback(scan_playbutton_nclicks, resize_percentage_slider_value):
    """
    Callback responsible for serving the corresponding video player instance when a thumbnail of 
    an uploaded DICOM file is clicked on.
    """
    print("->serve_scan_playback fired")
    print("-->",dash.callback_context.triggered)
    """ 
    Right now this fires every time a scan thumbnail is added, so a check is implemented to stop the scan playback selected from changing every such time. When a click occurs, the length of the triggers is 1 (just the button that was clicked), whereas when the thumbnail area is updated, the length of the triggers is the new number of thumbnails in the thumbnail area. The end case being that this callback executes for every thumbnail button clicked, when there are two thumbnails and one is removed (leaving only one in the thumbnail area) or when the first thumbnail is added.
    """
    if (len(dash.callback_context.triggered) > 1):
        print("---> PreventUpdate due to multiple triggers",flush=True)
        raise PreventUpdate
    
    str_dict = dash.callback_context.triggered[0]['prop_id']
    if (str_dict == '.'):
        # Possible bug, catch it
        print("---> PreventUpdate due to dot trigger (unknown trigger origin)",flush=True)
        raise PreventUpdate
    
    type_value, index_value = extract_type_index(str_dict)
    if (type_value == 'scan_playbutton'):
        if (len(scan_playbutton_nclicks) == 0):
            print("---> PreventUpdate due to empty thumbnail list (can this even occur?)",flush=True)
            raise PreventUpdate
        if (scan_playbutton_nclicks.count(None)==len(scan_playbutton_nclicks)):
            print("---> PreventUpdate for the first added scan thumbnail",flush=True)
            raise PreventUpdate

        # Execution reaches this far only if the user clicked on a scan thumbnail to view the playback
        # This is a stringified dictionary
        str_dict = dash.callback_context.triggered[0]['prop_id']
        scan_index_str = ""
        # The only number in that stringified dictionary is the index of the 'scan_playbutton' triggered
        for letter in str_dict:
            if letter.isdigit():
                scan_index_str = scan_index_str + letter
        # In case all scans were deleted, the below code will throw an error, catch it
        try:
            scan_index = int(scan_index_str)
        except:
            print("---> PreventUpdate due to error when handling the scan index",flush=True)
            raise PreventUpdate

        # Get the current DICOM filename the scan_index belongs to
        username = request.authorization['username']
        index_dict_path = './Sessions/' + username + '/file_indexes'
        with open(index_dict_path, 'r') as fp:
            index_dict = json.load(fp)

        filename = index_dict[str(scan_index)]
        write_to_log('user actions',filename+"file requested for playback")
        pixel_array_rgb,dateTime,framerate = fetch_fields(filename,get_pixel_array=True,get_datetime=True,get_framerate=True)
        resize_factor = 1/(resize_percentage_slider_value/100)
        videoHeight = int(pixel_array_rgb.shape[1]/resize_factor)
        videoWidth = int(pixel_array_rgb.shape[2]/resize_factor)
        image_pixels_list = prep_video_for_playback(pixel_array_rgb,resize_factor)

        print("---> Returning props to the CVP with a resize factor of",resize_factor,flush=True)
        return (dateTime,filename,framerate,videoHeight,image_pixels_list,videoWidth)


@app.callback(
    Output('scan_playback_loader', 'children'),
    Input({'type': 'clear_all_scans_button', 'index': ALL}, 'n_clicks'),
    Input({'type': 'hidden_div_button', 'index': 'end_of_study'}, 'n_clicks'), 
    prevent_initial_call = True
)
def reset_cvp(clear_all_scans_button_nclicks, hidden_div_button_nclicks):
    """
    Callback responsible for resetting the CVP when the use-case requires it
    """
    print("-> reset_cvp fired")
    print("-->",dash.callback_context.triggered)
    str_dict = dash.callback_context.triggered[0]['prop_id']
    type_value, index_value = extract_type_index(str_dict)

    if (type_value == 'clear_all_scans_button'):
        print('---> Scans are being cleared, resetting the CVP.')
        return cvp.cornerstoneVP(id="cvp")

    if (type_value == 'hidden_div_button' and index_value == 'end_of_study'):
        # This exists as a work-around to prevent the app from severely lagging when
        # the end of study window is open while the cvp is displaying video
        print('---> End of study window is being served, resetting the CVP.')
        return cvp.cornerstoneVP(id="cvp")
    
    print('---> PreventUpdate, trigger not recognized')
    raise PreventUpdate


@app.callback(
    Output(component_id='scan_count', component_property='children'),
    Input(component_id='scan_thumbnails', component_property='children')
)
def update_scan_count(scan_thumbnails_children):
    # Get the number of dicom files this user has uploaded
    """
    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms/'
    scan_number = len(os.listdir(filepath))
    info = "Scan Count: " + str(scan_number)
    """
    print("-> update_scan_count fired")
    info = "Scan Count: " + str(len(scan_thumbnails_children))
    print("---> Updating Scan Count",flush=True)
    return info


@app.callback(
    Output(component_id='date_time', component_property='children'),
    Input(component_id='interval_component', component_property='n_intervals')
)
def update_datetime(n_intervals):
    return serve_datetime()


if __name__ == '__main__':
    if is_docker():
        app.run_server(debug=False,host="0.0.0.0",port=8050)
    else:
        app.run_server(debug=False)
