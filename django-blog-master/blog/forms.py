from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'lang']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'editable medium-editor-textarea'})
        }

    def __init__(self, *args, **kargs):
        super(PostForm, self).__init__(*args, **kargs)
        CHOICES = (('0', 'English'), ('1', 'Romnia'),)
        self.fields['lang'] = forms.ChoiceField(choices=CHOICES, label='Language', required=True)
