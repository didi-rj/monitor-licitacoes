import requests
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ==============================
# PALAVRAS TÉCNICAS
# ==============================

PALAVRAS = [
    "topografia", "topográfico", "topografico",
    "georreferenciamento", "georreferenciar",
    "levantamento planialtimétrico", "planialtimetrico",
    "levantamento cadastral", "cadastro urbano", "cadastro tecnico",
    "batimetria", "batimétrico", "batimetrico",
    "aerolevantamento", "drone", "vant", "v.a.n.t", "uas", "rpav",
    "ortofoto", "ortomosaico",
    "fotogrametria", "fotogramétrico",
    "lidar", "laser scanner", "nuvem de pontos",
    "geodésico", "geodesico", "gnss", "rtk"
]

# ==============================
# PALAVRAS DE RUÍDO (IGNORAR)
# ==============================

PALAVRAS_NEGATIVAS = [
    "locação de veículos",
    "fornecimento de combustível",
    "material de escritório",
    "equipamentos de informática",
    "serviço de limpeza",
    "vigilância",
    "consultoria administrativa",
    "levantamento de preços",
    "cadastro de fornecedores"
]

# ==============================
# CONFIGURAÇÃO DE EMAIL
# ==============================

EMAIL_REMETENTE = "didisurveygps@gmail.com"
EMAIL_SENHA = "hztc hetf mwtg aouo"
EMAIL_DESTINO = "didisurveygps@gmail.com"

# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def log(msg):
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}")

def criar_banco():
    conn = sqlite3.connect("banco.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS licitacoes (
            id TEXT PRIMARY KEY,
            orgao TEXT,
            objeto TEXT,
            data TEXT,
            link TEXT
        )
    """)
    conn.commit()
    conn.close()
    log("Banco de dados verificado/criado com sucesso.")

def enviar_email(texto):
    try:
        msg = MIMEText(texto)
        msg["Subject"] = "Nova Licitação Encontrada"
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = EMAIL_DESTINO

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.send_message(msg)

        log("Email enviado com sucesso!")
    except Exception as e:
        log(f"Erro ao enviar email: {e}")

def montar_link_pncp(numero_controle):
    try:
        # Formato comum:
        # 01616255000146-1-000016/2026
        
        if "/" in numero_controle and "-" in numero_controle:
            parte1, ano = numero_controle.split("/")
            partes = parte1.split("-")

            cnpj = partes[0]
            sequencial = partes[-1]

            # remove zeros à esquerda
            sequencial = str(int(sequencial))

            return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"

        # Caso já venha no formato novo
        elif numero_controle.count("/") == 2:
            return f"https://pncp.gov.br/app/editais/{numero_controle}"

        # fallback
        else:
            return f"https://pncp.gov.br/app/editais/{numero_controle}"

    except Exception:
        return f"https://pncp.gov.br/app/editais/{numero_controle}"

# ==============================
# BUSCA PRINCIPAL
# ==============================

def buscar():
    log("Iniciando busca no PNCP...")

    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

    data_inicial = "20260220"  # Ajuste se quiser
    data_final = datetime.now().strftime("%Y%m%d")

    pagina = 1
    tamanho = 50

    total_analisadas = 0
    total_novas = 0

    conn = sqlite3.connect("banco.db")
    c = conn.cursor()

    while True:
        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "codigoModalidadeContratacao": 6,
            "pagina": pagina,
            "tamanhoPagina": tamanho
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            dados = resp.json()
        except Exception as e:
            log(f"Erro na requisição/JSON: {e}")
            break

        if not isinstance(dados, dict) or "data" not in dados:
            log("Formato inesperado da API.")
            break

        lista = dados.get("data", [])
        if not lista:
            log("Nenhum registro nesta página.")
            break

        for item in lista:
            total_analisadas += 1
            objeto = (item.get("objetoCompra") or "").lower()

            # ==============================
            # FILTRO INTELIGENTE
            # ==============================

            matches = [p for p in PALAVRAS if p in objeto]
            negativo = any(n in objeto for n in PALAVRAS_NEGATIVAS)

            # Critério:
            # - Pelo menos 2 termos técnicos
            # - Não conter termos negativos
            if len(matches) >= 2 and not negativo:

                id_lic = item.get("numeroControlePNCP")
                orgao = (item.get("orgaoEntidade") or {}).get("razaoSocial", "")
                data_pub = item.get("dataPublicacaoPncp", "")
                link = montar_link_pncp(id_lic)

                try:
                    c.execute(
                        "INSERT INTO licitacoes VALUES (?, ?, ?, ?, ?)",
                        (id_lic, orgao, objeto, data_pub, link)
                    )
                    conn.commit()

                    texto = f"""Nova Licitação Encontrada:

Órgão: {orgao}
Data: {data_pub}

Objeto:
{objeto}

Link:
{link}
"""
                    enviar_email(texto)
                    total_novas += 1
                    log(f"Nova licitação salva: {id_lic}")

                except sqlite3.IntegrityError:
                    pass

        total_paginas = dados.get("totalPaginas")
        if isinstance(total_paginas, int) and pagina >= total_paginas:
            break

        pagina += 1

    conn.close()
    log("Busca finalizada.")
    log(f"Total analisadas: {total_analisadas}")
    log(f"Total novas encontradas: {total_novas}")

# ==============================
# EXECUÇÃO
# ==============================

if __name__ == "__main__":
    log("Sistema iniciado.")
    criar_banco()
    buscar()
    log("Sistema finalizado.")