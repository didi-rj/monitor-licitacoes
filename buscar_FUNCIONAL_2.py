import requests
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

PALAVRAS = [
    "topografia", "topográfico", "topografico",
    "georreferenciamento", "georreferenciar",
    "levantamento planialtimétrico", "planialtimetrico",
    "levantamento cadastral", "cadastro urbano", "cadastro tecnico",
    "batimetria", "batimétrico", "batimetrico",
    "aerolevantamento", "drone", "vant", "v.a.n.t", "uas", "rpav",
    "ortofoto", "ortomosaico", "ortomosaico",
    "fotogrametria", "fotogramétrico", "mapeamento",
    "lidar", "laser scanner", "nuvem de pontos",
    "geodésico", "geodesico", "gnss", "rtk"
]

PALAVRAS_NEGATIVAS = [
    "locação de veículos",
    "fornecimento de combustível",
    "material de escritório",
    "equipamentos de informática",
    "serviço de limpeza",
    "vigilância",
    "consultoria administrativa"
]

EMAIL_REMETENTE = "didisurveygps@gmail.com"
EMAIL_SENHA = "hztc hetf mwtg aouo"
EMAIL_DESTINO = "didisurveygps@gmail.com"

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

def buscar():
    log("Iniciando busca no PNCP...")

    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

    data_inicial = "20260220"  # AAAAMMDD
    data_final = datetime.now().strftime("%Y%m%d")  # AAAAMMDD

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
            "codigoModalidadeContratacao": 6,  # ajuste aqui (ex.: 6, 8, etc.)
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
            log(f"Formato inesperado. Chaves: {list(dados.keys()) if isinstance(dados, dict) else type(dados)}")
            break

        lista = dados.get("data", [])
        if not lista:
            log("Nenhum registro nesta página.")
            break

        for item in lista:
            total_analisadas += 1
            objeto = (item.get("objetoCompra") or "").lower()

            if any(p in objeto for p in PALAVRAS):
                id_lic = item.get("numeroControlePNCP")
                orgao = (item.get("orgaoEntidade") or {}).get("razaosocial", "")
                data_pub = item.get("dataPublicacaoPncp", "")
                link = f"https://pncp.gov.br/app/editais/{id_lic}"

                try:
                    c.execute(
                        "INSERT INTO licitacoes VALUES (?, ?, ?, ?, ?)",
                        (id_lic, orgao, objeto, data_pub, link)
                    )
                    conn.commit()

                    texto = f"""Nova Licitação Encontrada:

Órgão: {orgao}
Objeto: {objeto}
Data: {data_pub}
Link: {link}
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


if __name__ == "__main__":
    log("Sistema iniciado.")
    criar_banco()
    buscar()
    log("Sistema finalizado.")