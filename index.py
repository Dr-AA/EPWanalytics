# index.py
from dash import html, dcc
from dash.dependencies import Input, Output
from app import app

from navbar import create_navbar
from weather_graph.page_weather_graph import create_page_weather_graph
from weather_graph.callbacks_weather_graph import callbacks_weather_graph


nav = create_navbar()

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    nav,
    dcc.Store(id='y-fixed-store', data={"active": False, "var": None, "range": None}),
    dcc.Store(id='epw-store', data=None),   # on y mettra le DF sérialisé si besoin
    dcc.Store(id='axes-store', data={'x': None, 'y': None}),
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    return create_page_weather_graph()


callbacks_weather_graph(app)


if __name__ == '__main__':
    app.run(debug=True)
