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
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')

class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    vagas = db.Column(db.Integer, nullable=False)

class Inscricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)

# --- 3. DECORADOR PERSONALIZADO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa de fazer login para aceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. PROCESSADOR DE CONTEXTO ---
@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(current_user_data=user)
    return dict(current_user_data=None)

# --- 5. ROTAS (AS PÁGINAS E LÓGICA DO SITE) ---
@app.route('/')
def lista_cursos():
    cursos = Curso.query.all()
    return render_template('lista_cursos.html', cursos=cursos)

@app.route('/curso/<int:curso_id>')
def detalhe_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    inscritos_count = Inscricao.query.filter_by(curso_id=curso.id).count()
    vagas_restantes = curso.vagas - inscritos_count
    ja_inscrito = False
    if 'user_id' in session:
        inscricao = Inscricao.query.filter_by(curso_id=curso.id, user_id=session['user_id']).first()
        if inscricao:
            ja_inscrito = True
    return render_template('detalhe_curso.html', curso=curso, vagas_restantes=vagas_restantes, ja_inscrito=ja_inscrito)

@app.route('/curso/<int:curso_id>/inscrever', methods=['POST'])
@login_required
def inscrever_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    inscricao_existente = Inscricao.query.filter_by(curso_id=curso.id, user_id=session['user_id']).first()
    if inscricao_existente:
        flash('Você já está inscrito neste curso.', 'info')
        return redirect(url_for('detalhe_curso', curso_id=curso.id))
    inscritos_count = Inscricao.query.filter_by(curso_id=curso.id).count()
    if inscritos_count >= curso.vagas:
        flash('Vagas esgotadas para este curso!', 'danger')
        return redirect(url_for('detalhe_curso', curso_id=curso.id))
    nova_inscricao = Inscricao(user_id=session['user_id'], curso_id=curso.id)
    db.session.add(nova_inscricao)
    db.session.commit()
    flash('Inscrição realizada com sucesso!', 'success')
    return redirect(url_for('detalhe_curso', curso_id=curso.id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not (len(username) == 12 and username.isdigit()):
            flash('Formato de matrícula inválido. Use apenas os 12 dígitos.', 'danger')
            return redirect(url_for('register'))
        user_existente = User.query.filter_by(username=username).first()
        if user_existente:
            flash('Esta matrícula já está registada.', 'danger')
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
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('lista_cursos'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
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
    inscricoes_user = Inscricao.query.filter_by(user_id=user.id).all()
    cursos_user = [Curso.query.get(i.curso_id) for i in inscricoes_user]
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('account.html', image_file=image_file, cursos=cursos_user)

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
        if Curso.query.count() == 0:
            c1 = Curso(titulo='Introdução a Algoritmos', descricao='Aprenda a lógica de programação.', vagas=25)
            c2 = Curso(titulo='Redes de Computadores 101', descricao='Os fundamentos da internet.', vagas=20)
            db.session.add(c1)
            db.session.add(c2)
            db.session.commit()
    return "<h1>Banco de dados inicializado com sucesso!</h1><p>Pode remover esta rota do ficheiro app.py agora.</p>"