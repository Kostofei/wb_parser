from django.shortcuts import render

from parser.models import Item


def main_page_view(request):
    items = Item.objects.all()
    context = {
        'items': items
    }
    return render(request, 'main_page.html', context)
