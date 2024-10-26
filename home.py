import streamlit as st
from pymongo import MongoClient
import random
from datetime import datetime, timedelta
import base64
import requests



st.set_page_config( 
    page_title="Futebol Society",
    page_icon="soccer",
)
st.image('https://www.assof.com.br/ASSOF/wp-content/uploads/2022/02/CAMPO-DE-FUTEBOL-SITE--2048x683.jpg', width=500)
def convert_bytes_to_base64(image_bytes):
    return base64.b64encode(image_bytes.read()).decode("utf-8")


client = MongoClient("mongodb+srv://user_01:sucesso1807@cluster0.slfd3no.mongodb.net/")
db = client["futebol"]
collection = db["atletas"]
collection_pontuacao = db["pontuacao"]
collection_cartoes = db["cartoes"]
collection_config = db["config"] 

# Função para verificar e limpar dados a cada 2 dias
def limpar_dados():
    config = collection_config.find_one({"_id": "config"})
    if config:
        ultima_limpeza = config["ultima_limpeza"]
        if datetime.now() >= ultima_limpeza + timedelta(hours=8):
            collection_pontuacao.delete_many({})
            collection_cartoes.delete_many({})
            collection_config.update_one({"_id": "config"}, {"$set": {"ultima_limpeza": datetime.now()}})
            return True
    else:
        collection_config.insert_one({"_id": "config", "ultima_limpeza": datetime.now()})
        return True
    return False

# Função para inserir atleta no banco de dados
def inserir_atleta(nome, posicao):
    atleta = {
        "nome": nome,
        "posicao": posicao
    }
    collection.insert_one(atleta)

# Função para sortear times, mesmo que faltem jogadores para algumas posições
def sortear_times_com_configuracao(atletas_presentes, qtd_times):
    formacao_ideal = {
        "Zagueiro": 2,
        "Ala": 2,
        "Meio-Campo": 1,
        "Atacante": 1
    }

    # Organizar atletas por posição
    atletas_por_posicao = {
        "Zagueiro": [],
        "Ala": [],
        "Meio-Campo": [],
        "Atacante": []
    }

    for atleta in atletas_presentes:
        if atleta["posicao"] in atletas_por_posicao:
            atletas_por_posicao[atleta["posicao"]].append(atleta)

    times = [[] for _ in range(qtd_times)]

    # Função para distribuir atletas por posição entre os times
    def distribuir_atletas(posicao, qtd_necessaria):
        random.shuffle(atletas_por_posicao[posicao])
        for time in times:
            for _ in range(qtd_necessaria):
                if atletas_por_posicao[posicao]:
                    time.append(atletas_por_posicao[posicao].pop())

    # Distribuir os jogadores que existem para cada posição
    distribuir_atletas("Zagueiro", 2)
    distribuir_atletas("Ala", 2)
    distribuir_atletas("Meio-Campo", 1)
    distribuir_atletas("Atacante", 1)

    # Agora, distribuir os jogadores restantes (que sobraram) para os times restantes
    jogadores_restantes = []
    for posicao, atletas in atletas_por_posicao.items():
        jogadores_restantes.extend(atletas)

    random.shuffle(jogadores_restantes)  # Embaralhar para que a distribuição seja aleatória

    # Distribuir os jogadores restantes entre os times (respeitando o limite de 6 jogadores por time)
    for jogador in jogadores_restantes:
        for time in times:
            if len(time) < 7:
                time.append(jogador)
                break

    return times, True

# Função para registrar a pontuação de um atleta
def registrar_pontuacao(nome, pontuacao):
    collection_pontuacao.insert_one({
        "nome": nome,
        "pontuacao": pontuacao
    })

# Função para registrar cartões de um atleta
def registrar_cartoes(nome, amarelos, vermelhos):
    collection_cartoes.insert_one({
        "nome": nome,
        "amarelos": amarelos,
        "vermelhos": vermelhos
    })

# Função para exibir cartões recebidos
def exibir_cartoes():
    cartoes = list(collection_cartoes.find())
    return cartoes

# Função para encontrar o atleta com mais pontos na semana
def atleta_mais_pontos():
    pipeline = [
        {
            "$group": {
                "_id": "$nome",
                "total_pontos": {"$sum": "$pontuacao"}
            }
        },
        {
            "$sort": {"total_pontos": -1}
        },
        {
            "$limit": 1
        }
    ]
    resultado = list(collection_pontuacao.aggregate(pipeline))
    return resultado[0] if resultado else None

# Interface do Streamlit
st.title("Society FC")

# Limpar dados se necessário
limpeza_realizada = limpar_dados()
if limpeza_realizada:
    st.success("Os dados de pontuação e cartões foram limpos, com sucesso!.")

# Menu lateral para navegação
menu = st.sidebar.selectbox("Menu", ["Cadastro de Atletas", "Sortear Atleta", "Sortear Times", "Pontuação", "Cartões da Semana", "Melhor Time da Semana"])

if menu == "Cadastro de Atletas":
    st.subheader("Cadastro de Atletas")
    nome = st.text_input("Nome do Atleta")
    posicao = st.text_input("Posição do Atleta")

    if st.button("Salvar Atleta"):
        if nome and posicao:
            inserir_atleta(nome, posicao)
            st.success(f"Atleta {nome} na posição {posicao} salvo com sucesso!")
        else:
            st.error("Por favor, preencha todos os campos.")

elif menu == "Sortear Times":
    st.subheader("Sorteio de Times")

    # Seleção de atletas presentes
    atletas = list(collection.find())
    atleta_nomes = {atleta['nome']: atleta for atleta in atletas}
    atletas_presentes = st.multiselect("Selecione os Atletas Presentes", options=atleta_nomes.keys())

    qtd_times = st.number_input("Quantidade de Times", min_value=2, step=1)

    if st.button("Sortear Times"):
        if not atletas_presentes:
            st.error("Por favor, selecione os atletas presentes.")
        else:
            atletas_selecionados = [atleta_nomes[nome] for nome in atletas_presentes]
            times, times_validos = sortear_times_com_configuracao(atletas_selecionados, qtd_times)

            if times_validos:
                for i, time in enumerate(times, start=1):
                    st.write(f"Time {i}:")
                    for atleta in time:
                        st.write(f"- {atleta['nome']} ({atleta['posicao']})")
            else:
                st.error("Não foi possível formar todos os times corretamente.")

elif menu == "Pontuação":
    st.subheader("Pontuação dos Atletas")
    atletas = list(collection.find())
    atleta_nomes = [atleta['nome'] for atleta in atletas]
    
    nome = st.selectbox("Escolha o Atleta", atleta_nomes)
    pontuacao = st.number_input("Pontuação", min_value=0, step=1)

    if st.button("Registrar Pontuação"):
        registrar_pontuacao(nome, pontuacao)
        st.success(f"Pontuação de {pontuacao} registrada para o atleta {nome}.")

elif menu == "Cartões da Semana":
    st.subheader("Registro de Cartões")
    atletas = list(collection.find())
    atleta_nomes = [atleta['nome'] for atleta in atletas]
    
    nome = st.selectbox("Escolha o Atleta", atleta_nomes)
    amarelos = st.number_input("Cartões Amarelos", min_value=0, step=1)
    vermelhos = st.number_input("Cartões Vermelhos", min_value=0, step=1)

    if st.button("Registrar Cartões"):
        registrar_cartoes(nome, amarelos, vermelhos)
        st.success(f"Cartões registrados para o atleta {nome}.")

    st.subheader("Cartões Recebidos na Semana")
    cartoes = exibir_cartoes()
    if cartoes:
        for cartao in cartoes:
            st.write(f"{cartao['nome']}: {cartao['amarelos']} amarelo(s), {cartao['vermelhos']} vermelho(s)")
    else:
        st.warning("Nenhum cartão registrado.")

elif menu == "Melhor Time da Semana":
    st.subheader("Melhor Time da Semana")
    atleta = atleta_mais_pontos()
    if atleta:
        st.success(f"Melhor TIME da Semana foi o de : {atleta['_id']} com {atleta['total_pontos']} pontos.")
    else:
        st.warning("Nenhum ponto registrado esta semana.")


st.markdown("---")  # Linha separadora
st.markdown("""
<div style='text-align: center; color: grey;'>
    <small>Desenvolvido por Sérgio Santos, (77)99921-1063 © 2024</small>
</div>
""", unsafe_allow_html=True)
