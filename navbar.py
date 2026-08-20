
# navbar.py
import dash_bootstrap_components as dbc
from dash import html

def create_navbar():
    navbar = dbc.Container(
        dbc.Row([
            dbc.Col(
                html.Img(
                    src=r'assets/Logo-Bleu-V2.png',
                    alt='image',
                    className='img-fluid',
                    style={'max-width': '180px','marginTop':"0px"}
                ),
                width=2,
                className='d-flex align-items-center justify-content-center'
            ),
            dbc.Col(
                dbc.NavbarSimple(
                    children=[],
                    brand="ClimateCheck : Say Hi to your Building Sim Weather Files",
                    brand_style={"textTransform": "none","fontFamily": "Verdana, sans-serif","fontSize": "17px"},
                    brand_href="/",
                    sticky="top",
                    color="#1f388b",  # couleur de fond
                    dark=True,        # texte clair
                    style={"height": '50px'}
                )
            )
        ],
        style={"marginBottom": "50px"}),
        fluid=False,
        style={"maxWidth": "1800px"}
    )
    return navbar
