from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Patient, Medecin, Specialite, Creneau

class PatientRegistrationForm(forms.ModelForm):
    nom = forms.CharField(max_length=100)
    prenom = forms.CharField(max_length=100)
    date_naissance = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    adresse = forms.CharField(widget=forms.Textarea, required=False)
    telephone = forms.CharField(max_length=20)
    
    # Champs de mot de passe sans aucune validation
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=True
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        widget=forms.PasswordInput,
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'nom', 'prenom', 'date_naissance', 'adresse', 'telephone']

    def save(self, commit=True, patient_instance=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = 'patient'
        if commit:
            user.save()
            if patient_instance:
                # Update existing patient
                patient = patient_instance
                patient.nom = self.cleaned_data['nom']
                patient.prenom = self.cleaned_data['prenom']
                patient.date_naissance = self.cleaned_data['date_naissance']
                patient.adresse = self.cleaned_data['adresse']
                patient.telephone = self.cleaned_data['telephone']
                patient.save()
            else:
                # Create new patient
                patient = Patient.objects.create(
                    user=user,
                    nom=self.cleaned_data['nom'],
                    prenom=self.cleaned_data['prenom'],
                    date_naissance=self.cleaned_data['date_naissance'],
                    adresse=self.cleaned_data['adresse'],
                    telephone=self.cleaned_data['telephone']
                )
        return user

class MedecinRegistrationForm(forms.ModelForm):
    nom = forms.CharField(max_length=100)
    prenom = forms.CharField(max_length=100)
    specialite = forms.ModelChoiceField(
        queryset=Specialite.objects.all().order_by('nom'),
        empty_label="Sélectionnez une spécialité",
        required=True
    )
    
    # Champs de mot de passe sans aucune validation
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=True
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        widget=forms.PasswordInput,
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'nom', 'prenom', 'specialite']

    def save(self, commit=True, medecin_instance=None):
        user = super().save(commit=False)
        # Définir le mot de passe uniquement si fourni
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        user.role = 'medecin'
        if commit:
            user.save()
            if medecin_instance:
                # Update existing medecin
                medecin = medecin_instance
                medecin.nom = self.cleaned_data['nom']
                medecin.prenom = self.cleaned_data['prenom']
                medecin.specialite = self.cleaned_data['specialite']
                medecin.save()
            else:
                # Create new medecin
                medecin = Medecin.objects.create(
                    user=user,
                    nom=self.cleaned_data['nom'],
                    prenom=self.cleaned_data['prenom'],
                    specialite=self.cleaned_data['specialite']
                )
        return user

class SpecialiteForm(forms.ModelForm):
    class Meta:
        model = Specialite
        fields = ['nom']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg',
                'placeholder': 'Nom de la spécialité'
            })
        }

class CreneauForm(forms.ModelForm):
    class Meta:
        model = Creneau
        fields = ['jour', 'heure_debut', 'heure_fin']
        widgets = {
            'jour': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'heure_debut': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
                'type': 'time'
            }),
            'heure_fin': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
                'type': 'time'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')
        
        if heure_debut and heure_fin and heure_debut >= heure_fin:
            raise forms.ValidationError("L'heure de début doit être antérieure à l'heure de fin.")
        
        return cleaned_data 