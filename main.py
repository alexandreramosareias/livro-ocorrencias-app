import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
import datetime
from kivy.metrics import dp 

import csv # Ainda necessário se você planeja salvar o CSV na RegisterScreen
import os # Ainda necessário se você planeja salvar o CSV na RegisterScreen
import calendar 

import requests 
import json

GLOBAL_FIREBASE_PROJECT_ID = "edmundo-silva"
GLOBAL_WEB_API_KEY = "AIzaSyD2jnd3DIxhkz6cN1-zl5_SWqu623olTVQ"

kivy.require('2.3.1')

# --- Widgets para o Calendário ---
class CalendarButton(Button):
    is_current_month = False 
    is_selected = False 

class CalendarWidget(GridLayout):
    cols = 7 
    month_label = ObjectProperty(None) 
    popup_ref = ObjectProperty(None) 
    
    current_year = NumericProperty(datetime.date.today().year) 
    current_month = NumericProperty(datetime.date.today().month) 

    target_text_input = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def generate_calendar_days(self):
        self.clear_widgets() 

        week_days = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
        for day in week_days:
            self.add_widget(Label(text=day, font_size='16sp', bold=True))

        first_day_of_month = datetime.date(self.current_year, self.current_month, 1)
        start_day_offset = (first_day_of_month.weekday() + 1) % 7 

        num_days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]

        for _ in range(start_day_offset):
            self.add_widget(Label(text=''))

        for day in range(1, num_days_in_month + 1):
            btn = CalendarButton(text=str(day))
            btn.is_current_month = True
            btn.bind(on_release=self.select_date) 
            self.add_widget(btn)

        if self.month_label: 
            self.month_label.text = first_day_of_month.strftime('%B %Y')

    def select_date(self, instance):
        if self.target_text_input:
            selected_date = f"{int(instance.text):02d}/{self.current_month:02d}/{self.current_year}"
            self.target_text_input.text = selected_date
        
        if self.popup_ref:
            self.popup_ref.dismiss() 

    def go_prev_month(self, instance): 
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
        self.current_year -= 1
        self.generate_calendar_days()

    def go_next_month(self, instance): 
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.generate_calendar_days()

class SearchResultsPopup(Popup):
    results_text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.title = 'Resultados da Consulta'
        self.size_hint = (0.9, 0.9)

        main_layout = BoxLayout(orientation='vertical', spacing='10dp', padding='10dp')

        scroll_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height')) 

        self.results_label = Label(
            text='', 
            markup=True,
            size_hint_y=None, 
            halign='left',
            valign='top'
        )
        self.results_label.bind(width=lambda instance, value: instance.setter('text_size')(instance, (value, None)))
        self.results_label.bind(texture_size=lambda instance, value: instance.setter('height')(instance, value[1])) 
        
        scroll_layout.add_widget(self.results_label)
        
        scroll_view = ScrollView(do_scroll_x=False)
        scroll_view.add_widget(scroll_layout)

        main_layout.add_widget(scroll_view)

        close_button = Button(text='Fechar', size_hint_y=None, height='48dp')
        close_button.bind(on_release=self.dismiss)
        main_layout.add_widget(close_button)

        self.content = main_layout
    
    def on_results_text(self, instance, value):
        if hasattr(self, 'results_label'):
            self.results_label.text = value

# --- Definição das Classes das Telas ---
class HomeScreen(Screen):
    pass

class RegisterScreen(Screen):
    # Propriedades para referenciar os IDs do KivyMD
    aluno_input = ObjectProperty(None)
    professor_input = ObjectProperty(None)
    turma_input = ObjectProperty(None)
    data_input = ObjectProperty(None)
    natureza_spinner = ObjectProperty(None)
    descricao_input = ObjectProperty(None)

    # NOVAS VARIÁVEIS PARA O FIREBASE
    FIREBASE_PROJECT_ID = "edmundo-silva" # <-- VERIFIQUE ESTE ID!
    WEB_API_KEY = GLOBAL_WEB_API_KEY
    FIRESTORE_COLLECTION = "ocorrencias" 
    FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/{FIRESTORE_COLLECTION}"

    def on_enter(self, *args):
        # Limpa os campos quando a tela é acessada
        self.clear_fields()
        print("Entrou na tela de Registro e limpou os campos.")

    def clear_fields(self):
        self.ids.aluno_input.text = ''
        self.ids.professor_input.text = ''
        self.ids.turma_input.text = ''
        self.ids.data_input.text = ''
        self.ids.natureza_spinner.text = 'Selecione a Natureza'
        self.ids.descricao_input.text = ''

    def show_info_popup(self, title, message):
        box = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        box.add_widget(Label(text=message, markup=True, size_hint_y=None, height='60dp', halign='center', valign='middle'))
        
        btn = Button(text="Ok", size_hint_y=None, height='48dp')
        box.add_widget(btn)
        
        popup = Popup(title=title, content=box, size_hint=(0.7, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    # ESTA É A FUNÇÃO QUE ENVIA OS DADOS PARA O FIREBASE
    def save_occurrence_cloud(self, data_dict):
        """Salva uma ocorrência no Firestore."""
        headers = {'Content-Type': 'application/json'}
        firestore_data = {
            "fields": {
                "Aluno": {"stringValue": data_dict["Aluno"]},
                "Professor": {"stringValue": data_dict["Professor"]},
                "Turma": {"stringValue": data_dict["Turma"]},
                "Data": {"stringValue": data_dict["Data"]},
                "Natureza": {"stringValue": data_dict["Natureza"]},
                "Descricao": {"stringValue": data_dict["Descricao"]}
            }
        }
        try:
            response = requests.post(self.FIRESTORE_URL, headers=headers, data=json.dumps(firestore_data))
            response.raise_for_status() 
            print(f"Ocorrência salva no Firestore: {response.json()}")
            return True 
        except requests.exceptions.RequestException as e:
            print(f"Erro ao salvar no Firestore: {e}")
            self.show_info_popup("Erro na Nuvem", f"Erro ao salvar no banco de dados:\n[b]{e}[/b]\nVerifique sua conexão e ID do projeto Firebase.")
            return False 

    # ESTA É A FUNÇÃO QUE O SEU KV CHAMA, E ELA POR SUA VEZ CHAMA save_occurrence_cloud
    def save_occurrence(self):
        aluno = self.ids.aluno_input.text.strip()
        professor = self.ids.professor_input.text.strip()
        turma = self.ids.turma_input.text.strip()
        data = self.ids.data_input.text.strip()
        natureza = self.ids.natureza_spinner.text.strip()
        descricao = self.ids.descricao_input.text.strip()

        missing_fields = []
        if not aluno:
            missing_fields.append("Aluno")
        if not professor:
            missing_fields.append("Professor")
        if not turma:
            missing_fields.append("Turma")
        if not data:
            missing_fields.append("Data")
        if natureza == 'Selecione a Natureza':
            missing_fields.append("Natureza")
        if not descricao:
            missing_fields.append("Descrição")

        if missing_fields:
            if len(missing_fields) == 1:
                message = f"O campo [b]'{missing_fields[0]}'[/b] está em branco."
            else:
                formatted_fields = [f"[b]'{f}'[/b]" for f in missing_fields]
                message = f"Os campos {', '.join(formatted_fields)} estão em branco."
            message += "\n\nPor favor, preencha [b]todos[/b] os campos obrigatórios para registrar a ocorrência."
            self.show_info_popup("Campos em Branco!", message)
            return 
        
        new_occurrence_data = {
            "Aluno": aluno,
            "Professor": professor,
            "Turma": turma,
            "Data": data,
            "Natureza": natureza,
            "Descricao": descricao
        }

        if self.save_occurrence_cloud(new_occurrence_data):
            print(f"Ocorrência de {aluno} enviada para a nuvem!")
            self.show_info_popup("Sucesso!", f"Ocorrência de [b]{aluno}[/b] registrada na nuvem!")
            self.clear_fields()

    def show_date_picker(self):
        calendar_widget = CalendarWidget(target_text_input=self.ids.data_input)
        
        popup = Popup(title='Selecionar Data',
                      content=BoxLayout(orientation='vertical', spacing='10dp'),
                      size_hint=(0.9, 0.9))
        
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        
        prev_btn = Button(text='<', size_hint_x=0.15)
        prev_btn.bind(on_release=calendar_widget.go_prev_month)
        header_layout.add_widget(prev_btn)
        
        month_label = Label(text='', font_size='20sp')
        calendar_widget.month_label = month_label 
        header_layout.add_widget(month_label)
        
        next_btn = Button(text='>', size_hint_x=0.15)
        next_btn.bind(on_release=calendar_widget.go_next_month)
        header_layout.add_widget(next_btn)

        popup.content.add_widget(header_layout) 
        popup.content.add_widget(calendar_widget) 

        calendar_widget.popup_ref = popup 
        
        popup.open()
        
        today = datetime.date.today()
        calendar_widget.current_month = today.month
        calendar_widget.current_year = today.year 
        calendar_widget.generate_calendar_days()

# --- AQUI É ONDE A CLASSE QueryScreen DEVE COMEÇAR (totalmente alinhada à esquerda) ---
class QueryScreen(Screen):
    FIREBASE_PROJECT_ID = "edmundo-silva"
    FIRESTORE_COLLECTION = "ocorrencias" 
    FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/{FIRESTORE_COLLECTION}"
    
    def __init__(self, **kwargs):
        super(QueryScreen, self).__init__(**kwargs)
    
    def on_enter(self, *args): 
        # Estes IDs devem corresponder aos IDs dos TextInputs e Spinner no seu meuapp.kv para a QueryScreen
        self.ids.query_aluno_input.text = ''
        self.ids.query_turma_input.text = ''
        self.ids.query_natureza_spinner.text = 'Selecione a Natureza'
        print("Entrou na tela de Consulta e limpou os campos de busca.")

    def fetch_occurrences_from_cloud(self):
        """Busca todas as ocorrências do Firestore."""
        print(f"Buscando dados do Firebase em: {self.FIRESTORE_URL}")
        try:
            response = requests.get(self.FIRESTORE_URL)
            response.raise_for_status() # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
            
            data = response.json()
            occurrences = []
            
            # O Firestore retorna os documentos dentro de 'documents'
            # Cada documento tem um campo 'fields' que contém os dados reais
            if 'documents' in data:
                for doc in data['documents']:
                    record = {}
                    fields = doc.get('fields', {})
                    for key, value_obj in fields.items():
                        # O Firestore aninha os valores por tipo (stringValue, integerValue, etc.)
                        # Tentamos extrair o valor real, assumindo que é stringValue na maioria dos casos
                        if 'stringValue' in value_obj:
                            record[key] = value_obj['stringValue']
                        elif 'integerValue' in value_obj:
                            record[key] = str(value_obj['integerValue']) # Convertendo para string para consistência
                        # Adicione mais tipos se você tiver (e.g., booleanValue, doubleValue)
                    occurrences.append(record)
            print(f"Dados recebidos do Firebase: {occurrences}")
            return occurrences
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar dados do Firestore: {e}")
            # Mostrar um popup de erro para o usuário
            popup_content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
            popup_content.add_widget(Label(text=f"Erro ao conectar ou buscar dados do Firebase:\n[b]{e}[/b]\nVerifique sua conexão e ID do projeto Firebase, ou regras de segurança."))
            close_btn = Button(text="Fechar", size_hint_y=None, height='48dp')
            error_popup = Popup(title="Erro na Nuvem", content=popup_content, size_hint=(0.7, 0.3))
            close_btn.bind(on_release=error_popup.dismiss)
            popup_content.add_widget(close_btn)
            error_popup.open()
            return [] # Retorna lista vazia em caso de erro

    def perform_query(self):
        print("\n--- Iniciando Consulta ---") 

        aluno = self.ids.query_aluno_input.text.strip().lower()
        turma = self.ids.query_turma_input.text.strip().lower()
        natureza = self.ids.query_natureza_spinner.text.strip()

        if natureza == 'Selecione a Natureza' or natureza == '':
            natureza_filtro = ''
        else:
            natureza_filtro = natureza.lower()
        
        print(f"Parâmetros de Busca: Aluno='{aluno}', Turma='{turma}', Natureza='{natureza_filtro}'") 

        # --- AQUI ESTÁ A MUDANÇA PRINCIPAL: BUSCA DO FIREBASE ---
        all_occurrences = self.fetch_occurrences_from_cloud() # Pega todos os registros do Firebase
        
        # Se houve um erro ao buscar do Firebase, all_occurrences será uma lista vazia e o erro já foi exibido
        if not all_occurrences:
            display_text = "Nenhuma ocorrência encontrada ou erro ao buscar dados da nuvem."
            results_popup = SearchResultsPopup() 
            results_popup.results_text = display_text 
            results_popup.open() 
            self.ids.query_aluno_input.text = ''
            self.ids.query_turma_input.text = ''
            self.ids.query_natureza_spinner.text = 'Selecione a Natureza'
            print("--- Consulta Finalizada ---")
            return
        
        # Filtra os resultados obtidos do Firebase
        results = []
        for row in all_occurrences:
            aluno_cloud = row.get('Aluno', '').lower()
            turma_cloud = row.get('Turma', '').lower()
            natureza_cloud = row.get('Natureza', '').lower()

            match_aluno = not aluno or (aluno in aluno_cloud)
            match_turma = not turma or (turma in turma_cloud)
            match_natureza = not natureza_filtro or (natureza_filtro in natureza_cloud)

            print(f"   Comparando CLOUD: Aluno('{aluno_cloud}') vs filtro '{aluno}' -> {match_aluno}") 
            print(f"   Comparando CLOUD: Turma('{turma_cloud}') vs filtro '{turma}' -> {match_turma}") 
            print(f"   Comparando CLOUD: Natureza('{natureza_cloud}') vs filtro '{natureza_filtro}' -> {match_natureza}") 

            if match_aluno and match_turma and match_natureza:
                results.append(row)
                print(f"   -> Linha Adicionada aos Resultados (CLOUD): {row.get('Aluno')}") 
        
        print(f"Total de resultados encontrados: {len(results)}") 

        if results:
            display_text = "Ocorrências Encontradas:\n\n"
            for i, record in enumerate(results):
                display_text += f"[b]Ocorrência {i+1}:[/b]\n" 
                display_text += f"   Aluno: {record.get('Aluno', 'N/A')}\n"
                display_text += f"   Turma: {record.get('Turma', 'N/A')}\n"
                display_text += f"   Data: {record.get('Data', 'N/A')}\n"
                display_text += f"   Professor: {record.get('Professor', 'N/A')}\n"
                display_text += f"   Natureza: {record.get('Natureza', 'N/A')}\n"
                display_text += f"   Descrição: {record.get('Descricao', 'N/A')}\n\n"
        else:
            display_text = "Nenhuma ocorrência encontrada com os critérios informados."
        
        print(f"Texto a ser exibido no popup:\n{display_text}") 

        results_popup = SearchResultsPopup() 
        results_popup.results_text = display_text 
        results_popup.open() 

        self.ids.query_aluno_input.text = ''
        self.ids.query_turma_input.text = ''
        self.ids.query_natureza_spinner.text = 'Selecione a Natureza'
        print("Campos de busca limpos após a consulta.")
        print("--- Consulta Finalizada ---")

# --- NOVAS CLASSES PARA AUTENTICAÇÃO ---

class LoginScreen(Screen):
    # As chaves e URLs do Firebase precisam estar aqui também
    FIREBASE_PROJECT_ID = "edmundo-silva-cloud-firestore"
    WEB_API_KEY = GLOBAL_WEB_API_KEY
    AUTH_SIGN_IN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"

    # Propriedades para referenciar os TextInputs do KV
    email_input = ObjectProperty(None)
    password_input = ObjectProperty(None)

    def on_enter(self, *args):
        # Limpa os campos quando a tela é exibida
        if self.email_input:
            self.email_input.text = ''
        if self.password_input:
            self.password_input.text = ''

    def login_user(self, email, password):
        if not email or not password:
            self.show_popup("Erro de Login", "Por favor, preencha todos os campos.")
            return

        try:
            payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
            headers = {"Content-Type": "application/json"}

            # Sincrono para exemplo, em um app real considerar threading
            response = requests.post(self.AUTH_SIGN_IN_URL, data=payload, headers=headers)
            response_data = response.json()

            if response.ok:
                self.show_popup("Sucesso", "Login realizado com sucesso!")
                # Aqui você pode salvar o token ou navegar para outra tela
                # Por exemplo: app.root.current = 'home'
                print("User UID:", response_data.get("localId"))
                print("ID Token:", response_data.get("idToken"))
                app.root.current = 'home' # Ou para uma tela pós-login
            else:
                error_message = response_data.get("error", {}).get("message", "Erro desconhecido")
                self.show_popup("Erro de Login", f"Erro: {error_message}")

        except requests.exceptions.RequestException as e:
            self.show_popup("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
        except Exception as e:
            self.show_popup("Erro Inesperado", f"Ocorreu um erro: {e}")

    def show_popup(self, title, message):
        popup_content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        popup_content.add_widget(Label(text=message, halign='center', valign='middle'))
        btn = Button(text='Ok', size_hint_y=None, height='48dp')
        popup_content.add_widget(btn)

        popup = Popup(title=title, content=popup_content, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

class RegisterUserScreen(Screen):
    # As chaves e URLs do Firebase precisam estar aqui também
    FIREBASE_PROJECT_ID = "edmundo-silva-cloud-firestore"
    WEB_API_KEY = "AIzaSyD2jnd3DIxhkz6cN1-zl5_SWqu623olTVQ"
    AUTH_SIGN_UP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"

    # Propriedades para referenciar os TextInputs do KV
    email_input = ObjectProperty(None)
    password_input = ObjectProperty(None)
    confirm_password_input = ObjectProperty(None)

    def on_enter(self, *args):
        # Limpa os campos quando a tela é exibida
        if self.email_input:
            self.email_input.text = ''
        if self.password_input:
            self.password_input.text = ''
        if self.confirm_password_input:
            self.confirm_password_input.text = ''

    def register_new_user(self, email, password, confirm_password):
        if not email or not password or not confirm_password:
            self.show_popup("Erro de Registro", "Por favor, preencha todos os campos.")
            return

        if password != confirm_password:
            self.show_popup("Erro de Registro", "As senhas não coincidem.")
            return

        if len(password) < 6:
            self.show_popup("Erro de Registro", "A senha deve ter no mínimo 6 caracteres.")
            return

        try:
            payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
            headers = {"Content-Type": "application/json"}

            # Sincrono para exemplo, em um app real considerar threading
            response = requests.post(self.AUTH_SIGN_UP_URL, data=payload, headers=headers)
            response_data = response.json()

            if response.ok:
                self.show_popup("Sucesso", "Conta criada com sucesso! Faça login agora.")
                # Após o registro, pode-se ir para a tela de login
                app.root.current = 'login' 
            else:
                error_message = response_data.get("error", {}).get("message", "Erro desconhecido")
                # Traduzir algumas mensagens comuns de erro do Firebase Auth
                if "EMAIL_EXISTS" in error_message:
                    error_message = "Este email já está em uso."
                elif "INVALID_EMAIL" in error_message:
                    error_message = "Formato de email inválido."
                elif "WEAK_PASSWORD" in error_message:
                    error_message = "A senha é muito fraca (mínimo 6 caracteres)."

                self.show_popup("Erro de Registro", f"Erro: {error_message}")

        except requests.exceptions.RequestException as e:
            self.show_popup("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
        except Exception as e:
            self.show_popup("Erro Inesperado", f"Ocorreu um erro: {e}")

    def show_popup(self, title, message):
        popup_content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        popup_content.add_widget(Label(text=message, halign='center', valign='middle'))
        btn = Button(text='Ok', size_hint_y=None, height='48dp')
        popup_content.add_widget(btn)

        popup = Popup(title=title, content=popup_content, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()

# --- AQUI É ONDE A CLASSE MeuApp DEVE COMEÇAR ---
class MeuApp(App):
    title = 'Seeduc - Colégio Estadual Edmundo Silva'

    def build(self):
        # Cria o ScreenManager
        sm = ScreenManager()

        # Adiciona todas as telas ao ScreenManager
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(QueryScreen(name='query'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterUserScreen(name='register_user'))

        # Define a tela inicial como a tela de login
        sm.current = 'login' 

        return sm # Retorna o ScreenManager como o widget raiz do aplicativo

if __name__ == '__main__':
    app = MeuApp() # Atribui a instância do app a uma variável global 'app' para acesso em .kv
    app.run()