import os
from functools import wraps
from datetime import datetime, timezone
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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma-chave-secreta-para-desenvolvimento')
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

# --- 3. MODELOS DA BASE DE DADOS ---

# Tabelas de associação
inscricao_evento_tabela = db.Table('inscricao_evento',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('evento_id', db.Integer, db.ForeignKey('evento.id'), primary_key=True)
)

membros_clube_tabela = db.Table('membros_clube',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('clube_id', db.Integer, db.ForeignKey('clube.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False) # Matrícula
    password_hash = db.Column(db.String(256), nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    eventos_inscritos = db.relationship('Evento', secondary=inscricao_evento_tabela, back_populates='alunos_inscritos', lazy='dynamic')
    clubes_membro = db.relationship('Clube', secondary=membros_clube_tabela, back_populates='membros', lazy='dynamic')
    topicos_criados = db.relationship('ForumTopico', backref='autor', lazy='dynamic')
    posts_criados = db.relationship('ForumPost', backref='autor', lazy='dynamic')

    def __repr__(self):
        return f"User('{self.username}', '{self.image_file}')"

class Clube(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    membros = db.relationship('User', secondary=membros_clube_tabela, back_populates='clubes_membro', lazy='dynamic')
    eventos = db.relationship('Evento', backref='clube_organizador', lazy='dynamic')

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    vagas = db.Column(db.Integer, nullable=False)
    data_evento = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    clube_id = db.Column(db.Integer, db.ForeignKey('clube.id'), nullable=False)
    alunos_inscritos = db.relationship('User', secondary=inscricao_evento_tabela, back_populates='eventos_inscritos', lazy='dynamic')
    noticias = db.relationship('Noticia', backref='evento', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def vagas_restantes(self):
        return self.vagas - self.alunos_inscritos.count()

class Noticia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    evento_id = db.Column(db.Integer, db.ForeignKey('evento.id'), nullable=True)

class ForumTopico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    posts = db.relationship('ForumPost', backref='topico', lazy='dynamic', cascade="all, delete-orphan")

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conteudo = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topico_id = db.Column(db.Integer, db.ForeignKey('forum_topico.id'), nullable=False)

# --- 4. LÓGICA AUXILIAR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user_and_year():
    user = User.query.get(session['user_id']) if 'user_id' in session else None
    return dict(current_user_data=user, current_year=datetime.now(timezone.utc).year)

# --- 5. ROTAS ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('noticias'))
    return redirect(url_for('login'))

@app.route('/noticias')
@login_required
def noticias():
    todas_noticias = Noticia.query.order_by(Noticia.data_publicacao.desc()).all()
    return render_template('noticias.html', noticias=todas_noticias)

@app.route('/clubes')
@login_required
def clubes():
    todos_clubes = Clube.query.order_by(Clube.nome).all()
    return render_template('clubes.html', clubes=todos_clubes)

@app.route('/clube/<int:clube_id>')
@login_required
def detalhe_clube(clube_id):
    clube = Clube.query.get_or_404(clube_id)
    agora = datetime.now(timezone.utc)
    eventos_futuros = clube.eventos.filter(Evento.data_evento >= agora).order_by(Evento.data_evento.asc()).all()
    eventos_passados = clube.eventos.filter(Evento.data_evento < agora).order_by(Evento.data_evento.desc()).all()
    return render_template('detalhe_clube.html', clube=clube, eventos_futuros=eventos_futuros, eventos_passados=eventos_passados)

@app.route('/ranking')
@login_required
def ranking():
    clubes_rankeados = sorted(Clube.query.all(), key=lambda c: c.membros.count(), reverse=True)
    return render_template('ranking.html', clubes=clubes_rankeados)

@app.route('/forum')
@login_required
def forum():
    topicos = ForumTopico.query.order_by(ForumTopico.data_criacao.desc()).all()
    return render_template('forum.html', topicos=topicos)

@app.route('/forum/topico/<int:topico_id>', methods=['GET', 'POST'])
@login_required
def detalhe_topico(topico_id):
    topico = ForumTopico.query.get_or_404(topico_id)
    if request.method == 'POST':
        conteudo_post = request.form.get('conteudo')
        if conteudo_post:
            novo_post = ForumPost(conteudo=conteudo_post, user_id=session['user_id'], topico_id=topico.id)
            db.session.add(novo_post)
            db.session.commit()
            flash('Resposta adicionada com sucesso!', 'success')
            return redirect(url_for('detalhe_topico', topico_id=topico.id))
    posts = topico.posts.order_by(ForumPost.data_criacao.asc()).all()
    return render_template('detalhe_topico.html', topico=topico, posts=posts)

@app.route('/forum/novo_topico', methods=['GET', 'POST'])
@login_required
def criar_topico():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        if titulo and conteudo:
            novo_topico = ForumTopico(titulo=titulo, conteudo=conteudo, user_id=session['user_id'])
            db.session.add(novo_topico)
            db.session.commit()
            flash('Tópico criado com sucesso!', 'success')
            return redirect(url_for('detalhe_topico', topico_id=novo_topico.id))
    return render_template('criar_topico.html')

@app.route('/hub_servicos')
@login_required
def hub_servicos():
    eventos_futuros = Evento.query.filter(Evento.vagas > 0).order_by(Evento.data_evento.asc()).limit(3).all()
    return render_template('hub_servicos.html', eventos_futuros=eventos_futuros)

@app.route('/eventos')
@login_required
def eventos():
    todos_eventos = Evento.query.order_by(Evento.data_evento.asc()).all()
    return render_template('eventos.html', eventos=todos_eventos)

@app.route('/evento/<int:evento_id>')
@login_required
def detalhe_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    user = User.query.get(session['user_id'])
    ja_inscrito = evento in user.eventos_inscritos.all()
    return render_template('detalhe_evento.html', evento=evento, ja_inscrito=ja_inscrito)

@app.route('/evento/<int:evento_id>/inscrever', methods=['POST'])
@login_required
def inscrever_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    user = User.query.get(session['user_id'])
    if evento in user.eventos_inscritos.all():
        flash('Você já está inscrito neste evento.', 'info')
    elif evento.vagas_restantes <= 0:
        flash('Vagas esgotadas para este evento!', 'danger')
    else:
        user.eventos_inscritos.append(evento)
        db.session.commit()
        flash('Inscrição realizada com sucesso!', 'success')
    return redirect(url_for('detalhe_evento', evento_id=evento.id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: return redirect(url_for('noticias'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not (username and len(username) == 12 and username.isdigit()):
            flash('Formato de matrícula inválido. Use apenas os 12 dígitos.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Esta matrícula já está registrada. Tente fazer o login.', 'warning')
        else:
            password_hash = generate_password_hash(password)
            novo_user = User(username=username, password_hash=password_hash)
            db.session.add(novo_user)
            db.session.commit()
            flash('Conta criada com sucesso! Pode fazer o login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('noticias'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('noticias'))
        else:
            flash('Matrícula ou senha inválidos. Tente novamente.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user = User.query.get_or_404(session['user_id'])
    if request.method == 'POST' and 'picture' in request.files:
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
    return render_template('account.html', image_file=image_file, eventos=user.eventos_inscritos)

# --- Comandos CLI ---
@app.cli.command('seed-db')
def seed_db_command():
    """Popula o banco de dados com dados iniciais."""
    if Clube.query.count() > 0:
        print("O banco de dados já contém dados.")
        return
        
    clube1 = Clube(nome='Clube de Programação', descricao='Para entusiastas de código e desenvolvimento.', categoria='Tecnologia')
    clube2 = Clube(nome='Clube de Leitura', descricao='Discussões sobre obras literárias.', categoria='Cultura')
    clube3 = Clube(nome='Clube de Esportes', descricao='Organização de treinos e campeonatos.', categoria='Esportes')
    db.session.add_all([clube1, clube2, clube3])
    db.session.commit()
    print("Clubes de exemplo criados.")

    e1 = Evento(titulo='Maratona de Programação', descricao='Resolva desafios de programação em equipe.', vagas=50, clube_id=clube1.id, data_evento=datetime(2025, 8, 10, 9, 0, 0, tzinfo=timezone.utc))
    e2 = Evento(titulo='Debate sobre Ficção Científica', descricao='Análise do livro "Duna" de Frank Herbert.', vagas=30, clube_id=clube2.id, data_evento=datetime(2025, 8, 15, 18, 30, 0, tzinfo=timezone.utc))
    e3 = Evento(titulo='Torneio de Vôlei', descricao='Monte sua equipe e participe!', vagas=40, clube_id=clube3.id, data_evento=datetime(2025, 8, 20, 14, 0, 0, tzinfo=timezone.utc))
    db.session.add_all([e1, e2, e3])
    db.session.commit()
    print("Eventos de exemplo criados.")

    n1 = Noticia(titulo='Inscrições Abertas para a Maratona!', conteudo='As inscrições para a maratona de programação já começaram. Não perca!', evento=e1)
    db.session.add(n1)
    db.session.commit()
    print("Notícias de exemplo criadas.")
    

if __name__ == '__main__':
    app.run(debug=True)