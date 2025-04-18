from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages

def cambiar_contraseña(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            logout(request)
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('/')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'usuarios/cambiar_contraseña.html', {'form': form})