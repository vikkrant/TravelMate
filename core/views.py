from django.shortcuts import render

def landing_page(request):
    return render(request, 'core/landing.html')

def test_dark_mode(request):
    return render(request, 'test_dark_mode.html')

def test(request):
    return render(request, 'test.html') 