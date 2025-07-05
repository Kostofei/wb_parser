from django.shortcuts import render

from parser.models import Item


def main_page_view(request):
    return render(request, 'main_page.html')
