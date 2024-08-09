# -*- coding: utf-8 -*-
from enum import Enum
import requests
from bs4 import BeautifulSoup
from unicodedata import normalize
from stringcase import snakecase
import re


def normalize_data(text):
    return normalize('NFKD', text)


def snake(source):
    source = source.split(':')[0].strip() if source.find(
        ':') > 0 else source.strip()
    source = re.sub(r'[\W_]+ ', '', source)
    source = re.sub(' +', ' ', source)
    return snakecase(normalize_data(source.lower()).encode(
        'ASCII', 'ignore').decode('ASCII'))


class TipoInfo(Enum):
    nfe = None
    emitente = 'btn_aba_emitente'
    destinatario = 'btn_aba_destinatario'
    produtos = 'btn_aba_produtos'
    totais = 'btn_aba_totais'
    transporte = 'btn_aba_transporte'
    cobranca = 'btn_aba_cobranca'
    infadicionais = 'btn_aba_infadicionais'


class SefazBa:
    def __init__(self, url):
        self.url = url
        self.url_request = self.url.replace(
            'qrcode', 'Modulos/Geral/NFCEC_consulta_abas')
        self.session = requests.Session()
        self.session.get(url)

    def get_nota(self):
        nota = dict()
        nota['nfe'] = self.dinamic_colector(TipoInfo.nfe)
        nota['emitente'] = self.dinamic_colector(TipoInfo.emitente)
        nota['destinatario'] = self.dinamic_colector(TipoInfo.destinatario)
        nota['produtos'] = self.dinamic_colector(TipoInfo.produtos)
        nota['totais'] = self.dinamic_colector(TipoInfo.totais)
        nota['cobranca'] = self.dinamic_colector(TipoInfo.cobranca)
        nota['infadicionais'] = self.dinamic_colector(TipoInfo.infadicionais)
        return nota

    def save_state(self, soup):
        self.view_state = soup.find('input', id='__VIEWSTATE').get('value')
        self.event_validation = soup.find(
            'input', id='__EVENTVALIDATION').get('value')
        self.view_state_generator = soup.find(
            'input', id='__VIEWSTATEGENERATOR').get('value')

    def dinamic_colector(self, tipo: TipoInfo):
        if tipo.value is None:
            response = self.session.get(self.url_request)
        else:
            data = {
                '__VIEWSTATE': self.view_state,
                '__VIEWSTATEGENERATOR': self.view_state_generator,
                '__EVENTVALIDATION': self.event_validation,
                'hd_origem_chamada': '',
                tipo.value + '.x': '13^',
                tipo.value + '.y': '12^',
                'hid_uf_dest': ''
            }
            response = self.session.post(
                self.url_request, data=data, verify=False)
        soup = BeautifulSoup(normalize_data(response.text), 'html.parser')
        self.save_state(soup)

        data = dict()
        td_titulo = soup.find('td', {'class': 'table-titulo-aba'})

        titulo_aba = snake(td_titulo.text)
              
        if tipo != TipoInfo.produtos and tipo != TipoInfo.cobranca:
            data[titulo_aba] = dict()
            tds_aba = td_titulo.parent.parent.next_sibling.find_all('td')  
            for td in tds_aba:
                if td.label is None:
                    continue
                label = snake(td.label.text)
                if ''.join(td.span.get('class')).find('lin') > -1:
                    temp_span_value = td.span.text.strip()
                    # Endereço - Número
                    separator = '-' if temp_span_value.find('-') > -1 else ','
                    span_value = separator.join([va.strip()
                                                for va in temp_span_value.split(separator)])
                else:
                    span_value = td.span.text.strip()
                data[titulo_aba][label] = span_value

            td_titulos_aba_interna = soup.find_all(
                'td', {'class': 'table-titulo-aba-interna'})
            for td_titulos_interno in td_titulos_aba_interna:
                titulo_interno = snake(td_titulos_interno.text)
                tds_aba_interna = td_titulos_interno.parent.parent.next_sibling.find_all(
                    'td')
                data[titulo_interno] = dict()

                if len(tds_aba_interna) == 0 or tds_aba_interna[0].span is None or tds_aba_interna[0].label is None:
                    continue
                else:
                    for td in tds_aba_interna:
                        label = snake(td.label.text)
                        data[titulo_interno][label] = td.span.text.strip()
        elif tipo == TipoInfo.cobranca:
            data[titulo_aba] = dict()
            cobranca = soup.find_all('table', {'class': 'box'})
            cobranca_data = {}
            temporary_labels = None
            temporary_spans = None
            for table in cobranca:
                rows = table.find_all('tr') 
                if len(rows) == 1:
                    tl = (rows[0].find_all('label'))
                    temporary_labels = tl if len(tl) > 0 else temporary_labels
                    ts = (rows[0].find_all('span'))
                    temporary_spans = ts if len(ts) > 0 else temporary_spans
                    continue
                for row in rows:
                    labels = row.find_all('label')
                    spans = row.find_all('span')
                    for label, span in zip(labels, spans):
                        property_name = label.text.strip()
                        value = span.text.strip()
                        cobranca_data[property_name] = value
            data[titulo_aba]=cobranca_data
            
            for label, span in zip(temporary_labels, temporary_spans):
                property_name = label.text.strip()
                value = span.text.strip()
                cobranca_data[property_name] = value

        elif tipo == TipoInfo.produtos:
            data[titulo_aba] = list()
            produtos = soup.find_all(
                'td', {'class': 'table_produtos'})
            for produto in produtos:
                produto_data = dict()
                for td in produto.table.find_all('td'):
                    label = snake(td.label.text)
                    produto_data[label] = td.label.text.strip() if tipo == TipoInfo.cobranca else td.span.text.strip()

                table_td = produto.find(
                    'table', {'class': 'toggable'}).find_all('table')
                table_td_filter = table_td[:min([i if ['table-titulo-aba-interna'] == x.td.get('class') else len(
                    table_td) for i, x in enumerate(table_td)])]
                for td_titulos_interno in table_td_filter:
                    findall_td = td_titulos_interno.find_all('td')
                    tds_aba_interna = findall_td[:min([i if 'table' == x.next.name else len(
                        findall_td) for i, x in enumerate(findall_td)])]
                    for td in tds_aba_interna:
                        if td.span is None or td.label is None:
                            continue
                        label = snake(td.label.text)
                        produto_data[label] = td.span.text.strip()

                td_titulos_aba_interna = produto.find(
                    'table', {'class': 'toggable'}).find_all(
                    'td', {'class': 'table-titulo-aba-interna'})
                for td_titulos_interno in td_titulos_aba_interna:
                    titulo_interno = snake(td_titulos_interno.text)
                    tds_aba_interna = td_titulos_interno.parent.parent.next_sibling.find_all(
                        'td')
                    produto_data[titulo_interno] = dict()

                    if len(tds_aba_interna) == 0 or tds_aba_interna[0].span is None or tds_aba_interna[0].label is None:
                        continue
                    else:
                        for td in tds_aba_interna:
                            label = snake(td.label.text)
                            produto_data[titulo_interno][label] = td.span.text.strip(
                            )
                data[titulo_aba].append(produto_data)
        return(data)

def get_data_from_qrcode(url):
    sefaz = SefazBa(url)
    data = sefaz.get_nota()
    return data