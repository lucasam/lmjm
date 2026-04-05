import xml.etree.ElementTree as ET

tree = ET.parse("scripts/sample_nfe.xml")
root = tree.getroot()
ns = {"n": "http://www.portalfiscal.inf.br/nfe"}

ide = root.find(".//n:infNFe/n:ide", ns)
emit = root.find(".//n:infNFe/n:emit", ns)
dest = root.find(".//n:infNFe/n:dest", ns)
prod = root.find(".//n:infNFe/n:det/n:prod", ns)
transp = root.find(".//n:infNFe/n:transp", ns)

print("nNF:", ide.find("n:nNF", ns).text)
print("dhEmi:", ide.find("n:dhEmi", ns).text)
print("emit/xNome:", emit.find("n:xNome", ns).text)
print("dest/xNome:", dest.find("n:xNome", ns).text)
print("cProd:", prod.find("n:cProd", ns).text)
print("xProd:", prod.find("n:xProd", ns).text)
print("qCom:", prod.find("n:qCom", ns).text)
print("uCom:", prod.find("n:uCom", ns).text)
print("xPed:", prod.find("n:xPed", ns).text)
print("pesoL:", transp.find(".//n:vol/n:pesoL", ns).text)

rastro = prod.find("n:rastro", ns)
if rastro:
    print("nLote:", rastro.find("n:nLote", ns).text)
    print("dFab:", rastro.find("n:dFab", ns).text)
