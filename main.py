from sefazba import get_data_from_qrcode

response = get_data_from_qrcode('http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx?p=29240813574594125720650010009512201767788540|2|1|1|BC15D6D0586F8208629110C8E4D99E18D7046CCF')

print(response)