import ee

from modules.load_data import get_path

def  _initialize_ee():
    print("Starting ee initialization")

    auth_mode = get_path('GEE_AUTH_MODE')
    project_id = get_path('PROJECT_ID')

    try:
        ee.Authenticate(auth_mode=auth_mode)
        ee.Initialize(project=project_id)

    except Exception as e:
        print(f'Authentication error: {e}')
        raise

_initialize_ee()