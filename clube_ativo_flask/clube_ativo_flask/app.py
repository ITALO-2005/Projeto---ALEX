import os
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
# Carrega as configurações a partir das variáveis de ambiente para segurança
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-padrao-fraca-se-a-outra-falhar')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração da pasta de uploads e extensões permitidas
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/profile_pics')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- 2. INICIALIZAÇÃO DO BANCO DE DADOS E MIGRAÇÕES ---
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# --- 3. MODELOS (AS TABELAS DO BANCO DE DADOS) ---
# Tabela de associação para o relacionamento Muitos-para-Muitos
inscricao_tabela = db.Table('inscricao',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('curso_id', db.Integer, db.ForeignKey('curso.id'), primary_key=True)
)

class User(db.Model):
    """Modelo para os usuários (alunos)."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False) # Matrícula
    password_hash = db.Column(db.String(256), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    cursos = db.relationship('Curso', secondary=inscricao_tabela, back_populates='alunos', lazy='dynamic')

    def __repr__(self):
        return f"User('{self.username}', '{self.image_file}')"

class Curso(db.Model):
    """Modelo para os cursos oferecidos."""
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    vagas = db.Column(db.Integer, nullable=False)
    alunos = db.relationship('User', secondary=inscricao_tabela, back_populates='cursos', lazy='dynamic')

    @property
    def vagas_restantes(self):
        return self.vagas - self.alunos.count()

    def __repr__(self):
        return f"Curso('{self.titulo}')"


# --- 4. LÓGICA AUXILIAR (DECORADORES E PROCESSADORES DE CONTEXTO) ---
def login_required(f):
    """Decorador para garantir que o usuário está logado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa possuir uma matricula para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user_and_year():
    """Injeta dados do usuário e o ano atual em todos os templates."""
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(current_user_data=user, current_year=datetime.utcnow().year)


# --- 5. ROTAS (AS PÁGINAS E LÓGICA DO SITE) ---
@app.route('/')
@login_required
def home():
    """Página inicial que lista todos os cursos."""
    cursos = Curso.query.order_by(Curso.titulo).all()
    return render_template('lista_cursos.html', cursos=cursos)

@app.route('/curso/<int:curso_id>')
@login_required
def detalhe_curso(curso_id):
    """Mostra os detalhes de um curso específico."""
    curso = Curso.query.get_or_404(curso_id)
    ja_inscrito = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if curso in user.cursos.all():
            ja_inscrito = True
    return render_template('detalhe_curso.html', curso=curso, ja_inscrito=ja_inscrito)

@app.route('/curso/<int:curso_id>/inscrever', methods=['POST'])
@login_required
def inscrever_curso(curso_id):
    """Processa a inscrição de um usuário em um curso."""
    curso = Curso.query.get_or_404(curso_id)
    user = User.query.get(session['user_id'])

    if curso in user.cursos.all():
        flash('Você já está inscrito neste curso.', 'info')
        return redirect(url_for('detalhe_curso', curso_id=curso.id))

    if curso.vagas_restantes <= 0:
        flash('Vagas esgotadas para este curso!', 'danger')
        return redirect(url_for('detalhe_curso', curso_id=curso.id))

    user.cursos.append(curso)
    db.session.commit()
    flash('Inscrição realizada com sucesso!', 'success')
    return redirect(url_for('detalhe_curso', curso_id=curso.id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro de novos usuários."""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not (username and len(username) == 12 and username.isdigit()):
            flash('Formato de matrícula inválido. Use apenas os 12 dígitos.', 'danger')
            return redirect(url_for('register'))
        
        user_existente = User.query.filter_by(username=username).first()
        if user_existente:
            flash('Esta matrícula já está registrada. Tente fazer o login.', 'warning')
            return redirect(url_for('login'))

        password_hash = generate_password_hash(password)
        novo_user = User(username=username, password_hash=password_hash)
        db.session.add(novo_user)
        db.session.commit()
        flash('Conta criada com sucesso! Pode fazer o login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login."""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Matrícula ou senha inválidos. Tente novamente.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Realiza o logout do usuário."""
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """Página de perfil do usuário."""
    user = User.query.get_or_404(session['user_id'])
    if request.method == 'POST':
        if 'picture' in request.files:
            file = request.files['picture']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{user.username}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.image_file = filename
                db.session.commit()
                flash('Foto de perfil atualizada com sucesso!', 'success')
                return redirect(url_for('account'))
            else:
                flash('Tipo de arquivo inválido. Use png, jpg, jpeg ou gif.', 'danger')

    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('account.html', image_file=image_file, cursos=user.cursos)


# --- 6. COMANDOS DE TERMINAL PERSONALIZADOS ---
@app.cli.command('seed-db')
def seed_db_command():
    """Comando para popular o banco de dados com dados iniciais (seeding)."""
    if Curso.query.count() > 0:
        print('O banco de dados já contém cursos.')
        return

    c1 = Curso(titulo='Introdução a Algoritmos', descricao='Aprenda a lógica de programação e estruturas de dados fundamentais.', vagas=25)
    c2 = Curso(titulo='Redes de Computadores 101', descricao='Entenda os fundamentos da internet e protocolos de comunicação.', vagas=20)
    c3 = Curso(titulo='Clube de Teatro', descricao='Participe de apresentações e peças culturais', vagas=30)
    db.session.add_all([c1, c2, c3])
    db.session.commit()
    print('Banco de dados semeado com cursos de exemplo.')


if __name__ == '__main__':
    app.run(debug=True)