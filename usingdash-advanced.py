import pandas as pd
import plotly.graph_objects as go
import base64
import io
from dash import Dash, dcc, html, Input, Output, State, ALL, dash_table
from datetime import datetime

app = Dash(__name__)

df = pd.DataFrame()

app.layout = html.Div([
    html.H1("Dynamic Data Band Analyzer"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload CSV File'),
        multiple=False
    ),
    
    dcc.Dropdown(id='parameter-dropdown', placeholder="Select Parameter"),
    dcc.Checklist(id='zone-checklist', inline=True),
    
    html.Div([
        html.Label("Enter Bands (comma separated, e.g. 18,21,30)"),
        dcc.Input(id='bands-input', type='text', value='18,21,30'),
    ]),
    
    html.Div([
        html.Label("Enter Fail Thresholds (format: value:hours, e.g. 25:80,28:40)"),
        dcc.Input(id='fail-thresholds', type='text', value='25:80,28:40'),
    ]),
    
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=None,
        end_date=None,
        display_format='YYYY-MM-DD'
    ),
    
    dcc.RangeSlider(id='time-slider', min=0, max=23, step=1, value=[0, 23],
                    marks={i: str(i) for i in range(0, 24, 2)}),
    
    dcc.Graph(id='data-graph'),
    dash_table.DataTable(id='data-table')
])

@app.callback(
    [Output('parameter-dropdown', 'options'),
     Output('zone-checklist', 'options'),
     Output('zone-checklist', 'value'),
     Output('date-picker-range', 'start_date'),
     Output('date-picker-range', 'end_date')],
    Input('upload-data', 'contents')
)
def parse_data(contents):
    global df
    if contents is None:
        return [], [], [], None, None
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    csv_data = io.StringIO(decoded.decode('utf-8'))
    
    try:
        df_raw = pd.read_csv(csv_data, skiprows=2, header=None)
        param_names = df_raw.iloc[0, 1:].tolist()
        zone_names = df_raw.iloc[1, 1:].tolist()
        new_columns = ['Datetime'] + [f'{zone} {param}' for zone, param in zip(zone_names, param_names)]
        df = df_raw.iloc[2:].reset_index(drop=True)
        
        df.columns = new_columns
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['Datetime'] = df['Datetime'].astype(str).str[7:]
        df['Datetime'] = pd.to_datetime(df['Datetime'], format='%b %d %I:%M %p', errors='coerce')
        df = df.dropna(subset=['Datetime'])
        
        df['Date'] = df['Datetime'].dt.date  # Extract the date without time
        
        parameters = set(param_names)
        zones = set(zone_names)
        
        start_date = df['Date'].min()
        end_date = df['Date'].max()
        
        return ([{'label': p, 'value': p} for p in parameters],
                [{'label': z, 'value': z} for z in zones],
                list(zones),
                start_date,
                end_date)
    
    except Exception as e:
        print("Error parsing CSV:", str(e))
        return [], [], [], None, None

@app.callback(
    Output('data-graph', 'figure'),
    [Input('parameter-dropdown', 'value'),
     Input('zone-checklist', 'value'),
     Input('bands-input', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph(parameter, selected_zones, bands, start_date, end_date):
    if df.empty or not parameter or not selected_zones:
        print("No data or missing selections.")
        return go.Figure()
    
    df_filtered = df.copy()
    if start_date and end_date:
        df_filtered = df_filtered[(df_filtered['Date'] >= pd.to_datetime(start_date).date()) &
                                  (df_filtered['Date'] <= pd.to_datetime(end_date).date())]
    
    bands = [float(x) for x in bands.split(',')]
    bands.sort()
    band_labels = [f'Below {bands[0]}'] + [f'{bands[i]}-{bands[i+1]}' for i in range(len(bands)-1)] + [f'Above {bands[-1]}']
    
    band_counts = {zone: {label: 0 for label in band_labels} for zone in selected_zones}
    
    for zone in selected_zones:
        col_name = f'{zone} {parameter}'
        if col_name in df_filtered.columns:
            for value in df_filtered[col_name].dropna():
                if value < bands[0]:
                    band_counts[zone][f'Below {bands[0]}'] += 1
                elif value > bands[-1]:
                    band_counts[zone][f'Above {bands[-1]}'] += 1
                else:
                    for i in range(len(bands) - 1):
                        if bands[i] <= value < bands[i + 1]:
                            band_counts[zone][f'{bands[i]}-{bands[i + 1]}'] += 1
    
    fig = go.Figure()
    for band_label in band_labels:
        fig.add_trace(go.Bar(
            x=list(selected_zones),
            y=[band_counts[zone][band_label] for zone in selected_zones],
            name=band_label
        ))
    
    fig.update_layout(
        barmode='stack',
        title=f'{parameter} Distribution Across Zones',
        xaxis_title='Zones',
        yaxis_title='Hours in Band'
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)