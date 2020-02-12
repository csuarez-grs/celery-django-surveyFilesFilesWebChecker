from SurveyFilesWebChecker.settings import web_title

def add_variable_to_context(request):
    return {
        'web_title': web_title
    }