# MyLosungData

Dieses Repository enthält die Datensätze für das Projekt **[MyLosung](file:///home/jkamlah/Coding/private/MyLosung)** (`/home/jkamlah/Coding/private/MyLosung`).

## Skripte & Werkzeuge

### 1. Bibelstellen & Links für alle 60 Bibleserver-Übersetzungen (`bibleserver_passages.py`)
Nimmt die deutsche Basisausgabe (**LUT** / Lutherbibel 2017) aus `<Jahr>/LUT/text/` und ermittelt für alle 365 Tage die entsprechenden Bibelstellen und Links auf [ERF Bibleserver](https://www.bibleserver.com/webmasters) für alle **60 Übersetzungen** (23 Sprachen):

* **Direktlink**: `https://www.bibleserver.com/{Übersetzung}/{Bibelstelle}` (z. B. `https://www.bibleserver.com/ESV/Isaiah25:8`)
* **LUT-Vergleichslink**: `https://www.bibleserver.com/LUT.{Übersetzung}/{Bibelstelle}` (z. B. `https://www.bibleserver.com/LUT.ESV/Jesaja25,8`)

**Verwendung:**
```bash
# Gesamtes Jahr verarbeiten und bibleserver_passages.json generieren:
python3 bibleserver_passages.py 2026

# Einzelne Bibelstelle interaktiv über alle 60 Übersetzungen abfragen:
python3 bibleserver_passages.py --query "Jesaja 25,8"

# Bestimmtes Datum abfragen:
python3 bibleserver_passages.py --date 2026-01-01 --translation ESV
```

### 2. Englische KJV-Ausgabe & Audio-Generierung (`generate_losungen.py`)
Erzeugt aus der deutschen Vorlage eine englische KJV-XML-Datei (Passagenabruf von [die-bibel.de](https://www.die-bibel.de/bibel/KJV)) und bietet optional die Erstellung von Audio-Dateien via Gemini TTS API.

**Verwendung:**
```bash
# Englische KJV-XML generieren:
python3 generate_losungen.py 2026

# Audio-Dateien mit Gemini API erzeugen:
python3 generate_losungen.py 2026 --api-key YOUR_KEY --generate-audio --days 5
```

## Nutzungsbedingungen & Urheberrecht

Die in diesem Repository enthaltenen Losungsdaten basieren auf den offiziellen Daten der Evangelischen Brüder-Unität – Herrnhuter Brüdergemeine und unterliegen den folgenden Nutzungsbedingungen ([NUTZUNGSBEDINGUNGEN November 2023.pdf](file:///home/jkamlah/Coding/private/MyLosungData/2026/de/text/NUTZUNGSBEDINGUNGEN%20November%202023.pdf)):

---

### NUTZUNGSBEDINGUNGEN
**für die Verwendung der Losungen im Internet und für Desktop-Freeware Programme** (Stand: November 2023)

> Die Losungen der Herrnhuter Brüdergemeine sind urheberrechtlich geschützt. Inhaberin des Urheberrechts ist die Evangelische Brüder-Unität – Herrnhuter Brüdergemeine.  
> Die Bibeltexte aus der Lutherbibel, revidiert 2017, und aus der Lutherbibel, revidierte Texte 1984, durchgesehene Ausgabe in neuer Rechtschreibung, unterliegt dem Copyright der Deutschen Bibelgesellschaft, Stuttgart.

Die Veröffentlichung der Losungen auf Websites und die Erstellung und Weitergabe von Losungs-Freeware-Programmen ist zu den nachstehenden Nutzungsbedingungen mit freundlicher Genehmigung der Evangelischen Brüder-Unität – Herrnhuter Brüdergemeine und der Deutschen Bibelgesellschaft möglich:

- **Name & Plattformbeschränkung**: Die Losungen dürfen ausschließlich unter dem Namen »Die Losungen« auf Internet-Seiten sowie in Freeware-Programmen für PCs/Desktops genutzt werden. Die Bereitstellung von Freeware-Programmen für mobile Endgeräte (Apps für Smartphone, Tablet, Handy) ist nicht gestattet. Alle Veröffentlichungen der Losungen erfolgen für den Nutzer kostenlos. Sogenannte InApp-Käufe sind nicht erlaubt. Diese Gestattung gewährt ein nicht ausschließliches Recht, welches jederzeit widerrufen werden kann.
- **Vollständige Textanzeige**: Die Anzeige der Losungstexte besteht immer aus beiden Bibelversen, dem alttestamentlichen Text (der Losungsvers) und dem neutestamentlichen Vers (dem Lehrtext).
- **Datenquelle & Keine Änderungen**: Es dürfen nur die auf der Internetseite [www.losungen.de](https://www.losungen.de) angebotenen Daten verwendet werden. Änderungen an den Losungstexten und den Stellenangaben sind nicht gestattet. Insbesondere die im Losungsbuch veröffentlichten dritten Texte, die den beiden Bibeltexten zugeordnet sind, unterliegen eigenen Lizenzvereinbarungen und dürfen deshalb für elektronische Weiterverarbeitung im Freeware-Bereich nicht verwendet werden.
- **Gültigkeitszeitraum**: Auf Internetseiten und in Losungs-Freeware-Programmen dürfen jeweils nur die Losungstexte des laufenden Jahres sowie die des dem laufenden Jahr vorangehenden und nachfolgenden Jahres bereitgestellt werden.
- **Nicht-kommerzielle Nutzung**: Auf Internet-Seiten, die auch kommerziellen Zwecken dienen, sowie in Software, die entgeltlich angeboten wird, dürfen die Losungen nicht verwendet werden. Gleiches gilt für Internetseiten und Softwareprogramme, deren Inhalt geeignet ist, das Ansehen der Evangelischen Kirche und der Evangelischen Brüder-Unität – Herrnhuter Brüdergemeine herabzusetzen.
- **Sondervereinbarungen**: Anwendungen außerhalb dieser Nutzungsbedingungen bedürfen einer gesonderten Vereinbarung mit der Evangelischen Brüder-Unität – Herrnhuter Brüdergemeine.
- **Meldepflicht**: Bei Fertigstellung einer Internetveröffentlichung ist ein entsprechender Link oder im Falle eines Losungs-Freeware-Programms eine Kopie bzw. der Downloadlink an die unten genannte Adresse der Evangelischen Brüder-Unität – Herrnhuter Brüdergemeine zu übersenden.
- **Pflicht-Copyright-Hinweis**: Bei allen Veröffentlichungen der Losungen ist folgender gut sichtbarer Hinweis auf den Copyrightschutz der Losungen hinzuzufügen:
  > »© Evangelische Brüder-Unität – Herrnhuter Brüdergemeine« (mit Link auf [www.herrnhuter.de](https://www.herrnhuter.de)) sowie »Weitere Informationen finden Sie hier.« (mit Link auf [www.losungen.de](https://www.losungen.de))

#### Kontakt & Herausgeber
**Evangelische Brüder-Unität Herrnhut**  
Zittauer Str. 20, 02747 Herrnhut  
Telefon: 035873 487-0 | Fax: 035873 487-99  
E-Mail: support@losungen.de | Internet: [www.herrnhuter.de](https://www.herrnhuter.de)
