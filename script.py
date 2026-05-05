import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO
import re
import tempfile
import json

# --- RUN streamlit run script.py

# --- CONFIGURAÇÃO DA API ---
GENAI_API_KEY = "AIzaSyCUOEocIQRpGGvr8D9yqC0euU2WiJ4EoQE"
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# --- DICIONÁRIO (SEM ASTERISCOS PARA O EXCEL) ---
DICIONARIO_CAMPOS = {
    "Coletor de Dados": [
        "Android", "Processador", "RAM / ROM", "Expansão de Memória",
        "Dimensões", "Peso", "Display", "Bateria",
        "Temperatura Operacional", "Temperatura de Armazenagem",
        "Resistência a Quedas", "Indice Selagem e Vedação", "Leitor de Códigos",
        "Câmera Traseira", "Câmera Frontal", "WLAN",
        "Bluetooth", "Redes Móveis", "GPS"
    ],
    "Leitor de Dados": [
        "Campo de Visão", "Dimensões", "Peso", "Interface",
        "Interferência de Luz", "Bateria", "Temperatura Operacional",
        "Leitor de Códigos", "Velocidade de Escaneamento", "Distância Operacional",
        "Proteção", "Resistência a Queda", "Bluetooth", "Base de Carregamento", "Garantia"
    ],
    "Impressora Térmica": [
        "Método de Impressão", "Resolução", "Velocidade Máxima",
        "Largura de Impressão", "Linguagem de Programação", "Conectividade",
        "Sensores", "Memória", "Dimensões", "Peso"
    ]
}

# --- INTERFACE E CSS ---
st.set_page_config(page_title="Comparador de Dispositivos", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    header { visibility: hidden; }
    div.stButton > button:first-child {
        background-color: #3b82f6;
        color: white;
        border-radius: 5px;
        width: 100%;
        font-weight: bold;
    }
    /* Negrito apenas na exibição da tabela no navegador */
    th { font-weight: bold !important; text-transform: uppercase; }
    td:first-child { font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("Configurações")
    categoria = st.selectbox("Categoria", list(DICIONARIO_CAMPOS.keys()))
    qtd_produtos = st.sidebar.slider("Quantidade de Dispositivos", 1, 3, 2)
    st.divider()

st.title("🛡️ Comparador de Dispositivos")

campos_ativos = DICIONARIO_CAMPOS[categoria]


def processar_com_gemini(input_data, is_file=False):
    prompt = f"""
    Extraia dados técnicos de {categoria}. Retorne JSON puro com as chaves: {campos_ativos}.
    REGRAS:
    - WLAN: Apenas frequências (ex: 2.4/5G).
    - Processador: Modelo e núcleos (ex: Octa-core 2.0GHz).
    - Resumo: Seja muito enxuto. Use 'Não informado' se faltar.
    """
    try:
        if is_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(input_data.getvalue())
                tmp_path = tmp.name
            arquivo_gemini = genai.upload_file(path=tmp_path, mime_type="application/pdf")
            response = model.generate_content([prompt, arquivo_gemini])
        else:
            response = model.generate_content(f"{prompt} \n Link: {input_data}")

        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else None
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


# --- ENTRADAS ---
colunas_ui = st.columns(qtd_produtos)
entradas = []

for i, col in enumerate(colunas_ui):
    with col:
        st.subheader(f"Dispositivo {i + 1}")
        nome_custom = st.text_input(f"Nome do Modelo", placeholder=f"Ex: RT40", key=f"nome_{i}")
        tipo = st.segmented_control("Fonte:", ["Link", "PDF"], key=f"t_{i}", default="Link")

        if tipo == "Link":
            dado = st.text_input("URL", placeholder="https://...", key=f"u_{i}")
        else:
            dado = st.file_uploader("Datasheet", type="pdf", key=f"p_{i}")

        nome_final = nome_custom if nome_custom else f"Produto {i + 1}"
        entradas.append({"dado": dado, "is_file": (tipo == "PDF"), "nome": nome_final})

st.divider()

# --- PROCESSAMENTO ---
if st.button("GERAR COMPARATIVO"):
    if all(item["dado"] for item in entradas):
        with st.spinner("Analisando..."):
            resultados = []
            nomes_colunas = []

            for item in entradas:
                res = processar_com_gemini(item["dado"], is_file=item["is_file"])
                if res:
                    resultados.append(res)
                    nomes_colunas.append(item["nome"])

            if len(resultados) == len(entradas):
                df = pd.DataFrame(resultados, index=nomes_colunas).T

                st.success("Concluído")

                # Exibe na tela com negrito via Estilo (não afeta o Excel)
                st.table(df)

                # Gerar Excel limpo
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Comparativo')

                st.download_button(
                    label="BAIXAR EXCEL",
                    data=output.getvalue(),
                    file_name=f"comparativo_{categoria.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("Preencha todos os campos.")