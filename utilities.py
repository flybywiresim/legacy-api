#####################################
########### API UTILITIES ###########
#####################################

class Utilities:
    @staticmethod
    def render(output):
        return(output, 200, {
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
        })