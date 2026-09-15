import os
import time
import requests
import gzip
import concurrent.futures
from pathlib import Path
from src.utils import logger, eprint

DATA_DIR = "data"
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_DIR = "output"

if not os.path.exists(RAW_DATA_DIR): os.makedirs(RAW_DATA_DIR)
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def check_file_age(filepath, max_days=180):
    if not os.path.exists(filepath):
        return False, "Missing"
    age_days = (time.time() - os.path.getmtime(filepath)) / (24 * 3600)
    if age_days > max_days:
        return True, "Old"
    return True, "OK"

def download_file(url, dest_path):
    import urllib.request
    import urllib3
    urllib3.disable_warnings()
    try:
        if url.startswith("ftp://"):
            with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as f:
                while chunk := response.read(1024*1024):
                    f.write(chunk)
        else:
            response = requests.get(url, stream=True, verify=False)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
    except Exception as e:
        logger.error(f"ERRO ao baixar {url}: {e}")
        raise e

def global_update():
    logger.info("\n[Atualizacao Global] Baixando bancos de dados em paralelo...")
    urls_dests = [
        ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Doses_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Doses_Residencia.parquet")),
        ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Cobertura_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Cobertura_Residencia.parquet")),
        ("https://dados.anvisa.gov.br/dados/VigiMed_Notificacoes.csv", os.path.join(RAW_DATA_DIR, "VigiMed_Notificacoes.csv")),
        ("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", os.path.join(DATA_DIR, "cidades_ibge.json"))
    ]
    def download_task(item):
        url, dest = item
        filename = os.path.basename(dest)
        logger.info(f" Iniciando download: {filename}")
        try:
            if "municipios" in url:
                import urllib3
                urllib3.disable_warnings()
                req = requests.get(url, headers={'Accept-Encoding': 'gzip'}, verify=False)
                with open(dest, 'wb') as f:
                    f.write(req.content)
            else:
                download_file(url, dest)
            logger.info(f" Concluido: {filename}")
            return True
        except Exception as e:
            return False
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(download_task, urls_dests))
        
    if all(results):
        logger.info("Todos os bancos foram atualizados com sucesso!\n")
    else:
        logger.error("ERRO: Alguns bancos falharam no download. Tente novamente mais tarde.\n")
        import sys
        sys.exit(1)
