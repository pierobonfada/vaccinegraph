import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('vaccinegraph')

def eprint(*args, **kwargs):
    logger.info(*args, **kwargs)

def format_millions(x, pos):
    if x >= 1e6:
        return f'{x*1e-6:g} Milhões'
    elif x >= 1e3:
        return f'{x*1e-3:g} Mil'
    return f'{x:g}'

def padroniza_nome_vacina(nome):
    nome = str(nome).upper()
    
    # COVID-19 Subtypes
    covid_keywords = ['COVID', 'CORONAVAC', 'ASTRAZENECA', 'PFIZER', 'COMIRNATY', 'JANSSEN', 'BUTANTAN', 'FIOCRUZ', 'COVISHIELD', 'SPIKEVAX', 'MODERNA']
    if any(k in nome for k in covid_keywords):
        if 'PFIZER' in nome or 'COMIRNATY' in nome or 'BIONTECH' in nome:
            return 'COVID-19 (Pfizer)'
        if 'CORONAVAC' in nome or 'SINOVAC' in nome or 'BUTANTAN' in nome:
            return 'COVID-19 (Coronavac)'
        if 'ASTRAZENECA' in nome or 'FIOCRUZ' in nome or 'COVISHIELD' in nome or 'CHADOX' in nome:
            return 'COVID-19 (AstraZeneca)'
        if 'JANSSEN' in nome or 'AD26' in nome:
            return 'COVID-19 (Janssen)'
        if 'MODERNA' in nome or 'SPIKEVAX' in nome:
            return 'COVID-19 (Moderna)'
        if 'INATIVADA' in nome and 'SINOVAC' not in nome and 'BHARAT' not in nome and 'SINOPHARM' not in nome:
            return 'COVID-19 (Coronavac)' 
        if 'RECOMBINANTE' in nome and 'ASTRAZENECA' not in nome and 'JANSSEN' not in nome and 'GAMALEYA' not in nome:
            return 'COVID-19 (AstraZeneca)' 
        return 'COVID-19 (Outras/Genérica)'
        
    if 'DENGUE' in nome or 'QDENGA' in nome or 'DENGVAXIA' in nome:
        if 'QDENGA' in nome:
            return 'Dengue (Qdenga/Atenuada)'
        if 'DENGVAXIA' in nome or ('RECOMBINANTE' in nome and 'ATENUADA' in nome):
            return 'Dengue (Dengvaxia/Recombinante)'
        if 'ATENUADA' in nome and 'RECOMBINANTE' not in nome:
            return 'Dengue (Qdenga/Atenuada)'
        return 'Dengue (Outras/Genérica)'
        
    if 'INFLUENZA' in nome and 'HAEMOPHILUS' not in nome:
        if 'TETRAVALENTE' in nome or 'QUADRIVALENT' in nome or 'TETRA' in nome:
            return 'Influenza (Tetravalente)'
        if 'TRIVALENTE' in nome or 'TRIVALENT' in nome or 'SPLIT 3V' in nome:
            return 'Influenza (Trivalente)'
        return 'Influenza (Outras/Genérica)'
        
    if 'HAEMOPHILUS' in nome: return 'Haemophilus influenzae b (Hib)'
    if 'POLIO' in nome and 'ORAL' in nome: return 'Poliomielite Oral (VOP)'
    import re
    if re.search(r'\bVOP\b', nome): return 'Poliomielite Oral (VOP)'
    if 'POLIO' in nome: return 'Poliomielite Inativada (VIP)'
    if re.search(r'\bVIP\b', nome): return 'Poliomielite Inativada (VIP)'
    if 'HEPATITE B' in nome: return 'Hepatite B'
    if 'HEPATITE A' in nome: return 'Hepatite A'
    if 'FEBRE AMARELA' in nome: return 'Febre Amarela'
    if 'RAIVA' in nome: return 'Raiva'
    if 'VARICELA' in nome: return 'Varicela'
    if 'PENTA' in nome: return 'Pentavalente (DTP-HB-Hib)'
    if 'TRÍPLICE VIRAL' in nome or 'SARAMPO' in nome: return 'Tríplice Viral (SCR)'
    if 'PNEUMO' in nome: return 'Pneumocócica'
    if 'MENING' in nome: return 'Meningocócica'
    if re.search(r'\bBCG\b', nome): return 'BCG'
    if 'ROTAV' in nome: return 'Vacina Rotavírus'
    if re.search(r'\bHPV\b', nome): return 'HPV'
    if re.search(r'\bDTP\b', nome) and 'PENTA' not in nome: return 'DTP (Tríplice Bacteriana)'
    
    
    if 'SORO' in nome:
        if 'RABICO' in nome or 'RÁBICO' in nome: return 'Soro Antirrábico'
        if 'TETANICO' in nome or 'TETÂNICO' in nome: return 'Soro Antitetânico'
        if 'BOTROPICO' in nome or 'BOTRÓPICO' in nome: return 'Soro Antibotrópico'
        if 'CROTALICO' in nome or 'CROTÁLICO' in nome: return 'Soro Anticrotálico'
        if 'ESCORPIONICO' in nome or 'ESCORPIÔNICO' in nome: return 'Soro Antiescorpiônico'
        if 'ARACNIDICO' in nome or 'ARACNÍDICO' in nome: return 'Soro Antiaracnídico (Loxosceles, Phoneutria, Tityus)'
        if 'ELAPIDICO' in nome or 'ELAPÍDICO' in nome: return 'Soro Antielapídico'
        if 'BOTULINICO' in nome or 'BOTULÍNICO' in nome: return 'Soro Antibotulínico'
        return 'Soro (Outros)'

    return nome.title()

