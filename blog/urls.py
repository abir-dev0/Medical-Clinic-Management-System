from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.home, name='home'),
    path('register/patient/', views.register_patient, name='register_patient'),
    path('login/', views.login_view, name='login'),
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/rendezvous/', views.patient_rendezvous, name='patient_rendezvous'),
    path('patient/prendre-rendezvous/', views.prendre_rendezvous, name='prendre_rendezvous'),
    path('patient/dossier/', views.patient_dossier, name='patient_dossier'),
    path('medecin/', views.medecin_dashboard, name='medecin_dashboard'),
    path('medecin/rendezvous/', views.medecin_rendezvous, name='medecin_rendezvous'),
    path('medecin/rendezvous/<int:rdv_id>/detail/', views.medecin_rendezvous_detail, name='medecin_rendezvous_detail'),
    path('medecin/patients/', views.medecin_patients, name='medecin_patients'),
    path('logout/', views.logout_view, name='logout'),
    # Admin URLs
    path('owner/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('owner/rendezvous/', views.admin_rendezvous, name='admin_rendezvous'),
    path('owner/rendezvous/add/', views.admin_rendezvous_create, name='admin_rendezvous_create'),
    path('owner/dossiers/', views.admin_dossiers, name='admin_dossiers'),
    # CRUD Patients (admin)
    path('owner/patients/', views.patient_list, name='patient_list'),
    path('owner/patients/add/', views.patient_create, name='patient_create'),
    path('owner/patients/<int:patient_id>/edit/', views.patient_update, name='patient_update'),
    path('owner/patients/<int:patient_id>/delete/', views.patient_delete, name='patient_delete'),
    # CRUD Médecins (admin)
    path('owner/medecins/', views.medecin_list, name='medecin_list'),
    path('owner/medecins/add/', views.medecin_create, name='medecin_create'),
    path('owner/medecins/<int:medecin_id>/edit/', views.medecin_update, name='medecin_update'),
    path('owner/medecins/<int:medecin_id>/delete/', views.medecin_delete, name='medecin_delete'),
    # CRUD Spécialités (admin)
    path('owner/specialites/', views.specialite_list, name='specialite_list'),
    path('owner/specialites/add/', views.specialite_create, name='specialite_create'),
    path('owner/specialites/<int:specialite_id>/edit/', views.specialite_update, name='specialite_update'),
    path('owner/specialites/<int:specialite_id>/delete/', views.specialite_delete, name='specialite_delete'),
    path('medecin/rendezvous/<int:rdv_id>/confirmer/', views.confirmer_rendezvous, name='confirmer_rendezvous'),
    path('medecin/rendezvous/<int:rdv_id>/annuler/', views.annuler_rendezvous, name='annuler_rendez_vous'),
    path('medecin/patient/<int:patient_id>/dossier/', views.medecin_patient_dossier, name='medecin_patient_dossier'),
    path('medecin/creneaux/', views.medecin_creneaux, name='medecin_creneaux'),
    path('medecin/creneaux/add/', views.medecin_creneau_create, name='medecin_creneau_create'),
    path('medecin/creneaux/<int:creneau_id>/edit/', views.medecin_creneau_update, name='medecin_creneau_update'),
    path('medecin/creneaux/<int:creneau_id>/delete/', views.medecin_creneau_delete, name='medecin_creneau_delete'),
    path('medecin/rendezvous/<int:rdv_id>/modifier-statut/', views.modifier_statut_rendezvous, name='modifier_statut_rendezvous'),
    path('owner/rendezvous/<int:rdv_id>/edit/', views.admin_rendezvous_update, name='admin_rendezvous_update'),
    path('owner/rendezvous/<int:rdv_id>/delete/', views.admin_rendezvous_delete, name='admin_rendezvous_delete'),
    path('patient/rendezvous/<int:rdv_id>/edit/', views.patient_rendezvous_update, name='patient_rendezvous_update'),
    path('patient/rendezvous/<int:rdv_id>/delete/', views.patient_rendezvous_delete, name='patient_rendezvous_delete'),
    # URLs pour les comptes rendus
    path('medecin/rendezvous/<int:rdv_id>/compte-rendu/create/', views.medecin_compte_rendu_create, name='medecin_compte_rendu_create'),
    path('medecin/rendezvous/<int:rdv_id>/compte-rendu/', views.medecin_compte_rendu_detail, name='medecin_compte_rendu_detail'),
    path('medecin/rendezvous/<int:rdv_id>/compte-rendu/edit/', views.medecin_compte_rendu_update, name='medecin_compte_rendu_update'),
    path('patient/rendezvous/<int:rdv_id>/compte-rendu/', views.patient_compte_rendu_detail, name='patient_compte_rendu_detail'),
] 