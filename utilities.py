'''
API Utilities

This package provides a utility methods to aid development
of the API.
'''

def render(output):
    '''
    Returns the provided response with access and cache headers set.

    Parameters:
        output (object):The response object to be wrapped with headers

    Returns:
        render(object):The response with status code and headers added
    '''

    return (output, 200, {
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
    })
