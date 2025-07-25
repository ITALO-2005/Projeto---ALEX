"""Criação inicial do banco de dados

Revision ID: 93b81d3e11fc
Revises: 
Create Date: 2025-07-22 16:05:54.178591

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93b81d3e11fc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('clube',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('categoria', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nome')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('username', sa.String(length=12), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=False),
    sa.Column('image_file', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('evento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('vagas', sa.Integer(), nullable=False),
    sa.Column('data_evento', sa.DateTime(), nullable=False),
    sa.Column('clube_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['clube_id'], ['clube.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('forum_topico',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('conteudo', sa.Text(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('membros_clube',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('clube_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['clube_id'], ['clube.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'clube_id')
    )
    op.create_table('forum_post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conteudo', sa.Text(), nullable=False),
    sa.Column('data_criacao', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('topico_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['topico_id'], ['forum_topico.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('inscricao_evento',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('evento_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'evento_id')
    )
    op.create_table('noticia',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('conteudo', sa.Text(), nullable=False),
    sa.Column('data_publicacao', sa.DateTime(), nullable=False),
    sa.Column('evento_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['evento_id'], ['evento.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('noticia')
    op.drop_table('inscricao_evento')
    op.drop_table('forum_post')
    op.drop_table('membros_clube')
    op.drop_table('forum_topico')
    op.drop_table('evento')
    op.drop_table('user')
    op.drop_table('clube')
    # ### end Alembic commands ###
