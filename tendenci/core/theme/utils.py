import os
from django.conf import settings
from tendenci.core.site_settings.utils import get_setting
from tendenci.core.theme.middleware import get_current_request

def get_theme():
    request = get_current_request()
    if request:
        theme = request.session.get('theme', get_setting('module', 'theme_editor', 'theme'))
    else:
        theme = get_setting('module', 'theme_editor', 'theme')
    return theme

def get_theme_root(theme=None):
    if theme is None: # default theme
        theme = get_theme()
    theme_root = (os.path.join(settings.THEMES_DIR, theme)).replace('\\', '/')
    return theme_root
    
def get_theme_template(template_name, theme=None):
    """Returns a relative path for the theme template.
    This is used primarily as an input for loader's get_template
    """
    if theme is None: # default theme
        theme = get_theme()
    theme_template = template_name
    return theme_template

def theme_options():
    """
    Returns a string of the available themes in THEMES_DIR
    """
    options = ''
    themes = sorted(theme_choices())
    themes.reverse()
    for theme in themes:
        options = '%s, %s' % (theme, options)
    return options[:-2]
    
def theme_choices():
    """
    Returns a list of available themes in THEMES_DIR
    """
    if hasattr(settings, 'USE_S3_STORAGE') and settings.USE_S3_STORAGE:
        from storages.backends.s3boto import S3BotoStorage
        s3bs = S3BotoStorage()
        print s3bs.listdir('themes/thinksmart')
        dirs, files=s3bs.listdir('themes/thinksmart')
        for theme in files:
            yield theme
    else:
        for theme in os.listdir(settings.THEMES_DIR):
            if os.path.isdir(os.path.join(settings.THEMES_DIR, theme)):
                yield theme
