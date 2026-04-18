#!/usr/bin/env python3
"""Generate per-site worker catalogs (HTML + PDF via weasyprint). Run on raspibig."""
import json, re, random
from collections import defaultdict
from pathlib import Path

CV_FILE = "/opt/ACTIVE/WORKFORCE/cv_extracted.json"
OUT_DIR = "/opt/ACTIVE/CATALOGS"

SECTOR_COLORS = {
    'Constructii': '#FF5722', 'Productie': '#FF9800', 'Alimentar': '#E91E63',
    'Logistica': '#2196F3', 'Healthcare': '#00BCD4', 'Hospitality': '#9C27B0',
    'Agricultura': '#4CAF50', 'Electricieni': '#FFD600', 'Mecanici': '#78909C', 'General': '#607D8B',
}

SITES = [
    {"domain": "factoryjobs.eu",        "name": "FactoryJobs.eu",        "email": "office@factoryjobs.eu",        "catalog_email": "catalog@factoryjobs.eu",        "sectors": ["Productie","Constructii","Logistica","General"]},
    {"domain": "buildjobs.eu",           "name": "BuildJobs.eu",           "email": "office@buildjobs.eu",           "catalog_email": "catalog@buildjobs.eu",           "sectors": ["Constructii"]},
    {"domain": "electricjobs.eu",        "name": "ElectricJobs.eu",        "email": "office@electricjobs.eu",        "catalog_email": "catalog@electricjobs.eu",        "sectors": ["Electricieni"]},
    {"domain": "careworkers.eu",         "name": "CareWorkers.eu",         "email": "office@careworkers.eu",         "catalog_email": "catalog@careworkers.eu",         "sectors": ["Healthcare"]},
    {"domain": "farmworkers.eu",         "name": "FarmWorkers.eu",         "email": "office@farmworkers.eu",         "catalog_email": "catalog@farmworkers.eu",         "sectors": ["Agricultura"]},
    {"domain": "horecaworkers.eu",       "name": "HorecaWorkers.eu",       "email": "office@horecaworkers.eu",       "catalog_email": "catalog@horecaworkers.eu",       "sectors": ["Hospitality","Alimentar"]},
    {"domain": "meatworkers.eu",         "name": "MeatWorkers.eu",         "email": "office@meatworkers.eu",         "catalog_email": "catalog@meatworkers.eu",         "sectors": ["Alimentar"]},
    {"domain": "mechanicjobs.eu",        "name": "MechanicJobs.eu",        "email": "office@mechanicjobs.eu",        "catalog_email": "catalog@mechanicjobs.eu",        "sectors": ["Mecanici"]},
    {"domain": "warehouseworkers.eu",    "name": "WarehouseWorkers.eu",    "email": "office@warehouseworkers.eu",    "catalog_email": "catalog@warehouseworkers.eu",    "sectors": ["Logistica","Productie"]},
    {"domain": "interjob.ro",            "name": "InterJob.ro",            "email": "office@interjob.ro",            "catalog_email": "catalog@interjob.ro",            "sectors": ["Constructii","Productie","Alimentar","Logistica","Healthcare","Hospitality","Agricultura","General"]},
    {"domain": "expatsinromania.org",    "name": "ExpatsInRomania.org",    "email": "office@expatsinromania.org",    "catalog_email": "catalog@expatsinromania.org",    "sectors": ["General","Healthcare"]},
    {"domain": "nepalezi.com",           "name": "Nepalezi.com",           "email": "office@nepalezi.com",           "catalog_email": "catalog@nepalezi.com",           "sectors": ["Healthcare","General"]},
    {"domain": "mivromania.info",        "name": "MivRomania.info",        "email": "office@mivromania.info",        "catalog_email": "catalog@mivromania.info",        "sectors": ["Constructii","Productie","Alimentar","Logistica","Healthcare","Hospitality","Agricultura","General"]},
    {"domain": "aluminumrecyclehub.com", "name": "AluminumRecycleHub.com", "email": "office@aluminumrecyclehub.com", "catalog_email": "catalog@aluminumrecyclehub.com", "sectors": ["Productie","General"]},
    {"domain": "bppltd.co.uk",           "name": "WarehouseWorkers.eu",    "email": "office@bppltd.co.uk",           "catalog_email": "catalog@bppltd.co.uk",           "sectors": ["Logistica","Productie","General"]},
]

FILLER_CVS = {
'Constructii': [
  ("Bogdan Marinescu", "Sudor MIG/MAG – 8 ani experienta\nSpecializat in structuri metalice si conducte industriale\nLucrat in Romania, Germania si Norvegia\nCertificat sudura EN ISO 9606-1\nDisponibil imediat, permis cat B"),
  ("Gheorghe Popescu", "Zidar constructor – 12 ani experienta\nLucrari civile si industriale, zidarie BCA si caramida\nFinisaje interioare si exterioare\nLucrat pe santiere in Italia si UK\nDisponibil pentru deplasare Europa"),
  ("Andrei Stanescu", "Instalator sanitar si termic – 10 ani\nInstalare centrale termice, tevi PP si cupru\nReparatii urgente si lucrari noi\nLucrat in Austria 3 ani\nCertificat calificare profesionala"),
  ("Cosmin Vladescu", "Fierar betonist / Cofrajist – 7 ani\nLucrari beton armat, fundatii, stalpi, placi\nExperienta proiecte rezidentiale si industriale\nFizic bun, echipa sau individual"),
  ("Marian Dumitru", "Placat faianta si gresie – 9 ani\nBai, bucatarii, pardoseli comerciale\nLucrari de inalta calitate, referinte disponibile\nLucrat in Belgia si Olanda\nDisponibil 2 saptamani"),
  ("Catalin Rusu", "Lacatus mecanic – structuri metalice – 11 ani\nConfectionare si montaj constructii metalice\nSudura MAG, MIG, WIG\nLucrat pe santiere offshore Norvegia\nCertificat sudor nivel 2"),
  ("Vasile Oprea", "Tencuitor / Zugrav – 14 ani\nTencuiala mecanizata si manuala\nVopsitorie lavabila, fatade\nProiecte rezidentiale si comerciale\nLucrat Italia, Spania, Germania"),
  ("Liviu Matei", "Rigipsar – 8 ani experienta\nPereti despartitori, tavane false\nIzolatii termice si fonice\nFamiliarizat cu sisteme Knauf si Rigips\nDisponibil imediat"),
  ("Petre Lazarescu", "Montator instalatii climatizare – 5 ani\nInstalare si service aer conditionat, ventilatie\nFrigorist atestat, lucrat in hoteluri si birouri\nPermis cat B, disponibil deplasare"),
  ("Stefan Cristea", "Constructor zidarie si finisaje – 13 ani\nZidarie, tencuiala, gresie, faianta, zugraveli\nOmul de mana din echipa, supervizat 5 muncitori\nReferinte Anglia si Irlanda"),
  ("Ion Dumitru", "Montator tamplarie PVC si aluminiu – 7 ani\nInstalare ferestre, usi, pereti cortina\nExperienta showroom si santier\nLucrat in Danemarca 2 ani"),
  ("Mihai Barbu", "Instalator gaz – 6 ani\nMontaj conducte gaz metan, centrala termica\nAutorizatie ISCIR, lucrat in Italia\nDisponibil imediat"),
  ("Radu Florescu", "Mecanic utilaje constructii – 9 ani\nExcavatoare, buldoexcavatoare, macara turn\nPermis operator ISCIR\nLucrat pe proiecte autostrada Romania"),
  ("Ovidiu Georgescu", "Izolator termic si hidrofug – 8 ani\nIzolatii acoperis, subsol, terase\nLucrat pe proiecte mari Germania si Olanda\nDisponibil echipa sau individual"),
  ("Laurentiu Hotea", "Dulgher – 11 ani\nCofraj lemn traditional si modern\nSarpante, mansarde, structuri lemn\nLucrat Franta si Belgia 4 ani"),
  ("Cristian Popa", "Betonist calificat – 7 ani\nTurnare beton, finisare mecanica si manuala\nLucrari fundatii, pardoseli industriale\nCurs calificare absolvit"),
  ("Florin Nedelcu", "Electrician instalatii – 6 ani\nInstalare tablouri electrice, cablare industriala\nAtestare ANRE gr. II\nExperienta fabrici si hale de productie\nPermis auto cat B"),
  ("Relu Tanase", "Electrician auto si industrial – 10 ani\nInstalatii electrice hale, depozite, birouri\nPanouri fotovoltaice, 2 ani experienta\nAtestat ANRE"),
  ("Niculae Stan", "Sudor TIG / inox – 6 ani\nIndustria alimentara si farmaceutica\nConducte inox, rezervoare, utilaje\nCertificat EN 287 TIG\nExperienta Germania si Elvetia"),
  ("Dragos Enache", "Montator retele electrice – 5 ani\nRetele electrice aeriene si subterane\nLucrat pentru distribuitori energie Romania\nAtestari tehnice valabile"),
],
'Electricieni': [
  ("Florin Nedelcu", "Electrician instalatii – 6 ani\nInstalare tablouri electrice, cablare industriala\nAtestare ANRE gr. II\nExperienta fabrici si hale de productie\nPermis auto cat B"),
  ("Relu Tanase", "Electrician auto si industrial – 10 ani\nInstalatii electrice hale, depozite, birouri\nPanouri fotovoltaice, 2 ani experienta\nAtestat ANRE"),
  ("Dragos Enache", "Montator retele electrice – 5 ani\nRetele electrice aeriene si subterane\nLucrat pentru distribuitori energie Romania\nAtestari tehnice valabile"),
  ("Oleg Vasile", "Electrician intretinere productie – 10 ani\nIntretinere echipamente electrice fabrica\nPLC Siemens, variatori de turatie\nLucrat Moldova si Romania"),
  ("Ion Grecu", "Electrician industrial – 8 ani\nCablare panouri electrice, automatizari\nSchite electrice AutoCAD\nLucrat Germania 3 ani, atestat ANRE"),
  ("Sorin Badea", "Electrician retele MT/JT – 7 ani\nLucrari retele electrice aeriene si subterane\nPermis ANRE tip B2\nLucrat la distribuitor energie Romania"),
  ("Adrian Moga", "Electrician auto – 6 ani\nDiagnosticare si reparatii sisteme electrice auto\nExperienta service autorizat Mercedes si BMW\nCurs diagnoza TEXA"),
  ("Mihai Vasile", "Electrician constructii – 9 ani\nInstalatii electrice rezidentiale si comerciale\nProiecte bloc si hale industriale\nLucrat Italia si Germania"),
  ("Constantin Banu", "Automatist / Electrician PLC – 7 ani\nProgramare Siemens S7, Allen Bradley\nStartere, invertoare de frecventa\nLucrat in 4 tari UE"),
  ("Petre Ionita", "Electrician fotovoltaic – 4 ani\nInstalare sisteme solare on-grid si off-grid\nCertificat instalator panouri fotovoltaice\nDisponibil deplasare nationala si europeana"),
  ("Bogdan Toma", "Electrician tablouri electrice – 5 ani\nAsamblare tablouri industriale\nCitire scheme electrice, cablare\nLucrat producator tablouri Germania"),
  ("Marian Voicu", "Electrician mentenanta – 11 ani\nIntretinere preventiva si corectiva\nIndustria alimentara si auto\nDispus ture de noapte, experienta fabrica"),
  ("Valentin Rus", "Electrician energetica – 8 ani\nStatii electrice, transformatoare\nMontaj si mentenanta echipamente HV\nAtestare ANRE gr. IIB"),
  ("Cristian Radu", "Electrician instalatii electrice joasa tensiune – 6 ani\nApartamente, birouri, cladiri comerciale\nAtestat ANRE, lucrat Belgia si Franta\nSeriozitate, referinte disponibile"),
  ("George Pavel", "Electrician frigorist – 5 ani\nInstalare si service climatizare industriala\nFrigorist atestat, ISCIR categoria C\nLucrat la hotel si supermarket"),
  ("Liviu Chiriac", "Electrician retele FV si baterii – 3 ani\nSisteme solare industriale, BESS\nMonitorizare remote, invertor trifazat\nCertificat TUV installer"),
  ("Stefan Maxim", "Electrician IT – cablare structurata – 7 ani\nRetele date Cat6/Cat6A, fibra optica\nSplicing fibra, certificare Fluke\nLucrat in data center Romania si Austria"),
  ("Nelu Popescu", "Electrician instalatii civile – 14 ani\nLucrari complete electrice bloc nou\nAvizari ANRE, receptii lucrari\nLucrat independent si firma"),
  ("Razvan Lupu", "Electrician naval – 6 ani\nInstalare si mentenanta echipamente nave\nLucrat santier naval Galati si Olanda\nCertificat STCW electrotehnic"),
  ("Andrei Buliga", "Electrician scada si automatizari – 5 ani\nSisteme SCADA, protocol Modbus/Profibus\nProgramare HMI, interfete operator\nLucrat fabrica chimie si energie"),
],
'Productie': [
  ("Rakib Hossain", "Operator CNC – 5 ani experienta\nStrunjire, frezare, centru de prelucrare\nFamiliarizat cu programe Fanuc si Siemens\nLucrat in fabrica auto Germania\nDisponibil imediat"),
  ("Suresh Patel", "Operator linie de asamblare – 7 ani\nIndustria auto, asamblare componente electrice\nCalitate verificata, zero rebuturi\nLucrat la furnizori Volkswagen si BMW"),
  ("Pavel Novak", "Operator ambalare si productie – 6 ani\nLinii automate de ambalare, control calitate\nExperienta fabrica alimente si cosmetice\nLucrat in Cehia si Polonia"),
  ("Dilip Gurung", "Muncitor fabrica electronica – 4 ani\nAsamblare placi electronice, lipit manual\nCamera curata, ESD training\nLucrat in fabrica Samsung Slovacia"),
  ("Vikram Singh", "Operator masini industriale – 8 ani\nPresare, stantare, sudura robotizata\nExperienta injectie mase plastice\nLucrat in 3 tari din Europa"),
  ("Tomas Blazek", "Operator productie auto – 5 ani\nMontaj componente interior auto\nNorma 100%, lucrat la Skoda Mlada Boleslav\nDisponibil relocare"),
  ("Emeka Chukwu", "Stivuitorist si operator depozit – 7 ani\nPermis stivuitor valabil, europaleti\nInventar WMS, productie si logistica\nLucrat in Olanda 3 ani"),
  ("Bogdan Tudose", "Sudor in productie – 9 ani\nSudura MAG robotizata si semi-auto\nProductie serie, norme indeplinite\nCertificari valabile"),
  ("Sonu Kumar", "Operator masina de injectie plastic – 5 ani\nReglaj si supraveghere utilaj\nControl parametri, calitate produs\nLucrat in Austria 2 ani"),
  ("Pavel Olaru", "Mecanic intretinere utilaje – 11 ani\nIntretinere preventiva si corectiva\nLinie productie alimente si bauturi\nAutorizatii ISCIR"),
  ("Jozef Kovac", "Operator productie chimie – 6 ani\nProductie vopsele si adezivi industriali\nCertificat manipulare substante periculoase\nLucrat in Germania si Cehia"),
  ("Iosif Moldovan", "Inginer tehnolog productie – 8 ani\nOptimizare procese, reducere rebuturi\nExperienta SME si corporatie\nAbsolvent politehnica"),
  ("Oleg Vasile", "Electrician intretinere productie – 10 ani\nIntretinere echipamente electrice fabrica\nPLC Siemens, variatori de turatie\nLucrat Moldova si Romania"),
  ("Felix Andrei", "Operator hala productie – 4 ani\nProductie mobila, taiere CNC lemn\nExperienta fabrica Ikea furnizor\nDisponibil imediat"),
  ("Karim Benzara", "Operator strung CNC – 4 ani\nPiese de precizie pentru industria aeronautica\nTolerante stranse, citire desen tehnic\nLucrat in Franta, fabrica Safran"),
  ("Nguyen Van Duc", "Muncitor linie productie – 6 ani\nAsamblare, lipire, testare electrica\nRitm rapid, prezenta 100%\nLucrat in Ungaria si Romania"),
  ("Md Faruk Islam", "Operator control calitate – 6 ani\nInspectie vizuala si cu instrumente\nRaportare neconformitati, ISO 9001\nLucrat in fabrica textila si auto"),
  ("Abebe Tadesse", "Muncitor productie – 5 ani\nLinii de productie diverse, adaptabil\nFizic bun, disponibil ture de noapte\nLucrat in Romania si Ungaria"),
  ("Rajkumar Sharma", "Operator masina de cusut industriala – 7 ani\nIndustria textila, norme 120%\nLucrat in fabrica din Romania si Bulgaria"),
  ("Yassine Bouhali", "Operator logistica productie – 4 ani\nAlimentare linie, manipulare materiale\nExperienta zona ambalare si expeditie\nPermis stivuitor valabil"),
],
'Alimentar': [
  ("Sanjay Maharjan", "Macelar / Transator carne – 6 ani\nTransare porc, vita, pasare\nLinie industriala 400 capete/zi\nCertificat igiena alimentara\nLucrat in abator Danemarca"),
  ("Ismail Kone", "Muncitor abator – 5 ani\nEviscerare, portionare, ambalare\nIgiena HACCP, echipament frig\nLucrat in Polonia si Germania"),
  ("Rajesh Tamang", "Lucrator productie alimentara – 7 ani\nAmbalare, etichetare, control calitate\nExperienta fabrica mezeluri si conserve\nLucrat Olanda 3 ani"),
  ("Chidi Obi", "Brutar – 8 ani experienta\nPaine artizanala si industriala\nPatiserie, cozonaci, produse de post\nLucrat in brutarie Romania si Italia"),
  ("Habib Mansouri", "Macelar specializat – 9 ani\nDesosare, portionare, preparare specialitati\nCarne halal, certificare disponibila\nLucrat Franta si Belgia"),
  ("Biswajit Das", "Operator fabrica produse lactate – 5 ani\nPasteurizare, ambalare, control pH\nNorme HACCP, ISO 22000\nLucrat in fabrica Danone Romania"),
  ("Ahmed Khalid", "Pescar / Procesare peste – 6 ani\nFiletat, curatat, ambalare surgelate\nLucrat in Norvegia si Islanda\nExperienta fabrica procesare ton"),
  ("Florin Anghel", "Muncitor abator pasari – 4 ani\nEviscerare, portionare, ambalare pui\nLucrat la Transavia si Agricola\nNorme HACCP respectate"),
  ("Nour Eddine", "Cofetar – 8 ani\nTorturi personalizate si cofetarie clasica\nLucrat in hotel 5 stele si cofetarie artizanala\nDisponibil relocare Europa"),
  ("Vasile Constantin", "Mazelar specializat – 12 ani\nPreparare mezeluri traditionale romanesti\nExperienta proprie afacere + fabrica\nDisponibil imediat"),
  ("Ionut Gheorghe", "Muncitor fabrica zahar si dulciuri – 5 ani\nLinie productie bomboane si ciocolata\nControl calitate, ambalare, depozitare"),
  ("Dumitru Radulescu", "Operator fabrica bauturi – 6 ani\nProductie bere si sucuri, CIP cleaning\nCertificat operator utilaje industriale"),
  ("Petru Munteanu", "Lucrator fabrica peste si fructe de mare – 5 ani\nLucrat Norvegia, procesare somon\nRezistent la frig, ritm rapid"),
  ("Serban Florescu", "Bucatar colectivitati – 9 ani\nMeniuri cantina 500+ persoane/zi\nGestionare stocuri si aprovizionare"),
  ("Razvan Dinu", "Specialist control calitate alimentar – 7 ani\nAudit intern HACCP, BRC, IFS\nExperienta in mai multe fabrici"),
  ("Marian Ionescu", "Operator linie mezeluri – 8 ani\nUmplere automata, legare, afumare\nExperienta Smithfield Romania"),
  ("Relu Barbu", "Muncitor universal abator si transare – 5 ani\nFlexibil pe sectii, ritm rapid\nDisponibil ture, inclusiv noapte"),
  ("Mircea Vlad", "Bucatar linie productie – 7 ani\nGatit in productie de masa, 1000+ portii/zi\nMeniuri corporatii si spitale\nLucrat in catering industrial"),
  ("Traian Pavel", "Muncitor fabrica produse de panificatie – 6 ani\nDospit, copt, racire, ambalare\nLucrat Lidl Romania furnizor"),
  ("Constantin Badescu", "Macelar si preparator carne – 10 ani\nProprietate proprie, vanzare si productie\nCunoastere profunda materie prima"),
],
'Logistica': [
  ("Mihai Draghici", "Sofer camion cat C+E – 11 ani\nTransport international TIR Europa\nTahograf digital, CMR, ADR de baza\nLucrat pentru firma germana 4 ani"),
  ("Ion Petrescu", "Curier si sofer distributie – 7 ani\nLivrari last-mile, gestionare ruta\nExperienta DPD, DHL, Fan Courier\nPermis B, cunoastere GPS"),
  ("Adrian Marin", "Stivuitorist certificat – 6 ani\nDepozit logistic 20.000 mp\nWMS SAP, inventar, receptie marfa\nLucrat in depozit Kaufland"),
  ("Gheorghe Farcas", "Dispatcher logistica – 8 ani\nPlanificare rute, coordonare soferi\nNegociere transportatori, reducere costuri 15%\nExperienta firma import-export"),
  ("Bogdan Costache", "Operator depozit – 5 ani\nReceptie, expeditie, picking, packing\nForklift si transpalet electric\nLucrat in depozit Amazon Romania"),
  ("Florin Voicu", "Sofer transport persoane cat D – 9 ani\nAutocar si microbuz, rute internationale\nATR valabil, fara accidente\nLucrat Germania si Austria"),
  ("Cosmin Alexa", "Responsabil depozit – 7 ani\nGestionare stoc 5000 SKU-uri\nEchipa 8 persoane, KPI livrare 98%\nLucrat la depozit Dacia Renault"),
  ("Marian Tudor", "Sofer livrari frigorifice – 6 ani\nTransport produse lactate si carne\nPermis C, atestat transport marfuri\nLucrat Frigo-Trans Romania"),
  ("Stefan Bogdan", "Agent vama si logistica – 8 ani\nDeclaratii vamale import/export\nIncoterms, Customs Tariff\nExperienta broker vamal"),
  ("Nicu Hristea", "Sofer distributie locala – 10 ani\nRuta zilnica, 60-80 livrari/zi\nRelatie buna clienti, incasare numerar\nZero reclamatii in 3 ani"),
  ("Valentin Enache", "Operator sort & pick – 5 ani\nCentru logistic e-commerce\nNorma 200 colete/ora, scanner RF\nLucrat Emag si PC Garage"),
  ("Laurentiu Miron", "Sofer cisterna – 7 ani\nTransport produse petroliere si chimice\nADR cl. 3 si 8, fara incidente"),
  ("Daniel Oancea", "Muncitor manipulare marfa – 5 ani\nIncarcare descarcare TIR manual si mecanic\nFizic excelent, disponibil ture"),
  ("Radu Niculescu", "Sofer macara si utilaje grele – 8 ani\nCamion cu macara, platforma telescopica\nPermis ISCIR valabil"),
  ("Relu Simion", "Lucrator logistica si ambalare – 4 ani\nSortare, ambalare, etichetare comenzi\nLucrat in centru logistic Olanda\nDisponibil imediat"),
  ("Vasile Apostu", "Planificator aprovizionare – 9 ani\nMRP, SAP MM, gestiune stocuri\nReductie out-of-stock 30%"),
  ("Marius Fulga", "Sofer cat B+E – 7 ani\nTransport utilaje si material de constructii\nPermis remorcat, disponibil Europa"),
  ("Ion Lazar", "Lucrator depozit frigorific – 4 ani\nTemperaturi -18C, rezistent\nLucrat depozit Metro si Selgros"),
  ("Petru Gramada", "Agent logistica import Asia – 6 ani\nCoordinare containere FCL/LCL\nRelatie furnizori China si Vietnam"),
  ("Catalin Dima", "Coordonator transport intern – 6 ani\nOptimizare rute intra-city\nFlota 12 vehicule, costuri -20%"),
],
'Healthcare': [
  ("Mary Grace Santos", "Asistenta medicala – 7 ani experienta\nSectie chirurgie si ATI\nDiploma asistenta medicala generala\nLucrat in spital Germania 3 ani\nEngleza fluent, germana conversational"),
  ("Priya Nair", "Ingrijitoare batrani – 5 ani\nIngrijire la domiciliu, dementa si Alzheimer\nCurs calificare ingrijitor\nLucrat in Anglia si Irlanda\nRabdatoare, empatica"),
  ("Binita Tamang", "Asistenta medicala – 6 ani\nMedicina interna si geriatrie\nAdministrare medicamente, monitorizare\nDiploma recunoscuta UE\nDisponibila relocare"),
  ("Sunita Rai", "Ingrijitoare varstnici la domiciliu – 8 ani\nIngrijire 24/24, gatit, igiena\nLucrat in Austria si Germania\nCertificat Betreuungskraft 87b"),
  ("Rose Mendoza", "Asistenta medicala inregistrata – 9 ani\nICU, chirurgie, medicina generala\nDiploma recunoscuta UK si UE\nLicenta PRC valabila"),
  ("Kabita Shrestha", "Ingrijitor persoane cu dizabilitati – 6 ani\nFizioterapie de baza, logopedie suport\nLucrat in centru rezidential Olanda\nCurs NVQ Level 3"),
  ("Jennifer Ocampo", "Ajutor asistent medical – 5 ani\nSpital si centru de recuperare\nMasurare semne vitale, plagi simple\nDisponibila imediat"),
  ("Deepa Gurung", "Infirmiera – 7 ani\nSpital si clinica privata\nIngrijire postoperatorie\nCurs calificare infirmiera\nLucrat Romania si Cipru"),
  ("Ngozi Eze", "Asistent medical nutritionist – 4 ani\nPlanuri alimentare pacienti cronici\nDiabet, boli cardiovasculare\nAbsolventa facultate nutritie"),
  ("Lalita Karki", "Baby-sitter si ingrijitoare copii cu nevoi speciale – 6 ani\nAutism, ADHD, intarziere motorie\nLucrat in Belgia si Norvegia"),
  ("Anita Thapa", "Asistenta sociala – 8 ani\nEvaluare cazuri, anchete sociale\nLucrat in servicii protectia copilului"),
  ("Hamidou Diallo", "Kinetoterapeut – 6 ani\nReabilitare post-accident si ortopedie\nTehnici masaj terapeutic\nLucrat in Franta si Spania"),
  ("Aissatou Barry", "Auxiliar de viata – 7 ani\nIngrijire persoane dependente la domiciliu\nGatit dieta, igiena corporala\nCertificat DEAVS Franta"),
  ("Amara Coulibaly", "Infirmiera licentiata – 5 ani\nSectie pediatrie si neonatologie\nVaccinari, screening neonatal\nDiploma recunoscuta Europa"),
  ("Chinyere Okonkwo", "Asistent medical psihiatrie – 6 ani\nUrgente psihiatrice, terapie suport\nLucrat NHS Anglia\nTraining de-escaladare violenta"),
  ("Fatima El Idrissi", "Infirmiera policlinica – 8 ani\nConsultatii, pregatire pacient\nExperienta cabinet stomatologic\nLimbi: araba, franceza, engleza"),
  ("Oluwakemi Adebayo", "Ingrijitor varstnici centru rezidential – 5 ani\nTururi zi si noapte, documentatie\nLucrat in Dublin si Amsterdam"),
  ("Mirela Popescu", "Asistenta medicala geriatrie – 9 ani\nSectie cronici si paleatie\nAbsolventa AMG Bucuresti\nDisponibila imediat"),
  ("Carmen Dobre", "Infirmiera sectie ortopedie – 7 ani\nIngrijire post-operatorie, mobilizare\nLucrat in clinica privata Germania"),
  ("Blessing Osei", "Technician ingrijire pacient – 5 ani\nRecoltare analize, EKG, tensiune\nLucrat in clinica privata Lagos si Dublin"),
],
'Hospitality': [
  ("Rafael Millan", "Ospatar / Chelner – 8 ani experienta\nRestaurant fine dining si bistro\nWine service, upselling\nLucrat in Olanda si Anglia\nEngleza si spaniola fluent"),
  ("Hamza Rachidi", "Barman – 6 ani\nCocktailuri clasice si creative\nBar hotel 5 stele si beach bar\nLucrat Maroc, Franta, Belgia\nDisponibil imediat"),
  ("Pratik Shrestha", "Receptioner hotel – 5 ani\nCheck-in/out, rezervari, reclamatii\nSistem Fidelio si Opera PMS\nLucrat in hotel 4 stele Budapest"),
  ("Mehdi Alaoui", "Bucatar sef de rang – 7 ani\nBucatarie franceza si internationala\nExperienta Michelin Bib Gourmand\nLucrat Dubai si Paris"),
  ("Rohan Basnet", "Ajutor bucatar – 4 ani\nPregatire mise en place, garnituri\nBucatarie calda si rece\nLucrat in restaurant romanesc si italian"),
  ("Fatou Dieng", "Camerista hotel – 6 ani\nStandard 5 stele, 18 camere/tura\nPrezentare impecabila\nLucrat in hotel Marriott si Hilton"),
  ("Bijay Karki", "Chelner sef de rang – 9 ani\nRestaurant hotel international\nSupervizat echipa 4 persoane\nLucrat Singapore si Londra"),
  ("Ines Bouchard", "Receptionist si reservations agent – 5 ani\nBooking.com, Expedia, channel manager\nLimbi: engleza, franceza, romana\nLucrat in Franta si Romania"),
  ("Diego Fernandez", "Bucatar – 7 ani\nBucatarie italiana si fusion\nPasta proaspata, pizza napoletana\nLucrat Milano si Amsterdam"),
  ("Amina Diallo", "Housekeeping supervisor – 8 ani\nCoordona echipa 10 cameriste\nStandard LQA, audit curatenie\nLucrat Maroc si Franta"),
  ("Petrisor Vlad", "Bucatar linie calda – 6 ani\nCantina industriala 800 portii/zi\nMeniuri saptamanale, bugete\nLucrat in Austria"),
  ("Mihai Lacatus", "Pizzar – 9 ani\nPizza napoletana si pizza al taglio\nCuptor lemne si electric\nLucrat in Italia 4 ani"),
  ("Elena Marin", "Barista si casier – 5 ani\nCafenea specialty, latte art\nPOS si gestiune casa de marcat\nLucrat in Anglia"),
  ("Alina Popa", "Event coordinator hotel – 7 ani\nOrganizare nunti, conferinte\nLogistica 500+ persoane\nLucrat hotel 5 stele Bucuresti"),
  ("Gabriel Tudor", "Sef bucatar restaurant – 11 ani\nMeniu sezonier, cost food 28%\nEchipa 6 oameni, fara fluctuatie\nLucrat Germania si Elvetia"),
  ("Sorin Badea", "Stewarding si spalator vase – 4 ani\nCuratenie bucatarie profesionala\nGestionare chimica curatenie HACCP\nDisponibil ture de noapte"),
  ("Andreea Constantin", "Animatoare hotel – 5 ani\nActivitati copii si adulti\nLimbi: romana, engleza, italiana\nLucrat in Grecia si Turcia"),
  ("Victor Neagu", "Night auditor – 6 ani\nRapoarte noapte, balanta receptie\nSiguranta hotel, prim ajutor\nDisponibil ture noapte"),
  ("Iulia Stoica", "Sommelier – 7 ani\nWine pairing, degustari corporate\nCertificat WSET Level 3\nLucrat in restaurante premium"),
  ("Oluwaseun Adeyemi", "Barman si ospatar – 5 ani\nBar si sala restaurant simultan\nEvents si conferinte\nLucrat in Dublin si Londra"),
],
'Agricultura': [
  ("Rajan Thapa", "Lucrator agricol – 6 ani\nRecoltare legume si fructe in sera si camp\nTractor si utilaje agricole\nLucrat in Olanda si Belgia\nDisponibil imediat"),
  ("Ibou Diallo", "Culegator fructe sezonier – 5 ani\nMere, pere, capsuni, struguri\nNorma 400-600 kg/zi\nLucrat in Franta si Spania"),
  ("Dipak Rai", "Lucrator sera – 7 ani\nIngrijire rosii, castraveti, ardei\nSisteme irigatie, tratamente\nLucrat in Olanda 4 ani"),
  ("Youssef Benali", "Lucrator ferma animale – 5 ani\nVaci de lapte, porci, pasari\nMulgere mecanica, furajare\nLucrat in Danemarca"),
  ("Arjun Shrestha", "Lucrator recoltare – 4 ani\nRecoltare mecanica si manuala\nAsparagus, ceapa, cartofi\nLucrat Germania si Austria"),
  ("Tunde Okafor", "Sofer tractor si masini agricole – 8 ani\nArat, semanat, fertilizat, recoltat\nPermis tractor, cunoastere GPS agricol\nLucrat in UK"),
  ("Abdelaziz Hamid", "Peisagist si ingrijitor gradini – 6 ani\nIntretinere parcuri si gradini private\nTaiere, plantat, irigatii\nLucrat in Olanda si Belgia"),
  ("Kwame Asante", "Lucrator ferma horticola – 5 ani\nPlantat rasaduri, ingrijire, recoltare\nExperienta sera 5 ha\nRitm rapid, lucru in echipa"),
  ("Mircea Ionescu", "Mecanic utilaje agricole – 9 ani\nIntretinere combine, tractoare\nReglaj utilaje recoltare\nLucrat la ferma 2000 ha Romania"),
  ("Ion Florea", "Fermier legumicultor – 15 ani\nProductie rosii, ardei, vinete, morcovi\nIrigatie prin picurare, solarii\nVanzare piete si supermarketuri"),
  ("Vasile Miron", "Sofer camion agricultura – 7 ani\nTransport cereale si legume vrac\nPermis C+E, fara amenzi\nLucrat sezonier Germania"),
  ("Gheorghe Lungu", "Lucrator vie si vinificatie – 10 ani\nIngrijire vita de vie, culesul viei\nProductie vin artizanal\nLucrat in Franta si Italia"),
  ("Stefan Anghel", "Crescator animale – 12 ani\nOvine si bovine, 500 capete\nVeterinara de baza, fatari\nExperienta proprie si angajat"),
  ("Dan Cojocaru", "Lucrator apicultura – 8 ani\nIngrijire stupi, extractie miere\nCertificat apicultor\nLucrat in Romania si Austria"),
  ("Nelu Preda", "Legumicultor protejat – 6 ani\nSolarii tomate si ardei, 2 ha\nIrigatie automatizata, biostimulatori\nVanzare export Franta"),
  ("Marin Grigore", "Operator instalatii irigatie – 7 ani\nIrigatie prin picurare si aspersoare\nReparatii si reglaj\nLucrat la companie agricola 5000 ha"),
  ("Florea Dobre", "Tractorist calificat – 14 ani\nLucrari mecanice la sol, semanaturi\nPermis tractor si auto cat B\nLucrat UE via agentie"),
  ("Relu Vasile", "Lucrator recoltare fructe padure – 4 ani\nAfine, zmeura, ciuperci\nNorma 60-80 kg/zi afine\nLucrat Suedia si Finlanda"),
  ("Petre Niculae", "Operator masina de recoltat legume – 6 ani\nHarvester ceapa si cartofi\nIntretinere de baza utilaj\nLucrat Olanda si Belgia"),
  ("Costinel Barbu", "Lucrator camp si sera – 4 ani\nPlasticultira si agricultura de camp\nNorma buna, nu fumeaza\nDisponibil sezon complet"),
],
'Mecanici': [
  ("Ionut Grecu", "Mecanic auto – 9 ani experienta\nReparatii motoare, cutii viteze, frane\nDiagnoza computerizata Bosch KTS\nLucrat service autorizat Renault Romania\nPermis cat B, disponibil imediat"),
  ("Bogdan Marin", "Mecanic utilaje grele – 7 ani\nExcavatoare, buldoexcavatoare, macarale\nReparatii hidraulice si electrice\nLucrat pe santiere Germania si Austria\nPermis operator ISCIR valabil"),
  ("Stefan Lupu", "Lacatus mecanic – 10 ani\nPrelucrare metale, strunjire, frezare manuala\nLucrari CNC si manual\nLucrat fabrica utilaje Romania\nCertificat calificare profesionala"),
  ("Cosmin Enache", "Mecanic de intretinere industriala – 8 ani\nReparatii linii productie, pompe, compresoare\nPneuri industriale, rulmenti, garnituri\nLucrat in fabrica auto Dacia Pitesti"),
  ("Marian Stoica", "Mecanic agricol – 12 ani\nReparatii tractoare John Deere, Case\nSisteme hidraulice, motoare diesel\nLucrat la ferma 2000 ha si service agricol"),
  ("Adrian Vlad", "Tinichigiu auto – 6 ani\nReparatii caroserii, sudura tabla\nIndreptat si chituire, grunduire\nLucrat atelier caroserie Franta 2 ani"),
  ("Radu Apostu", "Mecanic naval – 8 ani\nMotoare marine diesel si benzina\nSisteme propulsie si bordul electric\nLucrat pe nave Marea Neagra si Rin"),
  ("George Nistor", "Mecanic pneumatica si hidraulica – 7 ani\nCilindri hidraulici, valve, pompe\nDiagnoza si reparatii sistem hidraulic\nLucrat in fabrica plastice si auto"),
  ("Valentin Nica", "Mecanic masini de constructii – 9 ani\nBeton pumpat, greder, compactor\nService si reparatii santier\nLucrat proiecte autostrada A1 si A3"),
  ("Laurentiu Danila", "Mecanic refrigerare si climatizare – 6 ani\nReparatii instalatii frig industrial\nGaze frigorifice R404A, R410A\nAtestat frigorist, lucrat supermarketuri"),
  ("Dan Balan", "Mecanic auto camion si TIR – 11 ani\nMotoare Volvo, Scania, DAF\nTahograf digital, frene Euro\nLucrat firma transport internationala"),
  ("Mihai Oproiu", "Mecanic motociclete si ATV – 5 ani\nReparatii complete, diagnoza, tuning\nExperienta proprie atelier + dealer"),
  ("Felix Petcu", "Mecanic masini CNC – 6 ani\nIntretinere si reglaj centre prelucrare\nSchimb scule, calibrare, mentenanta\nLucrat producator piese auto Cluj"),
  ("Sorin Mihalcea", "Vulcanizator si mecanic anvelope – 7 ani\nAnvelope industriale si auto\nPneuri masini grele, stivuitoare\nLucrat firma logistica"),
  ("Nicu Ionescu", "Mecanic electro-hidraulic – 8 ani\nUtilaje de ridicat, platforme\nCertificat ISCIR operator\nLucrat pe proiecte constructii civile"),
  ("Tiberiu Dima", "Mecanic motorsport – 4 ani\nPregatire vehicule competitie\nMotoare performante, suspensii sport\nExperienta echipa rally Romania"),
  ("Petre Manole", "Mecanic feroviar – 14 ani\nLocomotiva diesel si electric\nIntretinere material rulant CFR\nCertificat mecanic locomotiva"),
  ("Relu Moraru", "Mecanic pompe si compresoare – 9 ani\nIntretinere statii pompare apa\nCompresoare cu piston si surub\nLucrat companie apa si canal"),
  ("Ciprian Toader", "Mecanic auto electric si hibrid – 5 ani\nDiagnoza sisteme electrice auto\nBaterii HV, invertoare\nCurs specializare vehicule electrice"),
  ("Octavian Preda", "Mecanic general – adaptabil – 6 ani\nAuto, utilaje, instalatii\nPermis B, disponibil deplasare\nReferinte multiple, serios"),
],
'General': [
  ("Mourad Ait Ali", "Muncitor necalificat – disponibil imediat\nFlexibil pe orice sector\nFizic bun, 28 ani, permis B\nLucrat 2 ani in Franta\nSeriozitate si punctualitate"),
  ("Rajkumar Sharma", "Muncitor general – fabrica sau depozit\nExperienta diverse linii productie\nAdaptabil rapid, norma respectata\nLucrat Ungaria si Romania"),
  ("Aboubacar Balde", "Lucrator general polivalent\nManipulare marfa, curatenie industriala\nSectii productie, ambalare, depozit\nLucrat 3 ani in Franta"),
  ("Md Shahinur Islam", "Muncitor general – constructii sau fabrica\nFizic excelent, disciplinat\nLucrat in Romania si Ungaria\nDisponibil ture, inclusiv noapte"),
  ("Emmanuel Nwosu", "Muncitor polivalent – orice sector\nExperienta hala productie si depozit\nViza UE valabila, permis conducere\nDisponibil oricand"),
  ("Bikash Limbu", "General laborer – hard worker\nFactory / warehouse / construction\nLucrat Cehia si Slovacia\nFara pretentii, serios"),
  ("Santosh Adhikari", "Muncitor depozit si manipulare\nStivuitor manual si electric, scanner\nInventar, receptie, expeditie\nLucrat in centru logistic"),
  ("Tariq Mahmood", "General worker – disponibil imediat\nExperienta diverse fabrici si santiere\nPermis conducere cat B\nLucrat Dubai si Romania"),
  ("Adrian Pana", "Lucrator universal – adaptabil\nAm lucrat constructii, fabrica, agricultura\nRoman, 32 ani, permis B\nDisponibil deplasare Europa"),
  ("Mihai Ciobanu", "Necalificat dar serios si muncitor\nTinar, 24 ani, fara experienta externa\nMotivat sa plec in Europa\nRoman, permis in curs"),
  ("Stelian Bucur", "Muncitor sezonier – disponibil\nAgricoltura si constructii sezon\nLucrat Germania si Austria\nRoman, vorbesc engleza de baza"),
  ("George Toma", "Muncitor fabrica sau depozit\nRoman, 35 ani, familie stabila\nFoste experiente diverse\nCaut contract pe termen lung"),
  ("Dorel Frunza", "Muncitor polivalent Romania\nConstructii, fabrica, transport intern\nPermis B, disponibil Europa\nReferinte de la fostii angajatori"),
  ("Alin Miu", "Lucrator general – sectii diverse\nFizic bun, fara probleme medicale\nDoresc contract de munca legal\nDisponibil 2 saptamani"),
  ("Octavian Vlad", "Muncitor necalificat cu experienta\nAm lucrat in Austria 2 ani legal\nContract de munca cu firma romana\nCaut relocare stabila"),
  ("Ionut Draghici", "Lucrator polivalent – tineret\n22 ani, recent terminat scoala\nMotivat, invatare rapida\nDisponibil orice tara UE"),
  ("Liviu Sandu", "Muncitor fabrica – experienta 5 ani\nLinii productie diverse Romania\nDoresc experienta Europa\nPermis B, fara cazier"),
  ("Claudiu Horia", "Muncitor general – fizic bun\nConstructii si depozite, 4 ani exp\nRoman, 29 ani, serios\nDisponibil imediat"),
  ("Nelu Alexe", "Lucrator general – orice sector\nAdaptabil, invatare rapida\nLucrat in Belgia 1 an, santier\nRoman, permis B"),
  ("Dan Ionescu", "Muncitor necalificat – disponibil\nTanar, 26 ani, fara obligatii familiale\nDisponibil orice tara si orice tura\nMotivat financiar"),
],
}

CATEGORIES_KW = {
    'Constructii': ['weld','sudor','construction','builder','mason','carpenter','plumb','pipe',
        'scaffold','concrete','beton','steel','iron','painter','zugrav','facade','excavat',
        'install','montaj','roofer','dulgher','tencuitor','zidar','lacatus'],
    'Electricieni': ['electric','electrician','electr','voltaj','tensiune','tablou electric',
        'ANRE','cablare','retea electrica','fotovoltaic','solar','PLC','automatiz'],
    'Productie': ['factory','machine','operator','cnc','assembl','packaging','forklift',
        'quality control','production','electronic','automotive','wiring','ambalare','productie'],
    'Alimentar': ['butcher','meat','slaughter','baker','cook','bucatar','food','restaurant',
        'kitchen','pizz','chef','catering','abator','macelar'],
    'Logistica': ['driver','truck','transport','courier','logistics','cargo','loading',
        'delivery','shipping','sofer','depozit','stivuitorist'],
    'Healthcare': ['nurse','medical','infirm','hospital','care worker','pharma','health',
        'clinic','asistenta','ingrijitor','ingrijitoare'],
    'Hospitality': ['hotel','waiter','bartender','barman','housekeep','camerist',
        'receptionist','barista','cleaning','ospatar','chelner'],
    'Agricultura': ['farm','agri','harvest','picker','greenhouse','livestock','animal',
        'tractor','crop','garden','agricol','legumicultor'],
    'Mecanici': ['mecanic','mechanic','motor','engine','hydraulic','hidraulic','vulcaniz',
        'tinichig','lacatus mecanic','utilaje','repair','reparatii','diagnoza','service auto'],
}

CONTACT_RE = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\+?\d[\d\s\-().]{8,15}\d"),
    re.compile(r"https?://\S+"),
]

BAD_NAMES = {
    'resume','cv','my','professionnel','set','dos','kc','club','sicre','english',
    'painter','agricolo','agricola','the','and','for','with','dear','sir','madam',
    'hello','cover','letter','doc','page','curriculum','europass','official','full',
    'soft','corporate','offer','okegbenro','atolagbe','gurung','mandal','chibuye',
    'bhuiyan','thapa','choucair','darchashvili','villadsen','bargayou','kolawole',
    'ouldbara','antreprenor','nekesa','krishnan','santos','lena','report','builder',
    'europe','romania',
}

def get_name(filename):
    f = re.sub(r'^buildjobs\.eu_\d+_\d+_', '', filename.replace('.pdf',''))
    f = re.sub(r'^\d+_\d+_', '', f).replace('_',' ').replace('-',' ').strip()
    f = re.sub(r'\s*\(\d+\)\s*$', '', f)
    f = re.sub(r'\s+\d+\s*$', '', f).strip()
    words = f.split()
    if not words: return None
    first = words[0].capitalize()
    if len(first) < 3 or not first.isalpha(): return None
    if first.lower() in BAD_NAMES:
        if len(words) >= 2:
            s = words[1].capitalize()
            if len(s) >= 3 and s.isalpha() and s.lower() not in BAD_NAMES:
                return s
        return None
    return first

def mask_phone(text):
    return re.sub(r'(\+?[\d\s\-().]{7,})(\d{3})\b', lambda m: m.group(1)+'xxx', text)

def mask_passport(text):
    text = re.sub(r'\b[A-Z]{1,2}\d{6,9}\b', '[PASSPORT]', text)
    text = re.sub(r'\bpassport\s*[:#]?\s*[\w\d]+', 'passport: [REDACTED]', text, flags=re.IGNORECASE)
    return text

def display_name(full_name):
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0] + ' ' + parts[-1][0] + '.'
    return full_name

def load_real_cvs():
    with open(CV_FILE, encoding='utf-8') as f:
        raw = json.load(f)
    real = defaultdict(list)
    seen = set()
    JUNK = {'unknown','sgaz','petroventures','club_antreprenor','cv_english',
            'cv_agricolo_italiano','cv_agricola_espanol','cv__professionnel',
            'cv_professionnel','resume_lena','resume_(vkp)','1'}
    for cv in raw:
        fname = cv.get('file','')
        fkey = re.sub(r'_?\d+\.pdf$','', fname.lower().replace(' ','_'))
        if any(j in fkey for j in JUNK) or fname in seen:
            continue
        seen.add(fname)
        first = get_name(fname)
        if not first or first.lower() in BAD_NAMES:
            continue
        if not re.search(r'\b'+re.escape(first)+r'\b', cv['text'], re.IGNORECASE):
            continue
        text = cv['text']
        for p in CONTACT_RE:
            text = p.sub('[...]', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip())>2]
        body = '\n'.join(lines[:40])
        if len(body) < 50:
            continue
        blob = body.lower()
        # Specific sectors first (before generic ones)
        if any(kw in blob for kw in CATEGORIES_KW['Mecanici']):
            real['Mecanici'].append({'name': first, 'text': body})
            continue
        if any(kw in blob for kw in CATEGORIES_KW['Electricieni']):
            real['Electricieni'].append({'name': first, 'text': body})
            continue
        placed = False
        for cat, kws in CATEGORIES_KW.items():
            if cat == 'Electricieni':
                continue
            if any(kw in blob for kw in kws):
                real[cat].append({'name': first, 'text': body})
                placed = True
                break
        if not placed:
            real['General'].append({'name': first, 'text': body})
    return real

def build_workers(sectors, real_cvs):
    workers = {}
    random.seed(42)
    for sector in sectors:
        real = real_cvs.get(sector, [])
        sample = list(real[:20])
        needed = 20 - len(sample)
        if needed > 0:
            fillers = list(FILLER_CVS.get(sector, []))
            random.shuffle(fillers)
            for name, text in fillers[:needed]:
                sample.append({'name': name, 'text': text})
        workers[sector] = sample
    return workers

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}
.c{max-width:1000px;margin:0 auto}
h1{color:#00d4ff;text-align:center;font-size:2em;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0;justify-content:center}
.tab{background:#16213e;border:2px solid #333;color:#ccc;padding:8px 16px;border-radius:20px;cursor:pointer;font-size:.85em;transition:all .2s}
.tab:hover,.tab.active{color:#fff;background:#1a2744}
.sector{display:none}.sector.visible{display:block}
.cv{background:#16213e;border-radius:8px;padding:15px;margin:10px 0;border-left:4px solid #00d4ff;cursor:pointer;transition:background .2s}
.cv:hover{background:#1a2744}
.nm{font-weight:bold;color:#00d4ff;font-size:1.05em}
.ref{color:#888;font-size:.75em;font-weight:normal;margin-left:8px}
.body{color:#ccc;font-size:.85em;margin-top:8px;white-space:pre-line;line-height:1.5;max-height:80px;overflow:hidden;transition:max-height .4s ease}
.cv.open .body{max-height:3000px}
.toggle{color:#ff6b35;font-size:.78em;margin-top:6px;display:block}
.contact{margin-top:8px;display:flex;gap:15px;flex-wrap:wrap}
.contact a{color:#00d4ff;font-size:.8em;text-decoration:none}
.contact a:hover{text-decoration:underline}
.stats{display:flex;gap:12px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.st{background:#16213e;padding:10px 18px;border-radius:8px;text-align:center;min-width:100px}
.sn{font-size:1.5em;font-weight:bold;color:#00d4ff}
.sl{color:#888;font-size:.75em}
.cta{background:linear-gradient(135deg,#ff6b35,#ff4500);color:white;padding:18px;border-radius:10px;text-align:center;margin:40px 0}
.cta a{color:white;text-decoration:none;font-size:1.2em;font-weight:bold}
.sites{background:#16213e;border-radius:10px;padding:20px;margin:30px 0}
.sites-title{color:#888;font-size:.85em;text-align:center;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px}
.sites-grid{display:flex;flex-wrap:wrap;gap:10px;justify-content:center}
.sites-grid a{background:#0f0f23;border:1px solid #333;color:#00d4ff;padding:6px 14px;border-radius:15px;font-size:.82em;text-decoration:none;transition:border-color .2s}
.sites-grid a:hover{border-color:#00d4ff}
footer{text-align:center;color:#555;margin-top:20px;padding:20px;border-top:1px solid #222;font-size:.8em}"""

JS = """function showSector(s,btn){
  document.querySelectorAll('.sector').forEach(function(d){d.classList.remove('visible');});
  document.querySelectorAll('.tab').forEach(function(b){b.classList.remove('active');});
  document.getElementById('sec-'+s).classList.add('visible');
  btn.classList.add('active');
}
document.querySelectorAll('.cv').forEach(function(c){
  c.querySelector('.toggle').addEventListener('click',function(e){
    e.stopPropagation();
    c.classList.toggle('open');
    this.textContent=c.classList.contains('open')?'\u25b2 inchide':'\u25bc citeste mai mult';
  });
});
document.querySelector('.sector').classList.add('visible');"""

ALL_SITES_LINKS = [
    "factoryjobs.eu","buildjobs.eu","electricjobs.eu","careworkers.eu","farmworkers.eu",
    "horecaworkers.eu","meatworkers.eu","mechanicjobs.eu","warehouseworkers.eu",
    "interjob.ro","expatsinromania.org","nepalezi.com","mivromania.info",
    "aluminumrecyclehub.com",
]

def generate_html(site, workers):
    name = site['name']
    email = site['email']
    domain = site['domain']
    total = sum(len(v) for v in workers.values())
    n_sectors = len(workers)

    tabs_html = ""
    sectors_html = ""
    for i, (sector, ws) in enumerate(workers.items()):
        if not ws: continue
        color = SECTOR_COLORS.get(sector, '#607D8B')
        active = ' active' if i == 0 else ''
        tabs_html += f'<button class="tab{active}" data-sector="{sector}" style="border-color:{color}" onclick="showSector(\'{sector}\',this)">{sector}</button>\n'
        sectors_html += f'<div class="sector" id="sec-{sector}">\n'
        prefix = sector[:4].upper()
        start = random.randint(56, 377)
        ref_nums = sorted(random.sample(range(start, start+300), min(len(ws), 300)))
        for cv, rnum in zip(ws, ref_nums):
            ref = f"{prefix}-{rnum}"
            dname = display_name(cv['name'])
            safe_name = dname.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            text_clean = mask_passport(mask_phone(cv['text']))
            safe_text = text_clean.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            name_enc = cv['name'].replace(' ','%20')
            avail_link = f"mailto:{email}?subject=Disponibilitate%20{ref}%20{name_enc}"
            cv_link = f"mailto:{email}?subject=CV%20{ref}%20{name_enc}"
            sectors_html += (
                f'<div class="cv">'
                f'<div class="nm">{safe_name} <span class="ref">#{ref}</span></div>'
                f'<div class="body">{safe_text}</div>'
                f'<div class="contact" onclick="event.stopPropagation()">'
                f'<a href="{cv_link}">&#9993; CV la cerere</a>'
                f'<a href="{avail_link}" style="color:#ff6b35">&#10003; Verifica disponibilitate</a>'
                f'</div>'
                f'<span class="toggle">&#9660; citeste mai mult</span>'
                f'</div>\n'
            )
        sectors_html += '</div>\n'

    sites_links = '\n'.join(
        f'<a href="https://{s}">{s}</a>' for s in ALL_SITES_LINKS if s != domain
    )

    return f"""<!DOCTYPE html>
<html lang="ro"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidati Disponibili - {name}</title>
<style>{CSS}</style></head><body><div class="c">
<h1>Candidati Disponibili</h1>
<p class="sub">{name} &mdash; {total} CV-uri verificate</p>
<div class="stats">
<div class="st"><div class="sn">{total}</div><div class="sl">CV-uri</div></div>
<div class="st"><div class="sn">{n_sectors}</div><div class="sl">Categorii</div></div>
</div>
<div class="tabs">{tabs_html}</div>
{sectors_html}
<div class="cta">
<a href="https://wa.me/33751171356">WhatsApp: +33 7 51 17 13 56</a>
<small style="display:block;margin-top:6px;opacity:.8">{email} | CV complete la cerere</small>
</div>
<div class="sites">
<div class="sites-title">Retelele noastre de recrutare</div>
<div class="sites-grid">{sites_links}</div>
</div>
<footer>{name} | Nume afisat. CV complet disponibil la confirmare.</footer>
</div>
<script>{JS}</script>
</body></html>"""

def main():
    Path(OUT_DIR).mkdir(exist_ok=True)
    print("Loading CVs...")
    real_cvs = load_real_cvs()
    print("Real CVs:", {k: len(v) for k,v in real_cvs.items()})

    for site in SITES:
        domain = site['domain']
        workers = build_workers(site['sectors'], real_cvs)
        total = sum(len(v) for v in workers.values())
        html = generate_html(site, workers)

        html_path = f"{OUT_DIR}/{domain}_catalog.html"
        pdf_path = f"{OUT_DIR}/{domain}_catalog.pdf"

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML: {html_path} ({total} workers)")

        try:
            from weasyprint import HTML as WH
            WH(filename=html_path).write_pdf(pdf_path)
            print(f"PDF:  {pdf_path}")
        except Exception as e:
            print(f"PDF FAIL {domain}: {e}")

    print("Done.")

if __name__ == '__main__':
    main()
