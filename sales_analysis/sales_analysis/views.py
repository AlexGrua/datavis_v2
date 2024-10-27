from django.shortcuts import render
from django.http import JsonResponse


def home_page_view(request):
    return JsonResponse({'message': 'OK'})