# Import General Packages
from dash import html,dcc,dash_table
import pydicom
import datetime
from flask import request
# Importing Development Modules
import cvp
from utils import get_estimations_dict, load_session

header_color = '#02072F' # dark blue
background_color = '#28282B' # matte black
text_color = 'white'
thumbnail_button_color = 'gold'
window_background_color = '#28282B' # matte black
text_fond = ["Product Sans"]

"""
NOTE: For a lot of components, extra styling options other than height and width are taken care of in the css file in the assets folder
"""


def serve_homepage_layout():
    """
    Serves the layout of the entire App
    """
    layout = html.Div(
        [
        # App Header (top)
        html.Header(
            [
            dcc.Interval(id="interval_component"),
            html.Div(
                    html.Img(
                        src="./assets/GUI/heart_blueBG.png",
                        style={'height': "100%",'padding': '0%', 'margin': '0%'}
                    ),
                    id="logo",
                    style={'width': '20%', 'height': '100%', 'display': 'inline-block','verticalAlign': 'top','textAlign':'center','color':'white'}
            ),
            html.Div(
                html.Img(
                        src="./assets/GUI/echo_logo.png",
                        style={'height': "100%",'padding': '0%', 'margin': '0%'}
                ),
                style={'width': '60%', 'height': '100%', 'display': 'inline-block', 'textAlign': 'center', 'margin': '0px','color':'white'}
            ),
            # right-side div
            html.Div([
                html.Div(
                    serve_datetime(),
                    id="date_time",
                    style={'width': '80%', 'height': '100%', 'display': 'inline-block','textAlign':'center','color':'white'}
                ),
                html.Button(
                    html.Img(
                        src="./assets/GUI/icons8-doublewheel-64.png",
                        style={"width": '100%', 'height': "auto",'padding': '0%', 'margin': '0%'}
                    ),
                    style={'height': '100%', 'width': '20%'},
                    id={'type':'settings_window_button','index':'display_window_button'},
                    className="select-button"
                )],
                style={'height': '100%', 'width': '20%', 'display': 'inline-block','verticalAlign': 'top'}
            )
        ],
            style={'height': '10%', 'backgroundColor': header_color}
        ),

        # Imported Scans section (left)
        html.Div(
            [
                html.H3("Imported Scans",
                        style={'height': '3%', 'textAlign': 'center', 'margin': '1%', 'padding': '0px','color':text_color}),
                html.H4("Scan Count: 0", id="scan_count",
                        style={'height': '2%', 'textAlign': 'center', 'margin': '0.5%', 'padding': '0px','color':text_color}),
                html.Hr(),
                dcc.Loading(
                    html.Div(
                        [], 
                        id="scan_thumbnails",
                        style={'height': '100%', 'textAlign': 'center', 'margin': '0%', 'padding': '0px', 'backgroundColor':'black', 'direction': 'rtl','overflow': 'scroll'}
                    ),
                    type = 'dot',
                    # parent_style is style of the div that has the dcc.Loading component
                    parent_style={'height': '75%','textAlign': 'center', 'margin': '2.5% 2.5% 0.5% 2.5%','padding': '0px'},
                    style = {'opacity':'0.5'},
                    fullscreen=True # user should wait while the file's are being uploaded - is it ugly?
                ),
                # Uploaded scans without dcc.Loading
                #html.Div(
                #        [], 
                #        id="scan_thumbnails",
                 #       style={'height': '75%', 'textAlign': 'center', 'margin': '2.5% 2.5% 0.5% 2.5%', 'padding': '0px', 'backgroundColor':'white', 'direction': 'rtl','overflow': 'scroll'}
                #),
                html.Button('Clear All Scans', 
                            id={'type': 'clear_all_scans_button', 'index': '1'},
                            style={'width': '60%', 'height': '5%', 'margin': '0% 20%'},
                            className="select-button"),
                html.Button('Upload ECHO Scan', 
                            id={'type': 'hidden_div_button', 'index': 'upload_button'},
                            style={'width': '80%', 'height': '7%', 'margin': '2% 10% 1%'},
                            className="select-button")
            ],
            style={'width': '20%', 'height': '90%',
                   'display': 'inline-block', 'backgroundColor': background_color}
        ),
        
        # Scan playback section (middle)
        dcc.Loading(
            html.Div(
                cvp.cornerstoneVP(id="cvp"), 
                id='scan_playback_section', 
                style={'width': '100%', 'height': '100%', 'backgroundColor': '#130665'}
            ),
            type = 'circle',
            # parent_style is style of the dcc.Loading component
            parent_style={'width': '60%', 'height': '90%', 'display': 'inline-block', 'verticalAlign': 'top'},
            style = {'opacity':'0.5'},
            fullscreen=True,
            id='scan_playback_loader'
        ),

        # User Options section (right)
        html.Div([
            html.Button("Patient Info",
                        id={'type': 'patient_info_window_button',
                            'index': 'display_window_button'},
                        style={'width': '80%', 'height': '5%', 'margin': '5% 10%'},
                        className="select-button"
            ),
            html.Button("LVEF Estimation",
                        id={'type': 'hidden_div_button', 'index': 'LVEF_button'},
                        style={'width': '80%', 'height': '5%', 'margin': '45% 10% 2.5%'},
                        className="select-button"
            ),
            html.Button("LVGLS Estimation",
                        id={'type': 'hidden_div_button',
                            'index': 'LVGLS_button'},
                        style={'width': '80%', 'height': '5%', 'margin': '2.5% 10% 2.5%'},
                        className="select-button"
            ),
            html.Button("View Estimations",
                    id={'type': 'hidden_div_button', 'index': 'view_estimations'},
                    style={'width': '80%', 'height': '5%', 'margin': '20% 10% 2.5%'},
                    className="select-button"
            ),
            html.Button("Study Overview",
                id={'type': 'hidden_div_button','index': 'end_of_study'},
                style={'width': '80%', 'height': '5%', 'margin': '2.5% 10% 2.5%'},
                className="select-button"
            )
        ],
            id='options_section',
            style={'width': '20%', 'height': '90%', 'display': 'inline-block', 'verticalAlign': 'top','backgroundColor': background_color}),

        # Extra Div for Upload/Analysis Windows
        # This Div is in the DOM, but invisible - always underlying until used
        # No info is preserved on it however after it's use for a particular function's display
        # Wrapped with dcc.Loading so the estimation functions show they are running
        dcc.Loading(
            html.Div([],
                 id='hidden_div',
                 style={'position': 'fixed', 'top': '0%', 'left': '0%', 'zIndex': '-1'}
                 ),
                 parent_style={'position': 'fixed', 'top': '50%', 'left': '50%'},
                 style={'opacity':'0.5'},
                 fullscreen=True,
                 type = 'cube'
        ),
        # Settings Window Div
        # In constrast with hidden_div, this is hidden with display:None but retains the information on it
        # It is only used as settings window and other callbacks have access to it only to view the user's settings
        html.Div(
            serve_settings_window(),
            id="settings_window",
            style={'width': '55%', 'height': '80%','position': 'fixed', 'top': '11%', 'right': '22.5%', 'margin': '0%', 'padding': '0%','display':'none'}
        ),
        # Extra hidden Div for displaying messages during file uploads
        html.Div([],
                 id='uploaded_file_warning_div',
                 style={'backgroundColor': 'purple','position': 'fixed', 'top': '0%', 'left': '0%', 'zIndex': '-1'}
        ),
        # Patient Info Div
        # In constrast with the hidden divs, this is hidden with display:None but retains the information on it
        # It is only used as the patient info window and other callbacks have access to it to view the patient's info
        html.Div(
            serve_patient_info_window_children(),
            id="patient_info_window",
            style={'width': '40%', 'height': '85%','position': 'fixed', 'top': '11%', 'right': '1%', 'margin': '0%', 'padding': '0%','display':'none','color':text_color}
        )
    ],
        style={'height': '660px', 'backgroundColor': 'black','outlineStyle': 'hidden'}, id='app_div')
    return layout


def serve_settings_window():
    """
    Returns the children of the settings window
    """
    window_children = [
        # Header
        html.Header([
            html.Div(
                    [],
                    style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}
            ),
            html.H2(
                    "System Settings Window",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block','color':text_color}
            ),
            html.Button(
                        "X", 
                        id={'type': 'settings_window_button', 'index': 'X_button'},
                        style={'height': '100%','width': '5%', 'margin-left': '5%', 'verticalAlign': 'top'},
                        className = 'x-button'
            ),
            ],
            style={'width': '100%', 'height': '6%', 'backgroundColor': background_color}),
        # Body
        html.Div([
            # Resize slider option
            html.Div([
                html.H3(
                        "Video Quality Control",
                        style={"textAlign": "center"}
                ),
                html.H4(
                        "Choose the percentage of the original video quality you wish the video player to display:",
                        style={"textAlign": "center"}
                ),
                html.H5(
                    "NOTE: Higher video quality will result in the video playback taking longer to set up, which is why the default value is 70%.",
                    style={"textAlign": "center"}
                ),
                dcc.Slider(10, 100, 10, value=70, included=False,
                           marks={10: '10%', 20: '20%', 30: '30%', 40: '40%', 50: '50%',
                                  60: '60%', 70: '70%', 80: '80%', 90: '90%', 100: '100%'},
                           id={'type': 'settings_window_component', 'index': 'resize_percentage_slider'}, 
                           persistence=True)
            ],
                style={'display':'inline-block','height': '50%', 'width': '45%', 'backgroundColor': 'black', 'margin': '2% 3% 2% 2%',
                       'outlineStyle': 'dotted', 'outlineWidth': 'thin','verticalAlign':'top','color':text_color}
            ),
            html.Div([
                html.H3("LVEF Mask Display Type",
                        style={"textAlign": "center"}),
                html.H4("Choose the way the mask is displayed on the LVEF estimation screen:",
                        style={"textAlign": "center"}),
                html.H5("Border Mask displays the mask's border's only.",style={'margin':'0%','padding':'0%',"textAlign": "center"}),
                html.H5("Full Mask displays the entire mask's surface.",style={'margin':'0% 0% 5% 0%','padding':'0%',"textAlign": "center"}),
                dcc.RadioItems(
                    options=['Border Mask', 'Full Mask'],
                    value='Border Mask',
                    id={'type': 'settings_window_component', 'index': 'mask_display'}, persistence=True,
                    style={'textAlign':'center'},
                    className = "radio-buttons"
                )
            ],
                style={'display':'inline-block','height': '50%', 'width': '45%', 'backgroundColor': 'black', 'margin': '2% 3% 2% 2%','outlineStyle': 'dotted', 'outlineWidth': 'thin','verticalAlign':'top','color':text_color}
            ),
        ],
            style={'width': '100%', 'height': '94%','margin': '0%', 'padding': '0%', 'backgroundColor': background_color}
        )
    ]
    return (window_children)


def serve_datetime():
    """
    Returns the current date and time formatted in two H2 components
    """
    current_time = datetime.datetime.now()

    # Only numbers date string (DD/MM/YYYY)
    date_string = str(current_time.day) + "/" + \
        str(current_time.month) + "/" + str(current_time.year)
    # Worded date string
    days_dict = {0:'Monday',1:'Tuesday',2:'Wednesday',3:'Thursday',4:'Friday',5:'Saturday',6:'Sunday'}
    short_days_dict = {0:'Mon',1:'Tue',2:'Wed',3:'Thu',4:'Fri',5:'Sat',6:'Sun'}
    months_dict = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    day_name = short_days_dict[current_time.weekday()]
    month_name = months_dict[current_time.month]

    date_string_full = day_name + ", " + str(current_time.day) + " " + month_name + " " + str(current_time.year)
    # Pad with an extra 0 the hour, minute and second strings (in case of single digit values)
    hour_string = str(current_time.hour)
    if (len(hour_string) == 1):
        hour_string = "0" + hour_string

    minute_string = str(current_time.minute)
    if (len(minute_string) == 1):
        minute_string = "0" + minute_string

    second_string = str(current_time.second)
    if (len(second_string) == 1):
        second_string = "0" + second_string

    time_string = hour_string + ":" + minute_string + ":" + second_string

    date_component = html.H2(children=date_string_full, style={
                             'height': '45%', 'margin': '0px'})
    time_component = html.H2(children=time_string, style={
                             'height': '45%', 'margin': '0px'})
    datetime_element = html.Div(
        [date_component, time_component],
        id="date_time",
        style={'width': '20%', 'height': '100%', 'display': 'inline-block','verticalAlign': 'top','textAlign':'center','color':'white','outline':'double'}
    )
    return (date_component, time_component)


def serve_upload_window():
    """
    Returns the children and style properties of the upload window 
    """
    upload_window_children = html.Div(
        [
        # Header
        html.Header([
            html.Div([], style={'width': '10%', 'height': '100%',
                                'margin': '0px', 'display': 'inline-block'}),
            html.H3([], style={'width': '80%', 'height': '100%', 'margin': '0px',
                                               'textAlign': 'center', 'verticalAlign': 'top', 'display': 'inline-block','color':text_color}),
            html.Button("X", 
                        id={'type': 'hidden_div_button', 'index': 'X_button'}, 
                        style={'width': '5%', 'height': '100%', 'margin': '0px','margin-left':'5%'},
                        className = "x-button"
            ),
            ], 
            style={'width': '100%', 'height': '5%', 'backgroundColor': window_background_color,'margin':'0px','padding':'0px'}
        ),
        # Upload Window Body
        # Upload Window Body without dcc.Loading wrapping
        html.Div(
            [
                html.H3("Upload a DICOM file from your files",
                        style={'width':'100%','height':'5%','textAlign': 'center','margin': '0px', 'padding': '3% 0% 1%','color':text_color}
                ),
                html.H4("You can choose multiple files at once",
                        style={'width':'100%','height':'5%','textAlign': 'center', 'margin': '0px', 'padding': '1% 0% 1%','color':text_color}
                ),
                dcc.Upload(
                    [
                    "Drag and Drop a file here or ",
                    html.A(
                        "Select From Your Files", 
                        style={'textDecorationLine': 'underline', 'cursor': 'pointer'})
                    ],
                    style={
                    'width': '60%',
                    'height': '50%',
                    'lineHeight': '700%',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'textAlign': 'center',
                    'margin': '2% 20%',
                    'color':text_color},
                    multiple=True,  # Allow multiple files to be uploaded
                    id={
                        'type': 'file_upload',
                        'index': "no_use_needed"
                    }
                    #The index of the upload component must be a pattern-matching object
                    #(as it not rendered initially on the layout), but since there is only
                    #one upload object (hence, only one component with type:"file_upload"),
                    #the index's value is of no importance, other than it must be a string
                    #in order for the  extract_type_index() function to work smoothly
                )
            ], 
            style={'width': '100%', 'height': '95%', 'backgroundColor': window_background_color, 'margin': '0px'}
        )
        ], 
        style={'width': '40%', 'height': '35%', 'position': 'fixed', 'top': '20%', 'left': '30%'})
    upload_window_style = {'width': '30%', 'height': '20%','position': 'fixed', 'top': '20%', 'left': '30%'}
    return (upload_window_children,upload_window_style)


def serve_patient_info_window_children():
    """
    Returns the children property of the patient info window
    """
    window_children = [
        # Header
        html.Header([
            html.Div(
                [],
                style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}
            ),
            html.H2(
                "Patient Info",
                style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'}
            ),
            html.Button(
                "-->", 
                id={'type': 'patient_info_window_button', 'index': 'X_button'},
                style={'width': '5%', 'height': '100%', 'margin-left': '5%', 'verticalAlign': 'top'},
                className = 'x-button'
            )],
            style={'width': '100%', 'height': '6%', 'backgroundColor': background_color,'margin':'0%','padding':'0%'}
        ),
        # Body
        html.Div(
            [
            # Patient Detail (left)
            html.Div(
                [
                # Header
                html.H3(
                    "General Information",
                    style={'width': '100%', 'height': '5%', 'margin': '0%','padding':'0%', 'textAlign': 'center','verticalAlign':'top'}
                ),
                # First Name
                html.Div([
                    html.H4("First Name:",
                        style={'width': '35%', 'height': '100%', 'display': 'inline-block',
                           'margin': '0%', 'verticalAlign': 'top', 'padding': '0%'}
                    ),
                    dcc.Textarea(
                        placeholder="Enter patient's name",
                        style={'width': '65%', 'height': '66%', 'display': 'inline-block',
                           'margin': '0%', 'padding': '0%', 'border':'0px','borderRadius':'0px','resize':'none','textAlign':'center'},
                        readOnly=True,
                        persistence=True,
                        id="patient_window_first_name"
                    )],
                    style={'width': '98%', 'height': '10%','margin': '2% 1% 3%'}
                ),
                # Last Name
                html.Div([
                    html.H4("Last Name: ",
                        style={'width': '35%', 'height': '100%', 'display': 'inline-block',
                           'margin': '0%', 'verticalAlign': 'top', 'padding': '0%'}
                    ),
                    dcc.Textarea(
                        placeholder="Enter patient's last name",
                        style={'width': '65%', 'height': '66%', 'display': 'inline-block',
                           'margin': '0%', 'padding': '0%', 'border':'0px','borderRadius':'0px','resize':'none','textAlign':'center'},
                        readOnly=True,
                        persistence=True,
                        id='patient_window_last_name'
                    )
                    ],
                    style={'width': '98%', 'height': '10%','margin': '2% 1% 3%'}
                ),
                # Date Of Birth
                html.Div([
                    html.H4("Date Of Birth: ",
                        style={'width': '35%', 'height': '100%', 'display': 'inline-block',
                           'margin': '0%', 'verticalAlign': 'top', 'padding': '0%'}
                    ),
                    dcc.Textarea(
                        placeholder="Enter patient's date of birth",
                        style={'width': '65%', 'height': '66%', 'display': 'inline-block',
                           'margin': '0%', 'padding': '0%', 'border':'0px','borderRadius':'0px','resize':'none','textAlign':'center'},
                        readOnly=True,
                        persistence=True,
                        id="patient_window_dob"
                    )
                    ],
                    style={'width': '98%', 'height': '10%','margin': '2% 1% 3%'}
                ),
                # Gender
                html.Div([
                    html.H4("Gender: ",
                        style={'width': '35%', 'height': '100%', 'display': 'inline-block',
                           'margin': '0%', 'verticalAlign': 'top', 'padding': '0%'}
                    ),
                    dcc.Textarea(
                        placeholder="Enter patient's gender",
                        style={'width': '65%', 'height': '66%', 'display': 'inline-block',
                           'margin': '0%', 'padding': '0%', 'border':'0px','borderRadius':'0px','resize':'none','textAlign':'center'},
                        readOnly=True,
                        persistence=True,
                        id="patient_window_gender"
                    )
                    ],
                    style={'width': '98%', 'height': '10%','margin': '2% 1% 3%'}
                ),
                ],
                style={'width': '48%', 'height': '70%', 'margin': '2% 1%', 'display': 'inline-block', 'verticalAlign': 'top', 'overflow':'auto','outlineStyle': 'dotted', 'outlineWidth': 'thin','backgroundColor':'black','textAlign':'center'}
            ),
            
            # Patient Background (right)
            html.Div(
                [
                    html.H3(
                        "Background Information", 
                        style={'width': '100%', 'height': '5%', 'margin': '0%', 'textAlign': 'center','verticalAlign':'top'}),
                    dcc.Textarea(
                        placeholder="Enter any background information about the patient here",
                        id='patient_background_info', 
                        style={'width': '98%', 'height': '93%','display': 'inline-block','margin': '2% 0% 0%','padding':'0px','border':'0px','borderRadius':'0px','resize':'none'},
                        persistence=True,
                        persistence_type = 'session'
                    ),    
                ],
                style={'width': '48%', 'height': '70%', 'margin': '2% 1%', 'display': 'inline-block','verticalAlign': 'top','outlineStyle': 'dotted', 'outlineWidth': 'thin','textAlign':'center','backgroundColor':'black'}
            ),

            # Other Notes (bottom)
            html.Div(
            [
                html.H3(
                    "Other notes",
                    style={'width': '100%', 'height': '20%', 'margin': '0%','padding':'0%', 'textAlign': 'center','verticalAlign':'top'}
                ),
                dcc.Textarea(
                    placeholder="Enter any additional information/notes here",
                    id='patient_info_other_notes', 
                    style={'width': '100%', 'height': '80%', 'margin': '0%','padding':'0px','border':'0px','borderRadius':'0px','resize':'none'},
                    persistence=True
                )
                ],
                style={'width': '98%', 'height':'24%','margin': '0% 1%','padding': '0%','outlineStyle': 'dotted', 'outlineWidth': 'thin','textAlign':'center','backgroundColor':'black'}
            )],
            style={'width': '100%', 'height': '94%', 'backgroundColor': background_color, 'margin':'0%', 'padding':'0%'}
        )
    ]

    return window_children


def serve_LVEF_results_window(lvef_estimation, masked_video_cvp, execution_time):
    """
    Given the LVEF estimation and the masked video player, this function
    returns the children and style properties of the hidden_div,
    so that the results of the estimation are displayed to the user
    """
    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2("LVEF Estimation Results",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'})
        ],
        style={'width': '100%', 'height': '6%','margin': '0%', 'padding': '0%'}
        ),
        # Body
        html.Div(
            [
                html.H3(
                    "LVEF: " + str(round(lvef_estimation,1)) +"%",
                    id = {"type":"estimation_result_window","index":"estimaton_value"},
                    style={'width': '95%','height':'5%', 'textAlign':'center','verticalAlign':'top',
                    'margin':'0% 2.5%','padding':'0%'}
                    ),
                html.Div(
                    masked_video_cvp,
                    style={'width': '95%','height':'75%', 'backgroundColor':'black','color':'blue','margin':'0% 2.5%','padding':'0%'}
                ),
                # User input div
                html.Div(
                    dcc.Textarea(
                        placeholder="Enter any notes about the estimation here",
                        style={'width':'80%','height':'80%','padding':'0%','margin':'0%','resize':'none'},
                        id = {'type': 'estimation_result_window', 'index': 'notes'}
                    ),
                    style = {'width': '65%','height':'15%','padding':'0%','margin':'2.5%','display':'inline-block','verticalAlign':'top'}
                ),
                # Save/Reject Estimation Buttons Div
                html.Div([
                    html.Button(
                        "Save",
                        id = {'type': 'estimation_result_window', 'index': 'save_button'},
                        style={'width': '95%', 'height': '40%', 'margin':'0% 2.5% 2.5%'},
                        className="select-button"
                    ),
                    html.Button(
                        "Reject",
                        id = {'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '95%', 'height': '40%','margin':'0% 2.5% 2.5%'},
                        className="select-button"
                    ),
                ],
                style={'width': '20%', 'height': '15%', 'textAlign': 'center', 'margin':'2.5%','display':'inline-block','verticalAlign':'top'},
                ),
                # Hidden Div to store extra info about the estimation (time,etc etc)
                html.Div(
                    [
                        # Execution Time Info
                        html.Div(
                            execution_time,
                            id={'type': 'estimation_result_window', 'index': 'extra_info_div_execution_time'},
                            style={'display':'none','position':'absolute','width':'0px','height':'0px'}
                        )
                    ],
                    id={'type': 'estimation_result_window', 'index': 'extra_info_div'},
                    style = {'display':'none','position':'absolute','width':'0px','height':'0px'}
                )
                
            ],
            style={'width': '100%', 'height': '94%','margin': '0%', 'padding': '0%', },
            id = {"type":"estimation_result_window","index":"body"}
        )
    ]
    window_style = {'width': '58%', 'height': '80%', 'position': 'fixed', 'top': '11%', 'right': '21%', 'margin': '0%', 'padding': '0%','backgroundColor':background_color,'color':text_color}

    return (window_children, window_style)
    

def create_scan_selection_buttons(scan_thumbnails,estimation_type):
    """
    For every thumbnail in the thumbnail area, create the corresponding scan selection button and return them as a list
    To be used in serve_LVEF_selection_window()
    """
    username = request.authorization['username']
    filepath = './Sessions/' + username + '/Dicoms/'

    scan_selection = []
    # For every thumbnail in the thumbnail area, create the corresponding scan selection button
    for thumbnail in scan_thumbnails:
        image_src = thumbnail['props']['children'][0]['props']['children']['props']['src']
        scan_index = thumbnail['props']['children'][0]['props']['id']['index']
        scan_text = thumbnail['props']['children'][1]['props']['children']

        filename = scan_text.split(":")[0]
        ds = pydicom.dcmread(filepath+filename)
        if (ds.pixel_array.shape[0] < 62):
            # If the current scan's nframes is <62, do not list it as available for the LVEF estimation
            continue
    
        image_button = html.Div([
            html.Button(
                html.Img(src=image_src, style={
                         'width': '100%', 'height': '100%'}),
                style={'width': '100%', 'height': '90%'},
                id={'type': 'hidden_div_button',
                    'index': estimation_type + '_scan_select_button'+'/' + str(scan_index)}
            ),
            html.H4(scan_text, 
                    style={'width': '100%', 'height': '10%', 'margin': '0%', 'textAlign': 'center','color':thumbnail_button_color}),
        ],
            style={'width': '45%', 'height': '45%',
                   'display': 'inline-block', 'margin': '2.5%'}
        )
        scan_selection.append(image_button)
    return scan_selection


def serve_LVEF_selection_window(scan_thumbnails_children):
    """
    Returns the children and the style of the LVEF scan selection window
    NOTE: Scans with nframes<62 are not shown as an option for the LVEF estimation,
    due to the current LVEF pipelines' inability to deal with them
    """
    scan_selection = create_scan_selection_buttons(scan_thumbnails_children,'LVEF')

    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2([],
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block','color':text_color}),
            html.Button("X", 
                        id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '5%', 'height': '100%', 'margin-left': '5%'},
                        className = "x-button"
            )],
            style={'width': '100%', 'height': '6%', 'backgroundColor': window_background_color}),
        # Body
        html.Div(
            [
            html.H2(
                "Choose the scan to perform the LVEF estimation on",
                style={'width': '100%', 'height': '7%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block','color':text_color}
            ),
            html.H3(
                "Scans with less than 62 frames are currently not suitable for the LVEF estimation and are thus not shown",
                style={'width':'100%','height':'5%','color':text_color,'textAlign':'center','margin': '0px', 'padding': '0px'}
            ),
            html.Div(
                scan_selection,
                style={'width': '98%', 'height': '86%', 'backgroundColor': 'black',
                   'margin': '0% 1%', 'padding': '0%', 'overflow': 'auto', 'direction': 'ltr'}
            )
            ],
            style={'width': '100%', 'height': '94%','backgroundColor': window_background_color}
        )
    ]
    window_style = {'width': '55%', 'height': '80%',
                    'position': 'fixed', 'top': '11%', 'right': '22.5%', 'margin': '0%', 'padding': '0%'}

    return (window_children, window_style)


def serve_LVGLS_results_window(lvgls_estimation, masked_video_cvp, execution_time):
    """
    Given the LVGLS estimation and the masked video player, this function
    returns the children and style properties of the hidden_div,
    so that the results of the estimation are displayed to the user
    """
    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2("LVGLS Estimation Results",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'})
        ],
        style={'width': '100%', 'height': '6%','margin': '0%', 'padding': '0%'}
        ),
        # Body
        html.Div(
            [
                html.H3(
                    "LVGLS: " + str(round(lvgls_estimation,1)) +"%",
                    id = {"type":"estimation_result_window","index":"estimaton_value"},
                    style={'width': '95%','height':'5%', 'textAlign':'center','verticalAlign':'top',
                    'margin':'0% 2.5%','padding':'0%'}
                    ),
                html.Div(
                    masked_video_cvp,
                    style={'width': '95%','height':'75%', 'backgroundColor':'black','color':'blue','margin':'0% 2.5%','padding':'0%'}
                ),
                # User input div
                html.Div(
                    dcc.Textarea(
                        placeholder="Enter any notes about the estimation here",
                        style={'width':'80%','height':'80%','padding':'0%','margin':'0%','resize':'none'},
                        id = {'type': 'estimation_result_window', 'index': 'notes'}
                    ),
                    style = {'width': '65%','height':'15%','padding':'0%','margin':'2.5%','display':'inline-block','verticalAlign':'top'}
                ),
                # Save/Reject Estimation Buttons Div
                html.Div([
                    html.Button(
                        "Save",
                        id = {'type': 'estimation_result_window', 'index': 'save_button'},
                        style={'width': '95%', 'height': '40%', 'margin':'0% 2.5% 2.5%'},
                        className='select-button'
                    ),
                    html.Button(
                        "Reject",
                        id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '95%', 'height': '40%', 'margin':'0% 2.5% 2.5%'},
                        className='select-button'
                    )
                ],
                style={'width': '20%', 'height': '15%', 'textAlign': 'center', 'margin':'2.5%','display':'inline-block','verticalAlign':'top'},
                ),
                # Hidden Div to store extra info about the estimation (time,etc etc)
                html.Div(
                    [
                        # Execution Time Info
                        html.Div(
                            execution_time,
                            id={'type': 'estimation_result_window', 'index': 'extra_info_div_execution_time'},
                            style={'display':'none','position':'absolute','width':'0px','height':'0px'}
                        )
                    ],
                    id={'type': 'estimation_result_window', 'index': 'extra_info_div'},
                    style = {'display':'none','position':'absolute','width':'0px','height':'0px'}
                )
            ],
            style={'width': '100%', 'height': '94%','margin': '0%', 'padding': '0%'},
            id = {"type":"estimation_result_window","index":"body"}
        )
    ]
    window_style = {'width': '58%', 'height': '80%', 'backgroundColor': background_color,
                    'position': 'fixed', 'top': '11%', 'right': '21%', 'margin': '0%', 'padding': '0%','color':text_color}

    return (window_children, window_style)


def serve_LVGLS_selection(scan_thumbnails_children):
    scan_selection = create_scan_selection_buttons(scan_thumbnails_children,'LVGLS')

    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2([],
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'}),
            html.Button("X", 
                        id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '5%', 'height': '100%', 'margin-left': '5%'},
                        className = "x-button"),
            ],
            style={'width': '100%', 'height': '6%', 'backgroundColor': window_background_color}
        ),
        # Body
        html.Div(
            [   
                html.H2(
                    "Choose the scan to perform the LVGLS estimation on",
                    style={'width': '100%', 'height': '10%','margin': '0%','display':'inline-block', 'textAlign': 'center', 'verticalAlign': 'top','color':text_color}
                ),
                html.Div(
                    scan_selection,
                    style={'width': '98%', 'height': '88%','margin': '0% 1%', 'padding': '0%', 'overflow': 'auto', 'direction': 'ltr', 'backgroundColor': 'black'}
                )
            ],
            style={'width': '100%', 'height': '94%','margin': '0%', 'padding': '0%','backgroundColor':window_background_color}
        )
    ]
    window_style = {'width': '55%', 'height': '80%', 'position': 'fixed', 'top': '11%', 'right': '22.5%', 'margin': '0%', 'padding': '0%'}

    return (window_children, window_style)


def serve_estimation_error_window(error_msg=''):
    """
    In case there was a problem while perfoming an estimation, this server function is called to display an appropriate error message to the user.
    """
    # If no error message is given, display a generic one
    if (error_msg == ''):
        error_msg = 'An error occured whilst perfoming the estimation, please choose another file or contact support if this problem persists. '
    
    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2("ERROR",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'}),
            html.Button("X", id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '10%', 'height': '100%', 'margin': '0%', 'verticalAlign': 'top'}),
        ],
            style={'width': '100%', 'height': '6%', 'backgroundColor': 'red'}),
        # Body
        html.Div(
            error_msg,
            style={'width': '100%', 'height': '94%', 'backgroundColor': 'blue',
                   'margin': '0%', 'padding': '0%', 'overflow': 'auto', 'direction': 'ltr', 'backgroundColor': '#C4C4C4','textAlign':'center'}
        )
    ]
    window_style = {'width': '40%', 'height': '60%', 'backgroundColor': 'green',  # grey #C4C4C4
                    'position': 'fixed', 'top': '21%', 'right': '30%', 'margin': '0%', 'padding': '0%','outline':'1px solid white'}

    return (window_children, window_style)


def serve_invalid_files_warning_window(already_uploaded_files,diff_patient_files):
    """
    Returns the children and the style properties of the warning window for invalid uploaded files
    """

    error_files_display_divs = []
    if (len(already_uploaded_files)>0):
        div = html.Div(
                [
                html.H4(
                    "The following files were not accepted because they have already been uploaded:",
                    style={}
                ),
                html.Div(
                    dcc.Markdown(already_uploaded_files),
                    style={'overflow':'auto'}
                )
                ],
                style={'height':'50%','display':'inline-block','margin':'auto','padding':'0px'}
             )
        error_files_display_divs.append(div)
    if (len(diff_patient_files)>0):
        div=html.Div(
                [
                html.H4(
                    "The following files were not accepted because they refer to a different patient than the one currently studied:",
                    style={}
                ),
                html.Div(
                    dcc.Markdown(diff_patient_files),
                    style={'overflow':'auto'}
                )
                ],
                style={'height':'50%','display':'inline-block','margin':'auto','padding':'0px'}
             )  
        error_files_display_divs.append(div)
    
    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2("",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block'}),
            html.Button("X", id={'type': 'uploaded_file_warning_div', 'index': 'X_button'},
                        style={'width': '5%', 'height': '100%', 'margin-left': '5%', 'verticalAlign': 'top'},
                        className = "x-button")
            ],
            style={'width': '100%', 'height': '10%','margin': '0%', 'padding': '0%'}
        ),
        # Body
        html.Div(
            error_files_display_divs,
            style={'width': '100%', 'height': '90%',
                   'margin': '0%', 'padding': '0%','textAlign':'center',"overflow":"auto"},
        )
    ]
    window_style = {'width': '40%', 'height': '40%','position': 'fixed', 'top': '20%', 'left': '30%', 'margin': '0%', 'padding': '0%','color':text_color, 'backgroundColor': background_color}
    return (window_children,window_style)


def serve_estimations_overview_window():
    """
    Returns the children and style properties of the estimation's overview window
    """
    estimations_dict = get_estimations_dict()
    # If there are no estimations to display, show this instead
    if (len(estimations_dict) == 0):
        overview = "No estimations performed yet."
    else:
        # Display the estimations as a Dash DataTable
        overview = dash_table.DataTable(
            list(estimations_dict.values()),
            #columns = [{"name": i, "id": i} for i in estimations_dict["0"].values()],
            #columns=["Estimation Type","File Used","Estimation Value","Notes"],
            style_cell = {'textAlign':'center','backgroundColor':'black','color':'white'},
            style_header={'textAlign':'center','backgroundColor':'black','color':'white','fontWeight': 'bold'},
            style_data = {'whiteSpace': 'normal','height': 'auto'},
            style_cell_conditional=[
                {'if': {'column_id': 'File Used'},'width': '15%'},
                {'if': {'column_id': 'Estimation Type'},'width': '18%'},
                {'if': {'column_id': 'Estimation Value'},'width': '18%'},
                {'if': {'column_id': 'Estimation Time'},'width': '18%'},
                {'if': {'column_id': 'Notes'},'width': '31%'},
            ],
            sort_action='native'
        )
   
    
    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}),
            html.H2("Performed Estimations Overview",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block', 'color':text_color}),
            html.Button("X", 
                        id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '5%', 'height': '100%', 'margin-left': '5%'},
                        className = "x-button"
            )
        ],
        style={'width': '100%', 'height': '6%', 'backgroundColor': window_background_color,'margin': '0%', 'padding': '0%'}
        ),
        # Body
        html.Div(
            overview,
            style={'width': '98%', 'height': '92%','margin': '0% 1%', 'padding': '0%', 'backgroundColor': 'black',"overflow":"auto",'textAlign':'center','color':text_color},
        )
    ]
    window_style = {'width': '55%', 'height': '80%','position': 'fixed', 'top': '11%', 'right': '22.5%', 'margin': '0%', 'padding': '0%',
                    'backgroundColor':background_color}
    return (window_children,window_style)


def serve_study_overview_window():
    """
    Serves the children and the style of the Study Overview Window
    """

    window_children = [
        # Header
        html.Header([
            html.Div([],
                     style={'width': '10%', 'height': '100%', 'margin': '0px', 'display': 'inline-block'}
            ),
            html.H2("Study Overview Window",
                    style={'width': '80%', 'height': '100%', 'margin': '0%', 'textAlign': 'center', 'verticalAlign': 'top', 'display':'inline-block','color':text_color}
            ),
            html.Button("X", 
                        id={'type': 'hidden_div_button', 'index': 'X_button'},
                        style={'width': '5%', 'height': '100%', 'margin-left': '5%'},
                        className = "x-button"
            )
        ],
        style={'width': '100%', 'height': '6%', 'backgroundColor': background_color,'margin': '0%', 'padding': '0%'}
        ),
        # Body
        html.Div(
            [
            dcc.Download(id={'type':'end_of_study_window','index':"download_study_summary"}),
            html.Button(
                "Download Study Summary",
                style={'width': '25%', 'height': '15%', 'margin': '10% 10% 2.5%','display':'inline-block','verticalAlign':'top'},
                id={'type':'end_of_study_window','index':'download_study_summary_button'},
                className="select-button"
            ),
            html.Button(
                "Reset Workspace",
                style={'width': '25%', 'height': '15%', 'margin': '10% 10% 2.5%','display':'inline-block','verticalAlign':'top'},
                id={'type':'end_of_study_window','index':'reset_workspace_button'},
                className="select-button"
            )
            ],
            style={'width': '100%', 'height': '94%', 'margin': '0%', 'padding': '0%', 'backgroundColor': background_color, 'textAlign':'center'},
        )
    ]
    window_style = {'width': '40%', 'height': '60%','position': 'fixed', 'top': '20%', 'right': '30%', 'margin': '0%', 'padding': '0%'}
    return (window_children,window_style)


def serve_scan_thumbnail(img_b64, thumbnail_index, text):
    """
    Given the base-64 byte representation of the image, it's index and the text, this function creates the corresponding thumbnail
    """
    scan_thumbnail = html.Div([
        html.Button(
            html.Img(src=img_b64, style={'width': '100%', 'height': '100%'}),
            style={'width': '100%', 'height': '90%'}, id={'type': 'scan_playbutton', 'index': str(thumbnail_index)}
        ),
        html.H4(text, style={'margin': '0%', 'direction': 'ltr','color':thumbnail_button_color}),
        html.Button("X", style={'width': '12%', 'height': '12%', 'position': 'absolute', 'top': '0', 'left': '0'},
                    id={'type': 'scan_remove_button', 'index': str(thumbnail_index)})
    ], style={'witdh': '90%', 'height': '40%', 'margin': '4%', 'position': 'relative'})

    return scan_thumbnail


def load_session_thumbnails():
    """
    Called from the controller when a session is to be loaded
    """
    thumbnail_tuples = load_session()
    thumbnails = []
    for thumbnail_input, scan_index, thumbnail_text in thumbnail_tuples:
        thumbnails.append(serve_scan_thumbnail(thumbnail_input, scan_index, thumbnail_text))
    
    return thumbnails