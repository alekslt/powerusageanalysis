from pyramid.view import view_config

from .models import (
    Measurements,
    )

mes = Measurements(0)

@view_config(route_name='measuredata', renderer='json')
def measuredata(request):
    return Measurements(0)

@view_config(route_name='measure', renderer='templates/measure.pt')
def measure(request):
    return mes.__json__(request)

@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'project': 'measure'}
