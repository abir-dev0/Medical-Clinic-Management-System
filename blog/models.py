from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils import timezone

# Utilisateur personnalisé
class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('medecin', 'Médecin'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def set_password(self, raw_password):
        # Supprimer toutes les validations de mot de passe
        # Permettre n'importe quel mot de passe
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
        self._password = raw_password

# Patient
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20)

    def __str__(self):
        return self.user.get_full_name()

# Table des spécialités
class Specialite(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom

# Médecin
class Medecin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    specialite = models.ForeignKey(Specialite, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

# Rendez-vous
class RendezVous(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    medecin = models.ForeignKey(Medecin, on_delete=models.CASCADE)
    date_heure = models.DateTimeField()
    motif = models.CharField(max_length=255)
    statut = models.CharField(max_length=50, choices=[
        ('en attente', 'En attente'),
        ('confirmé', 'Confirmé'),
        ('annulé', 'Annulé'),
    ], default='en attente')

    def __str__(self):
        return f"{self.date_heure.strftime('%d/%m/%Y %H:%M')} - {self.patient.user.get_full_name()}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.date_heure:
            now = timezone.now()
            
            # Vérifier que la date/heure n'est pas dans le passé
            if self.date_heure <= now:
                raise ValidationError("Impossible de créer un rendez-vous pour une date et heure antérieure à maintenant.")
            
            # Vérifier que la date n'est pas trop éloignée dans le futur (optionnel)
            # max_future_date = now + timezone.timedelta(days=365)  # 1 an maximum
            # if self.date_heure > max_future_date:
            #     raise ValidationError("Impossible de créer un rendez-vous plus d'un an à l'avance.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# Compte rendu
class CompteRendu(models.Model):
    rendez_vous = models.ForeignKey(RendezVous, on_delete=models.CASCADE, related_name='comptes_rendus')
    date_creation = models.DateField(auto_now_add=True)
    contenu = models.TextField()
    diagnostic = models.TextField()

    def __str__(self):
        return f"Compte rendu du {self.date_creation} - {self.rendez_vous.patient.user.get_full_name()}"
    
    class Meta:
        ordering = ['-date_creation']

# Dossier médical
class DossierMedical(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    observations = models.TextField()
    fichiers = models.FileField(upload_to='dossiers/', blank=True, null=True)

    def __str__(self):
        return f"Dossier médical - {self.patient.user.get_full_name()}"

# Ordonnance
class Ordonnance(models.Model):
    dossier = models.ForeignKey(DossierMedical, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    contenu = models.TextField()

    def __str__(self):
        return f"Ordonnance du {self.date} - {self.dossier.patient.user.get_full_name()}"

# Créneaux horaires des médecins
class Creneau(models.Model):
    JOURS_CHOICES = [
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
        ('dimanche', 'Dimanche'),
    ]
    
    medecin = models.ForeignKey(Medecin, on_delete=models.CASCADE, related_name='creneaux')
    jour = models.CharField(max_length=10, choices=JOURS_CHOICES)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    
    class Meta:
        unique_together = ['medecin', 'jour', 'heure_debut']
        ordering = ['medecin', 'jour', 'heure_debut']
    
    def __str__(self):
        return f"{self.medecin.user.get_full_name()} - {self.get_jour_display()} {self.heure_debut} à {self.heure_fin}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.heure_debut >= self.heure_fin:
            raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")
