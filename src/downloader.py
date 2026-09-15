import os
import time
import requests
import gzip
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
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

def download_file(url, dest_path, position=0):
    import urllib.request
    import urllib3
    urllib3.disable_warnings()
    try:
        filename = os.path.basename(dest_path)
        if url.startswith("ftp://"):
            with urllib.request.urlopen(url) as response:
                total = int(response.info().get('Content-Length', 0))
                with open(dest_path, 'wb') as f:
                    with tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024, desc=filename, position=position, leave=True) as pbar:
                        while chunk := response.read(1024*1024):
                            f.write(chunk)
                            pbar.update(len(chunk))
        else:
            response = requests.get(url, stream=True, verify=False)
            response.raise_for_status()
            total = int(response.headers.get('content-length', 0))
            with open(dest_path, 'wb') as f:
                with tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024, desc=filename, position=position, leave=True) as pbar:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
    except Exception as e:
        logger.error(f"\nERRO ao baixar {url}: {e}")
        raise e

def global_update():
    logger.info("\n[Atualizacao Global] Baixando bancos de dados em paralelo...")
    urls_dests = [
        ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Doses_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Doses_Residencia.parquet")),
        ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Cobertura_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Cobertura_Residencia.parquet")),
        ("https://dados.anvisa.gov.br/dados/VigiMed_Notificacoes.csv", os.path.join(RAW_DATA_DIR, "VigiMed_Notificacoes.csv")),
        ("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", os.path.join(DATA_DIR, "cidades_ibge.json"))
    ]
    # Remove initial logger.info inside threads to avoid corrupting tqdm output
    def download_task(args):
        idx, (url, dest) = args
        filename = os.path.basename(dest)
        try:
            if "municipios" in url:
                import urllib3
                urllib3.disable_warnings()
                req = requests.get(url, headers={'Accept-Encoding': 'gzip'}, verify=False)
                with open(dest, 'wb') as f:
                    f.write(req.content)
                # Municipios eh tao rapido que faremos uma barra falsa instantanea 100%
                with tqdm(total=1, unit='B', unit_scale=True, desc=filename, position=idx, leave=True) as pbar:
                    pbar.update(1)
            else:
                download_file(url, dest, position=idx)
            return True
        except Exception as e:
            return False
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(download_task, enumerate(urls_dests)))
    print("\n" * len(urls_dests))  # Push cursor down past the bars
        
    if all(results):
        logger.info("Todos os bancos foram atualizados com sucesso!\n")
    else:
        logger.error("ERRO: Alguns bancos falharam no download. Tente novamente mais tarde.\n")
        import sys
        sys.exit(1)
