ITALO DANTAS
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# --- 1. CONFIGURAÇÃO INICIAL DA APLICAÇÃO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'minha-chave-secreta-de-estudante-123'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(basedir, 'static/profile_pics')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
db = SQLAlchemy(app)

# --- 2. MODELOS (AS TABELAS DO BANCO DE DADOS) ---

# Tabela de associação para o relacionamento Muitos-para-Muitos entre User e Curso
inscricao_tabela = db.Table('inscricao',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('curso_id', db.Integer, db.ForeignKey('curso.id'), primary_key=True)
)

class User(db.Model):
    """Modelo para os usuários (alunos)."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False) # Matrícula
    password_hash = db.Column(db.String(128), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    
    # Relacionamento para acessar os cursos em que o usuário está inscrito
    cursos = db.relationship('Curso', secondary=inscricao_tabela, back_populates='alunos')

class Curso(db.Model):
    """Modelo para os cursos oferecidos."""
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    vagas = db.Column(db.Integer, nullable=False)

    # Relacionamento para acessar os alunos inscritos no curso
    alunos = db.relationship('User', secondary=inscricao_tabela, back_populates='cursos')

    @property
    def vagas_restantes(self):
        return self.vagas - len(self.alunos)

# A tabela Inscricao agora é representada pela 'inscricao_tabela' acima.
# Manter a classe pode ser útil se você quiser adicionar mais dados à inscrição (ex: data).
# Por simplicidade, para um aluno de TSI, a tabela de associação é mais direta.

# --- 3. DECORADOR PERSONALIZADO (CONTROLE DE ACESSO) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. PROCESSADOR DE CONTEXTO (DISPONIBILIZA DADOS GLOBAIS PARA OS TEMPLATES) ---
@app.context_processor
def inject_user():
    """Injeta os dados do usuário logado em todos os templates."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(current_user_data=user)
    return dict(current_user_data=None)

# --- 5. ROTAS (AS PÁGINAS E LÓGICA DO SITE) ---

@app.route('/')
def lista_cursos():
    """Página inicial que lista todos os cursos."""
    cursos = Curso.query.all()
    return render_template('lista_cursos.html', cursos=cursos)

@app.route('/curso/<int:curso_id>')
def detalhe_curso(curso_id):
    """Mostra os detalhes de um curso específico."""
    curso = Curso.query.get_or_404(curso_id)
    ja_inscrito = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if curso in user.cursos:
            ja_inscrito = True
    return render_template('detalhe_curso.html', curso=curso, vagas_restantes=curso.vagas_restantes, ja_inscrito=ja_inscrito)

@app.route('/curso/<int:curso_id>/inscrever', methods=['POST'])
@login_required
def inscrever_curso(curso_id):
    """Processa a inscrição de um usuário em um curso."""
    curso = Curso.query.get_or_404(curso_id)
    user = User.query.get(session['user_id'])

    if curso in user.cursos:
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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not (len(username) == 12 and username.isdigit()):
            flash('Formato de matrícula inválido. Use apenas os 12 dígitos.', 'danger')
            return redirect(url_for('register'))
        
        user_existente = User.query.filter_by(username=username).first()
        if user_existente:
            flash('Esta matrícula já está registrada.', 'danger')
            return redirect(url_for('register'))

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
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('lista_cursos'))
        else:
            flash('Matrícula ou senha inválidos.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Realiza o logout do usuário."""
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('lista_cursos'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """Página de perfil do usuário."""
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        if 'picture' in request.files:
            file = request.files['picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.image_file = filename
                db.session.commit()
                flash('Foto de perfil atualizada com sucesso!', 'success')
                return redirect(url_for('account'))
    
    # Com os relacionamentos, não precisamos mais de lógicas complexas aqui!
    # Os cursos já estão em user.cursos.
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('account.html', image_file=image_file, cursos=user.cursos)

# --- 6. COMANDOS DE TERMINAL ---
@app.cli.command('init-db')
def init_db_command():
    """Comando para criar as tabelas e popular com dados iniciais."""
    db.create_all()
    # Adiciona cursos iniciais apenas se não houver nenhum
    if Curso.query.count() == 0:
        c1 = Curso(titulo='Introdução a Algoritmos', descricao='Aprenda a lógica de programação e estruturas de dados fundamentais para o desenvolvimento de software.', vagas=25)
        c2 = Curso(titulo='Redes de Computadores 101', descricao='Entenda os fundamentos da internet, protocolos de comunicação e como os dados viajam pelo mundo.', vagas=20)
        c3 = Curso(titulo='Desenvolvimento Web com Flask', descricao='Crie aplicações web dinâmicas e poderosas utilizando o micro-framework Flask em Python.', vagas=30)
        db.session.add_all([c1, c2, c3])
        db.session.commit()
        print('Banco de dados inicializado com cursos de exemplo.')
    else:
        print('Banco de dados já contém dados. Nenhum curso foi adicionado.')