from django import forms


class Base64SignatureWidget(forms.Textarea):
    template_name = 'signature/signature_widget.html'

    def format_value(self, value):
        if value:
        
            if "data:image" in value:
                return value
            
            return f'data:image/png;base64,{value}'
        return ''

    def value_from_datadict(self, data, files, name):
        if data.get(name):
            if data[name].startswith('data:'):
                return data[name].split(',')[1]
        return None
