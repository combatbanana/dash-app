import dash

from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import base64
import io
import pyperclip

import dash_daq as daq
import plotly.graph_objects as go
import numpy as np
from PIL import Image

# Initialize the Dash app
app = dash.Dash(__name__)

df = pd.DataFrame()  # Placeholder for uploaded data
image_data = None  # Placeholder for uploaded image

app.layout = html.Div([
    html.H1("Daylighting Analysis"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV File'),
        multiple=False
    ),
    
    html.Label("Set UDI Threshold (%):"),
    dcc.Input(id='udi-threshold', type='number', value=50, min=0, max=100),
    
    html.Label("Set sDA Threshold (%):"),
    dcc.Input(id='sda-threshold', type='number', value=50, min=0, max=100),
    
    html.Label("Filter Zones (Include or Exclude containing word):"),
    dcc.Input(id='zone-filter', type='text', placeholder='Enter word to filter'),
    dcc.RadioItems(
        id='filter-mode',
        options=[
            {'label': 'Exclude', 'value': 'exclude'},
            {'label': 'Include', 'value': 'include'}
        ],
        value='exclude',
        inline=True
    ),
    dcc.Checklist(id='zone-checklist', inline=False),
    
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        style_table={'overflowX': 'auto'}
    ),
    
    html.Button("Copy Table to Clipboard", id="copy-btn", n_clicks=0),
    dcc.Textarea(id="clipboard-data", style={'display': 'none'}),

    html.H2("Upload Building Plan (PNG)"),
    dcc.Upload(
        id='upload-image',
        children=html.Button('Upload PNG File'),
        multiple=False
    ),
    html.Div(id='image-container', children=[]),
    dcc.Graph(id='image-overlay', config={'modeBarButtonsToAdd': ['drawopenpath']}),
    dcc.Dropdown(id='zone-dropdown', options=[], style={'display': 'none'}),
    html.Div(id='overlay-results', children="")
])

@app.callback(
    [Output('image-overlay', 'figure'),
     Output('zone-dropdown', 'options')],
    Input('upload-image', 'contents')
)
def display_image(contents):
    global image_data
    if not contents:
        return go.Figure(), []
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    image_data = Image.open(io.BytesIO(decoded))
    width, height = image_data.size
    
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=image_data,
            xref="x",
            yref="y",
            x=0,
            y=height,
            sizex=width,
            sizey=height,
            xanchor="left",
            yanchor="top",
            layer="below"
        )
    )
    fig.update_xaxes(visible=False, range=[0, width])
    fig.update_yaxes(visible=False, range=[0, height])
    fig.update_layout(width=800, height=600, dragmode='pan')
    
    if df.empty:
        return fig, []
    
    all_zones = df['Zone'].dropna().unique().tolist()
    dropdown_options = [{'label': z, 'value': z} for z in all_zones]
    
    return fig, dropdown_options

@app.callback(
    [Output('zone-dropdown', 'style'),
     Output('zone-dropdown', 'value')],
    Input('image-overlay', 'clickData')
)
def show_dropdown_on_click(clickData):
    if not clickData:
        return {'display': 'none'}, None
    return {'display': 'block'}, None

@app.callback(
    Output('overlay-results', 'children'),
    [Input('zone-dropdown', 'value')]
)
def overlay_results(selected_zone):
    if not selected_zone or df.empty:
        return ""
    
    zone_data = df[df['Zone'] == selected_zone].iloc[0]
    sda_result = f"sDA: {zone_data['sDA Area in Range (%)']}% ({'Pass' if zone_data['sDA Area in Range (%)'] >= 50 else 'Fail'})"
    udi_result = f"UDI: {zone_data['UDI Area in Range (%)']}% ({'Pass' if zone_data['UDI Area in Range (%)'] >= 50 else 'Fail'})"
    
    return html.Div([
        html.H3(f"Results for {selected_zone}"),
        html.P(sda_result),
        html.P(udi_result)
    ])

if __name__ == '__main__':
    app.run_server(debug=True)
