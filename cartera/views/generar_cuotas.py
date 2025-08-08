from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from academico.models import Alumno
from cartera.models import Deuda, Cuota
from cartera.forms import GenerarCuotasForm
from cartera.utils import generar_fechas_pago
from academico.permissions import group_required

@login_required
@group_required('SecretariaCartera', 'Superusuario')
def generar_cuotas_view(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    try:
        deuda = Deuda.objects.get(alumno=alumno, estado='emitida')
    except Deuda.DoesNotExist:
        messages.error(request, 'El alumno no tiene una deuda activa.')
        return redirect('alumno_detail', pk=alumno.id)

    if Cuota.objects.filter(deuda=deuda).exists():
        messages.warning(request, 'Este alumno ya tiene cuotas generadas.')
        return redirect('alumno_detail', pk=alumno.id)

    if request.method == 'POST':
        form = GenerarCuotasForm(request.POST)
        if form.is_valid():
            frecuencia = form.cleaned_data['frecuencia']
            
            # Determinar las fechas de inicio y fin para la generación de cuotas
            if alumno.fecha_ingreso:
                fecha_inicio = alumno.fecha_ingreso
            else:
                fecha_inicio = timezone.localtime(timezone.now()).date()

            if alumno.fecha_culminacion:
                fecha_fin = alumno.fecha_culminacion
            else:
                fecha_fin = fecha_inicio + timezone.timedelta(days=365)

            valor_total = deuda.valor_total

            cuotas_a_crear = generar_fechas_pago(fecha_inicio, fecha_fin, frecuencia, valor_total)

            if not cuotas_a_crear:
                messages.error(request, 'No se pudieron generar cuotas con los parámetros seleccionados. Verifique las fechas del alumno.')
                return redirect('generar_cuotas', alumno_id=alumno.id)

            for fecha_vencimiento, monto in cuotas_a_crear:
                Cuota.objects.create(
                    deuda=deuda,
                    monto=monto,
                    fecha_vencimiento=fecha_vencimiento,
                    estado='pendiente'
                )
            
            deuda.cuotas_generadas = True
            deuda.save()

            messages.success(request, f'{len(cuotas_a_crear)} cuotas han sido creadas exitosamente.')
            return redirect('alumno_detail', pk=alumno.id)
    else:
        form = GenerarCuotasForm()

    context = {
        'form': form,
        'alumno': alumno,
        'deuda': deuda
    }
    return render(request, 'cartera/generar_cuotas_form.html', context)
