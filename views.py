
from django.shortcuts import render_to_response

def serve_templates(request, document_root, path):
  return render_to_response(document_root + "/" + path)
