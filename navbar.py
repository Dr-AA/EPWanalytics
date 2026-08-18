
# navbar.py
import dash_bootstrap_components as dbc
from dash import html

def create_navbar():
    navbar = html.Div([
        dbc.Row([
            dbc.Col(
                html.Img(
                    src=r'assets/Logo-Bleu-V2.png',
                    alt='image',
                    className='img-fluid',
                    style={'max-width': '140px'}
                ),
                width=2,
                className='d-flex align-items-center justify-content-center'
            ),
            dbc.Col(
                dbc.NavbarSimple(
                    children=[],
                    brand="ClimateViz : get to know your weather files for building thermal simulations",
                    brand_style={"textTransform": "none"},
                    brand_href="/",
                    sticky="top",
                    color="#1f388b",  # couleur de fond
                    dark=True,        # texte clair
                    style={"height": '50px'}
                )
            )
        ],
        style={"marginBottom": "0px"})
    ])
    return navbar
