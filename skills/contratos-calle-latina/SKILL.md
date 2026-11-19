---
name: contratos-calle-latina
description: Use when asked for Calle Latina Records contracts.
---

# Contratos Calle Latina Records

Genera el contrato estándar AUTHOR/COMPOSER de Calle Latina Records (en inglés, PDF, 2 páginas) para uno o muchos artistas a partir de datos en texto libre.

## Regla principal: solo cambian estos campos

| Dato | Campo JSON | Regla |
|---|---|---|
| Fecha del contrato | `date` | Opcional, `YYYY-MM-DD`. Si el usuario no la da, omitir el campo: el script usa la fecha de hoy en America/Santiago. Fechas tipo `05/03/2026` son día/mes/año. |
| Nombre del artista | `artist_name` | Textual. |
| Dirección | `address` | Textual. |
| RUT / DNI / cédula | `id_number` | Textual, tal cual lo escribe el usuario (no reformatear puntos ni guion). |
| Tracks (1..n) | `tracks: [{"title", "type"}]` | En el orden dado. `title` textual. |

Todo lo demás (partes, cláusulas, porcentajes, montos, redacción) es texto fijo dentro del script y no se toca nunca. La redacción se corrigió una vez en nov 2026 (pago el 30 de noviembre, "assigns", RECORD LABEL en vez de PUBLISHER, "its capacity", "both the lyrics and the music", typos); cualquier cambio posterior también va como actualización de este skill.

- Los datos variables se copian tal cual: no traducir al inglés nombres, direcciones ni títulos; no corregir ortografía ni mayúsculas.
- Si el usuario pide cambiar una cláusula, un porcentaje o cualquier texto fijo, no lo hagas en un contrato puntual: es un cambio de plantilla. Avísale y propón una actualización de este skill (editar el script embebido).

## Flujo

1. **Parsear** el texto libre a `contracts.json` (lista JSON, un objeto por contrato, en el orden en que el usuario los entrega).
   - Track sin `type`: usar `"Original"` y marcarlo como *asumido* en el resumen.
   - Falta nombre, ID, dirección o título de algún track: no inventar. Dejar el campo vacío; el script rechaza ese contrato y genera el resto.
2. **Escribir el script** de la sección "Script" con Write a `calle_latina_contracts.py` en el directorio de trabajo, copiado exacto, sin "mejorarlo". Requiere python3, `reportlab`, `pypdf` y la fuente Carlito (equivalente métrico de Calibri; si falta usa Helvetica y lo avisa).
3. **Ejecutar**: `python3 calle_latina_contracts.py contracts.json out/`. Imprime un JSON con `zip` y, por contrato, `status` (`ok`/`rejected`), `file`, `date`, `pages`, `warnings`/`errors`. Exit 1 = hubo rechazados (los válidos igual se generan).
4. **Verificar**: abrir con Read la página 1 de al menos un PDF (y la del contrato con más tracks) para confirmar que los datos quedaron bien puestos.
5. **Entregar** con SendUserFile: hasta 3 contratos, los PDFs individuales; más de 3, solo el `.zip`. Responder en español con una tabla `# | Artista | ID | Tracks | Fecha | Avisos` y nada más que lo relevante:
   - RUT con dígito verificador inválido (solo se valida si el ID tiene formato RUT con DV; DNI y cédulas extranjeras no se validan).
   - Type asumido como Original.
   - Interlineado comprimido: con muchos tracks el script reduce el espaciado (nunca la fuente ni el texto) para mantener 2 páginas. Caben ~12 tracks.
   - Más de 2 páginas: el contrato dice "which consists of two pages", así que preguntar al usuario cómo seguir (por ejemplo, dividir los tracks en dos contratos).
   - Rechazados: qué dato falta, para que el usuario lo complete.

## Ejemplo

Entrada: "Ana Pérez, ID 12.345.678, Calle Falsa 123, Rosario, Santa Fe, Argentina, fecha 1/12/2025. Tracks: Tema uno (Original), Tema dos (Original)"

```json
[{"date": "2025-12-01", "artist_name": "Ana Pérez", "id_number": "12.345.678",
  "address": "Calle Falsa 123, Rosario, Santa Fe, Argentina",
  "tracks": [{"title": "Tema uno", "type": "Original"}, {"title": "Tema dos", "type": "Original"}]}]
```

## Script

```python
#!/usr/bin/env python3
"""Calle Latina Records - author/composer contract generator (English, PDF).

Usage:
    python3 calle_latina_contracts.py contracts.json OUT_DIR

contracts.json is a JSON list. Each item:
    {
      "date": "YYYY-MM-DD",            # optional -> today (America/Santiago)
      "artist_name": "Ana Pérez",
      "id_number": "12.345.678",       # RUT / DNI / cedula, printed exactly as given
      "address": "Calle Falsa 123, Rosario, Santa Fe, Argentina",
      "tracks": [{"title": "Tema uno", "type": "Original"}, ...]   # 1..n
    }

Only those fields vary. Every other word of the contract is fixed in this file
and must not be edited per contract.

Prints a JSON report to stdout (files, pages, warnings) and writes one PDF per
contract plus a .zip with all of them into OUT_DIR. Exit code 1 if any contract
was rejected (the valid ones are still generated).
"""
import datetime as dt
import json
import os
import re
import sys
import unicodedata
import zipfile
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

# ---------------------------------------------------------------- fonts ----
FONT_DIRS = ["/usr/share/fonts/truetype/crosextra", "/usr/share/fonts/truetype/carlito",
             os.path.expanduser("~/.fonts"), "/usr/share/fonts/truetype"]
FONT_FILES = {"R": "Carlito-Regular.ttf", "B": "Carlito-Bold.ttf",
              "I": "Carlito-Italic.ttf", "BI": "Carlito-BoldItalic.ttf"}


def register_fonts():
    """Carlito = metric-compatible Calibri (the original font). Fallback Helvetica."""
    found = {}
    for key, fname in FONT_FILES.items():
        for d in FONT_DIRS:
            p = os.path.join(d, fname)
            if os.path.exists(p):
                found[key] = p
                break
    if len(found) == 4:
        for key, p in found.items():
            pdfmetrics.registerFont(TTFont("Body-" + key, p))
        pdfmetrics.registerFontFamily("Body", normal="Body-R", bold="Body-B",
                                      italic="Body-I", boldItalic="Body-BI")
        return "Body-R", None
    return "Helvetica", "Carlito font not found; used Helvetica (layout may differ from the original)"


# ---------------------------------------------------------------- helpers --
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def today_santiago():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Santiago")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=3)).date()


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def e(s):
    return escape(clean(s))


def slug(s):
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "artist"


def rut_warning(id_number):
    """Only for Chilean RUT-looking IDs (with check digit). DNI/cedula untouched."""
    m = re.fullmatch(r"(\d{1,2}\.?\d{3}\.?\d{3})-([\dkK])", id_number)
    if not m:
        return None
    body = m.group(1).replace(".", "")
    total, mult = 0, 2
    for d in reversed(body):
        total += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    dv = 11 - total % 11
    expected = "0" if dv == 11 else "K" if dv == 10 else str(dv)
    if m.group(2).upper() != expected:
        return f"RUT {id_number}: check digit should be {expected}"
    return None


def validate(c, i):
    errors, warnings = [], []
    for f in ("artist_name", "id_number", "address"):
        if not clean(c.get(f)):
            errors.append(f"missing {f}")
    tracks = c.get("tracks") or []
    if not tracks:
        errors.append("at least one track is required")
    for n, t in enumerate(tracks, 1):
        if not clean(t.get("title")):
            errors.append(f"track {n}: missing title")
        if not clean(t.get("type")):
            errors.append(f"track {n}: missing type")
    if c.get("date"):
        try:
            dt.date.fromisoformat(clean(c["date"]))
        except ValueError:
            errors.append(f"invalid date {c['date']!r} (use YYYY-MM-DD)")
    if clean(c.get("id_number")):
        w = rut_warning(clean(c["id_number"]))
        if w:
            warnings.append(w)
    return errors, warnings


# ---------------------------------------------------------------- layout ---
def styles(font, leading=11):
    base = ParagraphStyle("base", fontName=font, fontSize=9, leading=leading,
                          alignment=TA_LEFT, rightIndent=48, spaceAfter=0, spaceBefore=0,
                          allowWidows=0, allowOrphans=0)
    return {
        "L": base,
        "J": ParagraphStyle("J", parent=base, alignment=TA_JUSTIFY),
        "W": ParagraphStyle("W", parent=base, rightIndent=0),          # full width
        "R": ParagraphStyle("R", parent=base, alignment=TA_RIGHT, rightIndent=0),
    }


def build_story(c, font, leading=11, blank=12):
    S = styles(font, leading)
    GAP = object()                      # blank line before the next paragraph
    gap = lambda: GAP
    P = lambda txt, st="L": Paragraph(txt, S[st])

    d = dt.date.fromisoformat(clean(c["date"])) if c.get("date") else today_santiago()
    date_txt = f"<i>Santiago, Chile</i>, {d.day:02d} of <i>{MONTHS[d.month - 1]} {d.year}</i>"

    story = [P(date_txt, "R"), gap(),
             P("<b>PARTIES</b>"),
             P("From one side <b><i>Calle Latina Records</i></b> in its capacity as music publisher, "
               "represented by<br/><b><i>Matias Menafra and Juan David Garzon</i></b>, and from now on "
               "called RECORD LABEL."),
             gap(),
             P(f"And from another part <b>{e(c['artist_name'])}</b> with <b>ID: {e(c['id_number'])}</b>, "
               f"domiciled at <b>{e(c['address'])}</b>, and also and hereafter called AUTHOR.", "W"),
             gap(),
             P("Both parties mutually acknowledge the legal capacity necessary to enter into this "
               "contract and state the<br/>following:"),
             P("That the AUTHOR in his capacity as AUTHOR/COMPOSER is the holder of full ownership of "
               "the musical work called:"),
             gap()]

    for t in c["tracks"]:
        story += [KeepTogether([P(f"<b>Title of the work</b>: {e(t['title'])}"),
                                P(f"<b>Type:</b> {e(t['type'])}")]), gap()]

    story += [
        P("From now on referred to as COMPOSITION."), gap(),
        P("<b>STATEMENTS</b>"),
        P("The AUTHOR declares that the COMPOSITION does not infringe the Copyright of any work, "
          "affirming that it is not subject to any charge or encumbrance and is entitled to the free "
          "availability of it, as well as being fully empowered to enter into this contract and assign "
          "the rights that by the same are granted, so that it exonerates the RECORD LABEL from any "
          "claim that may arise as a result of the COMPOSITION.", "J"),
        gap(),
        P("Those rights that are collected by Management Companies will be paid directly by them to "
          "the holders, exempting the RECORD LABEL from all responsibility in this regard. In attention "
          "to the foregoing, both parties, by mutual agreement, enter into this contract under the "
          "following clauses:"),
        gap(),
        P("<b>FIRST:</b> The AUTHOR grants the RECORD LABEL his express consent to disclose and "
          "publish the COMPOSITION object of this contract."),
        gap(),
        P("<b>SECOND:</b> The AUTHOR assigns to the RECORD LABEL, with respect to the COMPOSITION, "
          "the exploitation rights in general of the same and in particular:"),
        P("a) The reproduction in graphic form and distribution (free or through consideration for "
          "sale, rental, etc.) of the printed copies."),
        P("b) That of reproduction by fixing the COMPOSITION on any mechanical, visual and/or sound "
          "support, as well as the public reproduction of said supports."),
        P("The right to compensatory remuneration is also included."),
        P("The right of inclusion (synchronization) of the complete or fragmented COMPOSITION in any "
          "audiovisual or sound support is also included."),
        P("c) The public communication of the COMPOSITION: representation and execution (for all "
          "means and procedures); the projection or exhibition from sound and/or audiovisual supports; "
          "the broadcast by radio or television (including the one carried out via telecommunication "
          "satellite or broadcasting); the wireless retransmission and public dissemination of the "
          "COMPOSITION broadcast or televised and the cable transmission of those same works.", "J"),
        P("Any type of data transmission (of all or part of the COMPOSITION) is included."),
        P("d) The transformation through literary adaptation, translation, arrangement and any other "
          "modification in its form, from which a different COMPOSITION is derived, including the "
          "authorization for the constitution of a compound COMPOSITION."),
        gap(),
        P("<b>THIRD:</b> The AUTHOR's moral right is reserved, which will be respected by the RECORD "
          "LABEL, which undertakes to demand that the third parties with whom it contracts safeguard "
          "such right.", "J"),
        gap(),
        P("<b>FOURTH:</b> The RECORD LABEL will exercise the rights granted in the worldwide "
          "territory, hereinafter called TERRITORY."),
        gap(),
        P("<b>FIFTH:</b> The DURATION of this contract is for ALL THE TIME OF PROTECTION granted to "
          "the authors, their successors and assigns, the current Laws and International "
          "Conventions, and those that are subsequently issued or agreed.", "J"),
        gap(),
        P("<b>SIXTH:</b> If the COMPOSITION object of this contract were made up of contributions "
          "from different authors and some of them belonged to different genres (literary and "
          "musical), however considered indivisible, the RECORD LABEL is empowered to use and "
          "authorize others to use separately, both the lyrics and the music of the COMPOSITION. All "
          "the authors of the COMPOSITION thus used will participate in the yields obtained in the "
          "proportion established in this contract.", "J"),
        gap(),
        P("<b>SEVENTH:</b> As consideration for the rights hereby assigned, the RECORD LABEL, in the "
          "exercise of its functions, is obliged to pay the AUTHOR the following percentages of the "
          "income obtained from the exploitation of the COMPOSITION:", "J"),
        P("seventy percent <b>(70%) for AUTHOR</b> and the remaining thirty percent <b>(30%) will "
          "correspond to the RECORD LABEL</b>."),
        P("In cases of the realization of a derivative work (remix) the amounts will be "
          "divided between forty percent <b>(40%) for the AUTHOR</b>; thirty percent <b>(30%) for the "
          "person who makes the remix</b> and thirty percent <b>(30%) for the RECORD "
          "LABEL</b>.", "J"),
        gap(),
        P("<b>EIGHTH:</b> The minimum amount of money required for the RECORD LABEL to settle the "
          "part corresponding to the AUTHOR will be <b>50 USD</b>, in such a way that if on the date "
          "of making the payment, the AUTHOR does not reach the minimum required, the payment will be "
          "postponed until this minimum is met.", "J"),
        gap(),
        P("<b>NINTH:</b> The corresponding settlements will be made by the RECORD LABEL to the AUTHOR "
          "twice a year, regardless of the date of signing the contract, on May 9 and November 30 of "
          "each year, being able to modify such dates by the RECORD LABEL, with prior notice to the "
          "AUTHOR.", "J"),
        gap(),
        P("<b>TENTH:</b> The AUTHOR authorizes the RECORD LABEL to register the COMPOSITION in the "
          "Copyright Registry of the countries covered by this contract, as well as the corresponding "
          "renewals, either in the name of the RECORD LABEL or the AUTHOR indistinctly, signing as many "
          "documents as are needed for it."),
        gap(),
        P("<b>ELEVENTH:</b> The assignment of the rights agreed herein does not cover the modalities of "
          "use or means of dissemination that do not exist or are unknown at the time of assignment. "
          "However, if in the future the RECORD LABEL wishes to exploit the rights by a new modality or "
          "by a new means currently unknown, it will duly communicate it to AUTHOR, understanding that "
          "it gives its full agreement, if within a period of fifteen calendar days it does not make "
          "any reservation.", "J"),
        gap(),
        P("<b>TWELFTH:</b> This contract will enter into force as of the date hereof, and will redound "
          "to the benefit of the interested parties and their successors and concessionaires."),
        gap(),
        P("<b>THIRTEENTH:</b> This contract may be elevated to a public deed at the request of either "
          "party, with the petitioner being responsible for all the expenses that this elevation may "
          "produce and provided that the other party consents voluntarily and freely.", "J"),
    ]

    sig = Table([[P("<i>----------------------------------</i>"),
                  P("<i>----------------------------------</i>")],
                 [P("Signature Author"), P("Signature Record Label")]],
                colWidths=[223, 245])
    sig.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 0),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 0.4)]))
    story.append(KeepTogether([
        P("The parties read and understand this contract, which consists of two pages, and sign it in "
          "the place and on the date indicated at the beginning of this contract, so that they accept "
          "the clauses and other provisions that appear in it."),
        Spacer(1, 56), sig]))
    return apply_gaps(story, GAP, blank), d


def apply_gaps(items, GAP, before=12):
    """Turn GAP markers into spaceBefore on the next paragraph. spaceBefore is dropped
    at the top of a page, so a page never starts with an empty line."""
    out, pending = [], False
    for it in items:
        if it is GAP:
            pending = True
            continue
        if pending:
            target = it._content[0] if isinstance(it, KeepTogether) else it
            target.style = ParagraphStyle(target.style.name + "+gap", parent=target.style,
                                          spaceBefore=before)
            pending = False
        out.append(it)
    return out


# Layout presets, tried in order until the contract fits in 2 pages (the text says
# "consists of two pages"). Only spacing changes; font size and wording never do.
LAYOUTS = [(11, 12), (11, 6), (10.5, 3)]


def render(c, out_dir, font, used_names):
    for leading, blank in LAYOUTS:
        path, pages, d = _render(c, out_dir, font, used_names, leading, blank)
        if pages <= 2:
            break
    else:  # does not fit even when tight: keep the normal spacing and warn
        leading, blank = LAYOUTS[0]
        path, pages, d = _render(c, out_dir, font, used_names, leading, blank)
    used_names.add(os.path.basename(path))
    return path, pages, d, (leading, blank) != LAYOUTS[0]


def _render(c, out_dir, font, used_names, leading, blank):
    story, d = build_story(c, font, leading, blank)
    name = f"Contract_{slug(c['artist_name'])}_{d.isoformat()}"
    fname, k = name + ".pdf", 2
    while fname in used_names:
        fname, k = f"{name}_{k}.pdf", k + 1
    path = os.path.join(out_dir, fname)
    doc = BaseDocTemplate(path, pagesize=letter,
                          title=f"Contract Calle Latina - {clean(c['artist_name'])}",
                          author="Calle Latina Records")
    frame = Frame(72, 72, 468, 648, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame])])
    doc.build(story)
    from pypdf import PdfReader
    pages = len(PdfReader(path).pages)
    return path, pages, d


# ---------------------------------------------------------------- main -----
def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as fh:
        contracts = json.load(fh)
    if isinstance(contracts, dict):
        contracts = [contracts]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    font, font_warn = register_fonts()

    report, files, used, failed = [], [], set(), False
    for i, c in enumerate(contracts, 1):
        errors, warnings = validate(c, i)
        entry = {"n": i, "artist": clean(c.get("artist_name")), "tracks": len(c.get("tracks") or [])}
        if errors:
            failed = True
            entry.update(status="rejected", errors=errors)
            report.append(entry)
            continue
        path, pages, d, compact = render(c, out_dir, font, used)
        if compact and pages <= 2:
            warnings.append("tighter line spacing used so the contract fits in two pages")
        if pages != 2:
            warnings.append(f"PDF has {pages} pages but the contract text says it 'consists of two pages'")
        if font_warn:
            warnings.append(font_warn)
        entry.update(status="ok", file=path, date=d.isoformat(), pages=pages, warnings=warnings)
        files.append(path)
        report.append(entry)

    if files:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        zpath = os.path.join(out_dir, f"Contracts_Calle_Latina_{stamp}.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, os.path.basename(f))
    else:
        zpath = None
    print(json.dumps({"zip": zpath, "contracts": report}, ensure_ascii=False, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
```