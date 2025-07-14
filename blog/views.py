from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import PatientRegistrationForm, MedecinRegistrationForm, SpecialiteForm, CreneauForm
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from .models import Patient, RendezVous, Medecin, DossierMedical, User, Specialite, Creneau, CompteRendu
from django.utils import timezone
from datetime import datetime

# Create your views here.

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and hasattr(u, 'role') and u.role == 'admin')(view_func)

def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compte patient créé avec succès. Connectez-vous.')
            return redirect('login')
    else:
        form = PatientRegistrationForm()
    return render(request, 'registration/register_patient.html', {'form': form})

def login_view(request):
    error = None
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if hasattr(user, 'role'):
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'patient':
                    return redirect('patient_rendezvous')
                elif user.role == 'medecin':
                    return redirect('medecin_dashboard')
            return redirect('/')
        else:
            error = "Identifiants invalides."
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'error': error})

@login_required
def patient_dashboard(request):
    return render(request, 'patient/dashboard.html')

@login_required
def patient_rendezvous(request):
    try:
        patient = Patient.objects.get(user=request.user)
        rendezvous = RendezVous.objects.filter(patient=patient).select_related('medecin').order_by('-date_heure')
    except Patient.DoesNotExist:
        rendezvous = []
    return render(request, 'patient/mes_rendez_vous.html', {
        'rendezvous': rendezvous,
        'today': timezone.now().date(),
        'now': timezone.now()
    })

@login_required
def prendre_rendezvous(request):
    medecins = Medecin.objects.all()
    min_date = timezone.now().strftime('%Y-%m-%d')
    creneaux = []
    heures_disponibles = []
    selected_medecin = None
    selected_date = None
    selected_heure = None
    error = None
    info_message = None
    
    # Récupérer les paramètres de la requête (GET ou POST)
    medecin_id = request.POST.get('medecin') or request.GET.get('medecin')
    date_rdv = request.POST.get('date_rdv') or request.GET.get('date_rdv')
    heure_rdv = request.POST.get('heure_rdv') or request.GET.get('heure_rdv')
    motif = request.POST.get('motif') or request.GET.get('motif')
    observations = request.POST.get('observations') or request.GET.get('observations')
    
    # Générer les heures disponibles si un médecin et une date sont sélectionnés
    if medecin_id:
        try:
            selected_medecin = Medecin.objects.get(id=medecin_id)
            if date_rdv:
                selected_date = date_rdv
                from datetime import datetime, timedelta, time
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
                jour_semaine = jours[date_obj.weekday()]
                creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
                
                if not creneaux.exists():
                    info_message = f"Le Dr. {selected_medecin.nom} n'a pas de créneaux définis pour le {jour_semaine}. Veuillez choisir une autre date ou contacter le médecin."
                else:
                    # Générer les heures disponibles par pas de 30 minutes
                    for creneau in creneaux:
                        current = datetime.combine(date_obj, creneau.heure_debut)
                        end = datetime.combine(date_obj, creneau.heure_fin)
                        while current < end:
                            heure_str = current.strftime('%H:%M')
                            # Vérifier si l'heure est déjà prise
                            date_heure = timezone.make_aware(current)
                            # Vérifier que l'heure n'est pas dans le passé pour aujourd'hui
                            if date_obj == timezone.now().date():
                                if current.time() <= timezone.now().time():
                                    current += timedelta(minutes=30)
                                    continue
                            if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exists():
                                heures_disponibles.append(heure_str)
                            current += timedelta(minutes=30)
                    
                    if not heures_disponibles and creneaux.exists():
                        info_message = f"Tous les créneaux du Dr. {selected_medecin.nom} pour le {jour_semaine} sont déjà réservés. Veuillez choisir une autre date."
        except Medecin.DoesNotExist:
            error = "Médecin non trouvé."
    
    if request.method == 'POST' and 'valider' in request.POST:
        try:
            patient = Patient.objects.get(user=request.user)
            medecin = Medecin.objects.get(id=medecin_id)
            from datetime import datetime
            
            # Validation de la date
            if not date_rdv:
                raise Exception("Veuillez sélectionner une date.")
            
            date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
            today = timezone.now().date()
            
            # Vérifier que la date n'est pas dans le passé
            if date_obj < today:
                raise Exception("Impossible de prendre un rendez-vous pour une date antérieure à aujourd'hui.")
            
            # Validation de l'heure
            if not heure_rdv:
                raise Exception("Veuillez choisir une heure valide.")
            
            heure_obj = datetime.strptime(heure_rdv, '%H:%M').time()
            date_heure = datetime.combine(date_obj, heure_obj)
            date_heure = timezone.make_aware(date_heure)
            
            # Vérifier que la date/heure n'est pas dans le passé
            if date_heure <= timezone.now():
                raise Exception("Impossible de prendre un rendez-vous pour une date et heure antérieure à maintenant.")
            
            # Vérifier que l'heure choisie est bien dans un créneau du médecin
            heure_valide = False
            for creneau in creneaux:
                if creneau.heure_debut <= heure_obj < creneau.heure_fin:
                    heure_valide = True
                    break
            if not heure_valide:
                raise Exception("L'heure choisie ne correspond pas aux horaires du médecin ce jour-là.")
            
            # Vérifier qu'il n'y a pas déjà un rendez-vous à cette heure
            if RendezVous.objects.filter(medecin=medecin, date_heure=date_heure).exists():
                raise Exception("Ce créneau est déjà réservé.")
            
            fichier = request.FILES.get('fichier')
            
            rendezvous = RendezVous(
                patient=patient,
                medecin=medecin,
                date_heure=date_heure,
                motif=motif,
                statut='en attente',
            )
            rendezvous.full_clean()
            rendezvous.save()
            if fichier:
                dossier, created = DossierMedical.objects.get_or_create(patient=patient)
                dossier.fichiers = fichier
                dossier.save()
            return redirect('patient_rendezvous')
        except Exception as e:
            error = str(e)
    
    return render(request, 'patient/prendre_rendez_vous.html', {
        'medecins': medecins,
        'heures_disponibles': heures_disponibles,
        'selected_medecin': selected_medecin,
        'selected_date': selected_date,
        'selected_heure': selected_heure,
        'min_date': min_date,
        'error': error,
        'info_message': info_message
    })

@login_required
def patient_dossier(request):
    try:
        patient = Patient.objects.get(user=request.user)
        dossier = DossierMedical.objects.get(patient=patient)
    except (Patient.DoesNotExist, DossierMedical.DoesNotExist):
        dossier = None
    return render(request, 'patient/dossier.html', {'dossier': dossier})


def logout_view(request):
    logout(request)
    return redirect('login')


def home(request):
    return render(request, 'home.html')

@admin_required
def patient_list(request):
    patients = Patient.objects.select_related('user').all()
    return render(request, 'admin/patient_list.html', {'patients': patients})

@admin_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('patient_list')
    else:
        form = PatientRegistrationForm()
    return render(request, 'admin/patient_form.html', {'form': form})

@admin_required
def patient_update(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    user = patient.user
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST, instance=user)
        if form.is_valid():
            form.save(patient_instance=patient)
            return redirect('patient_list')
    else:
        initial = {
            'date_naissance': patient.date_naissance,
            'adresse': patient.adresse,
            'telephone': patient.telephone,
            'username': user.username,
            'email': user.email,
        }
        form = PatientRegistrationForm(instance=user, initial=initial)
    return render(request, 'admin/patient_form.html', {'form': form})

@admin_required
def patient_delete(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    if request.method == 'POST':
        user = patient.user
        patient.delete()
        user.delete()
        return redirect('patient_list')
    return render(request, 'admin/patient_confirm_delete.html', {'patient': patient})

@admin_required
def admin_dashboard(request):
    total_patients = Patient.objects.count()
    total_medecins = Medecin.objects.count()
    total_rendezvous = RendezVous.objects.count()
    total_specialites = Specialite.objects.count()
    nb_dossiers = DossierMedical.objects.count()
    
    return render(request, 'admin/dashboard.html', {
        'total_patients': total_patients,
        'total_medecins': total_medecins,
        'total_rendezvous': total_rendezvous,
        'total_specialites': total_specialites,
        'nb_dossiers': nb_dossiers,
    })

@admin_required
def admin_rendezvous(request):
    rendezvous = RendezVous.objects.select_related('patient', 'medecin').all().order_by('-date_heure')
    return render(request, 'admin/rendezvous.html', {'rendezvous': rendezvous})

@admin_required
def admin_dossiers(request):
    dossiers = DossierMedical.objects.select_related('patient').all()
    return render(request, 'admin/dossiers.html', {'dossiers': dossiers})

@admin_required
def medecin_list(request):
    medecins = Medecin.objects.all()
    return render(request, 'admin/medecin_list.html', {'medecins': medecins})

@admin_required
def medecin_create(request):
    if request.method == 'POST':
        form = MedecinRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('medecin_list')
    else:
        form = MedecinRegistrationForm()
    return render(request, 'admin/medecin_form.html', {'form': form})

@admin_required
def medecin_update(request, medecin_id):
    medecin = get_object_or_404(Medecin, id=medecin_id)
    user = medecin.user
    if request.method == 'POST':
        form = MedecinRegistrationForm(request.POST, instance=user)
        form.fields['username'].disabled = True
        form.fields['password1'].required = False
        form.fields['password2'].required = False
        if form.is_valid():
            form.save(medecin_instance=medecin)
            return redirect('medecin_list')
    else:
        initial = {
            'nom': medecin.nom,
            'prenom': medecin.prenom,
            'specialite': medecin.specialite,
            'username': user.username,
            'email': user.email,
        }
        form = MedecinRegistrationForm(instance=user, initial=initial)
        form.fields['username'].disabled = True
        form.fields['password1'].required = False
        form.fields['password2'].required = False
    return render(request, 'admin/medecin_form.html', {'form': form})

@admin_required
def medecin_delete(request, medecin_id):
    medecin = get_object_or_404(Medecin, id=medecin_id)
    if request.method == 'POST':
        user = medecin.user
        medecin.delete()
        user.delete()
        return redirect('medecin_list')
    return render(request, 'admin/medecin_confirm_delete.html', {'medecin': medecin})

@admin_required
def specialite_list(request):
    specialites = Specialite.objects.all().order_by('nom')
    return render(request, 'admin/specialite_list.html', {'specialites': specialites})

@admin_required
def specialite_create(request):
    if request.method == 'POST':
        form = SpecialiteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Spécialité ajoutée avec succès.')
            return redirect('specialite_list')
    else:
        form = SpecialiteForm()
    return render(request, 'admin/specialite_form.html', {'form': form, 'title': 'Ajouter une spécialité'})

@admin_required
def specialite_update(request, specialite_id):
    specialite = get_object_or_404(Specialite, id=specialite_id)
    if request.method == 'POST':
        form = SpecialiteForm(request.POST, instance=specialite)
        if form.is_valid():
            form.save()
            messages.success(request, 'Spécialité modifiée avec succès.')
            return redirect('specialite_list')
    else:
        form = SpecialiteForm(instance=specialite)
    return render(request, 'admin/specialite_form.html', {'form': form, 'title': 'Modifier la spécialité'})

@admin_required
def specialite_delete(request, specialite_id):
    specialite = get_object_or_404(Specialite, id=specialite_id)
    if request.method == 'POST':
        specialite.delete()
        messages.success(request, 'Spécialité supprimée avec succès.')
        return redirect('specialite_list')
    return render(request, 'admin/specialite_confirm_delete.html', {'specialite': specialite})

@login_required
def medecin_dashboard(request):
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = RendezVous.objects.filter(medecin=medecin).select_related('patient').order_by('-date_heure')
        nb_rendezvous = rendezvous.count()
        nb_rendezvous_aujourd_hui = rendezvous.filter(date_heure__date=timezone.now().date()).count()
    except Medecin.DoesNotExist:
        rendezvous = []
        nb_rendezvous = 0
        nb_rendezvous_aujourd_hui = 0
    
    return render(request, 'medecin/dashboard.html', {
        'medecin': medecin,
        'rendezvous': rendezvous[:5],  # Les 5 derniers rendez-vous
        'nb_rendezvous': nb_rendezvous,
        'nb_rendezvous_aujourd_hui': nb_rendezvous_aujourd_hui
    })

@login_required
def medecin_rendezvous(request):
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = RendezVous.objects.filter(medecin=medecin).select_related('patient').order_by('-date_heure')
    except Medecin.DoesNotExist:
        rendezvous = []
    
    return render(request, 'medecin/rendezvous.html', {
        'medecin': medecin,
        'rendezvous': rendezvous,
        'today': timezone.now().date()
    })

@login_required
def medecin_rendezvous_detail(request, rdv_id):
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, medecin=medecin)
        
        # Récupérer le dossier médical du patient
        dossier = DossierMedical.objects.filter(patient=rendezvous.patient).first()
        
        # Récupérer les comptes rendus existants
        comptes_rendus = rendezvous.comptes_rendus.all()
        
        if request.method == 'POST':
            # Gestion du changement de statut
            nouveau_statut = request.POST.get('statut')
            if nouveau_statut in ['en attente', 'confirmé', 'annulé']:
                rendezvous.statut = nouveau_statut
                rendezvous.save()
                messages.success(request, f'Statut du rendez-vous mis à jour : {nouveau_statut}')
                return redirect('medecin_rendezvous_detail', rdv_id=rdv_id)
        
        return render(request, 'medecin/rendezvous_detail.html', {
            'medecin': medecin,
            'rendezvous': rendezvous,
            'dossier': dossier,
            'comptes_rendus': comptes_rendus,
            'today': timezone.now().date()
        })
    except Medecin.DoesNotExist:
        return redirect('login')

@login_required
def medecin_patients(request):
    try:
        medecin = Medecin.objects.get(user=request.user)
        # Récupérer tous les patients
        patients = Patient.objects.all().select_related('user')
    except Medecin.DoesNotExist:
        patients = []
    
    return render(request, 'medecin/patients.html', {
        'medecin': medecin,
        'patients': patients
    })

@login_required
def confirmer_rendezvous(request, rdv_id):
    rdv = get_object_or_404(RendezVous, id=rdv_id)
    rdv.statut = 'confirmé'
    rdv.save()
    return redirect('medecin_rendezvous')

@login_required
def annuler_rendezvous(request, rdv_id):
    rdv = get_object_or_404(RendezVous, id=rdv_id)
    rdv.statut = 'annulé'
    rdv.save()
    return redirect('medecin_rendezvous')

@login_required
def medecin_patient_dossier(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    try:
        dossier = DossierMedical.objects.get(patient=patient)
    except DossierMedical.DoesNotExist:
        dossier = None
    return render(request, 'medecin/dossier_patient.html', {'dossier': dossier, 'patient': patient})

@login_required
def medecin_creneaux(request):
    medecin = getattr(request.user, 'medecin', None)
    if not medecin:
        return redirect('medecin_dashboard')
    creneaux = Creneau.objects.filter(medecin=medecin).order_by('jour', 'heure_debut')
    return render(request, 'medecin/creneaux.html', {'creneaux': creneaux})

@login_required
def medecin_creneau_create(request):
    medecin = getattr(request.user, 'medecin', None)
    if not medecin:
        return redirect('medecin_dashboard')
    if request.method == 'POST':
        form = CreneauForm(request.POST)
        if form.is_valid():
            creneau = form.save(commit=False)
            creneau.medecin = medecin
            creneau.save()
            return redirect('medecin_creneaux')
    else:
        form = CreneauForm()
    return render(request, 'medecin/creneau_form.html', {'form': form})

@login_required
def medecin_creneau_update(request, creneau_id):
    medecin = getattr(request.user, 'medecin', None)
    creneau = get_object_or_404(Creneau, id=creneau_id, medecin=medecin)
    if request.method == 'POST':
        form = CreneauForm(request.POST, instance=creneau)
        if form.is_valid():
            form.save()
            return redirect('medecin_creneaux')
    else:
        form = CreneauForm(instance=creneau)
    return render(request, 'medecin/creneau_form.html', {'form': form})

@login_required
def medecin_creneau_delete(request, creneau_id):
    medecin = getattr(request.user, 'medecin', None)
    creneau = get_object_or_404(Creneau, id=creneau_id, medecin=medecin)
    if request.method == 'POST':
        creneau.delete()
        return redirect('medecin_creneaux')
    return render(request, 'medecin/creneau_confirm_delete.html', {'creneau': creneau})

@login_required
def modifier_statut_rendezvous(request, rdv_id):
    medecin = getattr(request.user, 'medecin', None)
    rdv = get_object_or_404(RendezVous, id=rdv_id, medecin=medecin)
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in ['en attente', 'confirmé', 'annulé']:
            rdv.statut = nouveau_statut
            rdv.save()
            return redirect('medecin_rendezvous')
    
    return render(request, 'medecin/modifier_statut_rendezvous.html', {
        'rendezvous': rdv,
        'statuts_disponibles': [
            ('en attente', 'En attente'),
            ('confirmé', 'Confirmé'),
            ('annulé', 'Annulé'),
        ]
    })

@admin_required
def admin_rendezvous_create(request):
    medecins = Medecin.objects.all()
    patients = Patient.objects.all()
    min_date = timezone.now().strftime('%Y-%m-%d')
    creneaux = []
    heures_disponibles = []
    selected_medecin = None
    selected_patient = None
    selected_date = None
    selected_heure = None

    if request.method == 'POST':
        medecin_id = request.POST.get('medecin')
        patient_id = request.POST.get('patient')
        date_rdv = request.POST.get('date_rdv')
        heure_rdv = request.POST.get('heure_rdv')
        motif = request.POST.get('motif')

        if patient_id:
            selected_patient = Patient.objects.get(id=patient_id)

        if medecin_id:
            selected_medecin = Medecin.objects.get(id=medecin_id)
            if date_rdv:
                selected_date = date_rdv
                from datetime import datetime, timedelta, time
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
                jour_semaine = jours[date_obj.weekday()]
                creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
                # Générer les heures disponibles par pas de 30 minutes
                for creneau in creneaux:
                    current = datetime.combine(date_obj, creneau.heure_debut)
                    end = datetime.combine(date_obj, creneau.heure_fin)
                    while current < end:
                        heure_str = current.strftime('%H:%M')
                        # Vérifier si l'heure est déjà prise
                        date_heure = timezone.make_aware(current)
                        
                        # Vérifier que l'heure n'est pas dans le passé pour aujourd'hui
                        if date_obj == timezone.now().date():
                            if current.time() <= timezone.now().time():
                                current += timedelta(minutes=30)
                                continue
                        
                        if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exists():
                            heures_disponibles.append(heure_str)
                        current += timedelta(minutes=30)

        if 'valider' in request.POST:
            try:
                patient = Patient.objects.get(id=patient_id)
                medecin = Medecin.objects.get(id=medecin_id)
                from datetime import datetime
                
                # Validation de la date
                if not date_rdv:
                    raise Exception("Veuillez sélectionner une date.")
                
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                today = timezone.now().date()
                
                # Vérifier que la date n'est pas dans le passé
                if date_obj < today:
                    raise Exception("Impossible de créer un rendez-vous pour une date antérieure à aujourd'hui.")
                
                # Validation de l'heure
                if not heure_rdv:
                    raise Exception("Veuillez choisir une heure valide.")
                
                heure_obj = datetime.strptime(heure_rdv, '%H:%M').time()
                date_heure = datetime.combine(date_obj, heure_obj)
                date_heure = timezone.make_aware(date_heure)

                # Vérifier que la date/heure n'est pas dans le passé
                if date_heure <= timezone.now():
                    raise Exception("Impossible de créer un rendez-vous pour une date et heure antérieure à maintenant.")

                # Vérifier que l'heure choisie est bien dans un créneau du médecin
                heure_valide = False
                for creneau in creneaux:
                    if creneau.heure_debut <= heure_obj < creneau.heure_fin:
                        heure_valide = True
                        break
                if not heure_valide:
                    raise Exception("L'heure choisie ne correspond pas aux horaires du médecin ce jour-là.")

                # Vérifier qu'il n'y a pas déjà un rendez-vous à cette heure
                if RendezVous.objects.filter(medecin=medecin, date_heure=date_heure).exists():
                    raise Exception("Ce créneau est déjà réservé.")

                rendezvous = RendezVous(
                    patient=patient,
                    medecin=medecin,
                    date_heure=date_heure,
                    motif=motif,
                    statut='en attente',  # Par défaut en attente
                )
                rendezvous.full_clean()
                rendezvous.save()
                return redirect('admin_rendezvous')
            except Exception as e:
                error_message = str(e)
                return render(request, 'admin/rendezvous_create.html', {
                    'medecins': medecins,
                    'patients': patients,
                    'heures_disponibles': heures_disponibles,
                    'selected_medecin': selected_medecin,
                    'selected_patient': selected_patient,
                    'selected_date': selected_date,
                    'selected_heure': heure_rdv,
                    'min_date': min_date,
                    'error': error_message
                })
        return render(request, 'admin/rendezvous_create.html', {
            'medecins': medecins,
            'patients': patients,
            'heures_disponibles': heures_disponibles,
            'selected_medecin': selected_medecin,
            'selected_patient': selected_patient,
            'selected_date': selected_date,
            'selected_heure': selected_heure,
            'min_date': min_date
        })
    else:
        return render(request, 'admin/rendezvous_create.html', {
            'medecins': medecins,
            'patients': patients,
            'heures_disponibles': heures_disponibles,
            'selected_medecin': selected_medecin,
            'selected_patient': selected_patient,
            'selected_date': selected_date,
            'selected_heure': selected_heure,
            'min_date': min_date
        })

@admin_required
def admin_rendezvous_update(request, rdv_id):
    rendezvous = get_object_or_404(RendezVous, id=rdv_id)
    medecins = Medecin.objects.all()
    patients = Patient.objects.all()
    min_date = timezone.now().strftime('%Y-%m-%d')
    creneaux = []
    heures_disponibles = []
    selected_medecin = rendezvous.medecin
    selected_patient = rendezvous.patient
    selected_date = rendezvous.date_heure.date().strftime('%Y-%m-%d')
    selected_heure = rendezvous.date_heure.strftime('%H:%M')
    error = None

    if request.method == 'POST':
        medecin_id = request.POST.get('medecin')
        patient_id = request.POST.get('patient')
        date_rdv = request.POST.get('date_rdv')
        heure_rdv = request.POST.get('heure_rdv')
        motif = request.POST.get('motif')

        if patient_id:
            selected_patient = Patient.objects.get(id=patient_id)
        if medecin_id:
            selected_medecin = Medecin.objects.get(id=medecin_id)
            if date_rdv:
                selected_date = date_rdv
                from datetime import datetime, timedelta
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
                jour_semaine = jours[date_obj.weekday()]
                creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
                for creneau in creneaux:
                    current = datetime.combine(date_obj, creneau.heure_debut)
                    end = datetime.combine(date_obj, creneau.heure_fin)
                    while current < end:
                        heure_str = current.strftime('%H:%M')
                        date_heure = timezone.make_aware(current)
                        
                        # Vérifier que l'heure n'est pas dans le passé pour aujourd'hui
                        if date_obj == timezone.now().date():
                            if current.time() <= timezone.now().time():
                                current += timedelta(minutes=30)
                                continue
                        
                        # Exclure l'heure du rendez-vous actuel
                        if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exclude(id=rdv_id).exists():
                            heures_disponibles.append(heure_str)
                        current += timedelta(minutes=30)
        if 'valider' in request.POST:
            try:
                patient = Patient.objects.get(id=patient_id)
                medecin = Medecin.objects.get(id=medecin_id)
                from datetime import datetime
                
                # Validation de la date
                if not date_rdv:
                    raise Exception("Veuillez sélectionner une date.")
                
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                today = timezone.now().date()
                
                # Vérifier que la date n'est pas dans le passé
                if date_obj < today:
                    raise Exception("Impossible de modifier un rendez-vous pour une date antérieure à aujourd'hui.")
                
                # Validation de l'heure
                if not heure_rdv:
                    raise Exception("Veuillez choisir une heure valide.")
                
                heure_obj = datetime.strptime(heure_rdv, '%H:%M').time()
                date_heure = datetime.combine(date_obj, heure_obj)
                date_heure = timezone.make_aware(date_heure)
                
                # Vérifier que la date/heure n'est pas dans le passé
                if date_heure <= timezone.now():
                    raise Exception("Impossible de modifier un rendez-vous pour une date et heure antérieure à maintenant.")
                
                # Vérifier que l'heure choisie est bien dans un créneau du médecin
                heure_valide = False
                for creneau in creneaux:
                    if creneau.heure_debut <= heure_obj < creneau.heure_fin:
                        heure_valide = True
                        break
                if not heure_valide:
                    raise Exception("L'heure choisie ne correspond pas aux horaires du médecin ce jour-là.")
                
                # Vérifier qu'il n'y a pas déjà un rendez-vous à cette heure
                if RendezVous.objects.filter(medecin=medecin, date_heure=date_heure).exclude(id=rdv_id).exists():
                    raise Exception("Ce créneau est déjà réservé.")
                
                rendezvous.patient = patient
                rendezvous.medecin = medecin
                rendezvous.date_heure = date_heure
                rendezvous.motif = motif
                rendezvous.full_clean()
                rendezvous.save()
                return redirect('admin_rendezvous')
            except Exception as e:
                error = str(e)
    else:
        # Pré-remplir les heures disponibles pour la date/heure actuelle
        from datetime import datetime, timedelta
        date_obj = rendezvous.date_heure.date()
        jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
        jour_semaine = jours[date_obj.weekday()]
        creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
        for creneau in creneaux:
            current = datetime.combine(date_obj, creneau.heure_debut)
            end = datetime.combine(date_obj, creneau.heure_fin)
            while current < end:
                heure_str = current.strftime('%H:%M')
                date_heure = timezone.make_aware(current)
                if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exclude(id=rdv_id).exists() or rendezvous.date_heure == date_heure:
                    heures_disponibles.append(heure_str)
                current += timedelta(minutes=30)
    return render(request, 'admin/rendezvous_update.html', {
        'rendezvous': rendezvous,
        'medecins': medecins,
        'patients': patients,
        'heures_disponibles': heures_disponibles,
        'selected_medecin': selected_medecin,
        'selected_patient': selected_patient,
        'selected_date': selected_date,
        'selected_heure': selected_heure,
        'min_date': min_date,
        'error': error
    })

@admin_required
def admin_rendezvous_delete(request, rdv_id):
    rendezvous = get_object_or_404(RendezVous, id=rdv_id)
    if request.method == 'POST':
        rendezvous.delete()
        return redirect('admin_rendezvous')
    return render(request, 'admin/rendezvous_confirm_delete.html', {'rendezvous': rendezvous})

@login_required
def patient_rendezvous_update(request, rdv_id):
    try:
        patient = Patient.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, patient=patient)
    except Patient.DoesNotExist:
        return redirect('patient_dashboard')
    
    medecins = Medecin.objects.all()
    min_date = timezone.now().strftime('%Y-%m-%d')
    creneaux = []
    heures_disponibles = []
    selected_medecin = rendezvous.medecin
    selected_date = rendezvous.date_heure.date().strftime('%Y-%m-%d')
    selected_heure = rendezvous.date_heure.strftime('%H:%M')
    error = None

    if request.method == 'POST':
        medecin_id = request.POST.get('medecin')
        date_rdv = request.POST.get('date_rdv')
        heure_rdv = request.POST.get('heure_rdv')
        motif = request.POST.get('motif')

        if medecin_id:
            selected_medecin = Medecin.objects.get(id=medecin_id)
            if date_rdv:
                selected_date = date_rdv
                from datetime import datetime, timedelta
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
                jour_semaine = jours[date_obj.weekday()]
                creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
                for creneau in creneaux:
                    current = datetime.combine(date_obj, creneau.heure_debut)
                    end = datetime.combine(date_obj, creneau.heure_fin)
                    while current < end:
                        heure_str = current.strftime('%H:%M')
                        date_heure = timezone.make_aware(current)
                        
                        # Vérifier que l'heure n'est pas dans le passé pour aujourd'hui
                        if date_obj == timezone.now().date():
                            if current.time() <= timezone.now().time():
                                current += timedelta(minutes=30)
                                continue
                        
                        # Exclure l'heure du rendez-vous actuel
                        if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exclude(id=rdv_id).exists():
                            heures_disponibles.append(heure_str)
                        current += timedelta(minutes=30)
        if 'valider' in request.POST:
            try:
                medecin = Medecin.objects.get(id=medecin_id)
                from datetime import datetime
                date_obj = datetime.strptime(date_rdv, '%Y-%m-%d').date()
                if not heure_rdv:
                    raise Exception("Veuillez choisir une heure valide.")
                heure_obj = datetime.strptime(heure_rdv, '%H:%M').time()
                date_heure = datetime.combine(date_obj, heure_obj)
                date_heure = timezone.make_aware(date_heure)
                if date_heure < timezone.now():
                    error = "Impossible de modifier un rendez-vous pour une date antérieure à aujourd'hui."
                    raise Exception(error)
                heure_valide = False
                for creneau in creneaux:
                    if creneau.heure_debut <= heure_obj < creneau.heure_fin:
                        heure_valide = True
                        break
                if not heure_valide:
                    raise Exception("L'heure choisie ne correspond pas aux horaires du médecin ce jour-là.")
                if RendezVous.objects.filter(medecin=medecin, date_heure=date_heure).exclude(id=rdv_id).exists():
                    raise Exception("Ce créneau est déjà réservé.")
                rendezvous.medecin = medecin
                rendezvous.date_heure = date_heure
                rendezvous.motif = motif
                rendezvous.full_clean()
                rendezvous.save()
                return redirect('patient_rendezvous')
            except Exception as e:
                error = str(e)
    else:
        # Pré-remplir les heures disponibles pour la date/heure actuelle
        from datetime import datetime, timedelta
        date_obj = rendezvous.date_heure.date()
        jours = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
        jour_semaine = jours[date_obj.weekday()]
        creneaux = Creneau.objects.filter(medecin=selected_medecin, jour=jour_semaine)
        for creneau in creneaux:
            current = datetime.combine(date_obj, creneau.heure_debut)
            end = datetime.combine(date_obj, creneau.heure_fin)
            while current < end:
                heure_str = current.strftime('%H:%M')
                date_heure = timezone.make_aware(current)
                if not RendezVous.objects.filter(medecin=selected_medecin, date_heure=date_heure).exclude(id=rdv_id).exists() or rendezvous.date_heure == date_heure:
                    heures_disponibles.append(heure_str)
                current += timedelta(minutes=30)
    return render(request, 'patient/rendezvous_update.html', {
        'rendezvous': rendezvous,
        'medecins': medecins,
        'heures_disponibles': heures_disponibles,
        'selected_medecin': selected_medecin,
        'selected_date': selected_date,
        'selected_heure': selected_heure,
        'min_date': min_date,
        'error': error
    })

@login_required
def patient_rendezvous_delete(request, rdv_id):
    try:
        patient = Patient.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, patient=patient)
    except Patient.DoesNotExist:
        return redirect('patient_dashboard')
    
    if request.method == 'POST':
        rendezvous.delete()
        return redirect('patient_rendezvous')
    return render(request, 'patient/rendezvous_confirm_delete.html', {'rendezvous': rendezvous})

# Vues pour les comptes rendus
@login_required
def medecin_compte_rendu_create(request, rdv_id):
    """Permet au médecin de créer un compte rendu pour un rendez-vous"""
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, medecin=medecin)
    except Medecin.DoesNotExist:
        return redirect('medecin_dashboard')
    
    # Vérifier que le rendez-vous est dans le passé ou aujourd'hui
    # Permettre la création de comptes rendus pour les rendez-vous du jour même
    if rendezvous.date_heure.date() > timezone.now().date():
        messages.error(request, "Vous ne pouvez créer un compte rendu que pour un rendez-vous qui a eu lieu aujourd'hui ou dans le passé.")
        return redirect('medecin_rendezvous')
    
    # Vérifier qu'il n'y a pas déjà un compte rendu pour ce rendez-vous
    if CompteRendu.objects.filter(rendez_vous=rendezvous).exists():
        messages.warning(request, "Un compte rendu existe déjà pour ce rendez-vous.")
        return redirect('medecin_compte_rendu_detail', rdv_id=rdv_id)
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        diagnostic = request.POST.get('diagnostic')
        
        if contenu and diagnostic:
            compte_rendu = CompteRendu.objects.create(
                rendez_vous=rendezvous,
                contenu=contenu,
                diagnostic=diagnostic
            )
            messages.success(request, "Compte rendu créé avec succès.")
            return redirect('medecin_compte_rendu_detail', rdv_id=rdv_id)
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
    
    return render(request, 'medecin/compte_rendu_create.html', {
        'rendezvous': rendezvous
    })

@login_required
def medecin_compte_rendu_detail(request, rdv_id):
    """Affiche le détail d'un compte rendu"""
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, medecin=medecin)
        compte_rendu = CompteRendu.objects.filter(rendez_vous=rendezvous).first()
    except Medecin.DoesNotExist:
        return redirect('medecin_dashboard')
    
    return render(request, 'medecin/compte_rendu_detail.html', {
        'rendezvous': rendezvous,
        'compte_rendu': compte_rendu
    })

@login_required
def medecin_compte_rendu_update(request, rdv_id):
    """Permet au médecin de modifier un compte rendu"""
    try:
        medecin = Medecin.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, medecin=medecin)
        compte_rendu = get_object_or_404(CompteRendu, rendez_vous=rendezvous)
    except Medecin.DoesNotExist:
        return redirect('medecin_dashboard')
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        diagnostic = request.POST.get('diagnostic')
        
        if contenu and diagnostic:
            compte_rendu.contenu = contenu
            compte_rendu.diagnostic = diagnostic
            compte_rendu.save()
            messages.success(request, "Compte rendu modifié avec succès.")
            return redirect('medecin_compte_rendu_detail', rdv_id=rdv_id)
        else:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
    
    return render(request, 'medecin/compte_rendu_update.html', {
        'rendezvous': rendezvous,
        'compte_rendu': compte_rendu
    })

@login_required
def patient_compte_rendu_detail(request, rdv_id):
    """Permet au patient de voir le compte rendu de son rendez-vous"""
    try:
        patient = Patient.objects.get(user=request.user)
        rendezvous = get_object_or_404(RendezVous, id=rdv_id, patient=patient)
        compte_rendu = CompteRendu.objects.filter(rendez_vous=rendezvous).first()
    except Patient.DoesNotExist:
        return redirect('patient_dashboard')
    
    return render(request, 'patient/compte_rendu_detail.html', {
        'rendezvous': rendezvous,
        'compte_rendu': compte_rendu
    })


