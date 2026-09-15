import ee
from .load_vector import get_path

_initialized = False

def  initialize_ee():
    auth_mode = get_path('GEE_AUTH_MODE')
    project_id = get_path('PROJECT_ID')
    global _initialized

    if _initialized:
        return ee

    try:
        ee.Initialize(project=project_id)
        print('EE initialization successfull')

    except Exception:
        try:
            print('Starting EE authentification')
            ee.Authenticate(auth_mode=auth_mode)
            ee.Initialize(project=project_id)

        except Exception as e:
            print(f'Authentication error: {e}')
            raise

    _initialized = True
    return ee
